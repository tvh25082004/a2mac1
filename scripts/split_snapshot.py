"""Split 182 exclusive STL files from the snapshot-zip (808MiB) into small ~85MB parts into download/.
Skip files already present in the 15 parts + part16. Stream copy, low RAM usage."""
import zipfile, json
from pathlib import Path
from collections import Counter

DL = Path("/home/z/my-project/download")
SNAP = Path("/tmp/my-project/download/DATA-CAD.zip")
PART_SIZE_FILES = 25  # ~85MB/part

# set of files already in download/ (part01..16)
have = set()
for zp in sorted(DL.glob("DATA-CAD*.zip")):
    try:
        have |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(zp).namelist() if nm.endswith(".stl"))
    except Exception:
        pass
print(f"download/ currently has {len(have)} unique STLs")

z = zipfile.ZipFile(SNAP)
names = [nm for nm in z.namelist() if nm.endswith(".stl")]
exclusive = [nm for nm in names if nm.split("/")[-1] not in have]
print(f"snapshot has {len(names)} STLs, exclusive: {len(exclusive)}")
mb = sum(z.getinfo(nm).compress_size for nm in exclusive) / 1048576
print(f"exclusive volume: {mb:.0f}MiB")

# original manifest if present
man_src = None
if "_MANIFEST.json" in z.namelist():
    try:
        man_src = json.loads(z.read("_MANIFEST.json"))
        v6 = man_src.get("VinFast VF6 Plus 2024", {})
        print(f"manifest snapshot: total={v6.get('total_files')}, files list={len(v6.get('files', []))}")
    except Exception as e:
        print("manifest snapshot read error:", e)

# split into parts 17..NN
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
             "note": f"Part {17 + bi}: extracted {len(batch)} exclusive files from the old set (894 files at first run)",
             "files": sorted(nm.split("/")[-1] for nm in batch)}}
        zo.writestr("_MANIFEST.json", json.dumps(m, ensure_ascii=False, indent=1))
    made.append(outp.name)
    print(f"  created {outp.name}: {len(batch)} files, {outp.stat().st_size/1048576:.0f}MiB")

# re-check the total
tot = set()
for zp in sorted(DL.glob("DATA-CAD*.zip")):
    tot |= set(nm.split("/")[-1] for nm in zipfile.ZipFile(zp).namelist() if nm.endswith(".stl"))
print(f"\nTOTAL download/ after splitting: {len(tot)} unique STLs / 1670 (missing {1670 - len(tot)})")
ok = all(zipfile.ZipFile(DL / n).testzip() is None for n in made)
print("testzip new parts:", "OK" if ok else "ERR")
Path("/home/z/my-project/data/cad_have.json").write_text(json.dumps(sorted(tot), ensure_ascii=False, indent=0))
