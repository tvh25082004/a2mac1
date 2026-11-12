#!/usr/bin/env python3
"""First pass: test the compare flow — POST item -> GET items -> compare/data."""
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
PID = "A0000004F0UTEU02"  # Acura MDX SH-AWD A-SPEC 2022

def show(tag, r, maxlen=800):
    txt = (r.text or "")
    print(f"--- {tag} -> {r.status_code}, len={len(txt)}")
    print(txt[:maxlen].replace("\n", " "))
    print()
    return r

# 0. is the token still alive?
r = S.get(f"{BASE}/api/compare/items", timeout=60)
if r.status_code in (401, 403):
    print(f"TOKEN no longer accepted: {r.status_code}")
    sys.exit(1)
print(f"TOKEN ALIVE ({r.status_code}) | current compare items: {r.text[:200]}")

# 1. add one item to the compare set
r = S.post(f"{BASE}/api/compare/item", json={"is3d": False, "item": {"itemId": PID}}, timeout=60)
show("POST compare/item {is3d:false, item:{itemId}}", r, 500)

# 2. view the compare set
r = S.get(f"{BASE}/api/compare/items", timeout=60)
show("GET compare/items", r, 900)
