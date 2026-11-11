#!/usr/bin/env python3
"""Tải 103 ảnh riêng tư (full-res) + crawl trạng thái 3D/Teardown cho 621 xe. Chạy song song, resume."""
import os, re, json, time, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
IMG_DIR = Path("/home/z/my-project/download/A2MAC1_anh_xe")
OUT_FULL = Path("/home/z/my-project/download/A2MAC1_anh_xe_fullHD")
OUT_FULL.mkdir(parents=True, exist_ok=True)

env = Path(".env").read_text()
raw = env.split("A2MAC1_TOKEN='")[1].split("'")[0]
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": BASE, "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

products = json.loads((DATA / "products_all.json").read_text())
name_of = {p["productId"]: p.get("resourceName", p["productId"]) for p in products}

def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|]+', "-", str(s)).strip()
    return s[:110] if s else "unknown"

# danh sách xe thiếu ảnh (publicUrls null nhưng có token)
need_img = []
for p in products:
    pid = p.get("productId")
    pf = p.get("pictureFile") or {}
    det = pf.get("details") or {}
    if det.get("token") and not (det.get("publicUrls") or {}).get("small"):
        need_img.append((pid, pf["originalValue"], det["token"], pf["details"].get("extension", "JPG")))
print("cần tải ảnh:", len(need_img), flush=True)

img_lock = threading.Lock()
img_results = []

def dl_image(item):
    pid, fid, ptok, ext = item
    # dest nhỏ 300px đã có cho xe public; xe này lưu full-res + bản nhỏ để nhúng
    try:
        r = S.get(BASE + "/files/downloads/files", params={"token": ptok, "api-version": "1.1"},
                  timeout=60)
        if r.status_code == 200 and len(r.content) > 1000 and "image" in r.headers.get("content-type", ""):
            name = f"{safe_name(name_of.get(pid, pid))} [{pid}].jpg"
            (OUT_FULL / name).write_bytes(r.content)
            with img_lock:
                img_results.append(pid)
            return pid, "OK", len(r.content)
        return pid, f"HTTP{r.status_code}", len(r.content)
    except Exception as e:
        return pid, "ERR", str(e)[:50]

t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    futs = [ex.submit(dl_image, it) for it in need_img]
    for i, f in enumerate(as_completed(futs), 1):
        pid, st, sz = f.result()
        if st != "OK":
            print("  ảnh FAIL:", pid, st, sz, flush=True)
print(f"ẢNH XONG: {len(img_results)}/{len(need_img)} | {time.time()-t0:.0f}s", flush=True)

# ---------- crawl trạng thái 3D/Teardown cho cả 621 xe ----------
HID = "A000005AE6M1EU01"
state_f = DATA / "teardown_state.json"
state = json.loads(state_f.read_text()) if state_f.exists() else {"done": {}, "rows": {}}
all_pids = [p["productId"] for p in products]
todo = [pid for pid in all_pids if pid not in state["done"]]
print("cần crawl teardown:", len(todo), flush=True)

def fetch_parts(pid):
    body = {"filters": [f"product-id eq {pid}"], "sorter": None, "page": {"number": 1, "size": 50}}
    for attempt in range(4):
        try:
            r = S.post(BASE + f"/api/hierarchies/{HID}/parts", json=body,
                       params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
                       timeout=60)
            if r.status_code == 200:
                return pid, r.json()
            if r.status_code == 401:
                return pid, None
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    return pid, None

lock = threading.Lock()
t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(fetch_parts, pid): pid for pid in todo}
    for i, f in enumerate(as_completed(futs), 1):
        pid, d = f.result()
        with lock:
            if d is not None:
                state["rows"][pid] = d
                state["done"][pid] = 1
            else:
                state["done"][pid] = 0
            if i % 50 == 0 or i == len(todo):
                state_f.write_text(json.dumps(state))
                print(f"  teardown {i}/{len(todo)} | {time.time()-t0:.0f}s", flush=True)
        if d is None:
            print("  teardown FAIL:", pid, flush=True)
state_f.write_text(json.dumps(state))
ok = sum(1 for v in state["done"].values() if v)
print(f"TEARDOWN XONG: {ok}/{len(all_pids)} | {time.time()-t0:.0f}s", flush=True)
