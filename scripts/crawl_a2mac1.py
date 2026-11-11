#!/usr/bin/env python3
"""
Crawler A2MAC1 IBP — lấy full danh sách xe + thông số kỹ thuật.
Có resume: chạy dở với token cũ, gửi token mới là chạy tiếp từ chỗ dừng.
KHÔNG in token ra màn hình.

Chạy:
  python crawl_a2mac1.py products            # bước 1: full danh sách xe
  python crawl_a2mac1.py compare             # bước 2: thông số kỹ thuật (batch 25 xe)
  python crawl_a2mac1.py all                 # cả 2 bước
  python crawl_a2mac1.py products --page-size 500
"""
import os, re, json, time, sys, base64, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE = "https://ibp.a2mac1.com"
DATA = Path("/home/z/my-project/data")
DATA.mkdir(exist_ok=True)
F_PRODUCTS = DATA / "products_all.json"
F_STATE = DATA / "crawl_state.json"
F_COMPARE_DIR = DATA / "compare_batches"

load_dotenv(Path(__file__).resolve().parent / ".env")
raw = os.getenv("A2MAC1_TOKEN", "")
m = re.search(r"access_token=([^;\s]+)", raw)
TOKEN = m.group(1) if m else raw

S = requests.Session()
S.headers.update({
    "Cookie": f"access_token={TOKEN}",
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})
DELAY = float(os.getenv("A2MAC1_DELAY", "1.0"))


def jwt_exp(tok):
    p = tok.split(".")[1]
    p += "=" * (-len(p) % 4)
    return json.loads(base64.urlsafe_b64decode(p)).get("exp", 0)


def load_state():
    if F_STATE.exists():
        return json.loads(F_STATE.read_text())
    return {"done_item_ids": [], "batches": []}


def save_state(st):
    F_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))


def call(method, path, body=None, params=None, retries=4):
    for i in range(retries):
        r = S.request(method, BASE + path, json=body, params=params,
                      allow_redirects=False, timeout=180)
        if r.status_code == 429:
            wait = 5 * (i + 1)
            print(f"  [429] chờ {wait}s...", flush=True)
            time.sleep(wait)
            continue
        if r.status_code in (401, 403):
            sys.exit("TOKEN_DEAD: server từ chối token (401/403). Cần token mới từ trình duyệt.")
        if r.status_code in (301, 302, 303, 307, 308):
            sys.exit(f"REDIRECT: {r.headers.get('Location')} — phiên hết hạn?")
        if r.status_code >= 500:
            print(f"  [{r.status_code}] retry {i+1}...", flush=True)
            time.sleep(3)
            continue
        if r.status_code >= 400:
            sys.exit(f"HTTP {r.status_code} tại {path}: {r.text[:300]}")
        time.sleep(DELAY)
        return r.json() if r.content and (r.headers.get("content-type", "").lower().find("json") >= 0 or (r.text or "")[:1] in "{[") else (r.text if r.content else None)
    sys.exit("Quá số lần retry")


def step_products(page_size, max_pages):
    """Phân trang api/visual/products để lấy toàn bộ products."""
    all_items = []
    for page in range(1, max_pages + 1):
        body = {"filters": [], "sorter": None, "page": {"number": page, "size": page_size}}
        data = call("POST", "/api/visual/products", body)
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for k in ("items", "products", "results", "data", "rows"):
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
            if not items and isinstance(data.get("products"), dict):
                items = data["products"].get("items", [])
        n = len(items)
        print(f"  page {page}: {n} sản phẩm", flush=True)
        if n == 0:
            break
        all_items.extend(items)
        if n < page_size:
            break
        F_PRODUCTS.write_text(json.dumps(all_items, ensure_ascii=False, indent=1))
    F_PRODUCTS.write_text(json.dumps(all_items, ensure_ascii=False, indent=1))
    print(f"==> TỔNG {len(all_items)} sản phẩm -> {F_PRODUCTS}", flush=True)
    # in thử structure của 1 item
    if all_items:
        print("  [sample keys]:", ", ".join(list(all_items[0].keys())[:25]), flush=True)
    return all_items


