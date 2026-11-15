"""Diagnose why new cars fail get-files: test Treo/Navara/VF8 productIds live."""
import json

import requests

TOK = open('/tmp/a2mac1_tok').read().strip()
BASE = "https://ibp.a2mac1.com"
S = requests.Session()
S.headers.update({
    "Authorization": f"Bearer {TOK}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
    "Referer": "https://ibp.a2mac1.com/",
    "Content-Type": "application/json",
})
HID = "00000003LSK4EU01"  # hierarchy type "3D AutoReverse"

q = json.load(open('data/cad_priority.json'))
ids = {c['name']: c['id'] for c in q}

for name in ["Mahindra Treo EV-3W SFT 2023", "Nissan Navara 2.3 Calibre V 7AT 2021",
             "VinFast VF8 Plus 2023"]:
    pid = ids[name]
    r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid], "hierarchyId": HID, "isBookmark": False}, timeout=60)
    body = r.text[:200].replace("\n", " ")
    print(f"{name[:35]:35} | pid={pid} | HTTP {r.status_code} | {body}")
