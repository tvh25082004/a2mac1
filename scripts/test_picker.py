#!/usr/bin/env python3
"""All-in-one: picker -> project/scenario id -> compare item -> compare/data matrix."""
import os, re, json, time, sys
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

def brief(r, n=500):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

# 1. picker: lấy product kèm projectId/scenarioId
body = {"filters": [], "sorter": None, "page": {"number": 1, "size": 3},
        "dataContext": None, "resourceId": None, "withOwnerShip": False,
        "includesMappingProductTypeData": False}
r = S.post(f"{BASE}/api/products/picker", json=body, timeout=60)
print("== PICKER ==")
brief(r, 900)
items = []
if r.status_code == 200:
    try:
        j = r.json()
        if isinstance(j, dict):
            for k in ("items", "products", "results", "data"):
                if isinstance(j.get(k), list):
                    items = j[k]; break
        elif isinstance(j, list):
            items = j
    except Exception:
        pass
print(f"picker items: {len(items)}")
if items:
    print("keys:", list(items[0].keys()))
    print(json.dumps(items[0], ensure_ascii=False)[:1200])
