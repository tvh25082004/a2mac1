"""Build the FULL car queue for cad_bulk4: keep the 3 in-progress cars first, then ALL
remaining cars from the 621-car Excel matched to A2MAC1 productIds (products_all.json),
sorted by 3D file count descending. Output: data/cad_priority.json"""
import json
import re

def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()

# 3D file counts per car from the benchmark Excel
import openpyxl
wb = openpyxl.load_workbook('upload/A2MAC1_benchmark_full_621_Version2.xlsx', read_only=True)
ws = wb['3D & Teardown']
counts = {}
for row in ws.iter_rows(min_row=5, values_only=True):
    name, f3d = row[3], row[6]
    if not name:
        continue
    try:
        f3d = int(f3d)
    except (TypeError, ValueError):
        f3d = 0
    if f3d > 0:
        counts[norm(str(name))] = (str(name), f3d)
wb.close()

products = json.load(open('data/products_all.json'))
by_name = {norm(p.get('resourceName')): p.get('productId') for p in products}

head = json.load(open('data/cad_priority.json'))[:3]  # L60, VF8, VF6 in progress
head_names = {norm(c['name']) for c in head}

queue, unmatched = [], []
for key, (name, f3d) in sorted(counts.items(), key=lambda kv: -kv[1][1]):
    if key in head_names:
        continue
    pid = by_name.get(key)
    if not pid:
        # prefix fallback: match longest common product name start
        cands = [(k, v) for k, v in by_name.items() if k[:22] == key[:22] and len(k) >= 22]
        pid = cands[0][1] if cands else None
    if pid:
        queue.append({'id': pid, 'name': name})
    else:
        unmatched.append(name)

out = head + queue
json.dump(out, open('data/cad_priority.json', 'w'), ensure_ascii=False, indent=1)
print(f'queue: {len(out)} xe (3 dang lam + {len(queue)} moi) | khong khop productId: {len(unmatched)}')
for u in unmatched[:10]:
    print('  UNMATCHED:', u)
print('Tong file 3D trong hang doi moi:', sum(counts[norm(q["name"])][1] for q in queue))
