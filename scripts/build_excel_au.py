#!/usr/bin/env python3
"""Build the A&U team Excel: Package Measurements (SAE/A2M values) + Media gallery inventory
+ full 621-vehicle catalogue with VOP harvest status. Data source: real probe captures in
data/vop_schem_summary.json + data/vop_cmp_*.json (session #15/#16, BYD Tang L EV 2025).
NO tokens/credentials are written into the workbook.
Output: download/A2MAC1_AU_Package_Measurements.xlsx
"""
import json, re
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path('/home/z/my-project')
OUT = ROOT / 'download' / 'A2MAC1_AU_Package_Measurements.xlsx'
OUT.parent.mkdir(parents=True, exist_ok=True)

products = json.load(open(ROOT / 'data' / 'products_all.json'))
ss = json.load(open(ROOT / 'data' / 'vop_schem_summary.json'))
sae_flat = ss.get('sae', {})           # "group|propname|scenario" -> value (BYD Tang)
tokens = ss.get('tokens', [])          # media inventory (name/ext only; no token values)

# ---- parse the numeric values from the two captured compare dumps -------------------
BYD_PID = 'A0000074SYPAEU01'
BYD_CAR = 'BYD Tang L EV 2025'
JUNK_NAMES = {'Schematic', 'Front Manikin', '2nd Row Manikin', '3rd Row Manikin', 'Download'}
values = {}          # property display name -> float value
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
                        if not nm or nm in JUNK_NAMES or e.get('formatedValue') in (None, ''):
                            continue
                        try:
                            values[nm] = float(e['formatedValue'])
                        except (TypeError, ValueError):
                            values[nm] = e['formatedValue']

# column order: SAE codes first (numeric asc), then A2M codes
def code_of(name):
    m = re.match(r'(SAE|A2M)-([A-Za-z0-9\-]+?)(?:-(Mass\d))?\s*-\s*(.*)$', name)
    std = 0 if (m and m.group(1) == 'SAE') else 1
    code = m.group(2) if m else name
    mass = int(m.group(3)[4:]) if (m and m.group(3)) else 0
    idx = re.search(r'-(\d)$', code)
    base = code[:idx.start()] if idx else code
    num = int(idx.group(1)) if idx else 0
    return (std, base, num, mass, name)

prop_names = sorted(values.keys(), key=code_of)

# simpler, robust header builder
def short_header2(name):
    mm = re.match(r'(SAE|A2M)-([^-\s]+(?:-GVM)?)\s*-\s*(.*)$', name)
    if not mm:
        return name
    code, rest = mm.group(1) and mm.group(2), mm.group(3)
    unit = ''
    mu = re.search(r'\[(mm|[A-Za-z°]+)\]\s*$', rest)
    if mu:
        unit = f' [{mu.group(1)}]'
        rest = rest[:mu.start()].strip()
    mass = ''
    mz = re.search(r'-(Mass\d)\s*$', rest)
    if mz:
        mass = f' -{mz.group(1)}'
        rest = rest[:mz.start()].strip()
    return f'{code} {rest}{unit}{mass}'

# ---- media inventory (no token values) ---------------------------------------------
media_rows = []
n_by_kind = {'Schematic': 0, 'Front Manikin': 0, '2nd Row Manikin': 0, '3rd Row Manikin': 0, 'Download': 0}
for t in tokens:
    nm, ext = t.get('name') or '?', (t.get('ext') or '?').lower()
    n_by_kind[nm] = n_by_kind.get(nm, 0) + 1
    media_rows.append((t.get('node'), nm, ext.upper()))
# schematic files captured inside the Summary compare dump (6 entries "Schematic | files")
n_schematic = sum(1 for _ in range(6))
seq = {}
file_names = []
for node, nm, ext in media_rows:
    seq[nm] = seq.get(nm, 0) + 1
    base = BYD_CAR.replace(' ', '_')
    file_names.append(f"{base}_{nm.replace(' ', '-')}-{seq[nm] if nm != 'Download' else ''}.{ext.lower()}".replace('-.', '.'))

# ---- catalogue status ----------------------------------------------------------------
status_by_pid = {}
status_by_pid['A0000074SYPAEU01'] = ('PROBE OK', '37 giá trị SAE/A2M + 26 media (6 Schematic, 19 Manikin JPG, 1 ZIP)')
status_by_pid['A000004QZ0HYEU01'] = ('CHỜ TOKEN', 'VF8 — API trả 403 tạm thời lúc probe, cần token mới để probe lại')

# ---- workbook ------------------------------------------------------------------------
thin = Border(*[Side(style='thin', color='B0B0B0')] * 4)
h_fill = PatternFill('solid', fgColor='1F4E5F')
h_font = Font(bold=True, color='FFFFFF', size=10)
ok_fill = PatternFill('solid', fgColor='C6EFCE')
wait_fill = PatternFill('solid', fgColor='FFEB9C')
sub_font = Font(italic=True, size=9, color='555555')

wb = openpyxl.Workbook()
wb.properties.creator = 'Z.ai agent'

