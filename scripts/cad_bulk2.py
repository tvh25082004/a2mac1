"""CAD downloader v2 - smarter than v1:
1) get-files (1 request) -> if 403 = server still locked, exit immediately
2) Prefer PACKAGE DOWNLOADS: POST /downloads {name, archiveIds:[], fileTokens:[...]} -> server zips -> GET /downloads/archives/{id}
3) Per-file fallback: test 4 token-encoding variants, pick the OK one, safe pace 0.7s/req
Guards: 500s time limit, stop when free disk < 1.5GB.
"""
import re, os, json, time, sys, shutil, threading, random
from pathlib import Path
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://ibp.a2mac1.com/api"
DATA = Path("/home/z/my-project/data")
OUT = DATA / "cad_files"
TIME_LIMIT = 500
START = time.time()

raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
S = requests.Session()
S.headers.update(H)

def left():
    return TIME_LIMIT - (time.time() - START)

def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}|{left():.0f}s left]", *a, flush=True)

def sanitize(s, maxlen=70):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip())[:maxlen].strip("_") or "part"

def disk_ok():
    return shutil.disk_usage("/home/z/my-project").free > 1.5e9

def get_files(pid, hid="00000003LSK4EU01"):
    r = S.post(f"{BASE}/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False}, timeout=60)
    log(f"get-files {pid[-6:]}/{hid[:6]}: HTTP {r.status_code}")
    if r.status_code != 200 or not r.text.strip():
        return None
    return r.json()

def try_composite(pid, recs, folder):
    """POST /downloads bundles many fileTokens into 1 server-side zip."""
    tokens = [r["token"] for r in recs if r.get("token")]
    if not tokens:
        return False
    for name, body in [
        ("full", {"name": f"cad_{pid[-10:]}", "archiveIds": [], "fileTokens": tokens}),
        ("chunks-500", None),
    ]:
        try:
            if body is None:
                log("composite full failed -> trying chunk 500")
                return any(try_composite_chunk(pid, tokens[i:i+500], folder, i)
                           for i in range(0, len(tokens), 500))
            r = S.post(f"{BASE}/downloads", json=body, timeout=120)
            log(f"POST /downloads ({name}, {len(tokens)} token): HTTP {r.status_code} ct={r.headers.get('content-type','')[:40]}")
            if r.status_code in (200, 201, 202) and r.content:
                ct = r.headers.get("content-type", "")
                if "json" in ct:
                    j = r.json()
                    aid = j.get("id") or j.get("archiveId") or j.get("downloadId")
                    log(f"  JSON -> id={aid}, keys={list(j)[:8]}")
                    if aid:
                        return fetch_archive(aid, folder)
                elif "zip" in ct or r.content[:2] == b"PK":
                    (folder / "cad_package.zip").write_bytes(r.content)
                    log(f"  direct ZIP: {len(r.content)/1e6:.1f}MB -> cad_package.zip")
                    return True
        except Exception as e:
            log(f"  composite {name}: EXC {type(e).__name__} {str(e)[:90]}")
    return False

def try_composite_chunk(pid, tokens, folder, idx):
    try:
        r = S.post(f"{BASE}/downloads", json={"name": f"cad_{pid[-10:]}_{idx}", "archiveIds": [], "fileTokens": tokens}, timeout=120)
        log(f"  chunk {idx} ({len(tokens)} token): HTTP {r.status_code}")
        if r.status_code in (200, 201, 202):
            ct = r.headers.get("content-type", "")
            if "json" in ct:
                j = r.json()
                aid = j.get("id") or j.get("archiveId") or j.get("downloadId")
                if aid:
                    return fetch_archive(aid, folder)
            elif r.content[:2] == b"PK":
                (folder / f"cad_package_{idx}.zip").write_bytes(r.content)
                return True
    except Exception as e:
        log(f"  chunk {idx}: EXC {type(e).__name__} {str(e)[:80]}")
    return False

def fetch_archive(aid, folder):
    r = S.get(f"{BASE}/downloads/archives/{aid}", timeout=(10, 300))
    log(f"GET /downloads/archives/{aid}: HTTP {r.status_code} {len(r.content)/1e6:.1f}MB")
    if r.status_code == 200 and r.content[:2] == b"PK":
        (folder / "cad_package.zip").write_bytes(r.content)
        return True
    return False

def test_variants(rec):
    ftok = rec["token"]
    furl = f"{BASE}/files/downloads/files"
    for name, url, kw in [
        ("A params=%raw", furl, {"params": {"token": ftok, "api-version": "1.1"}}),
        ("B verbatim-URL", f"{furl}?token={ftok}&api-version=1.1", {}),
        ("C unquote+params", furl, {"params": {"token": unquote(ftok), "api-version": "1.1"}}),
        ("D unquote-URL", f"{furl}?token={unquote(ftok)}&api-version=1.1", {}),
    ]:
        try:
            r = S.get(url, timeout=(10, 60), **kw)
            magic = r.content[:6] if r.content else b""
            log(f"  {name}: HTTP {r.status_code} {len(r.content)}B magic={magic} ct={r.headers.get('content-type','')[:36]}")
            if r.status_code == 200 and len(r.content) > 1000:
                return name, url, kw
        except Exception as e:
            log(f"  {name}: EXC {type(e).__name__}")
    return None

def sniff_ext(h, ct=""):
    if h[:2] == b"JT": return ".jt"
    if h[:5] == b"solid": return ".stl"
    if h[:2] == b"PK": return ".zip"
    if b"\nv " in h[:300]: return ".obj"
    return ".bin"

def per_file(recs, folder, variant):
    ok = err = nb = 0
    entries = []
    pace = [time.time()]
    def dl(it):
        time.sleep(random.uniform(0.5, 0.9))
        try:
            if variant == "A params=%raw":
                r = S.get(f"{BASE}/files/downloads/files", params={"token": it["token"], "api-version": "1.1"}, timeout=(10, 120))
            elif variant == "B verbatim-URL":
                r = S.get(f"{BASE}/files/downloads/files?token={it['token']}&api-version=1.1", timeout=(10, 120))
            elif variant == "C unquote+params":
                r = S.get(f"{BASE}/files/downloads/files", params={"token": unquote(it["token"]), "api-version": "1.1"}, timeout=(10, 120))
            else:
                r = S.get(f"{BASE}/files/downloads/files?token={unquote(it['token'])}&api-version=1.1", timeout=(10, 120))
        except Exception:
            return None
        return r if (r.status_code == 200 and r.content) else r.status_code
    with ThreadPoolExecutor(3) as ex:
        futs = {ex.submit(dl, it): it for it in recs}
        for i, fut in enumerate(as_completed(futs), 1):
            if left() < 30 or not disk_ok():
                for f in futs: f.cancel()
                break
            it = futs[fut]
            try:
                r = fut.result()
            except Exception:
                err += 1; continue
            if not isinstance(r, requests.Response):
                if r == 403: log(f"  403 at file {i} -> stop, cooldown needed")
                err += 1; continue
            ext = sniff_ext(r.content[:300], r.headers.get("content-type", ""))
            fn = f"{it['id']}__{sanitize(it.get('name') or it.get('partId'), 50)}{ext}"
            (folder / fn).write_bytes(r.content)
            ok += 1; nb += len(r.content)
            entries.append({"file": fn, "id": it["id"], "part": it.get("partId"), "name": it.get("name"),
                            "label": it.get("label"), "size": len(r.content)})
            if i % 100 == 0:
                log(f"  {ok}/{len(recs)} file, {nb/1e6:.0f}MB")
    entries.sort(key=lambda e: e["file"])
    return ok, err, nb, entries

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prog_path = DATA / "cad_progress.json"
    prog = json.loads(prog_path.read_text()) if prog_path.exists() else {}
    cars = json.load(open(DATA / "cad_priority.json"))
    CN = {'AITO','Aion','Aiways','Avatr','BAIC','BYD','Baojun','Changan','Chery','Denza','Exeed','GAC','Geely','Haval','IM','Jaecoo','Leapmotor','Li','Luxeed','Lynk','MG','Maxus','NIO','Onvo','Roewe','Voyah','WEY','Zeekr','Wuling','Hongqi','Bestune','Deepal','Dongfeng','XPeng','Xiaomi','JAC','Forthing','Venucia','Arcfox','Rising','HiPhi','Seres','iCAR','Soueast','Haima','Kaiyi','Foton','Zhiji','Wey'}
    queue = [c for c in cars if c["name"].split()[0] in CN or c["name"].lower().startswith("vinfast")]
    log(f"Queue {len(queue)} vehicles | token exp in {round((1794384887-time.time())/60,1) if '1794384887' in open('/home/z/my-project/scripts/cad_bulk.py').read() else '?'}")
    for ci, car in enumerate(queue):
        if left() < 90 or not disk_ok():
            log(f"STOP: time/disk"); break
        pid, name = car["id"], car["name"]
        brand = "VinFast" if name.lower().startswith("vinfast") else name.split()[0]
        folder = OUT / sanitize(brand, 30) / f"{sanitize(name, 80)}__{pid[-10:]}"
        folder.mkdir(parents=True, exist_ok=True)
        recs = get_files(pid)
        if not recs:
            log(f"[{ci}] {name}: could not get file list (403/no data) -> end session")
            prog[pid] = {"name": name, "files": 0, "status": "blocked-or-empty"}
            prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
            break
        recs = [r for r in recs if r.get("token")]
        seen, uniq = set(), []
        for r in recs:
            if r["id"] not in seen:
                seen.add(r["id"]); uniq.append(r)
        recs = uniq
        log(f"[{ci}] {name}: {len(recs)} unique files")
        # 1) composite
        t0 = time.time()
        comp = try_composite(pid, recs, folder)
        if comp:
            z = folder / "cad_package.zip"
            if z.exists():
                prog[pid] = {"name": name, "files": len(recs), "bytes": z.stat().st_size,
                             "status": "composite-zip", "mode": "package"}
                prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
                log(f"[{ci}] {name}: DONE as package {z.stat().st_size/1e6:.1f}MB ({time.time()-t0:.0f}s)")
                continue
        # 2) per-file
        log("composite unavailable -> test URL variants on 1 file")
        v = test_variants(recs[0])
        if not v:
            log("no variant downloadable -> stop (need new token/cooldown)")
            prog[pid] = {"name": name, "files": 0, "status": "download-blocked"}
            prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
            break
        ok, err, nb, entries = per_file(recs, folder, v[0])
        (folder / "manifest.json").write_text(json.dumps(
            {"product": pid, "name": name, "expected": len(recs), "downloaded": ok,
             "errors": err, "bytes": nb, "mode": "per-file", "variant": v[0],
             "status": "done" if ok == len(recs) else "partial", "files": entries}, ensure_ascii=False))
        prog[pid] = {"name": name, "files": ok, "bytes": nb, "status": "done" if ok == len(recs) else "partial"}
        prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
        log(f"[{ci}] {name}: {ok}/{len(recs)} files {nb/1e6:.1f}MB ({time.time()-t0:.0f}s)")
    tot = sum(p.get("bytes", 0) for p in prog.values())
    log(f"SESSION FINISHED: {sum(p.get('files',0) for p in prog.values())} files, {tot/1e6:.0f}MB, {len(prog)} vehicles")

if __name__ == "__main__":
    main()
