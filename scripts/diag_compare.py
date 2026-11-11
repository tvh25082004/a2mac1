#!/usr/bin/env python3
"""Chẩn đoán nhanh 401 trên compare/data — thử nhiều biến thể URL/body."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
tok = m.group(1) if m else raw

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={tok}",
    "Authorization": f"Bearer {tok}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
BASE = "https://ibp.a2mac1.com"

products = json.loads(Path("/home/z/my-project/data/products_all.json").read_text())
one_id = products[0].get("productId") or products[0].get("resourceId")
print("test id:", one_id)

TESTS = [
    ("POST", "/api/visual/products", {"filters": [], "sorter": None, "page": {"number": 1, "size": 1}}, None),
    ("POST", "/api/products/compare/data", {"filters": []}, {"hideMappedProperties": "true"}),
    ("POST", "/api/products/compare/data/by-items", {"itemIds": [one_id]}, {"hideMappedProperties": "true"}),
    ("POST", "/api/products/compare/data", {"itemIds": [one_id]}, {"hideMappedProperties": "true"}),
    ("GET",  f"/api/products/{one_id}/hierarchies", None, None),
]
for method, path, body, params in TESTS:
    try:
        r = S.request(method, BASE + path, json=body, params=params, allow_redirects=False, timeout=90)
        txt = (r.text or "")[:220].replace("\n", " ")
        print(f"{method} {path} params={params} -> {r.status_code} | {txt}")
    except Exception as e:
        print(f"{method} {path} -> ERROR {e}")
    time.sleep(0.6)
