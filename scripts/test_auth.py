#!/usr/bin/env python3
"""Quick token check against the server (skipping the local exp guard in a2mac1_tool.py).
Do NOT print the token to the screen."""
import os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
tok = m.group(1) if m else raw
if not tok:
    sys.exit("Token not found in .env")

s = requests.Session()
s.headers.update({
    "Cookie": f"access_token={tok}",
    "Authorization": f"Bearer {tok}",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
})

# try both lightweight endpoints for diagnosis
for path in ["/settings", "/api/products?api-version=2.0", "/api/hierarchies/A000005AE6M1EU01?api-version=2.0"]:
    try:
        r = s.get("https://ibp.a2mac1.com" + path, allow_redirects=False, timeout=30)
        body = (r.text or "")[:200].replace("\n", " ")
        print(f"{path} -> HTTP {r.status_code} | Location={r.headers.get('Location','-')} | body[:200]={body}")
    except Exception as e:
        print(f"{path} -> ERROR {e}")
