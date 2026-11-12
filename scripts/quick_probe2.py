#!/usr/bin/env python3
"""Quick test: auth + private images + parts filter for multiple vehicles."""
import os, re, json, time
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")

raw = os.getenv("A2MAC1_TOKEN", "") or Path(".env").read_text().split("A2MAC1_TOKEN='")[1].split("'")[0]
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": BASE, "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

# 1) auth check
r = S.get(BASE + "/api/products/quick-search?q=Audi&limit=2", timeout=30)
print("1) auth:", r.status_code, len(r.content))

# 2) private images: /files/downloads/files?token=<pictureToken>
products = json.loads((DATA / "products_all.json").read_text())
p = next(x for x in products if x["productId"] == "A000006XCOMIEU01")
pf = p["pictureFile"]
ptok = pf["details"]["token"]
for pat in ["/files/downloads/files", "/api/files/downloads/files"]:
    r = S.get(BASE + pat, params={"token": ptok, "api-version": "1.1"}, timeout=30)
    ct = r.headers.get("content-type", "")
    print(f"2) {pat}: {r.status_code} {ct[:30]} {len(r.content)}")
    if r.status_code == 200 and ("image" in ct or "octet" in ct):
        Path("/tmp/priv_img.jpg").write_bytes(r.content)
        print("   SAVED /tmp/priv_img.jpg")
        break

# 3) parts filter 1 vehicle vs multiple vehicles (OR)
HID = "A000005AE6M1EU01"
body1 = {"filters": ["product-id eq A0000004F0UTEU02"], "sorter": None, "page": {"number": 1, "size": 50}}
r = S.post(BASE + f"/api/hierarchies/{HID}/parts", json=body1,
           params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
           timeout=60)
print("3a) parts 1 vehicle:", r.status_code, len(r.content))
if r.status_code == 200:
    d = r.json(); print("   rows:", len(d.get("rows", [])))

f2 = ["product-id eq A0000004F0UTEU02", "product-id eq 00000001E3FYEU01"]
for joiner in [" or ", " || "]:
    body2 = {"filters": [joiner.join(f2)], "sorter": None, "page": {"number": 1, "size": 50}}
    r = S.post(BASE + f"/api/hierarchies/{HID}/parts", json=body2,
               params={"allowDynamicColumns": "true", "hideMappedProperties": "true"},
               timeout=60)
    n = len(r.json().get("rows", [])) if r.status_code == 200 else "-"
    print(f"3b) parts OR '{joiner.strip()}': {r.status_code} rows={n} len={len(r.content)}")
