#!/usr/bin/env python3
"""Chẩn đoán + tải lại ảnh lỗi."""
import json, re, time
from pathlib import Path
import requests

DATA = Path("/home/z/my-project/data")
OUT = Path("/home/z/my-project/download/A2MAC1_anh_xe")
products = json.loads((DATA / "products_all.json").read_text())

def safe_name(s):
    s = re.sub(r'[\\/:*?"<>|]+', "-", str(s)).strip()
    return s[:110] if s else "unknown"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
missing_url, http_fail, recovered = [], [], 0
for p in products:
    pid = p.get("productId")
    pf = p.get("pictureFile") or {}
    det = pf.get("details") or {}
    urls = det.get("publicUrls") or {}
    url = (urls.get("small") or urls.get("medium") or urls.get("large") or "").replace("\\", "/")
    name = f"{safe_name(p.get('resourceName', pid))} [{pid}].jpg"
    dest = OUT / name
    if dest.exists() and dest.stat().st_size > 1000:
        continue
    if not url:
        missing_url.append((pid, name, list(urls.keys()), bool(det.get("versionPaths"))))
        continue
    r = S.get(url, timeout=30)
    if r.status_code == 200 and len(r.content) > 500:
        dest.write_bytes(r.content); recovered += 1
    else:
        http_fail.append((pid, name[:50], r.status_code, len(r.content), url[:70]))
print("recovered:", recovered)
print("không có URL:", len(missing_url))
for x in missing_url[:5]:
    print("  ", x)
print("HTTP fail:", len(http_fail))
for x in http_fail[:8]:
    print("  ", x)
