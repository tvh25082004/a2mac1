"""Chain: get-hierarchy-nodes (VOP) -> node-scoped compare -> extract gallery tokens -> download samples."""
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

# 1) nodes
r = S.post(f"{BASE}/api/visual/hierarchies/get-hierarchy-nodes",
           json={"productIds": [PID], "hierarchyId": VOP, "filters": []}, timeout=60)
log("get-hierarchy-nodes:", r.status_code, "bytes:", len(r.content))
if r.status_code != 200:
    print(r.text[:300]); raise SystemExit(1)
nodes = r.json()
Path("/home/z/my-project/data/vop_nodes.json").write_text(json.dumps(nodes, ensure_ascii=False))
flat = nodes if isinstance(nodes, list) else nodes.get("data") or nodes.get("nodes") or []
def walk(ns, depth=0, acc=None):
    acc = acc if acc is not None else []
    for n in ns if isinstance(ns, list) else []:
        if isinstance(n, dict):
            acc.append({"id": n.get("id"), "name": n.get("name"), "depth": depth,
                        "n_children": len(n.get("children") or [])})
            walk(n.get("children") or [], depth + 1, acc)
    return acc
listing = walk(flat)
log(f"nodes={len(listing)}")
for n in listing[:25]:
    print("  " * n["depth"] + f"{n['name']} (id={n['id']}, children={n['n_children']})")

# 2) node-scoped compare on every leaf with few children (limit 6 nodes)
leaves = [n for n in listing if n["n_children"] == 0][:6]
alltok = []
sae = {}
for nd in leaves:
    time.sleep(0.4)
    r2 = S.post(f"{BASE}/api/products/compare/hierarchy/{VOP}/node/{nd['id']}/data/by-products",
                params={"hideMappedProperties": "true"}, json=[PID], timeout=90)
    if r2.status_code != 200:
        log(f"node {nd['name']}: HTTP {r2.status_code}"); continue
    js = r2.json()
    pv = (js.get("values") or {}).get(PID) or {}
    props = sum(len(g.get("properties") or []) for g in (js.get("propertyGroups") or []))
    log(f"node {nd['name']}: props={props}, props_with_values={len(pv)}")
    if not pv:
        continue
    for propid, scenarios in pv.items():
        for scen, entries in (scenarios.items() if isinstance(scenarios, dict) else []):
            if not isinstance(entries, list): continue
            for e in entries:
                name = e.get("propertyName") or ""
                det = e.get("details") or {}
                if isinstance(det, dict) and det.get("token"):
                    alltok.append({"node": nd["name"], "name": name, "token": det["token"],
                                   "ext": det.get("extension"),
                                   "pub": det.get("publicUrls")})
                nm = str(name).lower()
                if any(k in nm for k in ("h95", "h102", "h129", "clearance", "opening", "height to ground")):
                    sae[f"{nd['name']}|{name}|{scen}"] = e.get("formatedValue")

print("SAE:", json.dumps(sae, ensure_ascii=False)[:800])
print("tokens:", len(alltok))
Path("/home/z/my-project/data/vop_node_compare_summary.json").write_text(
    json.dumps({"sae": sae, "tokens": alltok[:20]}, ensure_ascii=False, indent=1))

# 3) download 2 sample images
def kind_of(b):
    if b[:3] == b"\xff\xd8\xff": return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    return None
for i, g in enumerate(alltok[:2]):
    r3 = S.get(f"{BASE}/files/downloads/files", params={"token": g["token"], "api-version": "1.1"}, timeout=120)
    kind = kind_of(r3.content[:16]) if r3.status_code == 200 else None
    ext = kind or (g.get("ext") or "bin")
    f = DL / f"BYD_Tang_L_{i+1}_{str(g['name'])[:40].replace(' ', '_')}.{ext}"
    if r3.status_code == 200:
        f.write_bytes(r3.content)
    log(f"img {i+1}: HTTP {r3.status_code}, {len(r3.content)}b, kind={kind}, pub={json.dumps(g.get('pub'))[:120]}")
