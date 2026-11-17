"""Probe A2MAC1 'Vehicle Occupant Packaging -> Package Measurements -> Schematics'
(Media Gallery schematic images, JPG/PNG) + SAE measurement values, per the A&U team request.

Run ONLY with a fresh token:  put JWT in /tmp/a2mac1_tok  then  python3 scripts/probe_vop_schematic.py
Results -> data/vop_probe_results.json ; test images -> download/VOP_schematic_test/
NO token is ever printed or saved into results.
"""
import json, sys, time, re
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
DL = Path("/home/z/my-project/download/VOP_schematic_test")
DL.mkdir(parents=True, exist_ok=True)
VOP = "00000005ZT4GEU01"  # Vehicle Occupant Packaging hierarchy

_tokfile = Path("/tmp/a2mac1_tok")
if _tokfile.exists():
    TOK = _tokfile.read_text().strip()
else:
    raw = (Path(__file__).parent / ".env").read_text().split("A2MAC1_TOKEN=")[1].split("\n")[0].strip().strip("'")
    TOK = re.search(r"access_token=([^;\s]+)", raw).group(1)
H = {"Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
     "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
S = requests.Session(); S.headers.update(H)

# test cars: BYD Tang L EV 2025 (in the user's screenshot), VF8, L60, Navara (CAD-covered car)
CARS = {
    "BYD Tang L EV 2025": "A0000074SYPAEU01",
    "VinFast VF8 Plus 2023": "A00000552G3KEU01",
    "Onvo L60 60kWh 4X4 2024": "A000004QZ0HYEU01",
    "Nissan Navara 2.3 Calibre V 7AT 2021": "A0000008OKW7EU02",
}
RES = {"tests": [], "images": [], "measurements": {}}

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

def record(name, ok, info):
    RES["tests"].append({"test": name, "ok": ok, "info": info})
    log(("OK " if ok else "FAIL ") + name + " :: " + str(info)[:220])

def looks_like_image(b: bytes):
    if b[:3] == b"\xff\xd8\xff": return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    if b[:4] == b"GIF8": return "gif"
    if b[:2] == b"BM": return "bmp"
    if b[:5].lower() == b"<?xml" or b[:4] == b"<svg": return "svg"
    if b[:4] == b"%PDF": return "pdf"
    return None

# ---------- Test A: get-files on VOP hierarchy -> look for image entries ----------
for car, pid in CARS.items():
    try:
        r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
                   json={"productIds": [pid], "hierarchyId": VOP, "isBookmark": False}, timeout=60)
        if r.status_code != 200:
            record(f"A get-files {car}", False, f"HTTP {r.status_code}")
            continue
        entries = r.json() or []
        exts = {}
        imgs = []
        for e in entries:
            nm = str(e.get("name") or e.get("fileName") or "")
            ext = nm.rsplit(".", 1)[-1].lower() if "." in nm else "(none)"
            exts[ext] = exts.get(ext, 0) + 1
            if ext in ("jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tif", "tiff"):
                imgs.append(e)
        record(f"A get-files {car}", True, f"{len(entries)} entries, exts={exts}, image-entries={len(imgs)}")
        for e in imgs[:6]:
            RES["images"].append({"car": car, "pid": pid, "entry": {k: e.get(k) for k in
                                  ("id", "name", "fileName", "token", "extension", "label", "isDownloadable")}})
        # stash full first entry to see schema
        if entries:
            RES.setdefault("entry_schema", {"car": car, "keys": list(entries[0].keys()),
                                            "sample": {k: entries[0].get(k) for k in list(entries[0].keys())[:14]}})
    except Exception as ex:
        record(f"A get-files {car}", False, repr(ex))
    time.sleep(0.4)

# ---------- Test B: hierarchies/{VOP}/parts -> measurement records (like Schedule & Content) ----------
for car, pid in CARS.items():
    try:
        r = S.post(f"{BASE}/api/hierarchies/{VOP}/parts",
                   params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
                   json={"filters": [f"product-id eq {pid}"], "sorter": None,
                         "page": {"number": 1, "size": 50}}, timeout=60)
        if r.status_code != 200:
            record(f"B hier-parts {car}", False, f"HTTP {r.status_code} {r.text[:120]}")
            continue
        js = r.json()
        recs = js.get("data") or js.get("items") or js.get("records") or []
        cols = js.get("columns") or js.get("properties") or []
        sample_keys = list(recs[0].keys())[:20] if recs and isinstance(recs[0], dict) else None
        RES["measurements"][car] = {"http": 200, "n_records": len(recs),
                                    "sample_keys": sample_keys,
                                    "columns_sample": [c.get("name") for c in cols[:20] if isinstance(c, dict)] if cols else None,
                                    "raw_first": json.dumps(recs[0], ensure_ascii=False)[:600] if recs else None}
        record(f"B hier-parts {car}", True, f"{len(recs)} records")
    except Exception as ex:
        record(f"B hier-parts {car}", False, repr(ex))
    time.sleep(0.4)

# ---------- Test C: download candidate image tokens (magic-byte check) ----------
# also try the car "pictureFile"-style download for VOP entries that carry tokens
for img in RES["images"][:6]:
    tok = (img.get("entry") or {}).get("token")
    if not tok:
        continue
    try:
        r = S.get(f"{BASE}/files/downloads/files", params={"token": tok, "api-version": "1.1"}, timeout=90)
        kind = looks_like_image(r.content[:16]) if r.status_code == 200 else None
        fname = f"{img['car'].replace(' ', '_')}_{img['entry'].get('name', 'img')}.{kind or 'bin'}"
        if kind:
            (DL / fname).write_bytes(r.content)
        record(f"C download {img['car']}/{img['entry'].get('name')}",
               r.status_code == 200, f"HTTP {r.status_code}, bytes={len(r.content)}, kind={kind}")
    except Exception as ex:
        record(f"C download {img['car']}", False, repr(ex))
    time.sleep(0.4)

# ---------- Test D: best-effort discovery of media-gallery endpoints ----------
GUESS = [
    ("GET", f"{BASE}/api/visual/media?productId=A0000074SYPAEU01"),
    ("GET", f"{BASE}/api/products/A0000074SYPAEU01/media"),
    ("GET", f"{BASE}/api/media?productId=A0000074SYPAEU01"),
    ("POST", f"{BASE}/api/visual/files/media-gallery", {"productIds": ["A0000074SYPAEU01"]}),
]
for g in GUESS:
    method, url = g[0], g[1]
    body = g[2] if len(g) > 2 else None
    try:
        r = (S.post(url, json=body, timeout=30) if method == "POST" else S.get(url, timeout=30))
        ct = r.headers.get("content-type", "")
        kind = looks_like_image(r.content[:16]) if r.status_code == 200 and "image" in ct else None
        record(f"D {method} {url.split('.com')[1]}", r.status_code in (200, 204),
               f"HTTP {r.status_code}, ct={ct}, bytes={len(r.content)}, kind={kind}")
    except Exception as ex:
        record(f"D {method} {url}", False, repr(ex))

# ---------- persist results (token-free) ----------
out = DATA / "vop_probe_results.json"
out.write_text(json.dumps(RES, ensure_ascii=False, indent=1))
log(f"saved -> {out}")
n_ok = sum(1 for t in RES["tests"] if t["ok"])
log(f"SUMMARY: {n_ok}/{len(RES['tests'])} tests OK, {len(RES['images'])} image entries, {len(DL.glob('*'))} images downloaded")
