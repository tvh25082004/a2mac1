#!/usr/bin/env python3
"""Where is the 403: is the whole account blocked or just data? Try lightweight endpoints + full cookies."""
import os, re, json
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
BASE = "https://ibp.a2mac1.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
S = requests.Session()

def t(tag, method, path, body=None, headers=None):
    H = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA,
         "Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
         "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"}
    if headers:
        H.update(headers)
    r = S.request(method, BASE + path, json=body, headers=H, timeout=60)
    body_snip = r.text[:220].replace("\n", " ")
    print(f"[{tag}] {method} {path} -> {r.status_code} | {body_snip!r}")

# full cookie string (all cookies like the browser)
t("full-cookie", "POST", "/api/visual/products", {"filters": [], "sorter": None, "page": {"number": 1, "size": 2}},
  {"Cookie": raw})
t("account", "GET", "/api/account")
t("credits-user", "GET", "/api/credits/user")
t("has-data", "GET", "/api/access/users/has-data")
t("has-datatable", "GET", "/api/access/users/has-datatable")
t("compare-items", "GET", "/api/compare/items")
t("version", "GET", "/api/application/version")
