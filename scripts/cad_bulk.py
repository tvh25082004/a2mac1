"""Bulk-download 3D/CAD files for priority vehicles (VinFast first, then Chinese brands).
Per vehicle: GET packages -> POST get-files -> download each file via /files/downloads/files?token=
Resumable, anti-403 (pacing + backoff), disk + time limits. Output: data/cad_files/
"""
import re, os, json, time, sys, shutil, threading, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://ibp.a2mac1.com/api"
DATA = Path("/home/z/my-project/data")
OUT = DATA / "cad_files"
TIME_LIMIT = 540          # seconds - self-stop before the tool call dies
DISK_MIN_FREE = 1.2e9     # stop when free < 1.2GB
WORKERS = 5
PACE = 0.22               # minimum gap between 2 requests (global)
START = time.time()

raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}

S = requests.Session()
S.headers.update(H)
ad = S.get_adapter("https://")
ad.max_retries = 1

_lock = threading.Lock()
_pace = [time.time()]
_throttle = [PACE]
_stat403 = [0]

def paced_get(url, **kw):
    with _lock:
        gap = _throttle[0] + random.uniform(0, 0.06)
        wait = _pace[0] + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _pace[0] = time.time()
    r = S.get(url, timeout=(10, 120), **kw)
    if r.status_code == 403:
        with _lock:
            _stat403[0] += 1
            _throttle[0] = min(1.0, _throttle[0] + 0.25)
    else:
        with _lock:
            _stat403[0] = 0
    return r

def paced_post(url, **kw):
    with _lock:
        gap = _throttle[0] + random.uniform(0, 0.06)
        wait = _pace[0] + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _pace[0] = time.time()
    return S.post(url, timeout=(10, 90), **kw)

def sanitize(s, maxlen=70):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip())[:maxlen].strip("_") or "part"

def sniff_ext(head: bytes, ctype: str) -> str:
    if head[:2] == b"JT": return ".jt"
    if head[:5] == b"solid" or (b"endsolid" in head[:400]): return ".stl"
    if head[:2] == b"PK": return ".zip"
    if b"\nv " in head[:300] or head[:2] == b"v ": return ".obj"
    if head[:4] == b"Ply " or head[:3] == b"ply": return ".ply"
    if "jt" in (ctype or "").lower(): return ".jt"
    return ".bin"

def left():
    return TIME_LIMIT - (time.time() - START)

def disk_ok():
    return shutil.disk_usage("/home/z/my-project").free > DISK_MIN_FREE

def get_hiers(pid):
    r = paced_get(f"{BASE}/visual/files/packages", params={"productIds": pid})
    if r.status_code != 200:
        return []
    try:
        j = r.json()
    except Exception:
        return []
    j = j[0] if isinstance(j, list) and j else j
    if isinstance(j, dict):
        for k in ("hierarchyIds", "hierarchies"):
            if k in j:
                v = j[k]
                if v and isinstance(v[0], dict):
                    return [x.get("id") or x.get("hierarchyId") for x in v]
                return list(v)
    return []

