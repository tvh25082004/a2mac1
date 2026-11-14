"""Restore VF6/VF8 manifest entries pruned by prune_manifest.py: their captures live on
the GitHub Release (not local), so they are NOT stranded. Keep L60's pruned state."""
import json, subprocess

old = json.loads(subprocess.check_output(
    ['git', 'show', 'HEAD:data/cad_skip_list.json']).decode())
cur = json.load(open('data/cad_skip_list.json'))

for car in ('VinFast VF6 Plus 2024', 'VinFast VF8 Plus 2023'):
    if car in old.get('manifest', {}):
        cur['manifest'][car] = old['manifest'][car]
        m = cur['manifest'][car]
        print(f'restored {car}: {len(m.get("ids", []))} ids / {m.get("total_files")} total')

json.dump(cur, open('data/cad_skip_list.json', 'w'), ensure_ascii=False, indent=1)
print('done_files khong doi (chi la cache ten file)')
