"""A&U full harvester: Vehicle Occupant Packaging -> Package Measurements values + Media Gallery images
for ALL 621 cars on the A2MAC1 server.

Confirmed endpoints (session #15 probe, BYD Tang L EV 2025):
  POST api/visual/hierarchies/get-hierarchy-nodes   {productIds, hierarchyId, filters: []}
  POST api/products/compare/hierarchy/{VOP}/node/{nid}/data/by-products?hideMappedProperties=true   [pid]
  GET  files/downloads/files?token=...&api-version=1.1        (gallery JPG / zip via details.token)

Values -> data/vop_harvest/<pid>.json ; images -> download/VOP_media/<car>/ ; resume state -> data/vop_harvest_state.json
Token: /tmp/a2mac1_tok (fresh each session). Run ALONE (no concurrent bulk download) to avoid 403 block.
"""
import json, time, re, sys
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
VOP = "00000005ZT4GEU01"
DATA = Path("/home/z/my-project/data/vop_harvest"); DATA.mkdir(parents=True, exist_ok=True)
DL = Path("/home/z/my-project/download/VOP_media"); DL.mkdir(parents=True, exist_ok=True)
STATE_F = Path("/home/z/my-project/data/vop_harvest_state.json")
TIME_LIMIT = 3000  # an toan hon window token ~25-27p; dung khi gan het

_tokfile = Path("/tmp/a2mac1_tok")
TOK = _tokfile.read_text().strip()
S = requests.Session()
S.headers.update({"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
                  "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
                  "Content-Type": "application/json"})

START = time.time()
def left(): return TIME_LIMIT - (time.time() - START)
def log(*a): print(f"[{time.strftime('%H:%M:%S')}|{left():.0f}s]", *a, flush=True)

state = json.loads(STATE_F.read_text()) if STATE_F.exists() else {"done": {}, "imgs": {}}
products = json.load(open("/home/z/my-project/data/products_all.json"))

def safe_name(s): return re.sub(r"[^\w.-]+", "_", s).strip("_")[:80]

# nodes duoc chon: cay "Package Measurements" toan bo + (du phong) 3D Data v3 gallery
MEAS_ROOTS = {"000000093NWAEU01"}

def get_nodes(pid):
    r = S.post(f"{BASE}/api/visual/hierarchies/get-hierarchy-nodes",
               json={"productIds": [pid], "hierarchyId": VOP, "filters": []}, timeout=60)
    time.sleep(0.45)
    if r.status_code == 403:
        return "403"
    if r.status_code != 200:
        return None
    return r.json()

def node_ids_under(nodes, roots):
    """Flat node list -> ids cua cay con goc roots (ke ca root)."""
    by_parent = {}
    alln = {}
    for n in nodes:
        nid = n.get("hierarchyNodeId"); par = n.get("hierarchyNodeParentId")
        alln[nid] = n
        by_parent.setdefault(par, []).append(nid)
    keep = set()
    def add_root(rid):
        if rid not in alln:
            return
        keep.add(rid)
        stack = [rid]
        while stack:
            cur = stack.pop()
            for ch in by_parent.get(cur, []) or []:
                if ch not in keep:
                    keep.add(ch); stack.append(ch)
    for r_ in roots: add_root(r_)
    return keep

def compare_node(pid, nid):
    r = S.post(f"{BASE}/api/products/compare/hierarchy/{VOP}/node/{nid}/data/by-products",
               params={"hideMappedProperties": "true"}, json=[pid], timeout=90)
    time.sleep(0.45)
    if r.status_code == 403:
        return "403"
    if r.status_code != 200:
        return None
    return r.json()

def dl_media(token, outp):
    r = S.get(f"{BASE}/files/downloads/files", params={"token": token, "api-version": "1.1"}, timeout=180)
    time.sleep(0.45)
    if r.status_code != 200 or len(r.content) < 100:
        return f"HTTP{r.status_code}"
    outp.write_bytes(r.content)
    return "OK"

