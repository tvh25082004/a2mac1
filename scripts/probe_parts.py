#!/usr/bin/env python3
"""Thử nhanh trong skew window cuối: parts theo product, has-3Dfiles lại."""
import os, re, json, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOK}", "Authorization": f"Bearer {TOK}",
    "Content-Type": "application/json", "Accept": "application/json",
    "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
HID = "A000005AE6M1EU01"

def t(tag, method, path, body=None, params=None):
    for i in range(4):
        r = S.request(method, BASE + path, json=body, params=params, timeout=60)
        if r.status_code == 200:
            print(f"[{tag}] 200 | {len(r.content)/1024:.0f} KB", flush=True)
            return r
        if r.status_code in (401, 403):
            print(f"[{tag}] {r.status_code} retry {i+1}", flush=True); time.sleep(3); continue
        print(f"[{tag}] {r.status_code} | {r.text[:150]}", flush=True)
        return r
    return r

# 1) parts tổng (trang 1)
r = t("parts all p1", "POST", f"/api/hierarchies/{HID}/parts",
      {"filters": [], "sorter": None, "page": {"number": 1, "size": 50}},
      {"allowDynamicColumns": "true", "hideMappedProperties": "true", "hideMappedProductTypesProperties": "false"})
if r.status_code == 200 and r.content:
    (DATA / "hier_parts_sample.json").write_text(r.text)
    d = r.json()
    if isinstance(d, dict):
        print("   keys:", list(d.keys())[:12])
        for k, v in d.items():
            if isinstance(v, list) and v:
                print(f"   [{k}] len={len(v)} sample:", json.dumps(v[0], ensure_ascii=False)[:400])

# 2) parts theo product-id filter
r = t("parts by product", "POST", f"/api/hierarchies/{HID}/parts",
      {"filters": ["product-id eq A0000004F0UTEU02"], "sorter": None, "page": {"number": 1, "size": 50}},
      {"allowDynamicColumns": "true", "hideMappedProperties": "true", "hideMappedProductTypesProperties": "false"})
if r.status_code == 200 and r.content:
    (DATA / "parts_by_product_sample.json").write_text(r.text)
    d = r.json()
    if isinstance(d, dict):
        print("   keys:", list(d.keys())[:12])
        for k, v in d.items():
            if isinstance(v, list) and v:
                print(f"   [{k}] len={len(v)} sample:", json.dumps(v[0], ensure_ascii=False)[:400])
    elif isinstance(d, list):
        print("   list len:", len(d), json.dumps(d[:1], ensure_ascii=False)[:400])

# 3) has-3Dfiles lại (chunk nhỏ)
r = t("has-3Dfiles 2", "POST", "/api/access/users/has-3Dfiles", ["A0000004F0UTEU02"])
if r.status_code == 200 and r.content:
    print("   ", r.text[:300])
