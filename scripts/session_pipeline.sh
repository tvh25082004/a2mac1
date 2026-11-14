#!/bin/bash
# A2MAC1 session pipeline: 1 token = 1 automatic full run.
# Usage: đặt JWT vào /tmp/a2mac1_tok rồi chạy: bash scripts/session_pipeline.sh
# Flow: download (ban-safe, resume) -> merge captures cũ từ Release về -> render chunk mới
#       -> package (cộng dồn) -> upload/replace -> tracker -> XÓA local sau khi đã lên GitHub
set -e
cd /home/z/my-project
mkdir -p download

if [ ! -s /tmp/a2mac1_tok ]; then
  echo "LOI: /tmp/a2mac1_tok rong hoac khong ton tai — can JWT (bat dau bang eyJ...)"
  exit 2
fi
REL_BASE="https://github.com/tvh25082004/a2mac1/releases/download/cad-captures-v1"

echo "=== [1/7] DOWNLOAD (pace an toàn ~1.3 file/s, cap 600 file/xe/phiên, tự resume) ==="
python3 scripts/cad_bulk4.py | tee /tmp/cad_bulk4.log || true

echo "=== [2/7] MERGE captures cu tu Release ve cap_out (cong don, chong mat do recycle) ==="
shopt -s nullglob
# lay danh sach xe co capture trong manifest, dam bao zip co local (hoac tai tu Release ve)
for car in $(python3 -c "
import json
mf = json.load(open('data/cad_skip_list.json')).get('manifest', {})
for name in sorted(mf): print(name.replace(' ', '__SP__'))"); do
  name="${car//__SP__/ }"
  fname="CAPTURES_${name// /_}.zip"
  if [ ! -f "download/$fname" ]; then
    echo "tai ve de merge: $fname"
    curl -sL --max-time 120 -o "download/$fname" "$REL_BASE/$fname" || true
  fi
  if [ -f "download/$fname" ]; then
    echo "merge tu $fname -> $name"
    mkdir -p "/tmp/cap_out_merge/$name" "/tmp/cap_out/$name"
    unzip -o -q "download/$fname" -d "/tmp/cap_out_merge/$name" 2>/dev/null || true
    # zip co the co prefix "<Ten xe>/" trong members -> find lam phang moi cap
    find "/tmp/cap_out_merge/$name" -name '*.png' -exec cp -n {} "/tmp/cap_out/$name/" \;
  fi
done
rm -rf /tmp/cap_out_merge
echo "merge xong: $(find /tmp/cap_out -name '*.png' 2>/dev/null | wc -l) PNG tong cong"

echo "=== [3/7] RENDER cac chunk moi (giu chunk lai den khi package xong) ==="
chunks=(download/DATA-CAD_*.zip)
if [ ${#chunks[@]} -gt 0 ]; then
  echo "render ${#chunks[@]} chunk..."
  KEEP_BUNDLES=1 python3 scripts/render_all_captures.py "${chunks[@]}" | tee /tmp/render.log
else
  echo "khong co chunk moi"
fi

echo "=== [4/7] PACKAGE captures per car (CONG DON toan bo PNG trong cap_out) ==="
python3 scripts/package_captures.py

echo "=== [5/7] UPLOAD/REFRESH Release (replace-if-changed) ==="
GH_PAT=$(git remote get-url origin | grep -oP '(ghp|gho|github_pat)_[A-Za-z0-9_]+' | head -1)
if [ -n "$GH_PAT" ]; then
  GH_PAT="$GH_PAT" python3 scripts/upload_captures_release.py
else
  echo "CANH BAO: khong tim thay PAT trong remote — upload tay sau"
fi

echo "=== [6/7] TRACKER refresh ==="
python3 scripts/build_tracker_xlsx.py

echo "=== [7/7] CLEANUP — moi thu da tren GitHub, xoa local cho nhe ==="
rm -f download/DATA-CAD_*.zip download/CAPTURES_*.zip /tmp/a2mac1_tok
echo "=== SESSION PIPELINE DONE ==="
