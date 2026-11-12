#!/usr/bin/env python3
"""Two final shots: views + context to find projectId/scenarioId -> if present, add compare -> data."""
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

def brief(r, n=900):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

print("== GET views ==")
r = S.get(f"{BASE}/api/products/{PID}/views", timeout=60)
brief(r)
views = []
try:
    views = r.json() if r.status_code == 200 else []
except Exception:
    pass

proj = scen = None
if views and isinstance(views, list) and isinstance(views[0], dict):
    print("view keys:", list(views[0].keys()))
    for v in views:
        proj = v.get("projectId") or proj
        scen = v.get("scenarioId") or scen
        # dig deeper
        s = json.dumps(v)
        if not proj and "projectId" in s:
            import re as _re
            mm = _re.search(r'"projectId"\s*:\s*"([^"]+)"', s)
            if mm: proj = mm.group(1)
        if not scen and "scenarioId" in s:
            import re as _re
            mm = _re.search(r'"scenarioId"\s*:\s*"([^"]+)"', s)
            if mm: scen = mm.group(1)
print(f"projectId={proj} scenarioId={scen}")

print("== POST compare/item with project/scenario ==")
r = S.post(f"{BASE}/api/compare/item",
           json={"is3d": False, "item": {"itemId": PID, "projectId": proj, "scenarioId": scen}}, timeout=60)
brief(r, 500)

print("== GET compare/items ==")
r = S.get(f"{BASE}/api/compare/items", timeout=60)
brief(r, 900)

print("== POST compare/data ==")
r = S.post(f"{BASE}/api/products/compare/data", json={"itemIds": None},
           params={"hideMappedProperties": "true"}, timeout=120)
brief(r, 1500)
