#!/usr/bin/env python3
"""Build the FINAL Excel file: spec matrix + embedded vehicle images + CAD&3D sheet.
Each brand sheet: rows 4-5 = vehicle image strip above each vehicle column, row 6 = property groups,
row 7 = property names, row 8+ = data."""
import json, os, sys, re, math
from pathlib import Path
from collections import OrderedDict
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.drawing.image import Image as XLImage

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
IMG_DIR = Path("/home/z/my-project/download/A2MAC1_anh_xe")
IMG_DIR_HD = Path("/home/z/my-project/data/embed_cache")   # 103 fullHD images downscaled to 320px for embedding
OUT = Path("/home/z/my-project/download/A2MAC1_benchmark_full_621_xe.xlsx")
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

# ---------- 1b. Image map (518 small public + 103 downscaled fullHD) ----------
img_map = {}
for f in IMG_DIR.glob("*.jpg"):
    m = re.search(r"\[([A-Za-z0-9]+)\]\.jpg$", f.name)
    if m:
        img_map[m.group(1)] = f
for f in IMG_DIR_HD.glob("*.jpg"):
    img_map[f.stem] = f
print("images:", len(img_map))

BRAND_PID, MODEL_PID, YEAR_PID, TRIM_PID = ("00000000TLEEDV01", "00000000TLEGDV01",
                                            "00000000TLDRDV01", "00000000TLD3DV01")

def parse_val(raw_v):
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

# ---------- 1c. 3D/CAD + Teardown data ----------
visual = json.loads((DATA / "visual_files_summary.json").read_text()) if (DATA / "visual_files_summary.json").exists() else {}
td_state = json.loads((DATA / "teardown_state.json").read_text()) if (DATA / "teardown_state.json").exists() else {"rows": {}}
pkgs_all = json.loads((DATA / "packages_all.json").read_text()) if (DATA / "packages_all.json").exists() else []
pkgs_count = {}
for pk in pkgs_all:
    pkgs_count[pk["productId"]] = pkgs_count.get(pk["productId"], 0) + 1

TD_PID = {"Package": "A0000067RCOMEU01", "Status": "A0000067RD7VEU01",
          "Teardown Status": "A000006GM65WEU01", "3D Status": "A000006GM82LEU01",
          "Teardown Date": "A000006GM7CQEU01"}

def td_fields(pid):
    """Extract the vehicle's teardown/3D status from rows — take the row with the latest Program Year."""
    resp = td_state["rows"].get(pid)
    if not resp or not resp.get("rows"):
        return None
    best = None
    for row in resp["rows"]:
        d = row.get("data", {})
        yr = d.get("A0000067RD13EU01") or [{}]
        try:
            ynum = float(yr[0].get("originalValue") or 0)
        except (TypeError, ValueError):
            ynum = 0
        if best is None or ynum > best[0]:
            best = (ynum, d)
    d = best[1]
    out = {}
    for key, prop in TD_PID.items():
        v = d.get(prop)
        if v and isinstance(v, list) and v:
            out[key] = v[0].get("formatedValue")
    return out

by_brand = {}
for pid, b in brand_of.items():
    by_brand.setdefault(b, []).append(pid)
print("brand count:", len(by_brand))

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
setup_sheet(ws, title=f"A2MAC1 IBP — Benchmark {len(vehicles)} dòng xe ({len(by_brand)} hãng) • {n_props} thông số + ảnh + 3D/CAD", last_col=7)
headers = ["STT", "Hãng xe", "Số dòng xe", "Số xe có ảnh", "Số xe có 3D/CAD", "Mở sheet"]
for c, h in enumerate(headers, 2):
    ws.cell(row=4, column=c, value=h)
style_header_row(ws, 4, 2, 7)
r = 5
brand_sheet_name = {}
used = set()
for b, lst in sorted(by_brand.items(), key=lambda x: x[0]):
    brand_sheet_name[b] = safe_sheet_name(b, used)
for i, (b, lst) in enumerate(sorted(by_brand.items(), key=lambda x: x[0]), 1):
    n_img = sum(1 for pid in lst if pid in img_map)
    n_3d = sum(1 for pid in lst if (visual.get(pid) or {}).get("files"))
    ws.cell(row=r, column=2, value=i).alignment = align_number()
    ws.cell(row=r, column=3, value=b)
    ws.cell(row=r, column=4, value=len(lst)).alignment = align_number()
    ws.cell(row=r, column=5, value=n_img).alignment = align_number()
    ws.cell(row=r, column=6, value=n_3d).alignment = align_number()
    link = ws.cell(row=r, column=7, value=f'=HYPERLINK("#\'{brand_sheet_name[b]}\'!B8","→ {brand_sheet_name[b]}")')
    link.font = Font(color="0563C1", underline="single", size=11)
    style_data_row(ws, r, 2, 7, i)
    r += 1