n_done = 0
for it in products:
    if left() < 120:
        log("GAN HET GIO — dung an toan, resume phien sau"); break
    pid = it["productId"]; car = it["resourceName"]
    if state["done"].get(pid):
        continue
    cdir = DL / safe_name(car); cdir.mkdir(parents=True, exist_ok=True)
    nodes = get_nodes(pid)
    if nodes == "403":
        log(f"403 tai nodes — nghi 20s roi dung luot (tranh block dai): {car}")
        time.sleep(20); break
    if not nodes:
        log(f"nodes fail {car}"); continue
    ids = node_ids_under(nodes, MEAS_ROOTS)
    if not ids:
        # xe khong co Package Measurements -> ghi done rong de khong retry mai
        (DATA / f"{pid}.json").write_text(json.dumps({"car": car, "has_measurements": False}, ensure_ascii=False))
        state["done"][pid] = {"car": car, "props": 0, "imgs": 0, "empty": True}
        n_done += 1; continue
    out = {"car": car, "pid": pid, "has_measurements": True, "nodes": {}, "media": []}
    nprops = nimgs = 0
    blocked = False
    for nid in sorted(ids):
        nd = next(n for n in nodes if n["hierarchyNodeId"] == nid)
        js = compare_node(pid, nid)
        if js == "403":
            log(f"403 tai compare node {nd['hierarchyNodeName']} — dung luot: {car}")
            blocked = True; time.sleep(15); break
        if js is None:
            continue
        pv = (js.get("values") or {}).get(pid) or {}
        groups = js.get("propertyGroups") or []
        propmeta = {}
        for g in groups:
            for p in g.get("properties") or []:
                propmeta[p.get("id")] = {"name": p.get("name"), "displayType": p.get("displayType"),
                                         "group": g.get("name") or (g.get("details") or {}).get("name")}
        nrecs = {}
        for propid, scenarios in pv.items():
            for scen, entries in (scenarios.items() if isinstance(scenarios, dict) else []):
                if not isinstance(entries, list): continue
                for e in entries:
                    meta = propmeta.get(propid, {})
                    nm = e.get("propertyName") or meta.get("name") or propid
                    det = e.get("details") or {}
                    tok = det.get("token") if isinstance(det, dict) else None
                    nrecs[f"{nm}|{scen}"] = {"value": e.get("formatedValue"), "unit": e.get("unitLabel")}
                    if tok:
                        ext = (det.get("extension") or "bin").lower()
                        fkey = f"{nid}_{propid}_{scen}_{safe_name(nm)}"
                        fpath = cdir / f"{fkey[:120]}.{ext}"
                        if not fpath.exists():
                            rr = dl_media(tok, fpath)
                            if rr != "OK":
                                log(f"  media fail {rr}: {nm}")
                                continue
                        nimgs += 1
                        out["media"].append({"node": nid, "node_name": nd["hierarchyNodeName"],
                                             "property": nm, "file": fpath.name, "ext": ext, "token": tok})
                nprops += 1
        out["nodes"][nid] = {"name": nd["hierarchyNodeName"], "n_props": nprops, "values": nrecs}
        nprops = 0 if False else nprops  # keep cumulative counting simple
    # recount props properly
    tot_props = sum(len(v["values"]) for v in out["nodes"].values())
    out["n_values"] = tot_props; out["n_images"] = len(out["media"])
    if not blocked or tot_props:
        (DATA / f"{pid}.json").write_text(json.dumps(out, ensure_ascii=False))
        state["done"][pid] = {"car": car, "props": tot_props, "imgs": len(out["media"])}
        n_done += 1
        log(f"{car}: {tot_props} values, {len(out['media'])} media")
    if blocked:
        break
    if n_done % 10 == 0:
        STATE_F.write_text(json.dumps(state, ensure_ascii=False, indent=1))

STATE_F.write_text(json.dumps(state, ensure_ascii=False, indent=1))
tot_c = len(state["done"]); tot_v = sum(v.get("props", 0) for v in state["done"].values())
tot_i = sum(v.get("imgs", 0) for v in state["done"].values())
log(f"XONG LUOT: +{n_done} xe nay | tong {tot_c}/621 xe, {tot_v} values, {tot_i} media")
