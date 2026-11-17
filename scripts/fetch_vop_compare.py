"""Fetch hierarchy-scoped compare data (Package Measurements values + media gallery tokens)
for BYD Tang L EV 2025 via api/products/compare/hierarchy/{VOP}/data/by-products.
Then download 2 sample schematic images via token. Results -> data/vop_compare_dump.json,
images -> download/VOP_schematic_test/.
"""
import json, time
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
VOP = "00000005ZT4GEU01"
PID = "A0000074SYPAEU01"
TOK = Path("/tmp/a2mac1_tok").read_text().strip()
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
                  "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
                  "Content-Type": "application/json"})
DL = Path("/home/z/my-project/download/VOP_schematic_test"); DL.mkdir(parents=True, exist_ok=True)

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

r = S.post(f"{BASE}/api/products/compare/hierarchy/{VOP}/data/by-products",
           params={"hideMappedProperties": "true"}, json=[PID], timeout=90)
log("compare hierarchy:", r.status_code, "bytes:", len(r.content))
if r.status_code != 200:
    print(r.text[:300]); raise SystemExit(1)
js = r.json()
Path("/home/z/my-project/data/vop_compare_dump.json").write_text(json.dumps(js, ensure_ascii=False))

groups = js.get("propertyGroups") or []
vals = js.get("values") or {}
log(f"propertyGroups={len(groups)}, values cars={len(vals)}")

# summarize groups + count gallery properties
out = {"groups": [], "gallery_tokens": [], "sae_values": {}}
for g in groups:
    gid = g.get("id"); gname = g.get("name") or (g.get("details") or {}).get("name")
    props = g.get("properties") or []
    ngal = 0
    for p in props:
        dt = str(p.get("displayType", ""))
        if "gallery" in dt.lower() or "image" in dt.lower():
            ngal += 1
    out["groups"].append({"id": gid, "name": gname, "props": len(props), "gallery_props": ngal})
log("groups:", json.dumps(out["groups"], ensure_ascii=False)[:800])

# walk values for the product: propertyId -> scenario -> entries; find tokens & SAE values
pv = vals.get(PID) or {}
log("properties with values:", len(pv))
galtok = []
sae = {}
for propid, scenarios in pv.items():
    for scen, entries in (scenarios.items() if isinstance(scenarios, dict) else []):
        if not isinstance(entries, list): continue
        for e in entries:
            name = e.get("propertyName") or ""
            fv = e.get("formatedValue")
            det = e.get("details") or {}
            if isinstance(det, dict) and det.get("token"):
                galtok.append({"propertyId": propid, "name": name, "token": det["token"],
                               "ext": det.get("extension"), "url": (det.get("publicUrls") or {})})
            if name and any(k in str(name).lower() for k in ("h95", "h102", "h129", "clearance", "opening", "height to ground")):
                sae[f"{name}|{scen}"] = fv
out["gallery_tokens"] = galtok[:12]
out["sae_values"] = sae
log("gallery tokens:", len(galtok), "| SAE-ish values:", json.dumps(sae, ensure_ascii=False)[:500])
Path("/home/z/my-project/data/vop_compare_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

# download 2 sample images
def kind_of(b):
    if b[:3] == b"\xff\xd8\xff": return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    return None
for i, g in enumerate(galtok[:2]):
    t = g["token"]
    r2 = S.get(f"{BASE}/files/downloads/files", params={"token": t, "api-version": "1.1"}, timeout=120)
    kind = kind_of(r2.content[:16]) if r2.status_code == 200 else None
    ext = kind or (g.get("ext") or "bin")
    f = DL / f"BYD_Tang_L_EV_2025_{i+1}_{g['name'][:40].replace(' ', '_')}.{ext}"
    if r2.status_code == 200:
        f.write_bytes(r2.content)
    log(f"download {i+1}: HTTP {r2.status_code}, {len(r2.content)} bytes, kind={kind} -> {f.name}")

print("SAE_VALUES:", json.dumps(sae, ensure_ascii=False))
