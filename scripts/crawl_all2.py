#!/usr/bin/env python3
"""ALL-IN-ONE foreground: packages + get-files + teardown cho 621 xe. Lưu stream, resume."""
import os, re, json, time, sys
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
HID_3D = "00000003LSK4EU01"
HID_VOP = "00000005ZT4GEU01"
HID_ALL = "A000005AE6M1EU01"
STEP = sys.argv[1] if len(sys.argv) > 1 else "all"

env = Path("/home/z/my-project/scripts/.env").read_text()
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

def auth_dead(r):
    return r is not None and r.status_code == 401

products = json.loads((DATA / "products_all.json").read_text())
all_pids = [p["productId"] for p in products]

# ---- packages ----
pkgs_f = DATA / "packages_all.json"
if STEP in ("all", "pkgs") and (not pkgs_f.exists() or len(json.loads(pkgs_f.read_text() or "[]")) < len(all_pids) - 10):
    pkgs_all = json.loads(pkgs_f.read_text()) if pkgs_f.exists() else []
    t0 = time.time()
    for i in range(0, len(all_pids), 25):
        chunk = all_pids[i:i+25]
        try:
            r = S.get(BASE + "/api/visual/files/packages", params=[("productIds", p) for p in chunk], timeout=90)
            if auth_dead(r):
                print("AUTH401 pkgs"); break
            if r.status_code == 200:
                pkgs_all.extend(r.json())
        except Exception as e:
            print("pkg err", str(e)[:50], flush=True)
        if (i // 25) % 5 == 0:
            print(f"pkgs {i+25}/{len(all_pids)} n={len(pkgs_all)} {time.time()-t0:.0f}s", flush=True)
    pkgs_f.write_text(json.dumps(pkgs_all))
pkgs_all = json.loads(pkgs_f.read_text())
pkgs_by_pid = {}
for pk in pkgs_all:
    pkgs_by_pid.setdefault(pk["productId"], []).append(pk)
print("PKGS XONG:", len(pkgs_all), "gói /", len(pkgs_by_pid), "xe", flush=True)

# ---- get-files ----
if STEP in ("all", "files"):
    out_f = DATA / "visual_files_summary.json"
    res = json.loads(out_f.read_text()) if out_f.exists() else {}
    def fetch_car(pid):
        hiers = set()
        for pk in pkgs_by_pid.get(pid, []):
            hiers.update(pk.get("hierarchyIds") or [])
        hiers = [h for h in sorted(hiers) if h in (HID_3D, HID_VOP)] or [HID_3D]
        rec = {"hiers": hiers, "files": {}, "downloadable": 0, "materials": Counter(), "names": []}
        dead = False
        for hid in hiers:
            body = {"productIds": [pid], "hierarchyId": hid, "isBookmark": False}
            for attempt in range(5):
                try:
                    r = S.post(BASE + "/api/visual/files/get-files?api-version=2.0", json=body, timeout=120)
                    if auth_dead(r):
                        dead = True; break
                    if r.status_code == 200:
                        fl = r.json()
                        rec["files"][hid] = len(fl)
                        for x in fl:
                            if x.get("isDownloadable"):
                                rec["downloadable"] += 1
                            rec["materials"][x.get("label") or "?"] += 1
                            if x.get("name"):
                                rec["names"].append(str(x["name"]))
                    break
                    time.sleep(0.25)
                except Exception:
                    time.sleep(0.25)
            if dead:
                return pid, "AUTH401"
        rec["materials"] = dict(rec["materials"])
        rec["names_count"] = len(rec["names"])
        rec["names_sample"] = rec["names"][:6]
        del rec["names"]
        return pid, rec

    todo = [p for p in all_pids if p not in res]
    print("get-files todo:", len(todo), flush=True)
    t0 = time.time(); n_ok = 0; dead_flag = False
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_car, pid): pid for pid in todo}
        for i, f in enumerate(as_completed(futs), 1):
            pid, rec = f.result()
            if rec == "AUTH401":
                print("AUTH401 files — dừng", flush=True); dead_flag = True; break
            res[pid] = rec
            if rec.get("files"):
                n_ok += 1
            if i % 30 == 0:
                out_f.write_text(json.dumps(res))
                print(f"files {i}/{len(todo)} cófile={n_ok} {time.time()-t0:.0f}s", flush=True)
    out_f.write_text(json.dumps(res))
    print("FILES XONG:", len(res), "xe,", n_ok, "xe có file 3D/CAD", flush=True)

# ---- teardown ----
if STEP in ("all", "teardown"):
    st_f = DATA / "teardown_state.json"
    state = json.loads(st_f.read_text()) if st_f.exists() else {"done": {}, "rows": {}}
    def fetch_td(pid):
        body = {"filters": [f"product-id eq {pid}"], "sorter": None, "page": {"number": 1, "size": 50}}
        for attempt in range(5):
            try:
                r = S.post(BASE + f"/api/hierarchies/{HID_ALL}/parts", json=body,
                           params={"allowDynamicColumns": "true", "hideMappedProperties": "true"}, timeout=60)
                if auth_dead(r):
                    return pid, "AUTH401"
                if r.status_code == 200:
                    return pid, r.json()
                time.sleep(4 if True else 1)
            except Exception:
                time.sleep(4 if True else 1)
        return pid, "FAIL"

    todo = [p for p in all_pids if p not in state["done"]]
    print("teardown todo:", len(todo), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_td, pid): pid for pid in todo}
        for i, f in enumerate(as_completed(futs), 1):
            pid, d = f.result()
            if d == "AUTH401":
                print("AUTH401 teardown — dừng", flush=True); break
            state["rows"][pid] = d
            state["done"][pid] = 0 if d == "FAIL" else 1
            if i % 60 == 0:
                st_f.write_text(json.dumps(state))
                print(f"teardown {i}/{len(todo)} {time.time()-t0:.0f}s", flush=True)
    st_f.write_text(json.dumps(state))
    ok = sum(1 for v in state["done"].values() if v)
    print("TEARDOWN XONG:", ok, "/", len(all_pids), flush=True)
print("DONE STEP=", STEP, flush=True)
