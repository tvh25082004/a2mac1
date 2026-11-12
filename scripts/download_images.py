#!/usr/bin/env python3
"""Download all A2MAC1 vehicle images (public blobs, no auth needed). Resumable."""
import json, re, time, sys
from pathlib import Path
import requests

DATA = Path("/home/z/my-project/data")
OUT = Path("/home/z/my-project/download/A2MAC1_anh_xe")
OUT.mkdir(parents=True, exist_ok=True)

products = json.loads((DATA / "products_all.json").read_text())
print("vehicles:", len(products))

def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|]+', "-", str(s)).strip()
    return s[:110] if s else "unknown"

ok = skip = fail = 0
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
t0 = time.time()
for i, p in enumerate(products, 1):
    pid = p.get("productId")
    pf = p.get("pictureFile") or {}
    det = pf.get("details") or {}
    urls = det.get("publicUrls") or {}
    url = (urls.get("small") or urls.get("medium") or urls.get("large") or "").replace("\\", "/")
    if not url or not pid:
        fail += 1
        continue
    name = f"{safe_name(p.get('resourceName', pid))} [{pid}].jpg"
    dest = OUT / name
    if dest.exists() and dest.stat().st_size > 1000:
        skip += 1
        continue
    try:
        r = S.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 500:
            dest.write_bytes(r.content)
            ok += 1
        else:
            fail += 1
            print(f"  [{r.status_code}] {name[:60]}")
    except Exception as e:
        fail += 1
        print(f"  ERR {name[:60]}: {str(e)[:60]}")
    if i % 100 == 0:
        print(f"  {i}/{len(products)} | ok={ok} skip={skip} fail={fail} | {time.time()-t0:.0f}s", flush=True)
    time.sleep(0.12)

print(f"==> DONE: ok={ok} skip={skip} fail={fail} | {time.time()-t0:.0f}s | folder: {OUT}")
