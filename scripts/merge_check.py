"""Kiem ke toan bo STL VF6 da co: snapshot zip + 15 part + part16 -> unique, thieu gi."""
import zipfile, json, re
from pathlib import Path

DL = Path("/home/z/my-project/download")
SNAP = Path("/tmp/my-project/download/DATA-CAD.zip")
sources = {}
all_files = {}  # fname -> list(zip nơi chứa)

def scan(zp, label):
    try:
        z = zipfile.ZipFile(zp)
    except Exception as e:
        print(f"[{label}] LOI mo: {e}"); return 0
    stls = [nm for nm in z.namelist() if nm.endswith(".stl")]
    bad = z.testzip()
    mb = sum(i.compress_size for i in z.infolist()) / 1048576
    print(f"[{label}] {len(stls)} STL, {mb:.0f}MiB, testzip={'OK' if bad is None else 'LOI:'+bad}")
    for nm in stls:
        f = nm.split("/")[-1]
        all_files.setdefault(f, []).append(label)
    return len(stls)

print("=== CAC NGUON ===")
n = scan(SNAP, "snapshot-zip(894?)")
for i in range(1, 16):
    scan(DL / f"DATA-CAD_{i:02d}.zip", f"part{i:02d}")
scan(DL / "DATA-CAD_16.zip", "part16")

print(f"\n=== TONG ===")
print(f"Tong STL unique: {len(all_files)} / 1670")
# doc skip tu manifest part16 de biet dung
z16 = zipfile.ZipFile(DL / "DATA-CAD_16.zip")
try:
    man = json.loads(z16.read("_MANIFEST.json"))
    vf6 = man.get("VinFast VF6 Plus 2024", {})
    print(f"Manifest part16: total_files server={vf6.get('total_files')}, da tai lan nay={len(vf6.get('files', []))}, incomplete={vf6.get('incomplete')}")
except Exception as e:
    print("Manifest loi:", e)
dup = {f: v for f, v in all_files.items() if len(v) > 1}
print(f"File trung lap giua cac nguon: {len(dup)}")
from collections import Counter
c = Counter(f for v in dup.values() for f in v)
print("Muc do trung theo nguon:", dict(c.most_common()))
# luu danh sach unique de lan sau skip
Path("/home/z/my-project/data/cad_have.json").write_text(json.dumps(sorted(all_files), ensure_ascii=False, indent=0))
print("Da luu data/cad_have.json")