ws.cell(row=r, column=3, value="TỔNG").font = font_subheader()
tot = ws.cell(row=r, column=4, value=len(vehicles))
tot.font = font_subheader(); tot.alignment = align_number()
tot2 = ws.cell(row=r, column=5, value=len(img_map))
tot2.font = font_subheader(); tot2.alignment = align_number()
tot3 = ws.cell(row=r, column=6, value=sum(1 for pid in vehicles if (visual.get(pid) or {}).get("files")))
tot3.font = font_subheader(); tot3.alignment = align_number()
style_total_row(ws, r, 2, 7)
note = ws.cell(row=r + 2, column=2,
               value="Nguồn: A2MAC1 IBP (ibp.a2mac1.com) • cào ngày 11/11/2026 • "
                     f"{n_props} thông số kỹ thuật / {len(groups)} nhóm • ảnh xe nhúng phía trên mỗi cột xe trong các sheet hãng • "
                     "sheet 'CAD & 3D' mô tả các loại dữ liệu còn lại của nền tảng")
note.font = font_caption()
ws.column_dimensions["B"].width = 8
ws.column_dimensions["C"].width = 24
ws.column_dimensions["D"].width = 12
ws.column_dimensions["E"].width = 14
ws.column_dimensions["F"].width = 14
ws.column_dimensions["G"].width = 26
ws.freeze_panes = "B5"

# ---------- 2b. 3D & Teardown sheet per vehicle ----------
sh3 = wb.create_sheet("3D & Teardown")
sh3.sheet_properties.tabColor = "1F6E43"
setup_sheet(sh3, title="Danh mục file 3D/CAD + trạng thái Teardown theo từng xe (đã quét ngày 11/11/2026)", last_col=12)
h3 = ["STT", "Hãng xe", "Tên xe", "Năm", "Số gói dữ liệu", "File 3D", "File tải được",
      "Vật liệu chính (top 3)", "Teardown Status", "3D Data Status", "Ghi chú"]
for c, h in enumerate(h3, 2):
    sh3.cell(row=4, column=c, value=h)
style_header_row(sh3, 4, 2, 12)
HID3D_NAME = "00000003LSK4EU01"
HIDVOP_NAME = "00000005ZT4GEU01"
n_file_total = 0
r = 5
for i, (b, pids_b) in enumerate(sorted(by_brand.items(), key=lambda x: x[0]), 1):
    for pid in sorted(pids_b, key=lambda p: str(name_of.get(p, ""))):
        v = visual.get(pid) or {}
        nfiles = sum(v.get("files", {}).values())
        ndl = v.get("downloadable", 0)
        n_file_total += nfiles
        mats = sorted((v.get("materials") or {}).items(), key=lambda kv: -kv[1])[:3]
        mats_txt = ", ".join(f"{k} ({n})" for k, n in mats) if mats else None
        td = td_fields(pid)
        note = None
        if not v.get("files"):
            note = "Không có package 3D trên nền tảng"
        if pid not in td_state["rows"]:
            note = (note + "; " if note else "") + "chưa quét teardown (403)"
        vals = [i, b, clean_text(name_of.get(pid)), year_of.get(pid),
                pkgs_count.get(pid), nfiles if nfiles else None, ndl if ndl else None,
                mats_txt, (td or {}).get("Teardown Status"), (td or {}).get("3D Status"), note]
        for c, val in enumerate(vals, 2):
            cell = sh3.cell(row=r, column=c, value=val)
            if c in (2, 5, 6, 7, 8):
                cell.alignment = align_number()
            elif c == 9:
                cell.alignment = align_text()
        style_data_row(sh3, r, 2, 12, i - 1)
        for c in (2, 5, 6, 7, 8):
            sh3.cell(row=r, column=c).alignment = align_number()
        r += 1
