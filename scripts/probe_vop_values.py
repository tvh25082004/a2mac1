"""Probe VOP Package Measurement properties+values via searchable-properties & compare API.
1 product (BYD Tang L EV 2025), few requests, paced. Token from /tmp/a2mac1_tok.
Results -> /home/z/my-project/data/vop_values_probe.json (no token inside).
"""
import json, time, re
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
VOP = "00000005ZT4GEU01"
PID = "A0000074SYPAEU01"  # BYD Tang L EV 2025
TOK = Path("/tmp/a2mac1_tok").read_text().strip()
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
                  "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
                  "Content-Type": "application/json"})
OUT = {}

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

# 1) searchable-properties for VOP hierarchy
r = S.post(f"{BASE}/api/input/products/hierarchies/{VOP}/searchable-properties",
           json={"productIds": [PID]}, timeout=60)
log("searchable-properties:", r.status_code)
try:
    props = r.json()
    OUT["searchable_properties_http"] = r.status_code
    OUT["searchable_properties_n"] = len(props) if isinstance(props, list) else None
    if isinstance(props, list):
        sgal = [p for p in props if isinstance(p, dict) and (p.get("displayType") == "gallery" or "gallery" in str(p.get("displayType", "")).lower())]
        OUT["gallery_props_n"] = len(sgal)
        OUT["prop_names_sample"] = [p.get("propertyName") or p.get("name") for p in props[:60] if isinstance(p, dict)]
        OUT["gallery_props_sample"] = [{k: p.get(k) for k in ("propertyId", "propertyName", "displayType", "propertyGroupId")} for p in sgal[:10]]
        # names containing SAE/H measurement keywords
        kw = [p.get("propertyName") or p.get("name") for p in props if isinstance(p, dict)
              and any(k in str(p.get("propertyName", "")).lower() for k in ("sae h", "h95", "h102", "h129", "clearance", "opening height"))]
        OUT["sae_like_names"] = kw[:30]
except Exception as ex:
    OUT["searchable_properties_err"] = repr(ex); log("ERR1", repr(ex)[:200])
time.sleep(0.4)

# 2) hierarchy parts (values live on parts?) with corrected body variants
for label, body in [
    ("parts-v1", {"filters": [f"product-id eq {PID}"], "sorter": None, "page": {"number": 1, "size": 30}}),
    ("parts-v2", {"filters": [f"product-id eq '{PID}'"], "sorter": None, "page": {"number": 1, "size": 30}}),
]:
    try:
        r = S.post(f"{BASE}/api/hierarchies/{VOP}/parts",
                   params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
                   json=body, timeout=60)
        js = r.json() if r.status_code == 200 else None
        keys = list(js.keys()) if isinstance(js, dict) else f"list[{len(js)}]" if isinstance(js, list) else None
        log(f"hier parts {label}:", r.status_code, "keys:", keys)
        OUT[f"hier_parts_{label}"] = {"http": r.status_code, "top_keys": keys,
                                      "n_data": len(js.get("data", [])) if isinstance(js, dict) and isinstance(js.get("data"), list) else None}
        if isinstance(js, dict):
            for k in ("data", "items", "records", "parts", "values"):
                if isinstance(js.get(k), list) and js[k]:
                    OUT[f"hier_parts_{label}_first"] = json.dumps(js[k][0], ensure_ascii=False)[:500]
                    break
    except Exception as ex:
        OUT[f"hier_parts_{label}_err"] = repr(ex); log("ERR2", repr(ex)[:200])
    time.sleep(0.4)

Path("/home/z/my-project/data/vop_values_probe.json").write_text(json.dumps(OUT, ensure_ascii=False, indent=1))
log("saved -> data/vop_values_probe.json")
print(json.dumps({k: v for k, v in OUT.items() if k != "prop_names_sample"}, ensure_ascii=False)[:1500])
