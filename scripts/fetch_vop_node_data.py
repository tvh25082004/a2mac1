"""Node-scoped compare for VOP Schematics nodes -> measurement values + gallery tokens -> sample images."""
import json, time, sys
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
VOP = "00000005ZT4GEU01"
PID = sys.argv[1] if len(sys.argv) > 1 else "A0000074SYPAEU01"
CARNAME = sys.argv[2] if len(sys.argv) > 2 else "BYD_Tang_L"
TOK = Path("/tmp/a2mac1_tok").read_text().strip()
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
                  "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
                  "Content-Type": "application/json"})
DL = Path("/home/z/my-project/download/VOP_schematic_test"); DL.mkdir(parents=True, exist_ok=True)

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

NODES = [
    ("Package Measurements", "000000093NWAEU01"),
    ("Schematics", "000000AFH8LREU02"),
    ("Exterior Dimensions", "0000000AWFS9EU01"),
    ("Exterior/Height", "00000004YO7QEU01"),
]
alltok, sae, gnames = [], {}, []
for nm, nid in NODES:
    time.sleep(0.4)
    r = S.post(f"{BASE}/api/products/compare/hierarchy/{VOP}/node/{nid}/data/by-products",
               params={"hideMappedProperties": "true"}, json=[PID], timeout=90)
    if r.status_code != 200:
        log(f"{nm}: HTTP {r.status_code}"); continue
    js = r.json()
    groups = js.get("propertyGroups") or []
    pv = (js.get("values") or {}).get(PID) or {}
    gnames.append({"node": nm, "groups": [(g.get("name") or (g.get("details") or {}).get("name")) for g in groups],
                   "props": sum(len(g.get("properties") or []) for g in groups), "props_with_values": len(pv)})
    log(f"{nm}: groups={len(groups)}, props={sum(len(g.get('properties') or []) for g in groups)}, values={len(pv)}")
    Path(f"/home/z/my-project/data/vop_cmp_{CARNAME}_{nid}.json").write_text(json.dumps(js, ensure_ascii=False))
    for propid, scenarios in pv.items():
        for scen, entries in (scenarios.items() if isinstance(scenarios, dict) else []):
            if not isinstance(entries, list): continue
            for e in entries:
                name = e.get("propertyName") or ""
                det = e.get("details") or {}
                if isinstance(det, dict) and det.get("token"):
                    alltok.append({"node": nm, "name": name, "token": det["token"], "ext": det.get("ext" "ension") if False else det.get("extension"), "pub": det.get("publicUrls")})
                nml = str(name).lower()
                if any(k in nml for k in ("h95", "h102", "h129", "clearance", "opening", "height")):
                    sae[f"{nm}|{name}|{scen}"] = e.get("formatedValue")

print("GROUPS:", json.dumps(gnames, ensure_ascii=False)[:700])
print("SAE:", json.dumps(sae, ensure_ascii=False)[:900])
print("TOKENS:", len(alltok))
for t in alltok[:8]:
    print("  tok:", t["node"], "|", t["name"], "| ext:", t.get("ext") if isinstance(t, dict) else "?", "| pub:", json.dumps(t.get("pub"))[:100] if isinstance(t, dict) else "")
Path(f"/home/z/my-project/data/vop_schem_summary_{CARNAME}.json").write_text(json.dumps({"sae": sae, "tokens": alltok[:20]}, ensure_ascii=False, indent=1))

def kind_of(b):
    if b[:3] == b"\xff\xd8\xff": return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    return None
for i, g in enumerate(alltok[:3]):
    r3 = S.get(f"{BASE}/files/downloads/files", params={"token": g["token"], "api-version": "1.1"}, timeout=120)
    kind = kind_of(r3.content[:16]) if r3.status_code == 200 else None
    ext = kind or (g.get("ext") or "bin")
    f = DL / f"{CARNAME}_{i+1}_{str(g['name'])[:38].replace(' ', '_')}.{ext}"
    if r3.status_code == 200:
        f.write_bytes(r3.content)
    log(f"img {i+1}: HTTP {r3.status_code}, {len(r3.content)}b, kind={kind} -> {f.name}")
