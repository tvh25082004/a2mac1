#!/usr/bin/env python3
"""Build Excel: 1 sheet per brand, each sheet = a matrix of 621 vehicles x 247 A2MAC1 specs.
Follows the design system of the xlsx skill (templates/base.py)."""
import json, os, sys, re
from pathlib import Path
from collections import OrderedDict
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill

XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
from templates.base import (
    setup_sheet, style_header_row, style_data_row, style_total_row,
    font_title, font_header, font_subheader, font_body, font_caption,
    fill_header, fill_total, fill_data_row, border_header,
    align_header, align_text, align_number, auto_fit_columns,
    COLUMN_WIDTHS, ROW_HEIGHTS, PRIMARY, SECONDARY, NEUTRAL_600, NEUTRAL_900,
)

DATA = Path("/home/z/my-project/data")
OUT = Path("/home/z/my-project/download/A2MAC1_thong_so_ky_thuat_621_xe.xlsx")
OUT.parent.mkdir(exist_ok=True)

# ---------- 1. Load schema + values ----------
files = sorted((DATA / "spec_batches").glob("batch_*.json"))
print("batch files:", len(files))

first = json.loads(files[0].read_text())
groups = OrderedDict()
for g in first["propertyGroups"]:
    groups[g["propertyGroupName"]] = OrderedDict(
        (p["propertyId"], {"name": p["propertyName"], "type": p["propertyType"]})
        for p in g["properties"])
# add properties that appear in other batches but not in the first batch
for f in files[1:]:
    for g in json.loads(f.read_text())["propertyGroups"]:
        grp = groups.setdefault(g["propertyGroupName"], OrderedDict())
        for p in g["properties"]:
            if p["propertyId"] not in grp:
                grp[p["propertyId"]] = {"name": p["propertyName"], "type": p["propertyType"]}

n_props = sum(len(v) for v in groups.values())
print("groups:", len(groups), "| properties:", n_props)

products = json.loads((DATA / "products_all.json").read_text())
name_of = {p["productId"]: p.get("resourceName", p["productId"]) for p in products}

vehicles = {}
for f in files:
    for pid, pvals in json.loads(f.read_text())["values"].items():
        vehicles[pid] = pvals
print("vehicles:", len(vehicles))

BRAND_PID, MODEL_PID, YEAR_PID, TRIM_PID = ("00000000TLEEDV01", "00000000TLEGDV01",
                                            "00000000TLDRDV01", "00000000TLD3DV01")

def parse_val(raw_v):
    """values[propId] = {scenario: [value objects]} -> (text, unit, numeric)"""
    if not isinstance(raw_v, dict):
        return None, None, None
    outs = []
    for sc, lst in raw_v.items():
        for v in (lst or []):
            outs.append(v)
    if not outs:
        return None, None, None
    texts = [str(v.get("formatedValue")) for v in outs if v.get("formatedValue") is not None]
    unit = outs[0].get("unitLabel")
    orig = outs[0].get("originalValue")
    text = " | ".join(texts) if texts else (str(orig) if orig is not None else None)
    num = None
    if len(outs) == 1 and unit is None and orig is not None and not isinstance(orig, (dict, list)):
        try:
            num = float(orig)
        except (TypeError, ValueError):
            num = None
    return text, unit, num

brand_of, model_of, year_of = {}, {}, {}
for pid, pvals in vehicles.items():
    brand_of[pid] = (parse_val(pvals.get(BRAND_PID))[0] or "Khác").strip()
    model_of[pid] = parse_val(pvals.get(MODEL_PID))[0]
    y, _, ynum = parse_val(pvals.get(YEAR_PID))
    year_of[pid] = ynum if ynum is not None else (int(y) if y and str(y).isdigit() else None)

by_brand = {}
for pid, b in brand_of.items():
    by_brand.setdefault(b, []).append(pid)
print("brand count:", len(by_brand))
for b, lst in sorted(by_brand.items(), key=lambda x: (-len(x[1]), x[0])):
    print(f"   {b}: {len(lst)} vehicles")

