#!/usr/bin/env python3
"""Cào thông số chi tiết TOÀN BỘ xe qua api/products/compare/data/by-products.
Batch 25 xe, resume bằng spec_state.json, retry chờ session warm-up."""
import os, re, json, time, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
F_PRODUCTS = DATA / "products_all.json"
F_STATE = DATA / "spec_state.json"
B_DIR = DATA / "spec_batches"

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

st = json.loads(F_STATE.read_text()) if F_STATE.exists() else {"done": [], "batches": []}
products = json.loads(F_PRODUCTS.read_text())
ids, names = [], {}
for p in products:
    pid = p.get("productId")
    if pid:
        ids.append(pid)
        names[pid] = p.get("resourceName", "")
todo = [i for i in ids if i not in st["done"]]
print(f"Tổng xe: {len(ids)} | đã xong: {len(st['done'])} | còn: {len(todo)}", flush=True)
B_DIR.mkdir(exist_ok=True)

batch_idx = len(st["batches"])
t0 = time.time()
for start in range(0, len(todo), 25):
    chunk = todo[start:start + 25]
    batch_idx += 1
    data, ok = None, False
    for attempt in range(7):
        try:
            r = S.post(BASE + "/api/products/compare/data/by-products", json=chunk,
                       params={"hideMappedProperties": "true"}, timeout=240)
        except Exception as e:
            print(f"  batch {batch_idx} net err: {e}", flush=True)
            time.sleep(4); continue
        if r.status_code == 200:
            data = r.json(); ok = True; break
        if r.status_code in (401, 403):
            print(f"  batch {batch_idx} HTTP {r.status_code} — chờ 4s retry (session warm-up)...", flush=True)
            time.sleep(4); continue
        if r.status_code == 429:
            print(f"  batch {batch_idx} 429 — chờ 10s", flush=True)
            time.sleep(10); continue
        if r.status_code >= 500:
            print(f"  batch {batch_idx} {r.status_code} — chờ 4s", flush=True)
            time.sleep(4); continue
        sys.exit(f"HTTP {r.status_code} tại batch {batch_idx}: {r.text[:200]}")
    if not ok:
        sys.exit(f"batch {batch_idx} thất bại sau 7 lần — chạy lại lệnh này để resume")
    out = B_DIR / f"batch_{batch_idx:04d}.json"
    out.write_text(json.dumps(data, ensure_ascii=False))
    got = sum(1 for c in chunk if c in (data.get("values") or {}))
    st["done"].extend(chunk)
    st["batches"].append(out.name)
    F_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))
    el = time.time() - t0
    print(f"  batch {batch_idx}: {got}/{len(chunk)} xe có values ({el:.0f}s) -> {out.name}", flush=True)
    time.sleep(0.4)

print(f"==> XONG. Tổng xe đã cào: {len(st['done'])}", flush=True)
