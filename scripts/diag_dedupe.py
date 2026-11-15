"""Check: do manifest 'name' keys (old schema) match current API record names for VF6?
If yes, dedupe by name recovers the ~1,055 already-captured files (ids rotate on server)."""
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

m = json.load(open('data/cad_skip_list.json'))['manifest']['VinFast VF6 Plus 2024']
old_names = {e.get('name') for e in m.get('files', []) if e.get('name')}
print(f"manifest names: {len(old_names)} unique")

pid = m['product']
api_names = set()
for hid in ("00000003LSK4EU01", "00000005ZT4GEU01", "0000009X67MIEU02"):
    r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid], "hierarchyId": hid, "isBookmark": False}, timeout=60)
    if r.status_code == 200:
        for e in r.json():
            api_names.add(e.get('name'))
print(f"API names (3 nganh chinh): {len(api_names)} unique")
print(f"OVERLAP (da co, bo qua): {len(old_names & api_names)}")
print(f"API names moi thuc su can tai: {len(api_names - old_names)}")
print("sample API name:", list(api_names)[:2])
print("sample manifest name:", list(old_names)[:2])
