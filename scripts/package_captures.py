"""Package rendered part captures: build index.csv per car (partId/material/size from manifest),
zip each car's PNG folder into download/CAPTURES_<Car>.zip, verify counts and integrity."""
import csv, json, os, zipfile, time

OUT = '/tmp/cap_out'
DL = '/home/z/my-project/download'
mf = json.load(open('/home/z/my-project/data/cad_skip_list.json'))['manifest']


def build_index(car):
    """Write index.csv into the car folder; return (n_png, rows_missing)."""
    m = mf.get(car, {})
    meta = {}
    for e in m.get('files', []):
        meta[os.path.splitext(os.path.basename(e['file']))[0]] = e
    car_dir = os.path.join(OUT, car)
    pngs = sorted(f for f in os.listdir(car_dir) if f.endswith('.png'))
    missing = 0
    ipath = os.path.join(car_dir, 'index.csv')
    with open(ipath, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['png_file', 'stl_name', 'partId', 'material_label',
                    'stl_size_MB', 'views'])
        for p in pngs:
            name = p[:-4]
            e = meta.get(name)
            if e:
                w.writerow([p, e['name'], e['part'], e['label'],
                            round(e['size'] / 1e6, 2), 'Iso;Front;Side;Top'])
            else:
                missing += 1
                w.writerow([p, name, '', '', '', 'Iso;Front;Side;Top'])
    return len(pngs), missing


def main():
    t0 = time.time()
    results = []
    for car in sorted(os.listdir(OUT)):
        car_dir = os.path.join(OUT, car)
        if not os.path.isdir(car_dir):
            continue
        n, missing = build_index(car)
        tag = car.replace(' ', '_').replace('/', '_')
        zpath = os.path.join(DL, f'CAPTURES_{tag}.zip')
        if os.path.exists(zpath):
            os.remove(zpath)
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            for f in sorted(os.listdir(car_dir)):
                z.write(os.path.join(car_dir, f), arcname=f'{car}/{f}')
        size = os.path.getsize(zpath)
        results.append((car, n, missing, size))
        print(f'{car}: {n} PNG (manifest thieu {missing}) -> {zpath} '
              f'{size/1e6:.1f}MB | {time.time()-t0:.0f}s', flush=True)
    tot = sum(n for _, n, _, _ in results)
    print(f'TOTAL {tot} captures, {sum(s for *_x, s in results)/1e6:.0f}MB', flush=True)


if __name__ == '__main__':
    main()
