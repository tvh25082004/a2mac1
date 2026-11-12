"""Split DATA-CAD.zip (2.49GB) into independent ~200MB parts (each part self-extractable).
Before deleting the master: save the list of downloaded files (resume for the next CAD session).
"""
import json, zipfile, os, shutil
from pathlib import Path

DL = Path("/home/z/my-project/download")
MASTER = DL / "DATA-CAD.zip"
CHUNK_TARGET = 200e6  # ~200MB per part
DATA = Path("/home/z/my-project/data")

# 1) Save skip-list + metadata to resume the next session (master will be deleted)
z = zipfile.ZipFile(MASTER)
names = z.namelist()
stl = [n for n in names if n.endswith(".stl")]
vinfos = [i for i in z.infolist() if i.filename == "_MANIFEST.json"]
mf = json.loads(z.open(vinfos[-1]).read())
(DATA / "cad_skip_list.json").write_text(json.dumps(
    {"product": mf.get("product"), "name": mf.get("name"),
     "hierarchy": mf.get("hierarchy"), "total_files": mf.get("total_files"),
     "done_files": sorted(stl)}, ensure_ascii=False, indent=1))
print(f"skip-list: {len(stl)} files downloaded -> data/cad_skip_list.json")

# 2) Split entries by target size (using known compressed size)
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
print(f"split {len(info_items)} files into {len(chunks)} parts (~{CHUNK_TARGET/1e6:.0f}MB)")

# 3) Write each chunk: each part includes _MANIFEST.json => independently extractable
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

# 4) Verify integrity of each part
bad = []
for p in chunk_paths:
    zz = zipfile.ZipFile(p)
    if zz.testzip() is not None:
        bad.append(p.name)
print("testzip:", "ALL OK" if not bad else f"ERROR: {bad}")

# 5) Delete master to reclaim 2.49GB of disk (chunks + skip-list are safe)
if not bad:
    MASTER.unlink()
    print(f"deleted {MASTER.name} -> free disk: {shutil.disk_usage('/home/z/my-project').free/1e9:.1f}GB")
# 6) Write README for the user
readme = """GUIDE - CAD DATA VinFast VF6 Plus 2024 (STL)
================================================
1. Download ALL the DATA-CAD_01.zip ... DATA-CAD_NN.zip files (each ~200MB)
2. Extract ALL of them into the SAME folder (e.g. C:\\CAD\\VF6\\)
3. Result: all 3D STL files per vehicle part + _MANIFEST.json
   (_MANIFEST.json: part number, material, dimensions of each part)

Open STL files with (free):
- Windows 3D Viewer (preinstalled)  - FreeCAD  - MeshLab
- SolidWorks / CATIA / NX (import STL)

Source: A2MAC1 IBP - GET /files/downloads/files?token=<fileToken>&api-version=1.1
Vehicle: VinFast VF6 Plus 2024 - 3D AutoReverse set (00000003LSK4EU01)
"""
(DL / "README-DATA-CAD.txt").write_text(readme, encoding="utf-8")
print("done README-DATA-CAD.txt")
