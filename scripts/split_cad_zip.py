"""Chia DATA-CAD.zip (2.49GB) thành các phần ~200MB độc lập (mỗi phần tự giải nén được).
Trước khi xóa master: lưu danh sách file đã tải (resume cho phiên CAD kế tiếp).
"""
import json, zipfile, os, shutil
from pathlib import Path

DL = Path("/home/z/my-project/download")
MASTER = DL / "DATA-CAD.zip"
CHUNK_TARGET = 200e6  # ~200MB mỗi phần
DATA = Path("/home/z/my-project/data")

# 1) Lưu skip-list + metadata để resume phiên sau (master sẽ bị xóa)
z = zipfile.ZipFile(MASTER)
names = z.namelist()
stl = [n for n in names if n.endswith(".stl")]
vinfos = [i for i in z.infolist() if i.filename == "_MANIFEST.json"]
mf = json.loads(z.open(vinfos[-1]).read())
(DATA / "cad_skip_list.json").write_text(json.dumps(
    {"product": mf.get("product"), "name": mf.get("name"),
     "hierarchy": mf.get("hierarchy"), "total_files": mf.get("total_files"),
     "done_files": sorted(stl)}, ensure_ascii=False, indent=1))
print(f"skip-list: {len(stl)} file đã tải -> data/cad_skip_list.json")

# 2) Chia entry theo dung lượng target (dùng compressed size đã biết)
info_items = [i for i in z.infolist() if i.filename.endswith(".stl")]
info_items.sort(key=lambda i: i.filename)
chunks = []
cur, cur_size = [], 0
for it in info_items:
    sz = max(i.file_size for i in [it])  # uncompressed
    if cur and cur_size + sz > CHUNK_TARGET:
        chunks.append(cur); cur, cur_size = [], 0
    cur.append(it); cur_size += sz
if cur: chunks.append(cur)
print(f"chia {len(info_items)} file thành {len(chunks)} phần (~{CHUNK_TARGET/1e6:.0f}MB)")

# 3) Ghi từng chunk: mỗi phần kèm _MANIFEST.json => tự giải nén độc lập
manifest_str = json.dumps(mf, ensure_ascii=False, indent=1)
chunk_paths = []
for ci, items in enumerate(chunks, 1):
    out = DL / f"DATA-CAD_{ci:02d}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zo:
        for it in items:
            zo.writestr(it.filename, z.open(it).read())
        zo.writestr("_MANIFEST.json", manifest_str)
    chunk_paths.append(out)
    print(f"  {out.name}: {len(items)} file, {out.stat().st_size/1e6:.0f}MB")
z.close()

# 4) Kiểm tra nguyên trạng từng phần
bad = []
for p in chunk_paths:
    zz = zipfile.ZipFile(p)
    if zz.testzip() is not None:
        bad.append(p.name)
print("testzip:", "OK tất cả" if not bad else f"LỖI: {bad}")

# 5) Xóa master để lấy lại 2.49GB disk (chunks + skip-list đã an toàn)
if not bad:
    MASTER.unlink()
    print(f"đã xóa {MASTER.name} -> disk free: {shutil.disk_usage('/home/z/my-project').free/1e9:.1f}GB")
# 6) Ghi README cho user
readme = """HƯỚNG DẪN - DATA CAD VinFast VF6 Plus 2024 (STL)
================================================
1. Tải TẤT CẢ các file DATA-CAD_01.zip ... DATA-CAD_NN.zip (mỗi file ~200MB)
2. Giải nén TẤT CẢ vào CÙNG một thư mục (VD: C:\\CAD\\VF6\\)
3. Kết quả: toàn bộ file STL 3D từng linh kiện xe + _MANIFEST.json
   (_MANIFEST.json: part number, vật liệu, kích thước từng linh kiện)

Mở file STL bằng (miễn phí):
- Windows 3D Viewer (cài sẵn)  - FreeCAD  - MeshLab
- SolidWorks / CATIA / NX (nhập STL)

Nguồn: A2MAC1 IBP - GET /files/downloads/files?token=<fileToken>&api-version=1.1
Xe: VinFast VF6 Plus 2024 - bộ 3D AutoReverse (00000003LSK4EU01)
"""
(DL / "README-DATA-CAD.txt").write_text(readme, encoding="utf-8")
print("xong README-DATA-CAD.txt")
