#!/usr/bin/env python3
"""Quick diag: is the token valid? Who returns 403?"""
import os, re, json, time, base64, datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOK = m.group(1) if m else raw
p = TOK.split(".")[1]; p += "=" * (-len(p) % 4)
pl = json.loads(base64.urlsafe_b64decode(p))
vn = datetime.timezone(datetime.timedelta(hours=7))
now = time.time()
print("jti :", pl["jti"])
print("exp :", datetime.datetime.fromtimestamp(pl["exp"], vn), "| iat:", datetime.datetime.fromtimestamp(pl["iat"], vn))
print("now :", datetime.datetime.fromtimestamp(now, vn))
print("remaining :", round((pl["exp"] - now) / 60, 1), "minutes | token len:", len(TOK))

BASE = "https://ibp.a2mac1.com"
S = requests.Session()

def try_hdrs(tag, headers):
    r = S.post(BASE + "/api/visual/products", json={"filters": [], "sorter": None, "page": {"number": 1, "size": 2}},
               headers=headers, timeout=60)
    srv = {k: v for k, v in r.headers.items() if k.lower() in ("server", "cf-ray", "x-azure-ref", "via", "x-cache", "www-authenticate", "content-type")}
    print(f"[{tag}] HTTP {r.status_code} | {srv} | body: {r.text[:150]!r}")

H = {"Content-Type": "application/json", "Accept": "application/json",
     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
try_hdrs("no auth", H)
try_hdrs("Bearer only", {**H, "Authorization": f"Bearer {TOK}"})
try_hdrs("Cookie only", {**H, "Cookie": f"access_token={TOK}"})
try_hdrs("Bearer+Cookie+Origin", {**H, "Authorization": f"Bearer {TOK}", "Cookie": f"access_token={TOK}",
                                   "Origin": "https://ibp.a2mac1.com", "Referer": "https://ibp.a2mac1.com/"})
