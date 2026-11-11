#!/usr/bin/env python3
"""Nước rút cuối: PUT compare/items (thay cả set) -> GET -> compare/data."""
import os, re, json, time, sys
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

def brief(r, n=600):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

print("== PUT compare/items (1 item, chỉ itemId) ==")
r = S.put(f"{BASE}/api/compare/items", json=[{"itemId": PID}], timeout=60)
brief(r)

print("== GET compare/items ==")
r = S.get(f"{BASE}/api/compare/items", timeout=60)
brief(r, 800)
items = []
try:
    items = r.json() if r.status_code == 200 else []
except Exception:
    pass
if items:
    print("item keys:", list(items[0].keys()))
    iid = items[0].get("itemId") or items[0].get("id")
    print("== POST compare/data (itemIds=[compare item id]) ==")
    r2 = S.post(f"{BASE}/api/products/compare/data", json={"itemIds": [iid]},
                params={"hideMappedProperties": "true"}, timeout=120)
    brief(r2, 1500)

print("== POST compare/item variant: projectId/scenarioId null ==")
r = S.post(f"{BASE}/api/compare/item", json={"is3d": False, "item": {"itemId": PID, "projectId": None, "scenarioId": None}}, timeout=60)
brief(r, 400)