# ========== Sheet 1: Package Measurements matrix ==========
ws = wb.active
ws.title = 'Package Measurements'
ws.cell(row=1, column=1, value='A2MAC1 — Vehicle Occupant Packaging / PACKAGE MEASUREMENTS (SAE J1100 / ISO)').font = Font(bold=True, size=13)
ws.cell(row=2, column=1, value='Mỗi dòng = một xe; mỗi cột = một mã đo SAE/A2M (mm). Nguồn: node "Summary" (00000004YO7QEU01) + "Package Measurements" (000000093NWAEU01) qua API compare/by-products.').font = sub_font
ws.cell(row=3, column=1, value='Yêu cầu A&U team: dữ liệu dạng ảnh (jpg/img) của trang Package Measurements — A2MAC1 lưu số liệu dạng text nên xuất trực tiếp giá trị, ảnh schematic JPG tải kèm (sheet Media Gallery).').font = sub_font

HEAD = ['STT', 'Hãng', 'Model', 'Năm', 'Product ID'] + [short_header2(n) for n in prop_names] + \
       ['Số ảnh Schematic', 'Manikin JPG', 'ZIP drawings', 'Ghi chú']
HR = 5
for c, h in enumerate(HEAD, 1):
    cell = ws.cell(row=HR, column=c, value=h)
    cell.fill = h_fill; cell.font = h_font
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

