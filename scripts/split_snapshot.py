"""Tach 182 file STL doc quyen tu snapshot-zip (808MiB) thanh cac part nho ~85MB vao download/.
Bo qua file da co trong 15 part + part16. Stream copy, khong phu RAM."""
import zipfile, json
from pathlib import Path
from collections import Counter

DL = Path("/home/z/my-project/download")
SNAP = Path("/tmp/my-project/download/DATA-CAD.zip")
PART_SIZE_FILES = 25  # ~85MB/part

# tap file da co trong download/ (part01..16)
have = set()
for zp in sorted(DL.glob("DATA-CAD*.zip")):
    try:
        have |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(zp).namelist() if nm.endswith(".stl"))
    except Exception:
        pass
print(f"download/ dang co {len(have)} STL unique")

z = zipfile.ZipFile(SNAP)
names = [nm for nm in z.namelist() if nm.endswith(".stl")]
exclusive = [nm for nm in names if nm.split("/")[-1] not in have]
print(f"snapshot co {len(names)} STL, doc quyen: {len(exclusive)}")
mb = sum(z.getinfo(nm).compress_size for nm in exclusive) / 1048576
print(f"dung luong doc quyen: {mb:.0f}MiB")

# manifest goc neu co
man_src = None
if "_MANIFEST.json" in z.namelist():
    try:
        man_src = json.loads(z.read("_MANIFEST.json"))
        v6 = man_src.get("VinFast VF6 Plus 2024", {})
        print(f"manifest snapshot: total={v6.get('total_files')}, files list={len(v6.get('files', []))}")
    except Exception as e:
        print("manifest snapshot doc loi:", e)

# tach thanh cac part 17..NN
batches = [exclusive[i:i + PART_SIZE_FILES] for i in range(0, len(exclusive), PART_SIZE_FILES)]
made = []
for bi, batch in enumerate(batches):
    outp = DL / f"DATA-CAD_{17 + bi:02d}.zip"
    with zipfile.ZipFile(outp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zo:
        for nm in batch:
            with z.open(nm) as fsrc, zo.open(nm, "w") as fdst:
                while True:
                    chunk = fsrc.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    fdst.write(chunk)
        m = {"VinFast VF6 Plus 2024": {"product": "A00000552G3KEU01",
             "note": f"Part {17 + bi}: trich {len(batch)} file doc quyen tu bo cu (gom 894 file lan dau)",
             "files": sorted(nm.split("/")[-1] for nm in batch)}}
        zo.writestr("_MANIFEST.json", json.dumps(m, ensure_ascii=False, indent=1))
    made.append(outp.name)
    print(f"  tao {outp.name}: {len(batch)} file, {outp.stat().st_size/1048576:.0f}MiB")

# kiem tra lai tong
tot = set()
for zp in sorted(DL.glob("DATA-CAD*.zip")):
    tot |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(zp).namelist() if nm.endswith(".stl"))
print(f"\nTONG download/ sau khi tach: {len(tot)} STL unique / 1670 (thieu {1670 - len(tot)})")
ok = all(zipfile.ZipFile(DL / n).testzip() is None for n in made)
print("testzip cac part moi:", "OK" if ok else "LOI")
Path("/home/z/my-project/data/cad_have.json").write_text(json.dumps(sorted(tot), ensure_ascii=False, indent=0))
