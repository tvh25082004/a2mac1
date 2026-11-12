#!/usr/bin/env python3
"""Final-minute harvest: every lightweight GET/POST that might return 200 -> save JSON."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
tok = m.group(1) if m else raw
PID = "A0000004F0UTEU02"

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={tok}",
    "Authorization": f"Bearer {tok}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
BASE = "https://ibp.a2mac1.com"
OUT = Path("/home/z/my-project/data/harvest"); OUT.mkdir(exist_ok=True, parents=True)

JOBS = [
    ("queries_v2", "GET", "/api/queries?api-version=2.0", None, None),
    ("filters_products_v2", "POST", "/api/filters/products?api-version=2.0", {"filters": [], "page": {"number": 1, "size": 200}}, None),
    ("filters_hierarchies", "POST", "/api/filters/hierarchies", {"filters": []}, None),
    ("product_types", "GET", "/api/products/product-types", None, None),
    ("ptg", "GET", "/api/products/" + PID + "/product-type-group", None, None),
    ("searchable_props_3d", "GET", f"/api/products/{PID}/hierarchies/00000003LSK4EU01/searchable-properties", None, None),
    ("quicksearch_all", "POST", "/api/quick-search?api-version=2.0", {"search": "", "filters": [], "hierarchyId": None, "hierarchyNodeId": None}, None),
]
for name, method, path, body, params in JOBS:
    try:
        r = S.request(method, BASE + path, json=body, params=params, timeout=45)
        txt = r.text or ""
        interesting = r.status_code == 200 and len(txt) > 5
        print(f"{name}: HTTP {r.status_code} len={len(txt)} {(txt[:150] if interesting else (txt[:120] if txt else ''))}")
        if interesting:
            (OUT / f"{name}.json").write_text(txt, encoding="utf-8")
    except Exception as e:
        print(f"{name}: ERROR {e}")
    time.sleep(0.3)
print("HARVEST DONE")
