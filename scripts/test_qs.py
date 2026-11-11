#!/usr/bin/env python3
"""quick-search đúng body -> tìm 1 xe kèm projectId/scenarioId -> compare item -> compare/data."""
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

def brief(r, n=700):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

print("== quick-search 'MDX' ==")
r = S.post(f"{BASE}/api/quick-search?api-version=2.0",
           json={"search": "MDX", "filters": [], "hierarchyId": None, "hierarchyNodeId": None}, timeout=60)
brief(r, 1200)
prods = []
try:
    j = r.json()
    prods = j.get("products", []) if isinstance(j, dict) else []
except Exception:
    pass
print(f"products: {len(prods)}")
if prods:
    p0 = prods[0]
    print("product keys:", list(p0.keys()))
    print(json.dumps(p0, ensure_ascii=False)[:1500])