def safe_sheet_name(name, used):
    s = re.sub(r"[:\\/?*\[\]]", "-", name).strip() or "Sheet"
    s = s[:31]
    base, i = s, 2
    while s.lower() in used:
        suffix = f" ({i})"; s = base[:31 - len(suffix)] + suffix; i += 1
    used.add(s.lower())
    return s

def clean_text(t):
    if t is None:
        return None
    t = str(t).replace("\xa0", " ").replace("\u200b", "").strip()
    if t == "":
        return None
    if t.startswith("="):
        t = "'" + t
    return t

wb = Workbook()
wb.properties.creator = "Z.ai"

# ---------- 2. Brand index sheet ----------
ws = wb.active
ws.title = "Danh mục hãng"
setup_sheet(ws, title=f"A2MAC1 IBP — Thông số kỹ thuật {len(vehicles)} dòng xe ({len(by_brand)} hãng xe)", last_col=5)
headers = ["STT", "Hãng xe", "Số dòng xe", "Mở sheet"]
for c, h in enumerate(headers, 2):
    ws.cell(row=4, column=c, value=h)
style_header_row(ws, 4, 2, 5)
r = 5
brand_sheet_name = {}
used = set()
for b, lst in sorted(by_brand.items(), key=lambda x: x[0]):
    brand_sheet_name[b] = safe_sheet_name(b, used)
for i, (b, lst) in enumerate(sorted(by_brand.items(), key=lambda x: x[0]), 1):
    ws.cell(row=r, column=2, value=i).alignment = align_number()
    ws.cell(row=r, column=3, value=b)
    ws.cell(row=r, column=4, value=len(lst)).alignment = align_number()
    link = ws.cell(row=r, column=5, value=f'=HYPERLINK("#\'{brand_sheet_name[b]}\'!B6","→ {brand_sheet_name[b]}")')
    link.font = Font(color="0563C1", underline="single", size=11)
    style_data_row(ws, r, 2, 5, i)
    r += 1
ws.cell(row=r, column=3, value="TỔNG").font = font_subheader()
tot = ws.cell(row=r, column=4, value=len(vehicles))
tot.font = font_subheader(); tot.alignment = align_number()
style_total_row(ws, r, 2, 5)
note = ws.cell(row=r + 2, column=2,
               value="Nguồn: A2MAC1 IBP (ibp.a2mac1.com) — api/products/compare/data/by-products • cào ngày 11/11/2026 • "
                     f"{n_props} thông số kỹ thuật từ {len(groups)} nhóm thông số")
note.font = font_caption()
ws.column_dimensions["B"].width = 8
ws.column_dimensions["C"].width = 24
ws.column_dimensions["D"].width = 12
ws.column_dimensions["E"].width = 26
ws.freeze_panes = "B5"

# ---------- 3. Per-brand sheets ----------
col_index = []  # (groupId groupname, propId, name, type)
col_index.append(("—", None, "Tên xe (Full Name)", "TEXT"))
for gname, props in groups.items():
    for pid, meta in props.items():
        col_index.append((gname, pid, meta["name"], meta["type"]))
NCOL = len(col_index) + 1  # +1 because columns start at B
print("columns per sheet:", NCOL)

