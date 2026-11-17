#!/bin/bash
# run_au_pipeline.sh — chạy TOÀN BỘ pipeline A&U trong 1 lệnh ngay khi có token mới.
# Cách dùng:
#   bash scripts/run_au_pipeline.sh "<cookie string chứa access_token=eyJ...>"
#   bash scripts/run_au_pipeline.sh --tok-file /path/to/token.txt
# JWT sống ~25-27 phút: mọi bước chạy liền, harvester tự dừng an toàn trước khi token chết,
# sau đó build Excel, đóng gói ZIP media và upload GitHub Release.
set -euo pipefail
cd /home/z/my-project

ARG="${1:-}"
if [ -z "$ARG" ]; then
  echo "Dùng: bash scripts/run_au_pipeline.sh '<cookie access_token=...>'"
  echo "  hoặc: bash scripts/run_au_pipeline.sh --tok-file /path/to/token.txt"
  exit 1
fi
if [ "$ARG" = "--tok-file" ]; then
  TOK=$(cat "${2:?thiếu đường dẫn file token}")
else
  TOK="$ARG"
fi
if [[ "$TOK" == *access_token=* ]]; then
  TOK=$(printf '%s' "$TOK" | grep -oE 'access_token=[^;[:space:]]+' | head -1 | cut -d= -f2-)
fi
[ -n "$TOK" ] || { echo "KHÔNG tìm thấy access_token trong đầu vào"; exit 1; }

umask 077
printf '%s' "$TOK" > /tmp/a2mac1_tok

echo "[1/4] Token đã ghi (/tmp/a2mac1_tok, $(printf '%s' "$TOK" | wc -c) bytes) — harvest 621 xe (resume, tự dừng an toàn)..."
python3 scripts/harvest_vop_all.py

echo "[2/4] Xây Excel A&U..."
python3 scripts/build_excel_au.py

echo "[3/4] Đóng gói ZIP media..."
if [ -d download/VOP_media ] && [ -n "$(ls -A download/VOP_media 2>/dev/null)" ]; then
  ZIP="download/VOP_media_$(date +%Y%m%d_%H%M).zip"
  rm -f "$ZIP"
  (cd download && zip -qr "$(basename "$ZIP")" VOP_media)
  echo "  Đã tạo $ZIP ($(du -h "$ZIP" | cut -f1))"
else
  echo "  (chưa có file media nào — bỏ qua ZIP)"
fi

echo "[4/4] Upload GitHub Release..."
python3 scripts/gh_release_au.py

echo "XONG. Kiểm tra: https://github.com/tvh25082004/a2mac1/releases/tag/au-vop-v1"
