#!/usr/bin/env python3
"""Diag v2: try the endpoints that read available specs before the token dies."""
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
PID = "A0000004F0UTEU02"  # Acura MDX 2022

def show(tag, r, maxlen=700):
    txt = (r.text or "")
    print(f"--- {tag} -> {r.status_code}, len={len(txt)}")
    print(txt[:maxlen].replace("\n", " "))
    print()

# 1. FULL list of hierarchies of one vehicle
r = S.get(f"{BASE}/api/products/{PID}/hierarchies", timeout=60)
try:
    hiers = r.json()
    print(f"HIERARCHIES of {PID}: {[ (h.get('id'), h.get('name')) for h in hiers ]}")
except Exception:
    show("hierarchies", r)

hid = hiers[0]["id"] if r.status_code == 200 and hiers else "A000005AE6M1EU01"

# 2. searchable-properties per hierarchy
r = S.get(f"{BASE}/api/products/{PID}/hierarchies/{hid}/searchable-properties", timeout=60)
show(f"searchable-properties [{hid}]", r, 900)

# 3. node tree of the first hierarchy (direct, without parentNodeId)
r = S.post(f"{BASE}/api/hierarchies/{hid}", json={}, timeout=60)
show(f"tree [{hid}]", r, 900)

# 4. current compare set of the user
r = S.get(f"{BASE}/api/compare/items", timeout=60)
show("compare/items", r, 400)

# 5. available-data of the product per hierarchy
r = S.post(f"{BASE}/api/products/{PID}/available-data", json={"filters": []},
           params={"hierarchyId": hid, "checkSimilarity": "false"}, timeout=60)
show("available-data", r, 600)
