"""CAD v4: tải thẳng vào các chunk DATA-CAD_NN.zip (~90MB), không dùng master.
Resume từ data/cad_skip_list.json. Tiếp tục đánh số chunk sau phần cuối cùng.
"""
import re, json, time, shutil, zipfile, os, random, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
DL = Path("/home/z/my-project/download")
START = time.time()
TIME_LIMIT = 480
CHUNK_TARGET = 90e6
raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
S = requests.Session(); S.headers.update(H)

def left(): return TIME_LIMIT - (time.time() - START)
def log(*a): print(f"[{time.strftime('%H:%M:%S')}|còn {left():.0f}s]", *a, flush=True)

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
    chunk_num = next_chunk_num()
    log(f"resume {len(done)} file | chunk bắt đầu: {chunk_num:02d} | token {left()}s")
    tmp = Path("/tmp/cad4"); tmp.mkdir(exist_ok=True)
    cars = json.load(open(DATA / "cad_priority.json"))[:2]
    BAN = [False]

    def dl(it, carname):
        try:
            time.sleep(0.15)
            r = S.get(f"{BASE}/files/downloads/files", params={"token": it["token"], "api-version": "1.1"}, timeout=(10, 150))
            if r.status_code == 403:
                BAN[0] = True; return None
            if r.status_code != 200 or len(r.content) < 500:
                return None
            m = re.search(r"filename=([^;]+)", r.headers.get("content-disposition", ""))
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", (m.group(1).strip().strip('"') if m else f"{it['id']}.stl"))
            p = tmp / f"{random.randint(10**5, 10**6-1)}_{fname}"
            p.write_bytes(r.content)
            return (carname, fname, p, len(r.content), {"part": it.get("partId"), "name": it.get("name"), "label": it.get("label")})
        except Exception:
            return None

    for car in cars:
        if left() < 60 or BAN[0] or shutil.disk_usage("/home/z/my-project").free < 0.8e9:
            break
        pid, name = car["id"], car["name"]
        log(f"== {name} ==")
        recs = get_files(pid)
        if not recs:
            log("get-files lỗi (403?) -> dừng phiên"); break
        seen, uniq = set(), []
        for r in recs:
            if r.get("token") and r["id"] not in seen:
                seen.add(r["id"]); uniq.append(r)
        todo = [r for r in uniq if not any(r["id"] in e.get("id", "##") for e in manifest_all.get(name, {}).get("files", [])) ]
        # đơn giản hơn: so theo tên file dự đoán không ổn -> dùng id
        done_ids = set(manifest_all.get(name, {}).get("ids", []))
        todo = [r for r in uniq if r["id"] not in done_ids]
        log(f"{len(uniq)} file unique, còn cần tải: {len(todo)}")
        mf = manifest_all.setdefault(name, {"product": pid, "total_files": len(uniq),
                                            "hierarchy": "00000003LSK4EU01 (3D AutoReverse)",
                                            "ids": list(done_ids), "files": []})
        n_ok = 0
        ex = ThreadPoolExecutor(3)
        futs = [ex.submit(dl, it, name) for it in todo]
        ex.shutdown(wait=False)
        zf = None
        zpath = DL / f"DATA-CAD_{chunk_num:02d}.zip"
        zf = zipfile.ZipFile(zpath, "a" if zpath.exists() else "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        chunk_bytes = sum(i.compress_size for i in zipfile.ZipFile(zpath).infolist()) if zpath.exists() else 0
        for fu in futs:
            if left() < 50 or BAN[0] or shutil.disk_usage("/home/z/my-project").free < 0.8e9:
                if BAN[0]: log("403 -> dừng car")
                for f2 in futs: f2.cancel()
                break
            res = fu.result()
            if not res: continue
            carname, fname, p, size, meta = res
            zf.write(p, f"{carname}/{fname}")
            zname_len = size
            p.unlink(missing_ok=True)
            mf["ids"].append(meta.get("part") or fname)
            mf["files"].append({"file": f"{carname}/{fname}", **meta, "size": size})
            done.add(fname)
            chunk_bytes += zname_len
            n_ok += 1
            if chunk_bytes > CHUNK_TARGET:
                zf.writestr("_MANIFEST.json", json.dumps({"batch": zpath.name, "note": "xem data/cad_skip_list.json để lấy manifest đầy đủ"}, ensure_ascii=False))
                zf.close()
                log(f"  đóng {zpath.name} ({chunk_bytes/1e6:.0f}MB, {n_ok} file phiên này)")
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
                    log(f"  đóng {zpath.name} ({chunk_bytes/1e6:.0f}MB)")
            except Exception:
                pass
        log(f"{name}: +{n_ok} file phiên này")
    skip_data["done_files"] = sorted(done)
    (DATA / "cad_skip_list.json").write_text(json.dumps(skip_data, ensure_ascii=False, indent=1))
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"KẾT THÚC: tổng {len(done)} file đã có trong chunks")

if __name__ == "__main__":
    main()
