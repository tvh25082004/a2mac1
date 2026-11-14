"""CAD v4: download straight into DATA-CAD_NN.zip chunks (~90MB), no master zip.
Resume from data/cad_skip_list.json. Continue chunk numbering after the last part.
"""
import re, json, time, shutil, zipfile, os, random, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
DL = Path("/home/z/my-project/download")
START = time.time()
TIME_LIMIT = 1000  # token sống ~20 phút; pace an toàn quan trọng hơn cửa sổ dài
CHUNK_TARGET = 90e6
_tokfile = Path("/tmp/a2mac1_tok")
if _tokfile.exists():
    TOK = _tokfile.read_text().strip()  # plain JWT written fresh each session
else:
    raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
    TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
S = requests.Session(); S.headers.update(H)

def left(): return TIME_LIMIT - (time.time() - START)
def log(*a): print(f"[{time.strftime('%H:%M:%S')}|{left():.0f}s left]", *a, flush=True)

def next_chunk_num():
    n = 0
    for p in DL.glob("DATA-CAD_*.zip"):
        try: n = max(n, int(p.stem.split("_")[1]))
        except Exception: pass
    return n + 1

def get_files(pid, hid="00000003LSK4EU01"):
    r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False}, timeout=60)
    return r.json() if r.status_code == 200 else None

def main():
    skip_data = json.load(open(DATA / "cad_skip_list.json"))
    done = set(skip_data["done_files"])
    manifest_all = skip_data.setdefault("manifest", {})
    # scan existing chunks -> use for filename de-dup (resume across sessions)
    names_in_chunks = set()
    for p in DL.glob("DATA-CAD_*.zip"):
        try:
            names_in_chunks |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(p).namelist() if nm.endswith(".stl"))
        except Exception:
            p.unlink(missing_ok=True)  # chunk corrupted because killed mid-way -> delete and recreate
    done |= names_in_chunks
    chunk_num = next_chunk_num()
    log(f"resume {len(done)} file names | starting chunk: {chunk_num:02d} | token {left()}s")
    tmp = Path("/tmp/cad4"); tmp.mkdir(exist_ok=True)
    cars = json.load(open(DATA / "cad_priority.json"))  # full queue: 510 xe, tự bò qua các phiên
    BAN = [False]; AUTH = [False]

    def dl(it, carname):
        try:
            time.sleep(0.6)  # slow pace: ~3 files/s for 4 min triggered a 403 ban
            r = S.get(f"{BASE}/files/downloads/files", params={"token": it["token"], "api-version": "1.1"}, timeout=(10, 150))
            if r.status_code == 403:
                BAN[0] = True; return None
            if r.status_code == 401:
                AUTH[0] = True; return None
            if r.status_code != 200 or len(r.content) < 500:
                return None
            m = re.search(r"filename=([^;]+)", r.headers.get("content-disposition", ""))
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", (m.group(1).strip().strip('"') if m else f"{it['id']}.stl"))
            p = tmp / f"{random.randint(10**5, 10**6-1)}_{fname}"
            p.write_bytes(r.content)
            return (carname, fname, p, len(r.content), {"part": it.get("partId"), "fid": it.get("id"), "name": it.get("name"), "label": it.get("label")})
        except Exception:
            return None

    for car in cars:
        if left() < 60 or BAN[0] or AUTH[0] or shutil.disk_usage("/home/z/my-project").free < 0.8e9:
            break
        pid, name = car["id"], car["name"]
        log(f"== {name} ==")
        recs = get_files(pid)
        if not recs:
            log("get-files error (403/token expired/no 3D) -> end session"); break
        seen, uniq = set(), []
        for r in recs:
            if r.get("token") and r["id"] not in seen:
                seen.add(r["id"]); uniq.append(r)
        SESSION_FILE_CAP = 600  # ~935 files/10min triggered a 403 ban; stay under
        # dedup: by stored record ids AND by partId (older manifests stored partId only)
        done_ids = set(manifest_all.get(name, {}).get("ids", []))
        done_parts = set(e.get("part") for e in manifest_all.get(name, {}).get("files", []) if e.get("part"))
        todo = [r for r in uniq if r["id"] not in done_ids and r.get("partId") not in done_parts]
        log(f"{len(uniq)} unique files, still to download: {len(todo)}")
        mf = manifest_all.setdefault(name, {"product": pid, "total_files": len(uniq),
                                            "hierarchy": "00000003LSK4EU01 (3D AutoReverse)",
                                            "ids": list(done_ids), "files": []})
        n_ok = 0
        ex = ThreadPoolExecutor(2)  # 2 workers + 0.6s stagger ~ 1.3 files/s, ban-safe
        futs = [ex.submit(dl, it, name) for it in todo]
        ex.shutdown(wait=False)
        zf = None
        zpath = DL / f"DATA-CAD_{chunk_num:02d}.zip"
        try:
            chunk_bytes = sum(i.compress_size for i in zipfile.ZipFile(zpath).infolist()) if zpath.exists() else 0
            zf = zipfile.ZipFile(zpath, "a" if zpath.exists() else "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        except Exception:
            zpath.unlink(missing_ok=True)
            chunk_bytes = 0
            zf = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        for fu in futs:
            if left() < 50 or BAN[0] or AUTH[0] or shutil.disk_usage("/home/z/my-project").free < 0.8e9 \
                    or n_ok >= SESSION_FILE_CAP:
                if BAN[0]: log("403 -> stop car")
                if AUTH[0]: log("401 token expired -> end session")
                if n_ok >= SESSION_FILE_CAP: log(f"file cap {SESSION_FILE_CAP} reached -> pause car (ban-safe volume)")
                for f2 in futs: f2.cancel()
                break
            res = fu.result()
            if not res: continue
            carname, fname, p, size, meta = res
            if fname in names_in_chunks:
                p.unlink(missing_ok=True); continue  # already present from an earlier session
            zf.write(p, f"{carname}/{fname}")
            p.unlink(missing_ok=True)
            names_in_chunks.add(fname)
            mf["ids"].append(meta.get("fid") or meta.get("part") or fname)
            mf["files"].append({"file": f"{carname}/{fname}", **meta, "size": size})
            done.add(fname)
            chunk_bytes += size
            n_ok += 1
            if n_ok % 50 == 0:  # save progress continuously for safe resume
                (DATA / "cad_skip_list.json").write_text(json.dumps(skip_data, ensure_ascii=False, indent=1))
            if chunk_bytes > CHUNK_TARGET:
                zf.writestr("_MANIFEST.json", json.dumps({"batch": zpath.name, "note": "see data/cad_skip_list.json for the full manifest"}, ensure_ascii=False))
                zf.close()
                log(f"  close {zpath.name} ({chunk_bytes/1e6:.0f}MB, {n_ok} files this session)")
                chunk_num += 1
                zpath = DL / f"DATA-CAD_{chunk_num:02d}.zip"
                zf = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
                chunk_bytes = 0
        if zf is not None:
            try:
                if chunk_bytes == 0:
                    zf.close(); zpath.unlink(missing_ok=True)
                else:
                    zf.writestr("_MANIFEST.json", json.dumps({"batch": zpath.name}, ensure_ascii=False))
                    zf.close()
                    log(f"  close {zpath.name} ({chunk_bytes/1e6:.0f}MB)")
            except Exception:
                pass
        log(f"{name}: +{n_ok} files this session")
    skip_data["done_files"] = sorted(done)
    (DATA / "cad_skip_list.json").write_text(json.dumps(skip_data, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"FINISHED: {len(done)} files total now in chunks")

if __name__ == "__main__":
    main()
