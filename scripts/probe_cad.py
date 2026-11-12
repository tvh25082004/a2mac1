#!/usr/bin/env python3
"""Try get-files with the package hierarchyId + download files with the package token."""
import os, re, json
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
env = Path("/home/z/my-project/scripts/.env").read_text()
raw = env.split("A2MAC1_TOKEN='")[1].split("'")[0]
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": BASE, "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

PIDS = ["A0000004F0UTEU02", "00000001E3FYEU01"]
r = S.get(BASE + "/api/visual/files/packages", params=[("productIds", p) for p in PIDS], timeout=60)
pkgs = r.json()
print("packages:", len(pkgs))
hids = sorted({h for pk in pkgs for h in (pk.get("hierarchyIds") or [])})
print("hierarchyIds in packages:", hids)

for hid in hids[:3]:
    body = {"productIds": PIDS, "hierarchyId": hid, "isBookmark": False}
    r = S.post(BASE + "/api/visual/files/get-files?api-version=2.0", json=body, timeout=60)
    print(f"get-files {hid}: {r.status_code} {len(r.content)}")
    if r.status_code == 200 and len(r.content) > 4:
        d = r.json()
        print(json.dumps(d, indent=1)[:2500])
        Path("/home/z/my-project/data/visual_files_sample.json").write_text(json.dumps(d))
        break

# trial download using the package token (first package)
pk = pkgs[0]
ptok = pk["token"]
for pat in ["/files/downloads/files", "/files/downloads"]:
    r = S.get(BASE + pat, params={"token": ptok, "api-version": "1.1"}, timeout=120)
    ct = r.headers.get("content-type", "")
    print(f"dl {pat}: {r.status_code} {ct[:40]} {len(r.content)}")
    if r.status_code == 200 and len(r.content) > 1000:
        fn = "/tmp/pkg_test" + (".zip" if "zip" in ct else ".bin")
        Path(fn).write_bytes(r.content)
        print("SAVED", fn)
        import zipfile
        if fn.endswith(".zip"):
            z = zipfile.ZipFile(fn)
            for n in z.namelist()[:15]:
                print("   ", n, z.getinfo(n).file_size)
        break
