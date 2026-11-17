"""Dump VOP hierarchies parts head+rows (measurement table) for BYD Tang L EV 2025."""
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

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

time.sleep(3)
r = S.post(f"{BASE}/api/hierarchies/{VOP}/parts",
           params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
           json={"filters": [f"product-id eq {PID}"], "sorter": None,
                 "page": {"number": 1, "size": 30}}, timeout=60)
log("parts:", r.status_code)
js = r.json()
head = js.get("head") or []
rows = js.get("rows") or []
log(f"head={len(head)} cols, rows={len(rows)}")
print("HEAD sample:", json.dumps(head[:6], ensure_ascii=False)[:900])
print("ROW-0 sample:", json.dumps(rows[0], ensure_ascii=False)[:1200] if rows else None)
# find any gallery/media/token fields
blob = json.dumps(js)[:300000]
for kw in ("token", "media", "gallery", "schematic"):
    print(f"kw '{kw}' in response:", blob.lower().count(kw.lower()))
Path("/home/z/my-project/data/vop_parts_dump.json").write_text(json.dumps(js, ensure_ascii=False))
log("saved full -> data/vop_parts_dump.json")

# retry searchable-properties after backoff
time.sleep(5)
r2 = S.post(f"{BASE}/api/input/products/hierarchies/{VOP}/searchable-properties",
            json={"productIds": [PID]}, timeout=60)
log("searchable-properties retry:", r2.status_code)
if r2.status_code == 200:
    props = r2.json()
    n = len(props) if isinstance(props, list) else None
    log("props n:", n)
    Path("/home/z/my-project/data/vop_searchable_props.json").write_text(json.dumps(props, ensure_ascii=False))
