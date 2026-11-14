"""Prune stranded entries from cad_skip_list.json manifest: parts recorded as downloaded
but whose rendered PNG no longer exists in /tmp/cap_out (lost to sandbox recycle).
Removing them lets the next session re-download + re-render those parts."""
import json, os

CAP = '/tmp/cap_out'
mf_path = '/home/z/my-project/data/cad_skip_list.json'
data = json.load(open(mf_path))
mf = data.get('manifest', {})

total_removed = 0
for car, m in mf.items():
    car_dir = os.path.join(CAP, car)
    have = set()
    if os.path.isdir(car_dir):
        have = {f[:-4] for f in os.listdir(car_dir) if f.endswith('.png')}
    keep_files, removed = [], []
    for e in m.get('files', []):
        base = e.get('file', '').split('/')[-1]
        base = base[:-4] if base.endswith('.stl') else base
        (keep_files if base in have else removed).append(e)
    if removed:
        removed_keys = {(e.get('part'), e.get('fid')) for e in removed}
        m['files'] = keep_files
        m['ids'] = [i for i in m.get('ids', [])
                    if not any(i in (p, f) for p, f in removed_keys if p or f)]
        print(f'{car}: bo {len(removed)} linh kien moc coi (khong con PNG), giu {len(keep_files)}')
        total_removed += len(removed)
    else:
        print(f'{car}: OK {len(keep_files)} linh kien deu co PNG')

data['manifest'] = mf
json.dump(data, open(mf_path, 'w'), ensure_ascii=False, indent=1)
print(f'TOTAL removed: {total_removed}')
