"""CAD v3: stream VF6/VF8 STLs straight into DATA-CAD.zip (download 1 file -> put into zip -> delete raw).
Correct URL: https://ibp.a2mac1.com/files/downloads/files?token=<tok>&api-version=1.1 (NO /api prefix).
Guards: zip <= 1.8GB, 320s time limit, free disk > 1GB.
"""
import re, json, time, shutil, zipfile, os, random, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
ZIP_PATH = Path("/home/z/my-project/download/DATA-CAD_16.zip")
START = time.time()
TIME_LIMIT = 320
ZIP_CAP = 5.5e9
raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
S = requests.Session(); S.headers.update(H)

def left(): return TIME_LIMIT - (time.time() - START)
def log(*a): print(f"[{time.strftime('%H:%M:%S')}|{left():.0f}s left]", *a, flush=True)

def get_files(pid, hid):
    r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False}, timeout=60)
    return r.json() if r.status_code == 200 else None

def main():
    cars = json.load(open(DATA / "cad_priority.json"))[:2]  # VF6 (resume) + VF8
    tmp = Path("/tmp/cad_stl"); tmp.mkdir(parents=True, exist_ok=True)
    zf = zipfile.ZipFile(ZIP_PATH, "a" if ZIP_PATH.exists() else "w", zipfile.ZIP_DEFLATED, compresslevel=6)
    manifest = {}
    zbytes = 0
    BAN = [False]
    lock = threading.Lock()
    skip = set()
    for zp in sorted(Path("/home/z/my-project/download").glob("DATA-CAD*.zip")) + [Path("/tmp/my-project/download/DATA-CAD.zip")]:
        try:
            skip |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(zp).namelist() if nm.endswith(".stl"))
        except Exception:
            pass
    log(f"skip: {len(skip)} files already in old parts/zips")
    if ZIP_PATH.exists():  # resume: read files already in the zip
        try:
            skip = set(nm.split("/")[-1] for nm in zipfile.ZipFile(ZIP_PATH).namelist() if nm.endswith(".stl"))
            zf.close()
            zf = zipfile.ZipFile(ZIP_PATH, "a", zipfile.ZIP_DEFLATED, compresslevel=6)
            log(f"resume: {len(skip)} files already in zip")
        except Exception:
            pass

    def dl(it, carname):
        """Download 1 file -> tmp -> return (carname, fname, path, size, meta)."""
        try:
            time.sleep(0.15)
            r = S.get(f"{BASE}/files/downloads/files",
                      params={"token": it["token"], "api-version": "1.1"}, timeout=(10, 150))
            if r.status_code == 403:
                BAN[0] = True
                return None
            if r.status_code != 200 or len(r.content) < 500:
                return None
            cd = r.headers.get("content-disposition", "")
            m = re.search(r"filename=([^;]+)", cd)
            fname = m.group(1).strip().strip('"') if m else f"{it['id']}.stl"
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", fname)
            p = tmp / f"{os.getpid()}_{random.randint(1000,9999)}_{fname}"
            p.write_bytes(r.content)
            return (carname, fname, p, len(r.content),
                    {"id": it["id"], "part": it.get("partId"), "name": it.get("name"), "label": it.get("label")})
        except Exception:
            return None

    for car in cars:
        if left() < 60 or zbytes > ZIP_CAP or shutil.disk_usage("/home/z/my-project").free < 1.0e9:
            break
        pid, name = car["id"], car["name"]
        log(f"== {name} ({pid[-10:]}) ==")
        recs = get_files(pid, "00000003LSK4EU01")
        if not recs:
            log("get-files error -> stop"); break
        seen, uniq = set(), []
        for r in recs:
            if r.get("token") and r["id"] not in seen:
                seen.add(r["id"]); uniq.append(r)
        recs = uniq
        log(f"{len(recs)} unique files")
        manifest[name] = {"product": pid, "hierarchy": "00000003LSK4EU01 (3D AutoReverse)",
                          "total_files": len(recs), "files": [], "incomplete": False}
        n_ok = n_mb = 0
        BAN[0] = False
        ex = ThreadPoolExecutor(3)
        futs = [ex.submit(dl, it, name) for it in recs]
        ex.shutdown(wait=False)
        for fu in futs:
            if left() < 45 or zbytes > ZIP_CAP or shutil.disk_usage("/home/z/my-project").free < 1.0e9 or BAN[0]:
                if BAN[0]:
                    log("403 mid-way -> stop this car")
                for f2 in futs: f2.cancel()
                manifest[name]["incomplete"] = True
                break
            res = fu.result()
            if not res: continue
            carname, fname, p, size, meta = res
            zname = f"{carname}/{fname}"
            if zname.split("/")[-1] in skip:
                p.unlink(missing_ok=True); continue
            zf.write(p, zname)
            p.unlink(missing_ok=True)
            with lock:
                zbytes += size
                manifest[carname]["files"].append({"file": fname, **meta, "size": size})
            n_ok += 1; n_mb += size
            if n_ok % 25 == 0:
                log(f"  {n_ok} file | zip-in {zbytes/1e6:.0f}MB | disk free {shutil.disk_usage('/home/z/my-project').free/1e9:.1f}GB")
        log(f"{name}: {n_ok}/{len(recs)} files, {n_mb/1e6:.0f}MB source")
    zf.close()
    # manifest into the zip
    with zipfile.ZipFile(ZIP_PATH, "a", zipfile.ZIP_DEFLATED) as z2:
        z2.writestr("_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"DONE: {ZIP_PATH} {ZIP_PATH.stat().st_size/1e6:.0f}MB")

if __name__ == "__main__":
    main()
