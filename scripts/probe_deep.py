#!/usr/bin/env python3
"""Probe endpoint api/products/compare/data/by-products với 5 productId."""
import os, re, json, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
BASE = "https://ibp.a2mac1.com"
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

products = json.loads(Path("/home/z/my-project/data/products_all.json").read_text())
ids = [p["productId"] for p in products[:5]]
names = [p["resourceName"] for p in products[:5]]
print("test ids:", names)

def show(tag, r):
    ct = r.headers.get("content-type", "")
    print(f"\n=== {tag}: HTTP {r.status_code} | {len(r.content)/1024:.0f} KB | {ct[:40]}")
    if r.status_code != 200:
        print(r.text[:400]); return None
    try:
        d = r.json()
    except Exception as e:
        print("không parse được JSON:", e, r.text[:200]); return None
    if isinstance(d, dict):
        print("top-level keys:", list(d.keys())[:20])
        for k, v in d.items():
            if isinstance(v, list):
                print(f"  [{k}] list len={len(v)}; sample:", json.dumps(v[0], ensure_ascii=False)[:600] if v else "")
            elif isinstance(v, dict):
                print(f"  [{k}] dict keys:", list(v.keys())[:15])
    elif isinstance(d, list):
        print(f"list len={len(d)}; sample:", json.dumps(d[0], ensure_ascii=False)[:800] if d else "EMPTY")
    return d

# 1) by-products: body = mảng id thuần
r = S.post(BASE + "/api/products/compare/data/by-products", json=ids,
           params={"hideMappedProperties": "true"}, timeout=180)
d1 = show("by-products hideMapped=true", r)

# 2) by-products không param
r = S.post(BASE + "/api/products/compare/data/by-products", json=ids, timeout=180)
d2 = show("by-products (no params)", r)

# 3) by-items với filters=[] (đúng theo bundle: v={itemIds, filters})
r = S.post(BASE + "/api/products/compare/data/by-items", json={"itemIds": ids, "filters": []},
           params={"hideMappedProperties": "true"}, timeout=180)
d3 = show("by-items +filters=[]", r)

# 4) hierarchies của product đầu tiên
r = S.get(BASE + f"/api/products/{ids[0]}/hierarchies", timeout=60)
print(f"\n=== hierarchies {ids[0]}: HTTP {r.status_code}")
if r.status_code == 200:
    h = r.json()
    print(json.dumps(h, ensure_ascii=False)[:800])
