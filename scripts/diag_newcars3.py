"""Round 3: map which hierarchy each car's files live in (new cars + the 3 old cars)."""
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

hiers = {h['id']: h['value'] for h in json.load(open('data/hierarchies_3d.json'))}
q = json.load(open('data/cad_priority.json'))
cars = ["Nissan Navara 2.3 Calibre V 7AT 2021",
        "Maruti Suzuki Celerio 1.0L VXI Petrol with CNG 5MT 2023",
        "VinFast VF8 Plus 2023", "VinFast VF6 Plus 2024", "Onvo L60 60kWh 4X4 2024"]
for name in cars:
    pid = next(c['id'] for c in q if c['name'] == name)
    found = []
    for hid, hname in hiers.items():
        r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
                   json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False}, timeout=60)
        if r.status_code == 200 and r.json():
            found.append(f"{hname}:{len(r.json())}")
    print(f"{name[:42]:42} | {' + '.join(found) if found else 'KHONG co file o hierarchy nao'}")