note3 = sh3.cell(row=r + 1, column=2,
                 value=f"Tổng {n_file_total:,} file 3D/CAD của {sum(1 for v in visual.values() if v.get('files'))} xe "
                       "(100% isDownloadable) • File 3D liệt kê theo bộ 3D AutoReverse; trạng thái Teardown/3D Data lấy từ "
                       "api/hierarchies/parts theo xe • tải file: /files/downloads/files?token=<fileToken>&api-version=1.1")
note3.font = font_caption()
sh3.freeze_panes = "D5"
for L, w in {"B": 6, "C": 16, "D": 34, "E": 8, "F": 10, "G": 10, "H": 12, "I": 40, "J": 16, "K": 16, "L": 26}.items():
    sh3.column_dimensions[L].width = w

# ---------- 3. Per-brand sheets (with images) ----------
col_index = []
col_index.append(("—", None, "Tên xe (Full Name)", "TEXT"))
for gname, props in groups.items():
    for pid, meta in props.items():
        col_index.append((gname, pid, meta["name"], meta["type"]))
NCOL = len(col_index) + 1
print("columns per sheet:", NCOL)

IMG_W, IMG_H = 78, 50          # display size (px)
row4_style_fill = fill_total()
n_embedded = 0
for b, pids in sorted(by_brand.items(), key=lambda x: x[0]):
    sname = brand_sheet_name[b]
    ws = wb.create_sheet(sname)
    setup_sheet(ws, title=f"{b} — {len(pids)} dòng xe • {n_props} thông số", last_col=min(NCOL, 40))
    ws.row_dimensions[4].height = 28   # image strip (2 rows)
    ws.row_dimensions[5].height = 28
    # row 6: property groups
    gi = 3
    for gname, props in groups.items():
        span = len(props)
        if span == 0:
            continue
        ws.merge_cells(start_row=6, start_column=gi, end_row=6, end_column=gi + span - 1)
        c = ws.cell(row=6, column=gi, value=gname)
        c.font = font_subheader(); c.fill = row4_style_fill
        c.alignment = Alignment(horizontal="left", vertical="center")
        for cc in range(gi, gi + span):
            ws.cell(row=6, column=cc).fill = row4_style_fill
            ws.cell(row=6, column=cc).font = font_subheader()
    cB6 = ws.cell(row=6, column=2, value="Thông tin xe")
    cB6.font = font_subheader(); cB6.fill = row4_style_fill
    ws.cell(row=6, column=2).fill = row4_style_fill
    ws.row_dimensions[6].height = 22
    # row 7: property names
    ws.cell(row=7, column=2, value="Tên xe (Full Name)")
    gi = 3
    for gname, props in groups.items():
        for pid, meta in props.items():
            ws.cell(row=7, column=gi, value=meta["name"])
            gi += 1
    style_header_row(ws, 7, 2, NCOL)
    ws.row_dimensions[7].height = 48
    # data: sort by Model -> year descending -> name
    pids_sorted = sorted(pids, key=lambda p: (str(model_of.get(p) or ""), -(year_of.get(p) or 0),
                                              str(name_of.get(p, ""))))
    r = 8
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
                   value="Nguồn: A2MAC1 IBP • cào ngày 11/11/2026 • ô trống = A2MAC1 chưa có dữ liệu cho thông số này")
    note.font = font_caption()
    ws.freeze_panes = "C8"
    ws.column_dimensions["B"].width = 36
    auto_fit_columns(ws, min_width=10, max_width=26, header_row=7, data_start_row=8)
    ws.column_dimensions["B"].width = 36
    # ensure vehicle columns are wide enough for images (>= 12.5 chars ~ 92px)
    for ci in range(3, NCOL + 1):
        L = get_column_letter(ci)
        cur = ws.column_dimensions[L].width or 10
        if cur < 12.5:
            ws.column_dimensions[L].width = 12.5
    # embed images above each vehicle column
    for i, pid in enumerate(pids_sorted):
        ci = 3 + i
        L = get_column_letter(ci)
        src = img_map.get(pid)
        if src:
            img = XLImage(str(src))
            w0, h0 = img.width, img.height
            scale = min(IMG_W / w0, IMG_H / h0)
            img.width = int(w0 * scale); img.height = int(h0 * scale)
            ws.add_image(img, f"{L}4")
            n_embedded += 1
        else:
            c = ws.cell(row=4, column=ci, value="Không có ảnh")
            c.font = font_caption()
            c.alignment = Alignment(horizontal="left", vertical="top")
print("images embedded:", n_embedded)

