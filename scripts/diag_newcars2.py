"""Round 2: try all 5 hierarchy types for Treo + check Excel 'File tai duoc' column."""
import json

import openpyxl
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

hiers = json.load(open('data/hierarchies_3d.json'))
for h in hiers:
    print(f"hierarchy: {h['id']} = {h['value']}")

q = json.load(open('data/cad_priority.json'))
pid_treo = next(c['id'] for c in q if c['name'].startswith('Mahindra Treo'))

print(f"\n--- get-files Treo ({pid_treo}) qua tung hierarchy ---")
for h in hiers:
    r = S.post(f"{BASE}/api/visual/files/get-files", params={"api-version": "2.0"},
               json={"productIds": [pid_treo], "hierarchyId": h['id'], "isBookmark": False},
               timeout=60)
    n = len(r.json()) if r.status_code == 200 else '-'
    print(f"{h['value']:30} | HTTP {r.status_code} | files: {n}")

wb = openpyxl.load_workbook('upload/A2MAC1_benchmark_full_621_Version2.xlsx', read_only=True)
ws = wb['3D & Teardown']
print("\n--- Excel: File 3D vs File tai duoc ---")
for row in ws.iter_rows(min_row=5, values_only=True):
    if row[3] and any(k in str(row[3]) for k in ('Treo', 'Navara 2.3', 'Celerio')):
        print(f"{str(row[3])[:45]:45} | f3D={row[6]} | tai duoc={row[7]}")
wb.close()
