"""Build A2MAC1 capture master tracker xlsx from the uploaded 621-car benchmark Excel.
One sheet: 621 cars with 3D file counts, per-car STL size estimate, capture status,
release zip links. Summary block on top. Output: download/A2MAC1_Capture_Tracker_621.xlsx"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

SRC = 'upload/A2MAC1_benchmark_full_621_Version2.xlsx'
OUT = 'download/A2MAC1_Capture_Tracker_621.xlsx'
REL = 'https://github.com/tvh25082004/a2mac1/releases/tag/cad-captures-v1'
DONE_ZIP = {  # name lower -> (status, link)
    'vinfast vf6 plus 2024': ('HOAN TAT 1,670 linh kiện x 4 góc nhìn', REL),
    'vinfast vf8 plus 2023': ('MỘT PHẦN 69/1,483 linh kiện', REL),
    'onvo l60 60kwh 4x4 2024': ('MỘT PHẦN 740/1,893 linh kiện x 4 góc nhìn', REL),
}
HIGHLIGHT = {'Qiyuan Q06', 'L60 60kWh 4X4'}

wb = openpyxl.load_workbook(SRC, read_only=True)
ws = wb['3D & Teardown']
cars = []
for row in ws.iter_rows(min_row=5, values_only=True):
    brand, name, year, f3d, fdl = row[2], row[3], row[4], row[6], row[7]
    if not name:
        continue
    try:
        f3d, fdl = int(f3d), int(fdl)
    except (TypeError, ValueError):
        f3d, fdl = 0, 0
    cars.append((str(brand or ''), str(name), str(year or ''), f3d, fdl))
wb.close()

out = openpyxl.Workbook()
out.properties.creator = 'Z.ai'
ws1 = out.active
ws1.title = 'Tracker 621 xe'

h_fill = PatternFill('solid', fgColor='1F4E5F')
h_font = Font(bold=True, color='FFFFFF', size=11)
ok_fill = PatternFill('solid', fgColor='C6EFCE')
part_fill = PatternFill('solid', fgColor='FFEB9C')
wait_fill = PatternFill('solid', fgColor='FCE4EC')
no3d_fill = PatternFill('solid', fgColor='E0E0E0')
hl_fill = PatternFill('solid', fgColor='FFF2CC')

headers = ['STT', 'Hãng xe', 'Tên xe', 'Năm', 'Số file 3D', 'Số file tải được',
           'Ước tính STL (GB)', 'Ảnh xe (photos)', 'Capture linh kiện 4 góc',
           'Zip captures', 'Ghi chú']
for c, h in enumerate(headers, 2):
    cell = ws1.cell(row=4, column=c, value=h)
    cell.fill = h_fill
    cell.font = h_font
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

r = 5
n3d = 0
for i, (brand, name, year, f3d, fdl) in enumerate(cars, 1):
    gb = round(fdl * 6 / 1000, 1)
    if fdl > 0:
        status = DONE_ZIP.get(name.lower())
        cap, link = status if status else ('Chờ access_token JWT', '')
        fill = ok_fill if status else wait_fill
        n3d += 1
    else:
        cap, link, fill = 'Không có 3D (chỉ ảnh xe)', '', no3d_fill
    note = ''
    for hl in HIGHLIGHT:
        if hl in name:
            note = {'Qiyuan Q06': 'Xe PQ report hiện tại — KHÔNG có CAD trên A2MAC1',
                    'L60 60kWh 4X4': 'Xe PQ report — đã capture 740/1,893 linh kiện (ban cắt phiên; resume phiên sau)'}[hl]
    vals = [i, brand, name, year, f3d, fdl, gb, 'CÓ (crawl xong)' if fdl >= 0 else '',
            cap, link, note]
    for c, v in enumerate(vals, 2):
        cell = ws1.cell(row=r, column=c, value=v)
        cell.fill = fill if not note else hl_fill
    r += 1

last = r - 1
# summary block
srow = last + 2
sums = [
    ('Tổng số xe trong danh mục', len(cars)),
    ('Xe có 3D tải được', n3d),
    ('Xe KHÔNG có 3D (chỉ ảnh)', len(cars) - n3d),
    ('Tổng file 3D (toàn danh mục)', sum(c[3] for c in cars)),
    ('Tổng file tải được', sum(c[4] for c in cars)),
    ('Tổng dung lượng STL ước tính (TB)', round(sum(c[4] for c in cars) * 6 / 1e6, 2)),
    ('Đã capture xong (xe)', 1),
    ('Đang chờ access_token (xe)', n3d - 1),
]
ws1.cell(row=srow, column=2, value='TỔNG KẾT').font = Font(bold=True, size=12)
for k, (label, val) in enumerate(sums):
    ws1.cell(row=srow + 1 + k, column=2, value=label).font = Font(bold=True)
    ws1.cell(row=srow + 1 + k, column=3, value=val)
ws1.cell(row=srow + len(sums) + 2, column=2,
         value='Quy ước: 1 file STL ~6MB. Capture 4 góc = Iso/Front/Side/Top, PNG nền trắng, có index.csv.')\
    .font = Font(italic=True, size=9)

widths = [5, 18, 42, 7, 11, 13, 13, 14, 30, 46, 44]
for c, w in enumerate(widths, 2):
    ws1.column_dimensions[get_column_letter(c)].width = w
ws1.freeze_panes = 'A5'
ws1.auto_filter.ref = f'B4:L{last}'
ws1.sheet_view.zoomScale = 85

out.save(OUT)
print(f'SAVED {OUT} | xe: {len(cars)} | co 3D: {n3d} | '
      f'file: {sum(c[4] for c in cars):,} | TB: {sum(c[4] for c in cars)*6/1e6:.2f}')
