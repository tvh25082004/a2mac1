#!/usr/bin/env python3
"""Node data: tech specs per node of one vehicle — try multiple body/params variants."""
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
PID = "A0000004F0UTEU02"     # Acura MDX
HID = "A000005AE6M1EU01"     # Schedule & Content
NID = "A000005AE6MJEU01"     # Exterior Lighting node

def brief(r, n=1000):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

print(f"== POST node/data {PID}/{HID}/{NID} ==")
r = S.post(f"{BASE}/api/products/{PID}/hierarchies/{HID}/nodes/{NID}/data", json={}, timeout=60)
brief(r)

print("== variant: body {propertyIds: []} + params ==")
r = S.post(f"{BASE}/api/products/{PID}/hierarchies/{HID}/nodes/{NID}/data",
           json={}, params={"api-version": "2.0"}, timeout=60)
brief(r)

print("== GET variant ==")
r = S.get(f"{BASE}/api/products/{PID}/hierarchies/{HID}/nodes/{NID}/data", timeout=60)
brief(r)
