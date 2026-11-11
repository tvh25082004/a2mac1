#!/usr/bin/env python3
"""Probe nhanh các endpoint POST để kiểm tra (1) token còn được server chấp nhận không, (2) body đúng dạng gì.
KHÔNG in token."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
tok = m.group(1) if m else raw

s = requests.Session()
s.headers.update({
    "Cookie": f"access_token={tok}",
    "Authorization": f"Bearer {tok}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
})
BASE = "https://ibp.a2mac1.com"

PROBES = [
    ("POST", "/api/quick-search?api-version=2.0", {"query": "Toyota"}),
    ("POST", "/api/filters/hierarchies/get-part-hierarchies?api-version=2.0", {}),
    ("POST", "/api/hierarchies/A000005AE6M1EU01", {}),
    ("POST", "/api/hierarchies/A000005AE6M1EU01", {"parentNodeId": None}),
    ("GET",  "/api/products?api-version=2.0", None),
    ("GET",  "/api/vehicles?api-version=2.0", None),
]

for method, path, body in PROBES:
    try:
        r = s.request(method, BASE + path, json=body, allow_redirects=False, timeout=40)
        txt = (r.text or "")
        snippet = txt[:300].replace("\n", " ")
        print(f"{method} {path} body={json.dumps(body)[:60]} -> HTTP {r.status_code} | {snippet}")
        print("-" * 100)
        time.sleep(0.8)
    except Exception as e:
        print(f"{method} {path} -> ERROR {e}")
