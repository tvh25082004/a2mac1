#!/usr/bin/env python3
"""Try downloading the 26 VOP media files (6 Schematic PNG + 19 Manikin JPG + 1 ZIP)
for BYD Tang L EV 2025 using ONLY the per-file download tokens saved in session #15
(data/vop_cmp_00000004YO7QEU01.json + data/vop_schem_summary.json).
No JWT required if the file tokens are still valid. Tokens are never printed."""
import json, time
from pathlib import Path
import requests

BASE = "https://ibp.a2mac1.com"
ROOT = Path("/home/z/my-project")
OUT = ROOT / "download" / "VOP_media" / "BYD_Tang_L_EV_2025"
OUT.mkdir(parents=True, exist_ok=True)

items = []  # (kind, seq, token, ext)
# 6 Schematic PNG from the Summary node compare dump (names 05..10)
j = json.load(open(ROOT / "data" / "vop_cmp_00000004YO7QEU01.json"))
pv = (j.get("values") or {}).get("A0000074SYPAEU01") or {}
for _propid, scen in pv.items():
    if isinstance(scen, dict):
        for _s, entries in scen.items():
            if isinstance(entries, list):
                for e in entries:
                    if (e.get("propertyName") or "") == "Schematic":
                        det = e.get("details") or {}
                        if det.get("token"):
                            items.append(("Schematic", det.get("name") or "x", det["token"],
                                          (det.get("extension") or "png").lower()))
# 20 gallery tokens from the Package Measurements node
ss = json.load(open(ROOT / "data" / "vop_schem_summary.json"))
seq = {}
for t in ss.get("tokens", []):
    nm = t.get("name") or "item"
    seq[nm] = seq.get(nm, 0) + 1
    ext = (t.get("ext") or "bin").lower()
    items.append((nm, seq[nm], t.get("token"), ext))

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://ibp.a2mac1.com/"})

ok, fail = [], []
for kind, seqn, tok, ext in items:
    label = f"{kind}-{seqn}.{ext}"
    fname = f"BYD_Tang_L_EV_2025_{kind.replace(' ', '-')}-{seqn}.{ext}"
    fpath = OUT / fname
    if fpath.exists() and fpath.stat().st_size > 100:
        ok.append((label, fpath.stat().st_size, "cached"))
        continue
    if not tok:
        fail.append((label, "no-token")); continue
    r = S.get(f"{BASE}/files/downloads/files", params={"token": tok, "api-version": "1.1"}, timeout=180)
    if r.status_code == 200 and len(r.content) > 100:
        fpath.write_bytes(r.content)
        ok.append((label, len(r.content), "downloaded"))
        print(f"OK   {fname}  {len(r.content)/1e6:.2f} MB", flush=True)
    else:
        fail.append((label, f"HTTP{r.status_code}"))
        print(f"FAIL {label}  HTTP{r.status_code}", flush=True)
    time.sleep(0.4)

print(f"\nDONE: {len(ok)} ok, {len(fail)} fail -> {OUT}")
json.dump({"ok": [[k, s, m] for k, s, m in ok], "fail": fail},
          open(ROOT / "data" / "vop_media_download_state.json", "w"), indent=1)
