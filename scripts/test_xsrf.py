#!/usr/bin/env python3
"""Test XSRF: fetch the XSRF-TOKEN cookie then send the X-XSRF-TOKEN header on POSTs."""
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

# 1. Some GET to receive the Set-Cookie XSRF-TOKEN
r0 = S.get(f"{BASE}/api/compare/items", timeout=60)
print("current cookies:", [c.name for c in S.cookies])
xsrf = S.cookies.get("XSRF-TOKEN")
print("XSRF-TOKEN:", (xsrf[:30] + "...") if xsrf else None)

if xsrf:
    S.headers["X-XSRF-TOKEN"] = xsrf
    print("\n== POST compare/item WITH XSRF ==")
    r = S.post(f"{BASE}/api/compare/item",
               json={"is3d": False, "item": {"itemId": PID}}, timeout=60)
    print("HTTP", r.status_code, "|", (r.text or "")[:400])
    print("\n== GET compare/items ==")
    r = S.get(f"{BASE}/api/compare/items", timeout=60)
    print("HTTP", r.status_code, "|", (r.text or "")[:900])
