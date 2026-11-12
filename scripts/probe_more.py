#!/usr/bin/env python3
"""Quick probe of additional data sources: full-props, BOM, 3D, datatables."""
import os, re, json, sys, time
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

def t(tag, method, path, body=None, params=None, show=500):
    for i in range(3):
        r = S.request(method, BASE + path, json=body, params=params, timeout=90)
        if r.status_code in (401, 403) and i < 2:
            time.sleep(3); continue
        break
    n = len(r.content)
    print(f"[{tag}] {r.status_code} | {n/1024:.0f} KB")
    if r.status_code == 200 and n:
        try:
            d = r.json()
            if isinstance(d, dict):
                print("   keys:", list(d.keys())[:15])
                for k, v in d.items():
                    if isinstance(v, list) and v:
                        print(f"   [{k}] len={len(v)} sample:", json.dumps(v[0], ensure_ascii=False)[:250])
            elif isinstance(d, list):
                print(f"   list len={len(d)} sample:", json.dumps(d[0], ensure_ascii=False)[:250] if d else "")
        except Exception:
            print("   (non-json)", r.text[:150])
    elif r.status_code != 200:
        print("   ", r.text[:120])
    return r

ids = ["A0000004F0UTEU02", "A0000005FLUTEU01"]  # Acura MDX 2022, RDX 2019
t("has-3Dfiles", "GET", "/api/access/users/has-3Dfiles")
t("has-datatable", "GET", "/api/access/users/has-datatable")
r = t("compare FULL (hideMapped=false)", "POST", "/api/products/compare/data/by-products",
      ids, {"hideMappedProperties": "false"})
if r.status_code == 200:
    d = r.json()
    nprops = sum(len(g["properties"]) for g in d["propertyGroups"])
    print(f"   ==> propertyGroups: {len(d['propertyGroups'])}, total props: {nprops}")
    for g in d["propertyGroups"]:
        print(f"      - {g['propertyGroupName']}: {len(g['properties'])}")
    v = d["values"].get(ids[0], {})
    filled = sum(1 for k, vv in v.items() if isinstance(vv, dict) and any((vv.get(s) for s in vv)))
    print(f"   vehicle 1 has values for {filled}/{nprops} props")
t("bom/product", "GET", f"/api/products/bom/{ids[0]}")
t("bom/product POST", "POST", f"/api/products/bom/{ids[0]}", {})
t("compare/bom", "POST", "/api/products/compare/bom", ids)
t("hierarchies-3d", "GET", "/api/filters/hierarchies-3d")
t("quick-search part", "POST", "/api/quick-search/part", {"search": "bumper", "filters": [], "hierarchyId": None}, show=300)
