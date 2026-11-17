#!/usr/bin/env python3
"""Ghep goi ZIP 'VOP_media' DUNG YEU CAU A&U: anh schematic/so do do luong, KHONG phai anh linh kiện.

Noi dung:
  VOP_media/README.txt
  VOP_media/BYD_Tang_L_EV_2025/_expected_files.csv        (26 file THAT tren server, ten quy uoc)
  VOP_media/BYD_Tang_L_EV_2025/..._Measures-CARD-reconstructed.jpg  (bang 37 gia tri SAE/A2M that, dang anh)
  VOP_media/BYD_Tang_L_EV_2025/..._Height-PROFILE-reconstructed.jpg (so do profile + cac so do Height chinh)
  VOP_media/REFERENCE/A2MAC1_UI_capture_BYD_Tang_Height_Schematic.png (anh nguoi dung gui)
Xuat: download/VOP_media_<ts>.zip  (gh_release_au.py tu upload release au-vop-v1)
"""
import csv, json, re, time, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/home/z/my-project')
STAGE = ROOT / 'download' / 'VOP_media_pkg'
CAR_DIR = STAGE / 'VOP_media' / 'BYD_Tang_L_EV_2025'
REF_DIR = STAGE / 'VOP_media' / 'REFERENCE'
CAR_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)

FD = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def F(sz, bold=False): return ImageFont.truetype(FB if bold else FD, sz)

BYD_PID = 'A0000074SYPAEU01'
BYD_CAR = 'BYD Tang L EV 2025'
JUNK = {'Schematic', 'Front Manikin', '2nd Row Manikin', '3rd Row Manikin', 'Download'}

# ---- du lieu that tu 2 cmp dump (giong Excel builder) --------------------------------
values = {}
for fn in ['vop_cmp_00000004YO7QEU01.json', 'vop_cmp_000000093NWAEU01.json']:
    j = json.load(open(ROOT / 'data' / fn))
    pv = (j.get('values') or {}).get(BYD_PID) or {}
    meta = {}
    for g in j.get('propertyGroups') or []:
        for p in g.get('properties') or []:
            meta[p.get('id')] = p.get('name')
    for _propid, scen in pv.items():
        if isinstance(scen, dict):
            for _s, entries in scen.items():
                if isinstance(entries, list):
                    for e in entries:
                        nm = e.get('propertyName') or meta.get(_propid)
                        if not nm or nm in JUNK or e.get('formatedValue') in (None, ''):
                            continue
                        try:
                            values[nm] = float(e['formatedValue'])
                        except (TypeError, ValueError):
                            values[nm] = e['formatedValue']

def code_of(name):
    m = re.match(r'(SAE|A2M)-([A-Za-z0-9\-]+?)(?:-(Mass\d))?\s*-\s*(.*)$', name)
    std = 0 if (m and m.group(1) == 'SAE') else 1
    code = m.group(2) if m else name
    idx = re.search(r'-(\d)$', code)
    base = code[:idx.start()] if idx else code
    num = int(idx.group(1)) if idx else 0
    return (std, base, num, name)

rows = sorted(values.keys(), key=code_of)
print(f'{len(rows)} gia tri that tu API')

# ---- CSV 26 file that -----------------------------------------------------------------
tokens = json.load(open(ROOT / 'data' / 'vop_schem_summary.json')).get('tokens', [])
j_sum = json.load(open(ROOT / 'data' / 'vop_cmp_00000004YO7QEU01.json'))
pv_sum = (j_sum.get('values') or {}).get(BYD_PID) or {}
sch = []
for _pid, scen in pv_sum.items():
    if isinstance(scen, dict):
        for _s, entries in scen.items():
            if isinstance(entries, list):
                for e in entries:
                    if (e.get('propertyName') or '') == 'Schematic':
                        det = e.get('details') or {}
                        if det.get('token'):
                            sch.append((det.get('name') or 'x', det.get('size') or 0))
base = BYD_CAR.replace(' ', '_')
csv_rows = []
for nm_s, sz in sorted(sch):
    csv_rows.append([f'{base}_Height-Schematic-{nm_s}.png', 'Summary (00000004YO7QEU01)', 'Schematic',
                     'PNG', sz, round(sz / 1e6, 2), 'Cho token moi — file token het han cung JWT (401)'])
