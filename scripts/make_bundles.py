"""Merge chunk zips (DATA-CAD_*.zip / CAD-VF6-*.zip) into bundles <=1.85GB for the GitHub Release.
Safe resume: write to .part, verify, only then rename to .zip + delete the sources. Killing mid-run = no data loss."""
import zipfile, json, sys
from pathlib import Path

DL = Path("/home/z/my-project/download")
BD = DL / "bundles"; BD.mkdir(exist_ok=True)
TARGET = 1.85e9  # GitHub asset limit 2GB

def close_and_verify(zpath, out, srcs_used, moved):
    out.close()
    z = zipfile.ZipFile(zpath)
    bad = z.testzip()
    cnt = sum(1 for nm in z.namelist() if nm.endswith(".stl"))
    z.close()
    if bad is not None:
        print(f"  ERROR {zpath.name}: {bad} -> keeping as-is for inspection"); sys.exit(1)
    final = zpath.with_suffix("") .with_suffix(".zip") if zpath.name.endswith(".zip.part") else zpath
    # zpath = 'CAD-..._01.zip.part' -> final 'CAD-..._01.zip'
    final = zpath.parent / zpath.name[:-5]
    zpath.rename(final)
    print(f"  OK {final.name}: {cnt} STL, {final.stat().st_size/1e9:.2f}GB")
    for sp in srcs_used:
        sp.unlink()
    return cnt

srcs = sorted(list(DL.glob("DATA-CAD_*.zip")) + list(DL.glob("CAD-VF6-*.zip")))
if not srcs:
    print("No chunks left to merge."); sys.exit(0)
n = len(list(BD.glob("CAD-bundle-*.zip"))) + 1
total_in = sum(sp.stat().st_size for sp in srcs) / 1e9
print(f"Merging {len(srcs)} chunks ({total_in:.1f}GB) -> bundle #{n}...")

zpath = BD / f"CAD-bundle-{n:02d}.zip.part"
out = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=1)  # level 1: STLs already compressed, merge fast
srcs_used, moved, cur = [], 0, 0
for sp in srcs:
    try:
        z = zipfile.ZipFile(sp)
    except Exception:
        sp.unlink(missing_ok=True); continue  # chunk corrupt -> drop it (already verified earlier)
    for nm in [nm for nm in z.namelist() if nm.endswith(".stl")]:
        out.writestr(nm, z.read(nm))
        cur += out.getinfo(nm).compress_size
        moved += 1
    z.close()
    srcs_used.append(sp)
    if cur > TARGET:
        out.writestr("_MANIFEST.json", json.dumps({"bundle": zpath.name, "stl": moved,
                        "sources": [s.name for s in srcs_used]}, ensure_ascii=False))
        close_and_verify(zpath, out, srcs_used, moved)
        n += 1
        srcs_used, moved, cur = [], 0, 0
        zpath = BD / f"CAD-bundle-{n:02d}.zip.part"
        out = zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=1)
if moved:
    out.writestr("_MANIFEST.json", json.dumps({"bundle": zpath.name, "stl": moved,
                    "sources": [s.name for s in srcs_used]}, ensure_ascii=False))
    close_and_verify(zpath, out, srcs_used, moved)
print(f"DONE. Bundles in {BD}:")
for b in sorted(BD.glob("CAD-bundle-*.zip")):
    print(f"  {b.name}  {b.stat().st_size/1e9:.2f}GB")
