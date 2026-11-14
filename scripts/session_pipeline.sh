#!/bin/bash
# A2MAC1 session pipeline: 1 token = 1 automatic full run.
# Usage: đặt JWT vào /tmp/a2mac1_tok rồi chạy: bash scripts/session_pipeline.sh
# Flow: download (ban-safe pace, resume) -> render new chunks -> package -> upload -> tracker -> cleanup
set -e
cd /home/z/my-project

if [ ! -s /tmp/a2mac1_tok ]; then
  echo "LOI: /tmp/a2mac1_tok rong hoac khong ton tai — can JWT (bat dau bang eyJ...)"
  exit 2
fi
echo "=== [1/6] DOWNLOAD (pace an toàn ~1.3 file/s, tự resume theo manifest) ==="
python3 scripts/cad_bulk4.py | tee /tmp/cad_bulk4.log || true

echo "=== [2/6] RENDER cac chunk moi ==="
shopt -s nullglob
chunks=(download/DATA-CAD_*.zip)
if [ ${#chunks[@]} -gt 0 ]; then
  echo "render ${#chunks[@]} chunk..."
  python3 scripts/render_all_captures.py "${chunks[@]}" | tee /tmp/render.log
else
  echo "khong co chunk moi (moi thu da render hoac khong tai duoc gi)"
fi

echo "=== [3/6] PACKAGE captures per car ==="
python3 scripts/package_captures.py

echo "=== [4/6] UPLOAD/REFRESH Release ==="
GH_PAT=$(git remote get-url origin | grep -oP '(ghp|gho|github_pat)_[A-Za-z0-9_]+' | head -1)
if [ -n "$GH_PAT" ]; then
  GH_PAT="$GH_PAT" python3 scripts/upload_captures_release.py
else
  echo "CANH BAO: khong tim thay PAT trong remote — upload tay sau"
fi

echo "=== [5/6] TRACKER refresh ==="
python3 scripts/build_tracker_xlsx.py

echo "=== [6/6] CLEANUP ==="
rm -f /tmp/a2mac1_tok
echo "=== SESSION PIPELINE DONE ==="