def get_files(pid, hid):
    r = paced_post(f"{BASE}/visual/files/get-files", params={"api-version": "2.0"},
                   json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False})
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prog_path = DATA / "cad_progress.json"
    prog = json.loads(prog_path.read_text()) if prog_path.exists() else {}
    cars = json.load(open(DATA / "cad_priority.json"))
    # filter real brands (drop false positives Hyundai/Mercedes/Mini...)
    CN = {'AITO','Aion','Aiways','Avatr','BAIC','BYD','Baojun','Changan','Chery','Denza','Exeed','GAC','Geely','Haval','IM','Jaecoo','Leapmotor','Li','Luxeed','Lynk','MG','Maxus','NIO','Onvo','Roewe','Voyah','WEY','Zeekr','Wuling','Hongqi','Bestune','Deepal','Dongfeng','XPeng','Xiaomi','JAC','Forthing','Venucia','Arcfox','Rising','HiPhi','Seres','iCAR','Soueast','Haima','Kaiyi','Foton','Zhiji','Wey'}
    queue = [c for c in cars if c["name"].split()[0] in CN or c["name"].lower().startswith("vinfast")]
    print(f"Queue: {len(queue)} vehicles (VinFast first). Token window {left():.0f}s", flush=True)

    tot_f = tot_b = 0
    for ci, car in enumerate(queue):
        if left() < 100 or not disk_ok():
            print(f"STOP queue: time {left():.0f}s / disk {shutil.disk_usage('/home/z/my-project').free/1e9:.1f}GB", flush=True)
            break
        pid, name = car["id"], car["name"]
        brand = "VinFast" if name.lower().startswith("vinfast") else name.split()[0]
        folder = OUT / sanitize(brand, 30) / f"{sanitize(name, 80)}__{pid[-10:]}"
        folder.mkdir(parents=True, exist_ok=True)
        mf = folder / "manifest.json"
        # resume: skip vehicles already done
        if mf.exists():
            m0 = json.loads(mf.read_text())
            if m0.get("status") == "done" and len(m0.get("files", [])) >= m0.get("expected", 1):
                print(f"[{ci}] SKIP {name} (done earlier)", flush=True)
                continue
        t0 = time.time()
        hiers = get_hiers(pid)
        if not hiers:
            hiers = ["00000003LSK4EU01", "A000005AE6M1EU01"]
        recs, seen = [], set()
        ok_hiers = []
        for hid in hiers:
            if left() < 60: break
            fl = get_files(pid, hid)
            if not fl: continue
            ok_hiers.append(hid)
            for it in fl:
                fid = it.get("id")
                if fid and fid not in seen and it.get("token"):
                    seen.add(fid)
                    recs.append(it)
        if not recs:
            print(f"[{ci}] {name}: 0 file (hiers={hiers})", flush=True)
            prog[pid] = {"name": name, "files": 0, "bytes": 0, "status": "no-files"}
            prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
            continue
        meta = {}
        n_ok = n_err = nbytes = 0
        entries = []
        with ThreadPoolExecutor(WORKERS) as ex:
            futs = {ex.submit(paced_get, f"{BASE}/files/downloads/files?token={it['token']}&api-version=1.1", stream=False): it for it in recs}
            done_n = 0
            for fut in as_completed(futs):
                it = futs[fut]
                done_n += 1
                if done_n % 30 == 0 and (left() < 40 or not disk_ok()):
                    for f2 in futs:
                        f2.cancel()
                    break
                try:
                    r = fut.result()
                except Exception:
                    n_err += 1
                    continue
                if r.status_code != 200 or not r.content:
                    n_err += 1
                    continue
                ext = sniff_ext(r.content[:400], r.headers.get("content-type", ""))
                fn = f"{it['id']}__{sanitize(it.get('name') or it.get('partId'), 50)}{ext}"
                (folder / fn).write_bytes(r.content)
                sz = len(r.content)
                nbytes += sz; n_ok += 1
                entries.append({"file": fn, "id": it["id"], "part": it.get("partId"),
                                "name": it.get("name"), "label": it.get("label"),
                                "versions": it.get("versionIds"), "size": sz})
        entries.sort(key=lambda e: e["file"])
        status = "done" if (n_err == 0 and left() > 30) else ("partial" if n_ok else "failed")
        mf.write_text(json.dumps({"product": pid, "name": name, "hierarchies": ok_hiers,
                                  "expected": len(recs), "downloaded": n_ok, "errors": n_err,
                                  "bytes": nbytes, "status": status, "files": entries},
                                 ensure_ascii=False))
        prog[pid] = {"name": name, "files": n_ok, "bytes": nbytes, "status": status, "errors": n_err}
        prog_path.write_text(json.dumps(prog, ensure_ascii=False, indent=1))
        tot_f += n_ok; tot_b += nbytes
        print(f"[{ci}] {name}: {n_ok}/{len(recs)} files, {nbytes/1e6:.1f}MB, {time.time()-t0:.0f}s "
              f"(recent 403s: {_stat403[0]}, pace {_throttle[0]:.2f}s) | total {tot_f} files {tot_b/1e6:.0f}MB | {left():.0f}s left", flush=True)
    print(f"FINISHED: {tot_f} files, {tot_b/1e6:.0f}MB, {len(prog)} vehicles in progress", flush=True)

if __name__ == "__main__":
    main()
