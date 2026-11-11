#!/usr/bin/env python3
"""Quét packages + visual files (3D/CAD) cho 621 xe — tóm tắt gọn, resume, 8 threads."""
import os, re, json, time, threading
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
HID_3D = "00000003LSK4EU01"   # 3D AutoReverse
HID_VOP = "00000005ZT4GEU01"  # Vehicle Occupant Packaging

env = (DATA.parent / "scripts" / ".env").read_text() if (DATA.parent / "scripts" / ".env").exists() else Path(".env").read_text()
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
all_pids = [p["productId"] for p in products]

# ---- 1) packages cho tất cả xe (batch 25) ----
pkgs_f = DATA / "packages_all.json"
if not pkgs_f.exists() or len(json.loads(pkgs_f.read_text() if pkgs_f.exists() else "[]")) < len(all_pids) - 10:
    pkgs_all = []
    t0 = time.time()
    for i in range(0, len(all_pids), 25):
        chunk = all_pids[i:i+25]
        try:
            r = S.get(BASE + "/api/visual/files/packages",
                      params=[("productIds", p) for p in chunk], timeout=90)
            if r.status_code == 200:
                pkgs_all.extend(r.json())
        except Exception as e:
            print("pkg batch err", str(e)[:60], flush=True)
        print(f"packages {i+25}/{len(all_pids)} n={len(pkgs_all)} {time.time()-t0:.0f}s", flush=True)
    pkgs_f.write_text(json.dumps(pkgs_all))
pkgs_all = json.loads(pkgs_f.read_text())
pkgs_by_pid = {}
for pk in pkgs_all:
    pkgs_by_pid.setdefault(pk["productId"], []).append(pk)
print("packages xe có gói:", len(pkgs_by_pid), flush=True)

# ---- 2) get-files từng xe từng hierarchy ----
out_f = DATA / "visual_files_summary.json"
res = json.loads(out_f.read_text()) if out_f.exists() else {}
lock = threading.Lock()

def fetch_car(pid):
    rec = {"packages": len(pkgs_by_pid.get(pid, [])), "hiers": [], "files": {}, "downloadable": 0,
           "materials": Counter(), "part_names": []}
    hiers = set()
    for pk in pkgs_by_pid.get(pid, []):
        hiers.update(pk.get("hierarchyIds") or [])
    rec["hiers"] = sorted(hiers)
    for hid in rec["hiers"]:
        if hid not in (HID_3D, HID_VOP):
            continue
        body = {"productIds": [pid], "hierarchyId": hid, "isBookmark": False}
        for attempt in range(3):
            try:
                r = S.post(BASE + "/api/visual/files/get-files?api-version=2.0", json=body, timeout=120)
                if r.status_code == 401:
                    return pid, "AUTH401"
                if r.status_code == 200:
                    fl = r.json()
                    rec["files"][hid] = len(fl)
                    for x in fl:
                        if x.get("isDownloadable"):
                            rec["downloadable"] += 1
                        lb = x.get("label") or "Không nhãn"
                        rec["materials"][lb] += 1
                        nm = x.get("name")
                        if nm:
                            rec["part_names"].append(str(nm))
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)
    rec["materials"] = dict(rec["materials"])
    rec["part_names_count"] = len(rec["part_names"])
    rec["part_names_sample"] = rec["part_names"][:8]
    del rec["part_names"]
    return pid, rec

todo = [p for p in all_pids if p not in res]
print("get-files cần quét:", len(todo), flush=True)
t0 = time.time(); n_ok = 0
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(fetch_car, pid): pid for pid in todo}
    for i, f in enumerate(as_completed(futs), 1):
        pid, rec = f.result()
        with lock:
            if rec == "AUTH401":
                print("AUTH 401 — DỪNG!", flush=True)
                out_f.write_text(json.dumps(res))
                raise SystemExit("AUTH_EXPIRED")
            res[pid] = rec
            if rec.get("files"):
                n_ok += 1
            if i % 40 == 0 or i == len(todo):
                out_f.write_text(json.dumps(res))
                print(f"get-files {i}/{len(todo)} | có file: {n_ok} | {time.time()-t0:.0f}s", flush=True)
out_f.write_text(json.dumps(res))
print(f"GET-FILES XONG: {len(res)} xe, {n_ok} xe có file 3D | {time.time()-t0:.0f}s", flush=True)
