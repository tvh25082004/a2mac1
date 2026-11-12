#!/usr/bin/env python3
"""BOM columns + datatables + chart-data — find the real source of spec tables."""
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

def brief(r, n=800):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

print("== BOM BillOfMaterial_Columns ==")
r = S.post(f"{BASE}/api/products/bom/BillOfMaterial_Columns", json={"productIds": [PID]}, timeout=120)
brief(r, 1200)

print("== datatables of the vehicle ==")
r = S.post(f"{BASE}/api/products/{PID}/datatables", json={"filters": [], "page": {"number": 1, "size": 10}, "search": "", "sorter": None}, timeout=60)
brief(r, 800)

print("== chart-data ==")
r = S.post(f"{BASE}/api/products/chart-data/resources/", json={"filters": [], "page": {"number": 1, "size": 5}}, timeout=60)
brief(r, 600)
