#!/usr/bin/env python3
"""Probe visual files (3D/CAD) packages + get-files cho 2 xe mẫu."""
import os, re, json
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
env = Path("/home/z/my-project/scripts/.env").read_text()
raw = env.split("A2MAC1_TOKEN='")[1].split("'")[0]
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": BASE, "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

PIDS = ["A0000004F0UTEU02", "00000001E3FYEU01"]  # Acura MDX 2022, Acura RDX 2019
HID = "A000005AE6M1EU01"

# 1) packages
r = S.get(BASE + "/api/visual/files/packages", params=[("productIds", p) for p in PIDS], timeout=60)
print("1) packages:", r.status_code, len(r.content))
if r.status_code == 200:
    d = r.json()
    print(json.dumps(d, indent=1)[:1800])

# 2) get-files (không hierarchyId)
body = {"productIds": PIDS, "isBookmark": False}
r = S.post(BASE + "/api/visual/files/get-files?api-version=2.0", json=body, timeout=60)
print("2) get-files:", r.status_code, len(r.content))
if r.status_code == 200:
    d = r.json()
    if isinstance(d, dict):
        print("keys:", list(d.keys()))
        print(json.dumps(d, indent=1)[:1500])
    else:
        print(json.dumps(d, indent=1)[:1500])

# 3) get-files với hierarchyId
body["hierarchyId"] = HID
r = S.post(BASE + "/api/visual/files/get-files?api-version=2.0", json=body, timeout=60)
print("3) get-files+hier:", r.status_code, len(r.content))
if r.status_code == 200:
    print(json.dumps(r.json(), indent=1)[:1200])
