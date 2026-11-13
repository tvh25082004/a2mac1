"""Batch-capture every STL part of every car from the CAD bundles -> 4-view PNG per part.
Reads members straight from the zip (no bulk extraction), renders in parallel (8 workers),
writes /tmp/cap_out/<Car>/<part>.png + errors log. Deletes each bundle zip after done."""
import io, os, struct, sys, zipfile, time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from concurrent.futures import ProcessPoolExecutor, as_completed

DEFAULT_BUNDLES = ['/tmp/cad_dl/CAD-bundle-01.zip', '/tmp/cad_dl/CAD-bundle-02.zip',
                   '/tmp/cad_dl/CAD-bundle-03.zip']
OUT = '/tmp/cap_out'
VIEWS = [('Iso view', 22, -55), ('Front', 0, -90), ('Side', 0, 0), ('Top', 90, -90)]


def parse_stl_bytes(data):
    if data[:5].lower() == b'solid' and b'facet' in data[:500]:
        raise ValueError('ascii stl')
    n = struct.unpack('<I', data[80:84])[0]
    if n == 0 or len(data) < 84 + n * 50:
        raise ValueError('bad/empty stl')
    rec = np.frombuffer(data, dtype=np.uint8, count=n * 50, offset=84).reshape(n, 50)
    return rec[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float32)


def render_one(task):
    car, name, outpath = task[0], task[1], task[2]
    for attempt in (1, 2):
        try:
            import gc
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            tri = parse_stl_bytes(task[3])
            gc.collect()
            if len(tri) > 40000:  # decimate dense meshes: fidelity kept, speed x10
                idx = np.random.choice(len(tri), 40000, replace=False)
                tri = tri[idx]
            pts = tri.reshape(-1, 3)
            mins, maxs = pts.min(0), pts.max(0)
            rng = float((maxs - mins).max()) or 1.0
            tri_c = tri - (mins + maxs) / 2
            v1, v2 = tri_c[:, 1] - tri_c[:, 0], tri_c[:, 2] - tri_c[:, 0]
            normals = np.cross(v1, v2)
            nn = np.linalg.norm(normals, axis=1, keepdims=True)
            normals = normals / np.where(nn == 0, 1, nn)
            light = np.array([0.4, 0.35, 0.85]); light /= np.linalg.norm(light)
            shade = 0.45 + 0.55 * np.clip(normals @ light, 0, 1)
            fig = Figure(figsize=(8, 8), dpi=90, facecolor='white')
            FigureCanvasAgg(fig)
            use_edges = len(tri) <= 20000
            m = rng * 0.62
            for k, (label, elev, azim) in enumerate(VIEWS):
                ax = fig.add_subplot(2, 2, k + 1, projection='3d')
                # mpl 3.9 bug: edgecolors='face' raises get_proj NoneType on Poly3DCollection
                col = Poly3DCollection(
                    tri_c,
                    edgecolors='#5a6570' if use_edges else 'none', linewidths=0.05)
                col.set_facecolor(np.c_[shade * 0.78, shade * 0.82, shade * 0.88,
                                        np.ones_like(shade)])
                ax.add_collection3d(col)
                ax.set_xlim(-m, m); ax.set_ylim(-m, m); ax.set_zlim(-m, m)
                ax.set_box_aspect((1, 1, 1))
                ax.view_init(elev=elev, azim=azim)
                ax.set_axis_off()
                ax.set_title(label, fontsize=10, pad=1)
            fig.suptitle(f'{car}  —  part {name}', fontsize=12, fontweight='bold')
            fig.savefig(outpath, dpi=90, facecolor='white')
            del fig, tri_c, tri, normals, shade
            gc.collect()
            return (car, name, 'OK', '')
        except Exception as e:
            import gc
            gc.collect()
            if attempt == 2:
                return (car, name, 'ERR', str(e)[:120])


def main():
    bundles = sys.argv[1:] or DEFAULT_BUNDLES
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    done = err = 0
    workers = 2
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for bi, bpath in enumerate(bundles, 1):
            if not os.path.exists(bpath):
                print(f'[bundle {bi}] MISSING {bpath}', flush=True)
                continue
            z = zipfile.ZipFile(bpath)
            members = [i for i in z.infolist()
                       if i.filename.lower().endswith('.stl') and i.file_size > 0]
            car = members[0].filename.split('/')[0]
            print(f'[bundle {bi}] {os.path.basename(bpath)} | car="{car}" | {len(members)} STL',
                  flush=True)
            inflight = []
            for i, info in enumerate(members):
                car_m, base = info.filename.split('/', 1)
                name = os.path.splitext(base)[0]
                outdir = os.path.join(OUT, car_m)
                os.makedirs(outdir, exist_ok=True)
                outpath = os.path.join(outdir, name + '.png')
                if os.path.exists(outpath):
                    done += 1
                    continue
                data = z.read(info)
                inflight.append(pool.submit(render_one,
                                            (car_m, name, outpath, data)))
                if len(inflight) >= 16:
                    for fu in as_completed(inflight):
                        c, n, st, msg = fu.result()
                        done += (st == 'OK'); err += (st != 'OK')
                        if st != 'OK':
                            print(f'  ERR {c}/{n}: {msg}', flush=True)
                    inflight = []
                if (i + 1) % 200 == 0:
                    print(f'  ...{i+1}/{len(members)} | ok={done} err={err} '
                          f'| {time.time()-t0:.0f}s', flush=True)
            for fu in as_completed(inflight):
                c, n, st, msg = fu.result()
                done += (st == 'OK'); err += (st != 'OK')
                if st != 'OK':
                    print(f'  ERR {c}/{n}: {msg}', flush=True)
            z.close()
            os.remove(bpath)
            print(f'[bundle {bi}] DONE -> zip deleted | ok={done} err={err} '
                  f'| {time.time()-t0:.0f}s', flush=True)
    print(f'ALL DONE ok={done} err={err} in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
