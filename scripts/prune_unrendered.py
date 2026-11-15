"""Prune manifest entries whose PNGs never made it to the release zip (render died OOM
at bundle 47 of session #14). After pruning, the next session re-downloads those files
(name-dedupe no longer skips them) and renders them properly.

- Celerio, Thar: release zips were 0-PNG junk (deleted from release) -> prune ALL entries
- Navara: zip has 106 PNGs of 138 entries -> prune the 32 missing
- Other cars: manifest thieu 0 per package output -> untouched"""
import json
import shutil
import zipfile

import requests

REL = "https://github.com/tvh25082004/a2mac1/releases/download/cad-captures-v1"
MAN = '/home/z/my-project/data/cad_skip_list.json'
data = json.load(open(MAN))
mf = data['manifest']

shutil.copy(MAN, MAN + '.bak')
plan = {
    'Maruti Suzuki Celerio 1.0L VXI Petrol with CNG 5MT 2023': None,   # prune all
    'Mahindra Thar 2.0L (P) mStallion 150 TGDi LX 2021': None,          # prune all
    'Nissan Navara 2.3 Calibre V 7AT 2021': 'CAPTURES_Nissan_Navara_2.3_Calibre_V_7AT_2021.zip',
}
for car, zipname in plan.items():
    m = mf.get(car)
    if not m:
        print(f'{car[:40]}: khong co trong manifest, bo qua')
        continue
    have = set()
    if zipname:
        z = zipfile.ZipFile(__import__('io').BytesIO(
            requests.get(f'{REL}/{zipname}', timeout=120).content))
        have = {n.split('/')[-1][:-4] for n in z.namelist()
                if n.lower().endswith('.png') and '/' in n}
    before = len(m['files'])
    m['files'] = [e for e in m['files']
                  if (zipname and __import__('os').path.splitext(
                      __import__('os').path.basename(e['file']))[0] in have)]
    m['ids'] = []  # id nhieu hon con name: de name-dedupe quyet dinh
    print(f'{car[:48]:48} | {before} -> {len(m["files"])} entries (prune {before - len(m["files"])})')

json.dump(data, open(MAN, 'w'), ensure_ascii=False, indent=1)
total = sum(len(m['files']) for m in mf.values())
print(f'Tong manifest sau prune: {total} entries')
