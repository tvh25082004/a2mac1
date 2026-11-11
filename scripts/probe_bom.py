#!/usr/bin/env python3
"""Probe BOM + 3D với đúng body theo bundle. Chạy NGAY trước khi token hết."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
BASE = "https://ibp.a2mac1.com"
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
HID = "A000005AE6M1EU01"  # Schedule & Content
IDS = ["A0000004F0UTEU02", "A0000005FLUTEU01"]

def t(tag, method, path, body=None, params=None):
    r = S.request(method, BASE + path, json=body, params=params, timeout=90)
    print(f"[{tag}] {r.status_code} | {len(r.content)/1024:.0f} KB")
    if r.status_code == 200 and r.content:
        try:
            d = r.json()
            if isinstance(d, dict):
                print("   keys:", list(d.keys())[:15])
                for k, v in d.items():
                    if isinstance(v, list) and v:
                        print(f"   [{k}] len={len(v)} sample:", json.dumps(v[0], ensure_ascii=False)[:350])
            elif isinstance(d, list) and d:
                print(f"   list len={len(d)} sample:", json.dumps(d[0], ensure_ascii=False)[:350])
        except Exception:
            print("   ", r.text[:150])
    elif r.status_code >= 400:
        print("   ", r.text[:180])
    return r

r = t("compare/bom", "POST", "/api/products/compare/bom",
      {"hierarchyId": HID, "hierarchyNodeId": None, "isVisual": True})
t("bom/hid (2 xe)", "POST", f"/api/products/bom/{HID}",
  {"productIds": IDS, "hierarchyId": HID, "page": {"number": 1, "size": 50},
   "search": None, "filters": [], "sorter": None, "selectedCostingProjects": None},
  {"allowDynamicColumns": "true", "hideMappedProperties": "true",
   "hideMappedProductTypesProperties": "false", "hasMappedDataDisplayed": "false"})
t("has-3Dfiles POST", "POST", "/api/access/users/has-3Dfiles", {})
