#!/usr/bin/env python3
"""BOM đúng chuẩn: POST api/products/bom/{columnset} body đầy đủ. Lưu ngay khi thành công."""
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
OUT = Path("/home/z/my-project/data")
OUT.mkdir(exist_ok=True)

def brief(r, n=500):
    t = (r.text or "")
    print(f"    HTTP {r.status_code} len={len(t)}: {t[:n]}")
    print()

HIDS = ["00000003LSK4EU01", "A000005AE6M1EU01"]  # 3D AutoReverse, Schedule & Content
for hid in HIDS:
    print(f"== BOM hierarchyId={hid} ==")
    body = {"productIds": [PID], "hierarchyId": hid, "page": {"number": 1, "size": 100},
            "search": "", "filters": [], "sorter": None, "selectedCostingProjects": None}
    r = S.post(f"{BASE}/api/products/bom/BillOfMaterial_Columns", json=body,
               params={"allowDynamicColumns": "true"}, timeout=120)
    brief(r, 800)
    if r.status_code == 200:
        try:
            j = r.json()
            if j and (isinstance(j, dict) and any(j.get(k) for k in ("rows", "items", "data", "columns")) or isinstance(j, list)):
                (OUT / f"bom_test_{hid}.json").write_text(json.dumps(j, ensure_ascii=False, indent=1))
                print(f"    [SAVED] bom_test_{hid}.json")
        except Exception:
            pass
    time.sleep(0.5)
