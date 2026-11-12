#!/usr/bin/env python3
"""Quick test of the endpoint that dumps a product's full data (run while the token is still valid)."""
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
ids = [p.get("productId") for p in products[:2]]
print("test ids:", ids)

TESTS = [
    ("POST", "/api/input/products/data?api-version=2.0", {"productIds": ids, "filters": [], "helpersListId": None}),
    ("POST", "/api/input/products/list?api-version=2.0", {"productIds": ids}),
    ("GET",  "/api/input/products/" + ids[0], None),
]
for method, path, body in TESTS:
    try:
        r = S.request(method, BASE + path, json=body, allow_redirects=False, timeout=90)
        txt = (r.text or "")
        print(f"--- {method} {path} -> {r.status_code}, len={len(txt)}")
        print(txt[:600].replace("\n", " "))
        try:
            j = json.loads(txt)
            if isinstance(j, list) and j:
                print("    [0] keys:", list(j[0].keys())[:30])
            elif isinstance(j, dict):
                print("    top keys:", list(j.keys())[:30])
        except Exception:
            pass
    except Exception as e:
        print(f"--- {method} {path} -> ERROR {e}")
    time.sleep(0.6)