def pick_ids(products):
    ids = []
    for p in products:
        pid = p.get("id") or p.get("productId") or p.get("itemId")
        if pid:
            ids.append(pid)
    return ids


def step_compare(batch_size=25):
    st = load_state()
    if not F_PRODUCTS.exists():
        sys.exit("Chưa có products_all.json — chạy `products` trước.")
    products = json.loads(F_PRODUCTS.read_text())
    ids = pick_ids(products)
    print(f"Số productId: {len(ids)}", flush=True)
    todo = [i for i in ids if i not in st["done_item_ids"]]
    print(f"Còn phải lấy: {len(todo)}", flush=True)
    F_COMPARE_DIR.mkdir(exist_ok=True)
    batch_idx = len(st["batches"])
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        batch_idx += 1
        body = {"itemIds": chunk}
        try:
            data = call("POST", "/api/products/compare/data/by-items", body,
                        params={"hideMappedProperties": "true", "hideMappedProductTypesProperties": "false"})
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [lỗi batch {batch_idx}]: {e} — thử lại 1 lần sau 5s", flush=True)
            time.sleep(5)
            data = call("POST", "/api/products/compare/data/by-items", body,
                        params={"hideMappedProperties": "true", "hideMappedProductTypesProperties": "false"})
        out = F_COMPARE_DIR / f"batch_{batch_idx:04d}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        st["done_item_ids"].extend(chunk)
        st["batches"].append(str(out.name))
        save_state(st)
        print(f"  batch {batch_idx}: {len(chunk)} xe -> {out.name}", flush=True)
    print(f"==> HOÀN TẤT so sánh thông số. Tổng batch: {len(st['batches'])}", flush=True)


def step_dump(batch_size=50):
    """Dump FULL dữ liệu product qua api/input/products/data (batch productIds)."""
    F_DUMP_DIR = DATA / "dump_batches"
    F_DUMP_STATE = DATA / "dump_state.json"
    st = json.loads(F_DUMP_STATE.read_text()) if F_DUMP_STATE.exists() else {"done": []}
    if not F_PRODUCTS.exists():
        sys.exit("Chưa có products_all.json — chạy `products` trước.")
    products = json.loads(F_PRODUCTS.read_text())
    ids = [p.get("productId") for p in products if p.get("productId")]
    todo = [i for i in ids if i not in st["done"]]
    print(f"Số productId: {len(ids)} | còn: {len(todo)}", flush=True)
    F_DUMP_DIR.mkdir(exist_ok=True)
    batch_idx = len(st.get("batches", []))
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        batch_idx += 1
        body = {"productIds": chunk, "filters": [], "helpersListId": None}
        data = call("POST", "/api/input/products/data?api-version=2.0", body)
        out = F_DUMP_DIR / f"dump_{batch_idx:04d}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        st.setdefault("done", []).extend(chunk)
        st.setdefault("batches", []).append(out.name)
        F_DUMP_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))
        print(f"  dump batch {batch_idx}: {len(chunk)} xe -> {out.name}", flush=True)
    print("==> HOÀN TẤT dump.", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["products", "compare", "dump", "all"])
    ap.add_argument("--page-size", type=int, default=500)
    ap.add_argument("--max-pages", type=int, default=100)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--force", action="store_true", help="chạy dù token cục bộ báo hết hạn (dựa vào clock-skew server)")
    a = ap.parse_args()

    left = jwt_exp(TOKEN) - time.time()
    if left < 0 and not a.force:
        sys.exit(f"TOKEN_DEAD: token hết hạn {-left/60:.1f} phút trước. Lấy token mới (F12 -> Application -> Cookies -> access_token).")
    print(f"[auth] token {'CÒN ' + str(round(left/60,1)) + ' phút' if left > 0 else 'HẾT HẠN CỤC BỘ (--force: vẫn thử, server có thể chấp nhận trong skew 5 phút)'}", flush=True)

    if a.step in ("products", "all"):
        step_products(a.page_size, a.max_pages)
    if a.step in ("compare", "all"):
        step_compare()
    if a.step in ("dump", "all"):
        step_dump(a.batch_size)


if __name__ == "__main__":
    main()
