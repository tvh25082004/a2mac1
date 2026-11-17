#!/usr/bin/env python3
"""Create/update GitHub Release 'au-vop-v1' with the A&U Package Measurements Excel
+ the 621-car capture tracker. Reads GH_PAT from scripts/.env (never printed)."""
import json
from pathlib import Path
import requests

USER, REPO = "tvh25082004", "a2mac1"
TAG = "au-vop-v1"
env = dict(l.strip().split("=", 1) for l in (Path(__file__).parent / ".env").read_text().splitlines() if "=" in l)
PAT = env.get("GH_PAT", "").strip().strip("'")
assert PAT, "Missing GH_PAT"
H = {"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{USER}/{REPO}"

BODY = (
    "**A&U team request — Package Measurements data (Vehicle Occupant Packaging, SAE J1100 / ISO)**\n\n"
    "Reference image received: BYD Tang L EV — Data Explorer → Vehicle Occupant Packaging → Package Measurements → "
    "Schematics → Exterior Dimensions → Height (side-view line drawing with SAE measure codes + values).\n\n"
    "**Verified obtainable (probe, BYD Tang L EV 2025):**\n"
    "- 43 SAE/A2M measure records as text (36 numeric values + 7 standards refs: SAE J1100 NOV2009, SAE J826 JUN2021, SAE J4004 AUG2008, GCIE 2019)\n"
    "- 26 media files: 6 Schematic JPG/PNG + 19 Manikin JPG (Front/2nd Row/3rd Row) + 1 ZIP package drawings\n"
    "- Values match the reference screenshot exactly: H156-GVM=167.8, H196=809.1, H202=782.5, H251=1880.0\n\n"
    "**Files:**\n"
    "- `A2MAC1_AU_Package_Measurements.xlsx` — values matrix (1 car fully probed), media gallery inventory, "
    "full 621-car catalogue with harvest status, request & method notes\n"
    "- `A2MAC1_Capture_Tracker_621.xlsx` — master capture tracker: 621 cars, 510 with 3D, 8 cars COMPLETE "
    "(7,782 parts x 4 views) on release cad-captures-v1\n\n"
    "**Status:** full 621-car harvest (`scripts/harvest_vop_all.py`, resume-capable) pending a fresh access_token "
    "(JWT lifetime ~25-30 min; last token expired). Images (JPG) will be downloaded and embedded in the Excel on the next run.\n\n"
    "_No credentials or tokens are included in any asset._"
)

# create or fetch release
r = requests.get(f"{api}/releases/tags/{TAG}", headers=H, timeout=30)
if r.status_code == 200:
    rel = r.json()
    requests.patch(f"{api}/releases/{rel['id']}", headers=H, timeout=30,
                   json={"name": "A&U Package Measurements + Capture Tracker", "body": BODY})
    print("release updated:", rel["id"])
else:
    r = requests.post(f"{api}/releases", headers=H, timeout=30, json={
        "tag_name": TAG, "target_commitish": "main",
        "name": "A&U Package Measurements + Capture Tracker", "body": BODY})
    rel = r.json()
    print("release created:", rel.get("id"), rel.get("html_url"))

aup = f"https://uploads.github.com/repos/{USER}/{REPO}/releases/{rel['id']}/assets"
have = {a["name"] for a in requests.get(f"{api}/releases/{rel['id']}/assets", headers=H, timeout=30).json()}
for f in ["/home/z/my-project/download/A2MAC1_AU_Package_Measurements.xlsx",
          "/home/z/my-project/download/A2MAC1_Capture_Tracker_621.xlsx"]:
    p = Path(f); name = p.name
    if name in have:
        requests.delete(f"{api}/releases/assets/" + str([a["id"] for a in requests.get(f"{api}/releases/{rel['id']}/assets", headers=H).json() if a["name"] == name][0]), headers=H)
        print("  deleted old", name)
    with open(p, "rb") as fh:
        rr = requests.post(aup, params={"name": name}, headers={
            "Authorization": f"token {PAT}", "Content-Type": "application/octet-stream"}, data=fh, timeout=600)
    print("  upload", name, "->", rr.status_code, rr.json().get("browser_download_url", rr.text[:150]))
print("LINK: https://github.com/" + USER + "/" + REPO + "/releases/tag/" + TAG)
