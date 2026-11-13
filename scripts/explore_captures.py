"""Explore captured-data sources: Onvo L60 teardown/3D/photo availability in harvested data."""
import json

# 1. L60 hierarchy parts table (teardown_state)
d = json.load(open('data/teardown_state.json'))
rows = d['rows']
hid_l60 = 'A000009JDWXOEU01'  # contains L60
entry = rows[hid_l60]
head = entry['head']
print('=== HEAD (cot cua bang parts L60) ===')
for h in head:
    print(' -', h.get('id'), '|', h.get('value'), '|', h.get('type'))

data_rows = entry.get('rows', [])
print('\nso part trong L60 hierarchy:', len(data_rows))
if data_rows:
    r0 = data_rows[0]
    print('keys row dau:', list(r0.keys()) if isinstance(r0, dict) else r0)
    s = json.dumps(r0, ensure_ascii=False)
    print('row dau:', s[:500])

# find any picture/token values across a few rows
import re
tok = 0
sample_pic = None
for r in data_rows[:50]:
    s = json.dumps(r)
    m = re.findall(r'"(picture|part-picture|pictureFile)"\s*:\s*"([^"]{10,80})"', s)
    if m and sample_pic is None:
        sample_pic = m[:2]
    tok += len(re.findall(r'token', s))
print('\ntoken xuat hien trong 50 row dau:', tok, '| picture sample:', sample_pic)

# 2. visual_files_summary cho L60 (productId A00000666HWJEU01)
v = json.load(open('data/visual_files_summary.json'))
for pid in ('A00000666HWJEU01', 'A000009JDWXOEU01'):
    if pid in v:
        info = v[pid]
        print('\n=== visual summary', pid, '===')
        print(json.dumps(info, ensure_ascii=False)[:400])