seq = {}
for t in tokens:
    nm, ext = t.get('name') or '?', (t.get('ext') or '?').lower()
    if nm == 'Download':
        fname, node = f'{base}_PackageDrawings.zip', 'Package Measurements (000000093NWAEU01)'
    else:
        seq[nm] = seq.get(nm, 0) + 1
        fname, node = f'{base}_{nm.replace(" ", "-")}-{seq[nm]}.{ext}', 'Package Measurements (000000093NWAEU01)'
    csv_rows.append([fname, node, nm, ext.upper(), '', '', 'Cho token moi — file token het han cung JWT (401)'])
with open(CAR_DIR / '_expected_files.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['ten_file_quy_uoc', 'node', 'ten_trong_gallery', 'dinh_dang', 'size_bytes', 'size_MB', 'trang_thai'])
    w.writerows(csv_rows)
print('CSV rows:', len(csv_rows))

# ---- anh CARD: bang gia tri -----------------------------------------------------------
W, H = 1720, 1180 + 46 * ((len(rows) + 1) // 2)
img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)
TEAL = (31, 78, 95); ORANGE = (196, 87, 0); GRAY = (90, 90, 90); LINE = (200, 205, 210)
d.rectangle([0, 0, W, 120], fill=TEAL)
d.text((50, 26), 'Vehicle Occupant Packaging — PACKAGE MEASUREMENTS', font=F(40, True), fill='white')
d.text((50, 80), f'{BYD_CAR}  ·  SAE J1100 / ISO  ·  A&U team request', font=F(24), fill=(215, 228, 235))
d.rectangle([0, 120, W, 172], fill=(255, 236, 210))
d.text((50, 132), 'RECONSTRUCTED from A2MAC1 API values — NOT the original A2MAC1 schematic render (originals PNG 05-10 need a fresh login token)',
       font=F(21, True), fill=ORANGE)
y0 = 205
def vfmt(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)

def cell(x, y, w, name, val):
    s = name
    mu = re.search(r'\s*\[([A-Za-z°]+)\]\s*$', s)
    unit = mu.group(1) if mu else ''
    if mu:
        s = s[:mu.start()].strip()
    parts = [p.strip() for p in s.split(' - ')]
    code = parts[0].replace('SAE-', '').replace('A2M-', '')
    desc = ' - '.join(parts[1:])
    vtxt = vfmt(val)
    text_val = len(vtxt) > 12          # gia tri la chuoi dai (standards/manikin spec)
    cw = d.textlength(code[:16], font=F(26, True))
    dx = x + max(170, cw + 18)
    if text_val:
        cap = 16
    else:                               # cap dong theo chieu rong that cua gia tri
        vw = d.textlength(vtxt, font=F(26, True))
        cap = max(8, int((x + w - 212 - vw - dx) / 8.5))
    if len(desc) > cap:
        cut = desc[:cap]
        if ' ' in cut:
            cut = cut[:cut.rfind(' ')]
        desc = cut + '...'
    d.line([x, y - 8, x + w, y - 8], fill=LINE, width=1)
    d.text((x, y), code[:16], font=F(26, True), fill=TEAL)
    if desc:
        d.text((dx, y + 9), desc, font=F(17), fill=(40, 40, 40))
    if text_val:
        d.text((x + w - 30, y + 4), vtxt, font=F(18, True), fill=(0, 60, 20), anchor='ra')
    else:
        d.text((x + w - 190, y), vtxt, font=F(26, True), fill=(0, 60, 20), anchor='ra')
        if unit:
            d.text((x + w - 180, y + 7), unit, font=F(17), fill=GRAY)
half = (len(rows) + 1) // 2
for col, chunk in enumerate((rows[:half], rows[half:])):
    x = 60 + col * 850
    yy = y0
    for nm in chunk:
        cell(x, yy, 800, nm, values[nm])
        yy += 46
fy = H - 64
d.line([0, fy - 14, W, fy - 14], fill=LINE, width=1)
d.text((60, fy), f'Generated {time.strftime("%Y-%m-%d %H:%M")} UTC · Source: A2MAC1 API compare/by-products · Data exact, no OCR needed',
       font=F(20), fill=GRAY)
d.text((W - 60, fy), 'Naming: Hang_Model_Nam_Muc-do_so-thu-tu', font=F(20), fill=GRAY, anchor='ra')
card = CAR_DIR / f'{base}_Measures-CARD-reconstructed.jpg'
img.save(card, 'JPEG', quality=88)
print('card:', card.name, img.size)

# ---- anh PROFILE: so do Height chinh --------------------------------------------------
def find(prefix):
    pat = re.compile(rf'^(SAE|A2M)-{re.escape(prefix)}\s*-\s')
    for nm in rows:
        if pat.match(nm):
            return nm
    return None
want = {k: find(k) for k in ['H100', 'H156', 'H156-GVM', 'H196', 'H202', 'H251']}
print('profile lookups:', {k: (v, values.get(v)) for k, v in want.items()})
W2, H2 = 2100, 900
img2 = Image.new('RGB', (W2, H2), 'white')
d2 = ImageDraw.Draw(img2)
GY = 730
def varrow(x, y_top, y_bot, label, val_txt, side=1, ly=None, fs=24):
    d2.line([x, y_top, x, y_bot], fill=(150, 30, 30), width=3)
    for yy in (y_top, y_bot):
        d2.polygon([(x - 7, yy + (8 if yy == y_top else -8)), (x + 7, yy + (8 if yy == y_top else -8)),
                    (x, yy)], fill=(150, 30, 30))
    ly = (y_top + y_bot) / 2 - 18 if ly is None else ly
    if side > 0:
        d2.text((x + 12, ly), label, font=F(fs, True), fill=(120, 20, 20))
        d2.text((x + 12, ly + fs + 6), val_txt, font=F(22), fill=(40, 40, 40))
    else:
        d2.text((x - 12, ly), label, font=F(fs, True), fill=(120, 20, 20), anchor='ra')
        d2.text((x - 12, ly + fs + 6), val_txt, font=F(22), fill=(40, 40, 40), anchor='ra')
d2.text((50, 24), f'{BYD_CAR} — Height measures (side profile)', font=F(34, True), fill=TEAL)
d2.text((50, 70), 'Diagram NOT to scale — chi de dinh vi cac so do; gia tri that tu API', font=F(21), fill=GRAY)
d2.rectangle([W2 - 520, 24, W2 - 40, 76], fill=(255, 236, 210))
d2.text((W2 - 510, 36), 'RECONSTRUCTED (API data) — not original render', font=F(18, True), fill=ORANGE)
# ground
d2.line([80, GY, 2020, GY], fill=(60, 60, 60), width=4)
for gx in range(90, 2020, 60):
    d2.line([gx, GY, gx - 14, GY + 16], fill=(140, 140, 140), width=2)
# body
body = [(410, 640), (450, 545), (650, 505), (790, 395), (1120, 375), (1340, 395), (1480, 505), (1530, 640)]
d2.line(body + [(410, 640)], fill=(31, 78, 95), width=6)
d2.line([(450, 545), (480, 640)], fill=TEAL, width=4)
d2.line([(1480, 505), (1450, 640)], fill=TEAL, width=4)
for wx, wr in ((630, 92), (1270, 92)):
    d2.ellipse([wx - wr, GY - wr, wx + wr, GY + wr], outline=(40, 40, 40), width=6)
    d2.ellipse([wx - 28, GY - 28, wx + 28, GY + 28], outline=(40, 40, 40), width=4)
scale = 0.30
def yv(mm): return GY - mm * scale
h100 = values.get(want['H100'])
if h100: varrow(1010, yv(h100), GY, 'H100 Vehicle Height - Body', f'{h100:.1f} mm')
h156 = values.get(want['H156'])
if h156: varrow(430, yv(h156), GY, 'H156 Ground Clearance', f'{h156:.1f} mm', side=-1)
gvm = values.get(want['H156-GVM'])
if gvm: d2.text((60, GY + 40), f'(H156-GVM at GVW = {gvm:.1f} mm)', font=F(19), fill=GRAY)
h251 = values.get(want['H251'])
if h251: varrow(1460, yv(h251), GY, 'H251 Liftgate Open Ht', f'{h251:.1f} mm')
h196 = values.get(want['H196'])
h202 = values.get(want['H202'])
if h196: varrow(1670, yv(h196), GY, 'H196 Lift-In Height', f'{h196:.1f} mm', ly=610)
if h202: varrow(1780, yv(h202), GY, 'H202 Rear Opening', f'{h202:.1f} mm', ly=yv(h202) + 6, fs=21)
d2.text((60, H2 - 46), f'Generated {time.strftime("%Y-%m-%d")} · Source: A2MAC1 API (BYD Tang L EV 2025, SAE J1100)', font=F(20), fill=GRAY)
prof = CAR_DIR / f'{base}_Height-PROFILE-reconstructed.jpg'
img2.save(prof, 'JPEG', quality=88)
print('profile:', prof.name, img2.size)

# ---- anh tham chieu + README -----------------------------------------------------------
ref = REF_DIR / 'A2MAC1_UI_capture_BYD_Tang_Height_Schematic.png'
ref.write_bytes((ROOT / 'upload' / 'pasted_image_1794910067519.png').read_bytes())
readme = f"""GOI MEDIA VOP — MEDIA GALLERY → MEASURES (yeu cau A&U team)
================================================================
Xe mau: BYD Tang L EV 2025 (Product ID {BYD_PID})

1) NOI DUNG GOI NAY
   - BYD_Tang_L_EV_2025/_expected_files.csv
       Danh muc 26 file media THAT tren server A2MAC1 (6 Schematic PNG muc Height,
       ten nguon 05-10, tong ~13.7 MB + 19 Manikin JPG + 1 ZIP ban ve package),
       ten file dat theo quy uoc Hãng_Model_Năm_Mục-đo_số-thứ-tự.
   - BYD_Tang_L_EV_2025/{card.name}
       Bang {len(rows)} gia tri SAE/A2M THAT (dang anh) — so lieu chinh xac tu API, KHONG can OCR.
   - BYD_Tang_L_EV_2025/{prof.name}
       So do profile dinh vi cac so do Height chinh (H156, H100, H196, H202, H251).
   - REFERENCE/A2MAC1_UI_capture_BYD_Tang_Height_Schematic.png
       Anh man hinh tham chieu nguoi dung gui (Media Gallery → Measures, muc Height).

2) VI SAO CHUA CO 6 FILE PNG SCHEMATIC GOC (05-10)?
   A2MAC1 bat buoc JWT dang nhap cho moi tai file; JWT va token tai file chi song
   ~25-30 phut. Token cu da het han (HTTP 401 — kiem tra 3 lan, lan gan nhat 2026-11-17).
   Khi co token moi, chay 1 lenh:
       bash scripts/run_au_pipeline.sh "<cookie access_token=...>"
   -> 621 xe tu harvest, anh goc tai ve DUNG ten quy uoc, ZIP nay tu day va
      tu upload lai GitHub Release (au-vop-v1).

3) QUY UOC DAT TEN
   Hãng_Model_Năm_Mục-đo_số-thứ-tự.ext
   Vi du: BYD_Tang_L_EV_2025_Height-Schematic-05.png

4) SO LIEU KHONG CAN OCR
   API tra text chinh xac, doi chieu 4/4 voi anh mau nguoi dung gui:
   H156-GVM = 167.8 | H196 = 809.1 | H202 = 782.5 | H251 = 1880.0
"""
(STAGE / 'VOP_media' / 'README.txt').write_text(readme, encoding='utf-8')

# ---- zip ------------------------------------------------------------------------------
zpath = ROOT / 'download' / f'VOP_media_{time.strftime("%Y%m%d_%H%M")}.zip'
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            z.write(p, p.relative_to(STAGE))
print('ZIP:', zpath.name, f'{zpath.stat().st_size/1e6:.2f} MB')
with zipfile.ZipFile(zpath) as z:
    for n in z.namelist():
        print('  ', n)
