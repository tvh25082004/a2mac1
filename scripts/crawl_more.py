#!/usr/bin/env python3
"""Crawl urgently within the token window: 3D availability for 621 vehicles + hierarchy tree + BOM node + parts."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
HID = "A000005AE6M1EU01"

def t(tag, method, path, body=None, params=None):
    data = None
    for i in range(8):
        r = S.request(method, BASE + path, json=body, params=params, timeout=120)
        if r.status_code == 200:
            return r
        if r.status_code in (401, 403):
            print(f"[{tag}] {r.status_code} — warm-up, waiting 4s, retry {i+1}", flush=True)
            time.sleep(4)
            continue
        print(f"[{tag}] {r.status_code} | {len(r.content)/1024:.0f} KB", flush=True)
        return r
    print(f"[{tag}] FAIL after 8 attempts", flush=True)
    return r

products = json.loads((DATA / "products_all.json").read_text())
ids = [p["productId"] for p in products if p.get("productId")]
print("vehicles:", len(ids))

# 1) 3D availability per vehicle (chunks of 200)
avail = {}
for i in range(0, len(ids), 200):
    chunk = ids[i:i + 200]
    r = t(f"has-3Dfiles {i}-{i+len(chunk)}", "POST", "/api/access/users/has-3Dfiles", chunk)
    if r.status_code == 200 and r.content:
        d = r.json()
        if isinstance(d, dict):
            avail.update(d)
        elif isinstance(d, list):
            for x in d:
                if isinstance(x, dict) and x.get("productId"):
                    avail[x["productId"]] = x
        else:
            print("   type:", type(d), str(d)[:200])
print("3D avail entries:", len(avail), "| sample:", json.dumps(list(avail.items())[:2] if isinstance(avail, dict) else list(avail)[:2], ensure_ascii=False)[:300])
(DATA / "files_3d_availability.json").write_text(json.dumps(avail, ensure_ascii=False, indent=1))

# 2) hierarchy tree with mapped nodes
r = t("tree hierarchy", "POST", f"/api/hierarchies/{HID}", {"Filters": None, "IncludeMappedNodes": True})
if r.status_code == 200 and r.content:
    (DATA / "hierarchy_tree.json").write_text(r.text)
    d = r.json()
    if isinstance(d, list):
        print("   root nodes:", len(d), "| sample:", json.dumps(d[0], ensure_ascii=False)[:400])
    elif isinstance(d, dict):
        print("   keys:", list(d.keys())[:20], "|", json.dumps(d, ensure_ascii=False)[:400])

# 3) BOM for the first node (try a node from the tree)
node_id = None
try:
    if isinstance(d, list) and d:
        node_id = d[0].get("id") or d[0].get("hierarchyNodeId")
    elif isinstance(d, dict):
        ch = d.get("children") or d.get("nodes") or []
        if ch:
            node_id = ch[0].get("id") or ch[0].get("hierarchyNodeId")
except Exception as e:
    print("tree parse:", e)
print("node tried:", node_id)
if node_id:
    r = t("compare/bom node", "POST", "/api/products/compare/bom",
          {"hierarchyId": HID, "hierarchyNodeId": node_id, "isVisual": True})
    if r.status_code == 200 and r.content:
        (DATA / "bom_sample.json").write_text(r.text)
    r = t(f"bom/{HID} node", "POST", f"/api/products/bom/{HID}",
          {"productIds": ["A0000004F0UTEU02"], "hierarchyId": HID, "hierarchyNodeId": node_id,
           "page": {"number": 1, "size": 50}, "search": None, "filters": [], "sorter": None,
           "selectedCostingProjects": None},
          {"allowDynamicColumns": "true", "hideMappedProperties": "true",
           "hideMappedProductTypesProperties": "false", "hasMappedDataDisplayed": "false"})
    if r.status_code == 200 and r.content:
        (DATA / "bom_sample2.json").write_text(r.text)

# 4) parts under the hierarchy (page 1)
r = t("hierarchy parts p1", "POST", f"/api/hierarchies/{HID}/parts",
      {"filters": [], "sorter": None, "page": {"number": 1, "size": 50}},
      {"allowDynamicColumns": "true", "hideMappedProperties": "true", "hideMappedProductTypesProperties": "false"})
if r.status_code == 200 and r.content:
    (DATA / "hier_parts_sample.json").write_text(r.text)

# 5) 3D hierarchies
r = t("hierarchies-3d POST", "POST", "/api/filters/hierarchies-3d", {"filters": []})
if r.status_code == 200 and r.content:
    (DATA / "hierarchies_3d.json").write_text(r.text)
    print("   ", r.text[:300])
print("DONE")
