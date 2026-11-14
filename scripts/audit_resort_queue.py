"""Audit the 621-car Excel against the crawl queue (thorough, per user request), then
re-sort the queue: L60/VF8/VF6 head first (finish in-progress), then SMALLEST 3D cars
first so each 600-file token session completes whole cars (zip done -> push -> delete)."""
import json
import re

import openpyxl


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


wb = openpyxl.load_workbook('upload/A2MAC1_benchmark_full_621_Version2.xlsx', read_only=True)
print('Sheets:', wb.sheetnames)
ws = wb['3D & Teardown']
rows = list(ws.iter_rows(min_row=4, values_only=True))
headers = [str(h) for h in rows[0]]
print('Columns:', headers)
counts, zero = {}, 0
for row in rows[1:]:
    name, f3d = row[3], row[6]
    if not name:
        continue
    try:
        f3d = int(f3d)
    except (TypeError, ValueError):
        f3d = 0
    if f3d > 0:
        counts[norm(str(name))] = (str(name), f3d)
    else:
        zero += 1
wb.close()
print(f'Excel: {len(counts)} xe co 3D >0 | {zero} xe f3d=0 (khong the crawl)')

queue = json.load(open('data/cad_priority.json'))
head, rest = queue[:3], queue[3:]
q_names = {norm(c['name']) for c in queue}
missing = [counts[k][0] for k in counts if k not in q_names]
extra = [c['name'] for c in queue if norm(c['name']) not in counts]
print(f'Doi chieu: queue {len(queue)} xe | Excel co ma queue THIEU: {len(missing)} | queue co ma Excel khong co: {len(extra)}')
for m in missing[:5]:
    print('  MISSING:', m)
for e in extra[:5]:
    print('  EXTRA:', e)

# re-sort: smallest cars first (whole car per token), keep head order
rest_sorted = sorted(rest, key=lambda c: counts.get(norm(c['name']), (0, 10**9))[1])
out = head + rest_sorted
json.dump(out, open('data/cad_priority.json', 'w'), ensure_ascii=False, indent=1)

sizes = [counts[norm(c['name'])][1] for c in rest_sorted]
small = sum(1 for s in sizes if s <= 600)
mid = sum(1 for s in sizes if 600 < s <= 1200)
big = sum(1 for s in sizes if s > 1200)
print(f'Hang doi moi: 3 dang lam + {len(rest_sorted)} xe moi (sap TANG dan theo so file)')
print(f'  <=600 file (1 token = xe HOAN CHINH): {small} xe')
print(f'  601-1200 file (2 token): {mid} xe | >1200 file: {big} xe')
print('5 xe dau tien sau VF8/VF6:')
for c in rest_sorted[:5]:
    print(f'  {counts[norm(c["name"])][1]:>5} file | {c["name"]}')