# ---------- 4. CAD & 3D sheet ----------
cad = wb.create_sheet("CAD & 3D")
cad.sheet_properties.tabColor = "2E75B6"
setup_sheet(cad, title="Dữ liệu bổ sung trên A2MAC1 — 3D / CAD / Teardown", last_col=5)
for c, h in enumerate(["Loại dữ liệu", "A2MAC1 có gì", "Cơ chế / Endpoint", "Trạng thái"], 2):
    cad.cell(row=4, column=c, value=h)
style_header_row(cad, 4, 2, 5)

cad_rows = [
    ("Ảnh xe (Photos)",
     "621/621 xe ĐÃ CÓ ĐỦ ảnh, nhúng phía trên cột mỗi xe trong các sheet hãng: 518 ảnh tiêu chuẩn (300x200, "
     "blob công khai) + 103 ảnh fullHD riêng tư (lên tới 4496x3000, đa số mẫu 2025-2026) đã tải bằng cơ chế file-token.",
     "Ảnh công khai: blob storage legacystorageeu.blob.core.windows.net/public. Ảnh riêng tư: GET "
     "/files/downloads/files?token=<fileToken>&api-version=1.1 — ĐÃ CHẠY THÀNH CÔNG (103/103).",
     "HOÀN THÀNH 621/621. Bản fullHD 193 MB nằm ở thư mục A2MAC1_anh_xe_fullHD; bản nhúng trong Excel đã tối ưu dung lượng."),
    ("File 3D/CAD từng linh kiện (ĐÃ QUÉT XONG)",
     "ĐÃ quét xong danh mục cho 578/621 xe: tổng 923.551 file mô hình 3D linh kiện, 100% isDownloadable=true "
     "(trung bình ~1.600 file/xe; xe nhiều nhất ~2.300 file). Mỗi file có: part number, vật liệu (Metal > Steel, "
     "Plastics > PP...), bản HD/SD, token tải riêng. 43 xe còn lại không có package 3D trên nền tảng.",
     "Liệt kê: POST /api/visual/files/get-files?api-version=2.0, body {productIds, hierarchyId: "
     "00000003LSK4EU01 (3D AutoReverse) hoặc 00000005ZT4GEU01 (Vehicle Occupant Packaging)}. Gói dữ liệu xe: "
     "GET /api/visual/files/packages?productIds=... Xem chi tiết từng xe trong sheet '3D & Teardown'.",
     "HOÀN THÀNH — danh mục 923.551 file đã tổng hợp theo xe. File tải được bằng token qua /files/downloads/files "
     "(cơ chế đã chạy thành công với ảnh). Tải hàng loạt cần chia phiên theo giới hạn 250 lượt visual của nền tảng."),
    ("Dữ liệu 3D tương tác (3D Viewer)",
     "5 bộ phân tích 3D: 3D AutoReverse, BIW (thân xe trắng), Chassis (khung gầm), Vehicle Occupant Packaging "
     "(không gian người ngồi), xEV Powertrain (động cơ - xe điện). Viewer nền tảng dùng glTF nén Draco.",
     "Trạng thái 3D/Teardown của TỪNG xe: POST /api/hierarchies/A000005AE6M1EU01/parts, filter "
     "\"product-id eq <productId>\" — trả về 3D Data - Status, Teardown Data - Status, ngày bàn giao dữ liệu.",
     "Endpoint đã xác minh 200 OK + đã quét teardown cho 420/621 xe (còn 201 xe bị 403 giữa phiên — cần token mới).",
     "Đã xác minh với xe mẫu. Cần phiên đăng nhập còn hạn để quét nốt 201 xe còn lại."),
    ("Parts / Teardown (BOM linh kiện)",
     "Danh mục linh kiện theo xe kèm 12 thuộc tính: Package, Status, Teardown Data - Status, Teardown Delivery Date, "
     "3D Data - Status, Preliminary/Final Data Delivery + ngày, và ảnh từng linh kiện.",
     "POST /api/hierarchies/{hierarchyId}/parts với filter \"product-id eq <productId>\", phân trang 50 dòng/lượt.",
     "Đã xác minh + quét được 420/621 xe (12 thuộc tính/bản ghi). Cần token mới để quét nốt 201 xe."),
    ("Tải file về (Download)",
     "Tải 1 file: /files/downloads/files?token=...&api-version=1.1 (+ tham số filename, applyWatermark). Tải nhiều "
     "file: POST /downloads (gộp archive). Có /downloads/archives/ và tải composite. Giới hạn nền tảng: 250 lượt "
     "tải visual. Quyền tài khoản: data.export-download ĐÃ CÓ.",
     "downloadService.downloadFile(baseUrl, fileToken, version, filename) — baseUrl = packageBaseUrl của gói.",
     "Cơ chế đã xác minh (dùng thành công cho ảnh). File 3D/CAD của từng linh kiện tải được bằng token tương tự."),
    ("Costing (chi phí bộ phận)",
     "Module tính chi phí theo linh kiện/hệ của xe.",
     "costing.web-component-url (theo cấu hình nền tảng).",
     "Phụ thuộc license Costing của tài khoản — chưa kiểm tra được."),
    ("Planning (kế hoạch dữ liệu)",
     "Bảng kế hoạch phát hành dữ liệu A2MAC1 (Worldwide_Planning.xlsm).",
     "planning.file-url.",
     "Có thể tải khi phiên đăng nhập còn hạn."),
]
rr = 5
for i, row_vals in enumerate(cad_rows):
    for c, v in enumerate(row_vals, 2):
        cell = cad.cell(row=rr, column=c, value=v)
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    style_data_row(cad, rr, 2, 5, i)
    for c in range(2, 6):
        cad.cell(row=rr, column=c).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    # estimate row height from the longest text
    est_lines = max(math.ceil(len(str(v)) / 55) for v in row_vals)
    cad.row_dimensions[rr].height = max(34, est_lines * 13 + 8)
    rr += 1

