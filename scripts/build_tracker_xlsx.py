"""Build A2MAC1 capture master tracker xlsx (auto status from data/cad_skip_list.json manifest).
Status per car comes from the download manifest, so every session's tracker refresh is automatic.
Output: download/A2MAC1_Capture_Tracker_621.xlsx"""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

SRC = 'upload/A2MAC1_benchmark_full_621_Version2.xlsx'
OUT = 'download/A2MAC1_Capture_Tracker_621.xlsx'
REL = 'https://github.com/tvh25082004/a2mac1/releases/tag/cad-captures-v1'
HIGHLIGHT = {'Qiyuan Q06', 'L60 60kWh 4X4'}
HIGHLIGHT_NOTE = {'Qiyuan Q06': 'Xe PQ report hiện tại — KHÔNG có CAD trên A2MAC1',
                  'L60 60kWh 4X4': 'Xe PQ report — capture đang chạy theo từng phiên'}

mf = json.load(open('data/cad_skip_list.json')).get('manifest', {})

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
    note = next((HIGHLIGHT_NOTE[k] for k in HIGHLIGHT if k in name), '')
    if name in mf:
        m = mf[name]
        done, total = len(m.get('ids', [])), m.get('total_files', 0)
        st = 'HOÀN TẤT' if done >= total else 'MỘT PHẦN'
        cap = f'{st} {done:,}/{total:,} linh kiện x 4 góc nhìn'
        fname = 'CAPTURES_' + name.replace(' ', '_') + '.zip'
        link = f'{REL}/download/{fname}' if done else ''
        fill = ok_fill if done >= total else part_fill
        n3d += 1
    elif fdl > 0:
        cap, link, fill = 'Chờ access_token JWT (API sẵn sàng — hết ban)', '', wait_fill
        n3d += 1
    else:
        cap, link, fill = 'Không có 3D (chỉ ảnh xe)', '', no3d_fill
    vals = [i, brand, name, year, f3d, fdl, gb, 'CÓ (crawl xong)', cap, link, note]
    for c, v in enumerate(vals, 2):
        cell = ws1.cell(row=r, column=c, value=v)
        cell.fill = hl_fill if note else fill
    r += 1

last = r - 1
srow = last + 2
tot_done = sum(len(m.get('ids', [])) for m in mf.values())
sums = [
    ('Tổng số xe trong danh mục', len(cars)),
    ('Xe có 3D tải được', n3d),
    ('Xe KHÔNG có 3D (chỉ ảnh)', len(cars) - n3d),
    ('Tổng file 3D (toàn danh mục)', sum(c[3] for c in cars)),
    ('Tổng file tải được', sum(c[4] for c in cars)),
    ('Tổng dung lượng STL ước tính (TB)', round(sum(c[4] for c in cars) * 6 / 1e6, 2)),
    ('Đã tải + render (linh kiện, tổng cộng)', tot_done),
    ('Xe đã có capture (trong manifest)', len(mf)),
]
ws1.cell(row=srow, column=2, value='TỔNG KẾT').font = Font(bold=True, size=12)
for k, (label, val) in enumerate(sums):
    ws1.cell(row=srow + 1 + k, column=2, value=label).font = Font(bold=True)
    ws1.cell(row=srow + 1 + k, column=3, value=val)
ws1.cell(row=srow + len(sums) + 2, column=2,
         value='Quy ước: 1 file STL ~6MB. Capture 4 góc = Iso/Front/Side/Top, PNG nền trắng, có index.csv. '
               'Trạng thái đọc tự động từ data/cad_skip_list.json sau mỗi phiên tải.')\
    .font = Font(italic=True, size=9)

widths = [5, 18, 42, 7, 11, 13, 13, 14, 32, 50, 44]
for c, w in enumerate(widths, 2):
    ws1.column_dimensions[get_column_letter(c)].width = w
ws1.freeze_panes = 'A5'
ws1.auto_filter.ref = f'B4:L{last}'
ws1.sheet_view.zoomScale = 85

out.save(OUT)
print(f'SAVED {OUT} | xe: {len(cars)} | co 3D: {n3d} | da render: {tot_done:,} linh kien | '
      f'xe trong manifest: {len(mf)}')