def car_row(r, car, pid, year, vals, sch, man, zipn, note, fill):
    brand = car.split(' ', 1)[0]
    model = car[len(brand):].strip()
    rowvals = [r - HR, brand, model, year, pid] + vals + [sch, man, zipn, note]
    for c, v in enumerate(rowvals, 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.border = thin
        cell.fill = fill
        if isinstance(v, float):
            cell.number_format = '0.0'

r = HR + 1
vals_byd = [values.get(n) for n in prop_names]
car_row(r, BYD_CAR, BYD_PID, 2025, vals_byd, 6, 19, 1, 'Dữ liệu thật đã probe (phiên #15/#16)', ok_fill)
r += 1
car_row(r, 'VinFast VF8 Plus 2023', 'A000004QZ0HYEU01', 2023,
        [None] * len(prop_names), None, None, None, 'Chờ token mới — API 403 tạm thời lúc probe', wait_fill)
last = r
ws.freeze_panes = 'F6'
ws.auto_filter.ref = f'A{HR}:{get_column_letter(len(HEAD))}{last}'
ws.column_dimensions['A'].width = 5
for c in (2, 3, 4, 5):
    ws.column_dimensions[get_column_letter(c)].width = 14 if c == 2 else 30
for c in range(6, len(HEAD) + 1):
    ws.column_dimensions[get_column_letter(c)].width = 13
ws.sheet_view.zoomScale = 85

# ========== Sheet 2: Media gallery inventory (BYD Tang) ==========
ws2 = wb.create_sheet('Media Gallery - BYD Tang')
ws2.cell(row=1, column=1, value='Media Gallery node "Package Measurements" — BYD Tang L EV 2025 (ảnh JPG theo yêu cầu A&U)').font = Font(bold=True, size=12)
ws2.cell(row=2, column=1, value='Quy tắc đặt tên: Hãng_Model_Năm_Loại-đo.jpg. File sẽ được tải về khi có token mới và đính kèm release GitHub.').font = sub_font
h2 = ['#', 'Node', 'Tên trong gallery', 'Định dạng', 'Tên file quy ước', 'Trạng thái']
for c, h in enumerate(h2, 1):
    cell = ws2.cell(row=4, column=c, value=h)
    cell.fill = h_fill; cell.font = h_font
rr = 5
for i, ((node, nm, ext), fname) in enumerate(zip(media_rows, file_names), 1):
    for c, v in enumerate([i, node, nm, ext, fname, 'Chờ token mới để tải'], 1):
        cell = ws2.cell(row=rr, column=c, value=v)
        cell.border = thin
    rr += 1
# 6 schematic files captured in the Summary node
for k in range(1, 7):
    for c, v in enumerate([len(media_rows) + k, 'Summary (00000004YO7QEU01)', 'Schematic', 'JPG/PNG',
                           f'{BYD_CAR.replace(" ", "_")}_Schematic-{k}.jpg', 'Chờ token mới để tải'], 1):
        cell = ws2.cell(row=rr, column=c, value=v)
        cell.border = thin
    rr += 1
for c, w in zip(range(1, 7), [5, 26, 22, 10, 46, 24]):
    ws2.column_dimensions[get_column_letter(c)].width = w

# ========== Sheet 3: catalogue 621 cars ==========
ws3 = wb.create_sheet('Danh mục 621 xe')
ws3.cell(row=1, column=1, value='Toàn bộ 621 xe đang có trên server A2MAC1 — trạng thái harvest Package Measurements cho A&U').font = Font(bold=True, size=12)
h3 = ['STT', 'Hãng', 'Tên xe đầy đủ', 'Product ID', 'Trạng thái VOP', 'Chi tiết']
for c, h in enumerate(h3, 1):
    cell = ws3.cell(row=3, column=c, value=h)
    cell.fill = h_fill; cell.font = h_font
rr = 4
for i, p in enumerate(products, 1):
    st, note = status_by_pid.get(p['productId'], ('CHỜ TOKEN', 'Harvest theo lượt khi có access_token mới'))
    if st == 'PROBE OK':
        fill = ok_fill
    elif st == 'CHỜ TOKEN' and '403' in note:
        fill = wait_fill
    else:
        fill = None
    brand = p['resourceName'].split(' ', 1)[0]
    for c, v in enumerate([i, brand, p['resourceName'], p['productId'], st, note], 1):
        cell = ws3.cell(row=rr, column=c, value=v)
        cell.border = thin
        if fill:
            cell.fill = fill
    rr += 1
ws3.freeze_panes = 'A4'
ws3.auto_filter.ref = f'A3:F{rr - 1}'
for c, w in zip(range(1, 7), [6, 16, 46, 22, 14, 52]):
    ws3.column_dimensions[get_column_letter(c)].width = w

# ========== Sheet 4: request & method ==========
ws4 = wb.create_sheet('Yêu cầu & Phương pháp')
req = ('"For your info bro, Please refer this image to find the main and most important data that can help '
       'the A&U team, the format for this data will be in jpg,img or any other image format only. Please check '
       'if the team can get this data and populate it in an excel for all the projects available on the A2MAC1 Server."')
lines = [
    ('Yêu cầu gốc từ A&U team', Font(bold=True, size=12)),
    (req, Font(italic=True, size=10)),
    ('', None),
    ('Ảnh tham chiếu người dùng cung cấp: BYD Tang L EV 2026 — Data Explorer → Vehicle Occupant Packaging → '
     'Package Measurements → Schematics → Exterior Dimensions → Height (line drawing side view, overlay kích thước, '
     'khung mã SAE H61-1/H156/H196/H202/H251…, tiêu đề "Vehicle Occupant Packaging – PACKAGE MEASUREMENTS", logo A2Mac1).', None),
    ('', None),
    ('Kết quả kiểm chứng trên API (phiên #15/#16, BYD Tang L EV 2025)', Font(bold=True, size=12)),
    ('1. Bảng số liệu "Measures" — LẤY ĐƯỢC dạng text: 37 giá trị SAE/A2M (node Summary) + 11 bản ghi chuẩn đo '
     '(SAE J1100 NOV2009, SAE J826 JUN2021, SAE J4004 AUG2008, GCIE 2019) qua POST /api/products/compare/hierarchy/…/data/by-products.', None),
    ('2. Ảnh schematic + manikin — LẤY ĐƯỢC: 6 Schematic (JPG/PNG) + 19 Manikin JPG (Front ×6, 2nd Row ×10, 3rd Row ×3) '
     '+ 1 ZIP bản vẽ package, tải qua GET /files/downloads/files?token=… (token ngắn hạn, cần phiên đăng nhập mới).', None),
    ('3. So khớp ảnh chụp mẫu: SAE-H156-GVM = 167.8, SAE-H196 = 809.1, SAE-H202 = 782.5, SAE-H251 = 1880.0 — '
     'trùng đúng 4 con số trong ảnh người dùng gửi.', None),
    ('', None),
    ('Cách hoàn thành cho 621 xe', Font(bold=True, size=12)),
    ('• Chạy scripts/harvest_vop_all.py (đã viết, có resume) khi có access_token mới: mỗi xe ~2–3s, quét toàn bộ node '
     'Package Measurements, lưu values → data/vop_harvest/<pid>.json, ảnh JPG → download/VOP_media/<xe>/.', None),
    ('• Sau harvest: điền đầy đủ Sheet "Package Measurements" (621 dòng), tải toàn bộ ảnh JPG, nhúng ảnh schematic đại diện '
     'vào Excel, đóng gói ZIP media và upload GitHub Release.', None),
    ('• Giới hạn hiện tại: access_token JWT chỉ sống ~25–30 phút và phiên sandbox bị recycle đã xóa token cũ (hết hạn '
     'khoảng 2.8 giờ trước). Cần người dùng cấp token mới (cookie access_token) hoặc tài khoản đăng nhập để tự lấy token.', None),
    ('', None),
    ('Tài liệu liên quan', Font(bold=True, size=12)),
    ('• Tracker capture 3D: download/A2MAC1_Capture_Tracker_621.xlsx (8 xe HOÀN TẤT — 7,782 linh kiện × 4 góc nhìn).', None),
    ('• GitHub: github.com/tvh25082004/a2mac1 (repo + Releases cad-captures-v1).', None),
]
rr = 1
for text, font in lines:
    cell = ws4.cell(row=rr, column=1, value=text)
    if font:
        cell.font = font
    cell.alignment = Alignment(wrap_text=True, vertical='top')
    rr += 1
ws4.column_dimensions['A'].width = 120

wb.save(OUT)
print('SAVED', OUT)
print('props:', len(prop_names), '| media rows:', len(media_rows) + 6, '| cars:', len(products))
