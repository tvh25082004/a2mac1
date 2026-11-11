#!/usr/bin/env python3
"""
A2MAC1 IBP local query tool.
Cài: pip install requests python-dotenv
Chạy: python a2mac1_tool.py check

QUAN TRỌNG: đường dẫn endpoint lấy từ README plugin opencli-plugin-a2mac1.
Body JSON của search / node data / BOM CHƯA được xác nhận. Các hàm dưới
đánh dấu [UNVERIFIED]. Hãy đối chiếu với DevTools > Network rồi sửa,
hoặc dùng lệnh `raw` để thử body trực tiếp.
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
        sys.exit("Thiếu A2MAC1_TOKEN trong .env")
    try:
        left = seconds_left(TOKEN)
    except Exception:
        sys.exit("Token không phải JWT hợp lệ")
    if left < 30:
        sys.exit(f"Token đã hết hạn ({-left:.0f}s trước). Lấy token mới từ trình duyệt.")
    s = requests.Session()
    s.headers.update({
        "Cookie": COOKIE,       # IBP dùng cookie access_token
        "Authorization": f"Bearer {TOKEN}",       # thêm cho chắc; bỏ nếu server từ chối
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    })
    print(f"[auth] token còn {left/60:.1f} phút", file=sys.stderr)
    return s

S = None
def session():
    global S
    if S is None:
        S = make_session()
    return S


# ---------- HTTP có retry ----------
def call(method, path, body=None, retries=4):
    url = BASE + path
    for i in range(retries):
        r = session().request(method, url, json=body, allow_redirects=False, timeout=120)
        if r.status_code == 429:
            wait = 5 * (i + 1)
            print(f"[429] chờ {wait}s", file=sys.stderr)
            time.sleep(wait); continue
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location", "")
            if "login.a2mac1.com" in loc:
                sys.exit("Phiên hết hạn (redirect về login). Lấy token mới.")
            sys.exit(f"Redirect bất thường tới {loc}")
        if r.status_code in (401, 403):
            sys.exit(f"{r.status_code}: token bị từ chối hoặc hết hạn")
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json() if r.content else None
    sys.exit("Quá số lần retry")


# ---------- Các endpoint (đường dẫn theo README plugin) ----------
def settings():
    return call("GET", "/settings")

def search(text):
    # [UNVERIFIED] body; thử các dạng: {"query": text} / {"text": text} / {"searchText": text}
    body = json.loads(os.getenv("A2MAC1_SEARCH_BODY", "null")) or {"query": text}
    return call("POST", "/api/quick-search?api-version=2.0", body)

def list_hierarchies():
    # [UNVERIFIED] body; plugin chỉ nói là "authoritative domain list"
    body = json.loads(os.getenv("A2MAC1_HIER_BODY", "{}"))
    return call("POST", "/api/filters/hierarchies/get-part-hierarchies?api-version=2.0", body)

def tree(hierarchy_id, parent_node_id=None):
    # README: body tùy chọn {"parentNodeId": ...}
    body = {"parentNodeId": parent_node_id} if parent_node_id else {}
    return call("POST", f"/api/hierarchies/{hierarchy_id}", body)

def node_data(pid, hid, nid):
    # [UNVERIFIED] body; có thể là {} hoặc có tham số cột/ngôn ngữ
    body = json.loads(os.getenv("A2MAC1_NODE_BODY", "{}"))
    return call("POST", f"/api/products/{pid}/hierarchies/{hid}/nodes/{nid}/data", body)

def bom(product_ids):
    # [UNVERIFIED] body; plugin nói trả cả bảng trong 1 response (~8MB/xe)
    body = json.loads(os.getenv("A2MAC1_BOM_BODY", "null")) or {"productIds": product_ids}
    return call("POST", "/api/products/bom/BillOfMaterial_Columns", body)


# ---------- Lưu file ----------
def save_json(name, data):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[saved] {p}", file=sys.stderr)

def flatten_rows(data):
    """Cố gắng biến list-of-dict thành CSV; nếu không được thì bỏ qua."""
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
        print("[csv] cấu trúc không phẳng, chỉ lưu JSON", file=sys.stderr); return
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
    sub.add_parser("check", help="kiểm tra token + /settings")
    sub.add_parser("hierarchies", help="liệt kê domain dữ liệu")
    p = sub.add_parser("search");  p.add_argument("text")
    p = sub.add_parser("tree");    p.add_argument("hierarchy_id"); p.add_argument("--parent")
    p = sub.add_parser("props");   p.add_argument("product_id"); p.add_argument("hierarchy_id"); p.add_argument("node_id")
    p = sub.add_parser("bom");     p.add_argument("product_ids", help="cách nhau bằng dấu phẩy")
    p = sub.add_parser("raw", help="gửi request tùy ý để dò body")
    p.add_argument("method"); p.add_argument("path"); p.add_argument("--body", default=None)
    p = sub.add_parser("batch", help="lấy props nhiều xe từ file txt (mỗi dòng 1 productId)")
    p.add_argument("file"); p.add_argument("hierarchy_id"); p.add_argument("node_id")
    a = ap.parse_args()

    if a.cmd == "check":
        pl = jwt_payload(TOKEN)
        print("email:", pl.get("email"), "| còn", round(seconds_left(TOKEN)/60, 1), "phút")
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
                print(f"[lỗi] {pid}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
