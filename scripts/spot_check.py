#!/usr/bin/env python3
"""Spot-check workbook: sheets, Review PASS/FAIL (giá trị đã recalc), dữ liệu mẫu."""
import json
from pathlib import Path
from openpyxl import load_workbook

OUT = Path("/home/z/my-project/download/A2MAC1_thong_so_ky_thuat_621_xe.xlsx")
wb = load_workbook(OUT, data_only=True)   # chỉ ĐỌC, không save
print("số sheet:", len(wb.sheetnames))
print("5 sheet đầu:", wb.sheetnames[:5])
print("5 sheet cuối:", wb.sheetnames[-5:])

# Review: tất cả PASS?
rv = wb["Review"]
fails, passes = [], 0
for r in range(5, rv.max_row + 1):
    name = rv.cell(row=r, column=2).value
    if not name or name in ("TỔNG",):
        continue
    status = rv.cell(row=r, column=5).value
    if status == "PASS":
        passes += 1
    else:
        fails.append((name, rv.cell(row=r, column=3).value, rv.cell(row=r, column=4).value, status))
print(f"Review: {passes} PASS, {len(fails)} FAIL")
if fails:
    print("FAIL chi tiết:", fails[:10])

# Sheet VinFast
if "VinFast" in wb.sheetnames:
    ws = wb["VinFast"]
    print("\nVinFast title:", ws["B2"].value)
    hdrs = [ws.cell(row=5, column=c).value for c in range(2, 12)]
    print("headers:", hdrs)
    for r in range(6, 9):
        row = [ws.cell(row=r, column=c).value for c in range(2, 12)]
        if row[0] is None:
            break
        print("  row:", row)

# Sheet Acura: check vài ô thông số số
ws = wb["Acura"]
print("\nAcura title:", ws["B2"].value)
print("row 6 (xe 1):", [ws.cell(row=6, column=c).value for c in range(2, 12)])
# tìm cột 'Weight Before Teardown (kg)' và 'Length'
hdr = {ws.cell(row=5, column=c).value: c for c in range(3, ws.max_column + 1)}
for want in ("Weight Before Teardown (kg)", "Model Year", "Segment", "Brand"):
    c = hdr.get(want)
    print(f"  {want}: col={c} -> row6={ws.cell(row=6, column=c).value if c else 'N/A'}")
print("max_row:", ws.max_row, "| max_col:", ws.max_column)
