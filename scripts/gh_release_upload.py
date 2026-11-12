"""Day code + upload CAD bundle len GitHub Release (tvh25082004/a2mac1).
Can GH_PAT trong scripts/.env (scope: repo). Cu phap: python3 scripts/gh_release_upload.py"""
import os, sys, json, subprocess
from pathlib import Path
import requests

USER, REPO = "tvh25082004", "a2mac1"
env = dict(l.strip().split("=", 1) for l in (Path(__file__).parent / ".env").read_text().splitlines() if "=" in l)
PAT = env.get("GH_PAT", "").strip().strip("'")
if not PAT:
    print("Thieu GH_PAT trong scripts/.env"); sys.exit(1)
H = {"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json"}
api = f"https://api.github.com/repos/{USER}/{REPO}"
aup = f"https://uploads.github.com/repos/{USER}/{REPO}"

# 1. tao repo neu chua co
r = requests.get(api, headers=H, timeout=30)
if r.status_code == 404:
    r = requests.post("https://api.github.com/user/repos", headers=H, timeout=30,
                      json={"name": REPO, "private": False,
                            "description": "A2MAC1 IBP crawler: 621 cars specs + VinFast VF6 CAD STL"})
    print("Tao repo:", r.status_code, r.json().get("html_url", r.text[:200]))
else:
    print("Repo da co:", r.json().get("html_url"))

# 2. push code
env2 = dict(os.environ, GIT_TERMINAL_PROMPT="0")
url = f"https://x-access-token:{PAT}@github.com/{USER}/{REPO}.git"
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True, cwd="/home/z/my-project")
subprocess.run(["git", "remote", "add", "origin", url], cwd="/home/z/my-project", check=True)
r = subprocess.run(["git", "push", "-u", "origin", "main"], cwd="/home/z/my-project", env=env2, capture_output=True, text=True)
print("push main:", r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")

# 3. tao release
rel = None
r = requests.get(f"{api}/releases", headers=H, timeout=30)
for x in r.json():
    if x.get("tag_name") == "cad-v1":
        rel = x; break
if not rel:
    r = requests.post(f"{api}/releases", headers=H, timeout=30, json={
        "tag_name": "cad-v1", "target_commitish": "main",
        "name": "DATA CAD - VinFast VF6 Plus 2024 (STL) - 1670/1670 file",
        "body": "Bo file STL 3D tung linh kien VinFast VF6 Plus 2024 (nguon A2MAC1 IBP, bo 3D AutoReverse): DU 1670/1670 file.\n"
                "Kem 69 file dau cua VinFast VF8 Plus 2023 (dang cap nhat).\n\n"
                "Cach dung: tai ca 3 file CAD-bundle-XX.zip, giai nen het vao cung thu muc."
                " Moi STL la 1 linh kien rieng; manifest chi tiet nam trong data/cad_skip_list.json tren repo."})
    rel = r.json(); print("Tao release:", rel.get("id"), rel.get("html_url"))
rid = rel["id"]

# 4. upload bundles (truyen so luong bundle toi da cho 1 lan chay: python3 gh_release_upload.py 1)
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0
bundles = sorted(Path("/home/z/my-project/download/bundles").glob("CAD-bundle-*.zip"))
have = {a["name"] for a in requests.get(f"{api}/releases/{rid}/assets", headers=H, timeout=30).json()}
done_n = 0
for b in bundles:
    if b.name in have:
        print(f"  {b.name} da upload truoc -> bo qua"); continue
    if LIMIT and done_n >= LIMIT:
        print(f"  (dung theo LIMIT={LIMIT}, chay lai de upload tiep)"); break
    print(f"  upload {b.name} ({b.stat().st_size/1e9:.2f}GB)...", flush=True)
    with open(b, "rb") as f:
        r = requests.post(f"{aup}/releases/{rid}/assets", params={"name": b.name}, headers={
            "Authorization": f"token {PAT}", "Content-Type": "application/zip"},
            data=f, timeout=3600)
    print("   ->", r.status_code, r.json().get("browser_download_url", r.text[:200]))
    done_n += 1
print("\nLINK TAI: https://github.com/" + USER + "/" + REPO + "/releases/tag/cad-v1")