row4_style_fill = fill_total()
for b, pids in sorted(by_brand.items(), key=lambda x: x[0]):
    sname = brand_sheet_name[b]
    ws = wb.create_sheet(sname)
    setup_sheet(ws, title=f"{b} — {len(pids)} dòng xe • {n_props} thông số", last_col=min(NCOL, 40))
    # row 4: property groups (merge by span)
    start = 3  # properties start at column C
    gi = 3
    for gname, props in groups.items():
        span = len(props)
        if span == 0:
            continue
        ws.merge_cells(start_row=4, start_column=gi, end_row=4, end_column=gi + span - 1)
        c = ws.cell(row=4, column=gi, value=gname)
        c.font = font_subheader(); c.fill = row4_style_fill
        c.alignment = Alignment(horizontal="left", vertical="center")
        for cc in range(gi, gi + span):
            ws.cell(row=4, column=cc).fill = row4_style_fill
            ws.cell(row=4, column=cc).font = font_subheader()
        gi += span
    cB4 = ws.cell(row=4, column=2, value="Thông tin xe")
    cB4.font = font_subheader(); cB4.fill = row4_style_fill
    ws.cell(row=4, column=2).fill = row4_style_fill
    # row 5: property names
    ws.cell(row=5, column=2, value="Tên xe (Full Name)")
    gi = 3
    for gname, props in groups.items():
        for pid, meta in props.items():
            ws.cell(row=5, column=gi, value=meta["name"])
            gi += 1
    style_header_row(ws, 5, 2, NCOL)
    ws.row_dimensions[4].height = 22
    ws.row_dimensions[5].height = 48
    # data: sort by Model -> year descending -> name
    pids_sorted = sorted(pids, key=lambda p: (str(model_of.get(p) or ""), -(year_of.get(p) or 0),
                                              str(name_of.get(p, ""))))
    r = 6
    for idx, pid in enumerate(pids_sorted):
        ws.cell(row=r, column=2, value=clean_text(name_of.get(pid)))
        pvals = vehicles.get(pid, {})
        gi = 3
        for gname, props in groups.items():
            for p_id, meta in props.items():
                if p_id == BRAND_PID:
                    ws.cell(row=r, column=gi, value=brand_of.get(pid))
                    gi += 1; continue
                text, unit, num = parse_val(pvals.get(p_id))
                cell = ws.cell(row=r, column=gi)
                if num is not None:
                    cell.value = int(num) if num.is_integer() else num
                    cell.number_format = "#,##0" if num.is_integer() else "General"
                    cell.alignment = align_number()
                elif text is not None:
                    t = clean_text(text)
                    if unit and not str(t).endswith(str(unit)):
                        t = f"{t} {unit}"
                    cell.value = t
                    cell.alignment = align_text()
                gi += 1
        style_data_row(ws, r, 2, NCOL, idx)
        r += 1
    note = ws.cell(row=r + 1, column=2,
                   value=f"Nguồn: A2MAC1 IBP • cào ngày 11/11/2026 • ô trống = A2MAC1 chưa có dữ liệu cho thông số này")
    note.font = font_caption()
    ws.freeze_panes = "C6"
    ws.column_dimensions["B"].width = 36
    auto_fit_columns(ws, min_width=10, max_width=26, header_row=5, data_start_row=6)
    ws.column_dimensions["B"].width = 36

# ---------- 4. Review sheet ----------
rv = wb.create_sheet("Review")
rv.sheet_properties.tabColor = "FFC000"
setup_sheet(rv, title="Kiểm tra chéo — số dòng xe mỗi hãng", last_col=5)
for c, h in enumerate(["Hãng xe", "Kỳ vọng", "Thực tế (COUNTA)", "Trạng thái"], 2):
    rv.cell(row=4, column=c, value=h)
style_header_row(rv, 4, 2, 5)
r = 5
for b, pids in sorted(by_brand.items(), key=lambda x: x[0]):
    sname = brand_sheet_name[b]
    rv.cell(row=r, column=2, value=b)
    rv.cell(row=r, column=3, value=len(pids))
    rv.cell(row=r, column=4, value=f"=COUNTA('{sname}'!B6:B{5 + len(pids)})")
    rv.cell(row=r, column=5, value=f'=IF(C{r}=D{r},"PASS","FAIL")')
    style_data_row(rv, r, 2, 5, r - 5)
    r += 1
rv.cell(row=r, column=2, value="TỔNG")
rv.cell(row=r, column=3, value=len(vehicles))
rv.cell(row=r, column=4, value=f"=SUM(D5:D{r-1})")
rv.cell(row=r, column=5, value=f'=IF(C{r}=D{r},"PASS","FAIL")')
style_total_row(rv, r, 2, 5)
rv.column_dimensions["B"].width = 26
rv.column_dimensions["C"].width = 12
rv.column_dimensions["D"].width = 18
rv.column_dimensions["E"].width = 14

wb.save(OUT)
print("SAVED:", OUT, f"({OUT.stat().st_size/1024/1024:.1f} MB)")
