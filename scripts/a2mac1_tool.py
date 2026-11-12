#!/usr/bin/env python3
"""
A2MAC1 IBP local query tool.
Install: pip install requests python-dotenv
Run: python a2mac1_tool.py check

IMPORTANT: endpoint paths taken from the opencli-plugin-a2mac1 plugin README.
The JSON bodies of search / node data / BOM are NOT yet confirmed. The functions below
are marked [UNVERIFIED]. Compare with DevTools > Network and fix,
or use the `raw` command to try a body directly.
"""
import argparse, base64, csv, json, os, re, sys, time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("A2MAC1_BASE", "https://ibp.a2mac1.com").rstrip("/")
RAW_TOKEN = os.getenv("A2MAC1_TOKEN", "").strip()
_TOK_MATCH = re.search(r"access_token=([^;\s]+)", RAW_TOKEN)
TOKEN = _TOK_MATCH.group(1) if _TOK_MATCH else RAW_TOKEN
COOKIE = RAW_TOKEN if (";" in RAW_TOKEN and "=" in RAW_TOKEN) else f"access_token={TOKEN}"
DELAY = float(os.getenv("A2MAC1_DELAY", "1.5"))
OUT = Path("out"); OUT.mkdir(exist_ok=True)


# ---------- Auth ----------
def jwt_payload(tok):
    p = tok.split(".")[1]
    p += "=" * (-len(p) % 4)
    return json.loads(base64.urlsafe_b64decode(p))

def seconds_left(tok):
    return jwt_payload(tok)["exp"] - time.time()

def make_session():
    if not TOKEN:
        sys.exit("Missing A2MAC1_TOKEN in .env")
    try:
        left = seconds_left(TOKEN)
    except Exception:
        sys.exit("Token is not a valid JWT")
    if left < 30:
        sys.exit(f"Token expired ({-left:.0f}s ago). Get a new token from the browser.")
    s = requests.Session()
    s.headers.update({
        "Cookie": COOKIE,       # IBP uses the access_token cookie
        "Authorization": f"Bearer {TOKEN}",       # added for safety; remove if the server rejects it
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    print(f"[auth] token has {left/60:.1f} minutes left", file=sys.stderr)
    return s

S = None
def session():
    global S
    if S is None:
        S = make_session()
    return S


# ---------- HTTP with retry ----------
def call(method, path, body=None, retries=4):
    url = BASE + path
    for i in range(retries):
        r = session().request(method, url, json=body, allow_redirects=False, timeout=120)
        if r.status_code == 429:
            wait = 5 * (i + 1)
            print(f"[429] waiting {wait}s", file=sys.stderr)
            time.sleep(wait); continue
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location", "")
            if "login.a2mac1.com" in loc:
                sys.exit("Session expired (redirect to login). Get a new token.")
            sys.exit(f"Unexpected redirect to {loc}")
        if r.status_code in (401, 403):
            sys.exit(f"{r.status_code}: token rejected or expired")
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json() if r.content else None
    sys.exit("Out of retries")


# ---------- Endpoints (paths per the plugin README) ----------
def settings():
    return call("GET", "/settings")

def search(text):
    # [UNVERIFIED] body; try shapes: {"query": text} / {"text": text} / {"searchText": text}
    body = json.loads(os.getenv("A2MAC1_SEARCH_BODY", "null")) or {"query": text}
    return call("POST", "/api/quick-search?api-version=2.0", body)

def list_hierarchies():
    # [UNVERIFIED] body; the plugin only says "authoritative domain list"
    body = json.loads(os.getenv("A2MAC1_HIER_BODY", "{}"))
    return call("POST", "/api/filters/hierarchies/get-part-hierarchies?api-version=2.0", body)

def tree(hierarchy_id, parent_node_id=None):
    # README: optional body {"parentNodeId": ...}
    body = {"parentNodeId": parent_node_id} if parent_node_id else {}
    return call("POST", f"/api/hierarchies/{hierarchy_id}", body)

def node_data(pid, hid, nid):
    # [UNVERIFIED] body; may be {} or include column/language params
    body = json.loads(os.getenv("A2MAC1_NODE_BODY", "{}"))
    return call("POST", f"/api/products/{pid}/hierarchies/{hid}/nodes/{nid}/data", body)

def bom(product_ids):
    # [UNVERIFIED] body; the plugin says it returns the whole table in 1 response (~8MB/vehicle)
    body = json.loads(os.getenv("A2MAC1_BOM_BODY", "null")) or {"productIds": product_ids}
    return call("POST", "/api/products/bom/BillOfMaterial_Columns", body)


# ---------- Save files ----------
def save_json(name, data):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {p}", file=sys.stderr)

def flatten_rows(data):
    """Try to turn a list-of-dict into CSV; skip if not possible."""
    if isinstance(data, dict):
        for k in ("items", "rows", "results", "data", "nodes", "products"):
            if isinstance(data.get(k), list):
                data = data[k]; break
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    return None

def save_csv(name, data):
    rows = flatten_rows(data)
    if not rows:
        print("[csv] non-flat structure, saving JSON only", file=sys.stderr); return
    cols = sorted({k for r in rows for k in r})
    p = OUT / f"{name}.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                        for k, v in r.items()})
    print(f"[saved] {p}", file=sys.stderr)

def emit(name, data):
    save_json(name, data); save_csv(name, data)


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="check token + /settings")
    sub.add_parser("hierarchies", help="list data domains")
    p = sub.add_parser("search");  p.add_argument("text")
    p = sub.add_parser("tree");    p.add_argument("hierarchy_id"); p.add_argument("--parent")
    p = sub.add_parser("props");   p.add_argument("product_id"); p.add_argument("hierarchy_id"); p.add_argument("node_id")
    p = sub.add_parser("bom");     p.add_argument("product_ids", help="comma-separated")
    p = sub.add_parser("raw", help="send an arbitrary request to probe a body")
    p.add_argument("method"); p.add_argument("path"); p.add_argument("--body", default=None)
    p = sub.add_parser("batch", help="fetch props for multiple vehicles from a txt file (one productId per line)")
    p.add_argument("file"); p.add_argument("hierarchy_id"); p.add_argument("node_id")
    a = ap.parse_args()

    if a.cmd == "check":
        pl = jwt_payload(TOKEN)
        print("email:", pl.get("email"), "|", round(seconds_left(TOKEN)/60, 1), "minutes left")
        emit("settings", settings())
    elif a.cmd == "hierarchies": emit("hierarchies", list_hierarchies())
    elif a.cmd == "search":      emit(f"search_{a.text.replace(' ', '_')}", search(a.text))
    elif a.cmd == "tree":        emit(f"tree_{a.hierarchy_id}", tree(a.hierarchy_id, a.parent))
    elif a.cmd == "props":       emit(f"props_{a.product_id}_{a.node_id}", node_data(a.product_id, a.hierarchy_id, a.node_id))
    elif a.cmd == "bom":
        ids = [x.strip() for x in a.product_ids.split(",") if x.strip()]
        emit("bom_" + "_".join(ids), bom(ids))
    elif a.cmd == "raw":
        body = json.loads(a.body) if a.body else None
        emit("raw", call(a.method.upper(), a.path, body))
    elif a.cmd == "batch":
        ids = [l.strip() for l in Path(a.file).read_text().splitlines() if l.strip()]
        for pid in ids:
            try:
                emit(f"props_{pid}_{a.node_id}", node_data(pid, a.hierarchy_id, a.node_id))
            except Exception as e:
                print(f"[error] {pid}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