guide = cad.cell(row=rr + 1, column=2,
                 value="VIỆC CÒN LẠI (cần token mới): ① quét teardown cho 201 xe còn lại; ② tải file 3D/CAD thật theo nhu cầu "
                       "benchmark (danh mục 923.551 file đã sẵn sàng trong sheet '3D & Teardown' — chọn xe + linh kiện rồi tải "
                       "qua /files/downloads/files?token=...). Cách cấp token: mở ibp.a2mac1.com → F12 → Application → Cookies → "
                       "copy 'access_token' gửi vào chat ngay (hạn ~24 phút). Ảnh xe đã đủ 621/621.")
guide.font = font_caption()
guide.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
cad.merge_cells(start_row=rr + 1, start_column=2, end_row=rr + 1, end_column=5)
cad.row_dimensions[rr + 1].height = 44
cad.column_dimensions["B"].width = 28
cad.column_dimensions["C"].width = 58
cad.column_dimensions["D"].width = 50
cad.column_dimensions["E"].width = 44
cad.freeze_panes = "B5"

# ---------- 5. Review sheet ----------
rv = wb.create_sheet("Review")
rv.sheet_properties.tabColor = "FFC000"
setup_sheet(rv, title="Kiểm tra chéo — số dòng xe mỗi hãng", last_col=6)
for c, h in enumerate(["Hãng xe", "Kỳ vọng", "Thực tế (COUNTA)", "Ảnh nhúng", "Trạng thái"], 2):
    rv.cell(row=4, column=c, value=h)
style_header_row(rv, 4, 2, 6)
r = 5
for b, pids in sorted(by_brand.items(), key=lambda x: x[0]):
    sname = brand_sheet_name[b]
    n_img = sum(1 for pid in pids if pid in img_map)
    rv.cell(row=r, column=2, value=b)
    rv.cell(row=r, column=3, value=len(pids))
    rv.cell(row=r, column=4, value=f"=COUNTA('{sname}'!B8:B{7 + len(pids)})")
    rv.cell(row=r, column=5, value=n_img)
    rv.cell(row=r, column=6, value=f'=IF(C{r}=D{r},"PASS","FAIL")')
    style_data_row(rv, r, 2, 6, r - 5)
    r += 1
rv.cell(row=r, column=2, value="TỔNG")
rv.cell(row=r, column=3, value=len(vehicles))
rv.cell(row=r, column=4, value=f"=SUM(D5:D{r-1})")
rv.cell(row=r, column=5, value=len(img_map))
rv.cell(row=r, column=6, value=f'=IF(C{r}=D{r},"PASS","FAIL")')
style_total_row(rv, r, 2, 6)
rv.column_dimensions["B"].width = 26
rv.column_dimensions["C"].width = 12
rv.column_dimensions["D"].width = 18
rv.column_dimensions["E"].width = 12
rv.column_dimensions["F"].width = 14

wb.save(OUT)
print("SAVED:", OUT, f"({OUT.stat().st_size/1024/1024:.1f} MB)")
