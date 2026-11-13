"""Render STL -> PNG captures (multi-view sheet), mimicking what A2MAC1's 3D viewer shows.
Pure matplotlib (headless-safe), no trimesh needed. Binary STL parser included."""
import struct, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm
for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',):
    try:
        fm.fontManager.addfont(fp)
    except Exception:
        pass
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def read_stl(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:5].lower() == b'solid' and len(data) < 200:
        raise ValueError('ASCII STL not supported here')
    n = struct.unpack('<I', data[80:84])[0]
    rec = np.frombuffer(data, dtype=np.uint8, count=n * 50, offset=84).reshape(n, 50)
    tri = rec[:, 12:48].copy().view('<f4').reshape(n, 3, 3).astype(np.float64)
    return tri


def render(tri, views, title, outfile):
    pts = tri.reshape(-1, 3)
    mins, maxs = pts.min(0), pts.max(0)
    center = (mins + maxs) / 2
    rng = (maxs - mins).max() or 1.0
    tri_c = tri - center
    # lambert shading theo face normal
    v1, v2 = tri_c[:, 1] - tri_c[:, 0], tri_c[:, 2] - tri_c[:, 0]
    normals = np.cross(v1, v2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms == 0, 1, norms)
    light = np.array([0.4, 0.35, 0.85])
    light = light / np.linalg.norm(light)
    fig, axes = plt.subplots(1, len(views), figsize=(4.6 * len(views), 4.4),
                             constrained_layout=True, subplot_kw={'projection': '3d'})
    axes = np.atleast_1d(axes)
    for ax, (label, elev, azim) in zip(axes, views):
        col = Poly3DCollection(tri_c, facecolors='#cfd6de', edgecolors='#5a6570', linewidths=0.06)
        shade = 0.45 + 0.55 * np.clip(normals @ light, 0, 1)
        col.set_facecolor(np.c_[shade * 0.78, shade * 0.82, shade * 0.88,
                                np.ones_like(shade)])
        ax.add_collection3d(col)
        m = rng * 0.62
        ax.set_xlim(-m, m); ax.set_ylim(-m, m); ax.set_zlim(-m, m)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(label, fontsize=11, pad=2)
    fig.suptitle(title, fontsize=13, fontweight='bold')
    fig.savefig(outfile, dpi=140, facecolor='white')
    plt.close(fig)
    print('saved:', outfile)


VIEWS_4 = [('Iso view', 22, -55), ('Front', 0, -90), ('Side', 0, 0), ('Top', 90, -90)]
VIEWS_1 = [('Iso view', 22, -55)]

CAR = 'VinFast VF6 Plus 2024'
src = '/tmp/VinFast VF6 Plus 2024__'
render(read_stl(src + '2522-1626.stl'), VIEWS_4,
       f'{CAR} — part 2522-1626 — rendered locally from A2MAC1 STL',
       '/home/z/my-project/download/CAD_capture_demo_VF6_2522-1626_4views.png')
render(read_stl(src + '2522-1598_1.stl'), VIEWS_1,
       f'{CAR} — part 2522-1598_1 — rendered locally from A2MAC1 STL',
       '/home/z/my-project/download/CAD_capture_demo_VF6_2522-1598_1_iso.png')
