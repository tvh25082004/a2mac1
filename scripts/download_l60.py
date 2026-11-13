"""Download A2MAC1 3D CAD files for one vehicle (default: Onvo L60) -> /tmp/a2mac1_dl/<car>/.
Auth via env A2MAC1_TOKEN (the access_token JWT cookie value). Conservative pacing to
avoid triggering another 403 ban: 3 concurrent downloads, ~0.8s stagger, retry x3.
Usage: A2MAC1_TOKEN=eyJ... python3 download_l60.py [--product ID] [--hierarchy ID] [--name "Car Name"]
Afterwards the STLs can be bundled with scripts/render_all_captures.py unchanged."""
import argparse, os, re, sys, time
import json
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://ibp.a2mac1.com/api"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

L60 = {"product": "A00000666HWJEU01", "hierarchy": "00000005ZT4GEU01",
       "name": "Onvo L60 60kWh 4X4 2024"}

lock_print = __import__('threading').Lock()


def hdr(tok, extra=None):
    h = {"Authorization": f"Bearer {tok}", "Cookie": f"access_token={tok}",
         "User-Agent": UA, "Origin": "https://ibp.a2mac1.com",
         "Referer": "https://ibp.a2mac1.com/", "Accept": "application/json"}
    h.update(extra or {})
    return h


def call(url, tok, method="GET", payload=None, tries=3, timeout=120):
    for t in range(tries):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=hdr(tok))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                try:
                    return r.status, json.loads(body)
                except ValueError:
                    return r.status, body
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return e.code, e.read()[:200]
            time.sleep(2 + 2 * t)
        except Exception:
            time.sleep(2 + 2 * t)
    return 0, b''


def paced_download(url, tok, outpath, size_hint, stagger=0.8):
    time.sleep(stagger)
    for t in range(3):
        try:
            req = urllib.request.Request(url, headers=hdr(tok,
                                         {"Accept": "application/octet-stream"}))
            with urllib.request.urlopen(req, timeout=(15, 300)) as r:
                with open(outpath, 'wb') as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
            return outpath, os.path.getsize(outpath), ''
        except Exception as e:
            if t == 2:
                return outpath, 0, str(e)[:120]
            time.sleep(3 * (t + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--product', default=L60['product'])
    ap.add_argument('--hierarchy', default=L60['hierarchy'])
    ap.add_argument('--name', default=L60['name'])
    ap.add_argument('--out', default=None)
    ap.add_argument('--limit', type=int, default=0, help='0 = all files')
    a = ap.parse_args()
    tok = os.environ.get('A2MAC1_TOKEN', '').strip()
    if not re.fullmatch(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', tok):
        print('LOI: A2MAC1_TOKEN phai la JWT access_token (bat dau bang eyJ...), '
              'khong phai chuoi cookie tracking.')
        sys.exit(2)
    outdir = a.out or f"/tmp/a2mac1_dl/{a.name}"
    os.makedirs(outdir, exist_ok=True)

    # 1) packages (thong tin)
    st, pk = call(f"{BASE}/visual/files/packages?productIds={a.product}&api-version=2.0", tok)
    pkgs = pk if isinstance(pk, list) else pk.get('value', []) if isinstance(pk, dict) else []
    print(f"packages: HTTP {st}, {len(pkgs)} package(s)")

    # 2) get-files -> danh sach file + token download
    st, rec = call(f"{BASE}/visual/files/get-files?api-version=2.0", tok, "POST",
                   {"productIds": [a.product], "hierarchyId": a.hierarchy,
                    "isBookmark": False})
    if st in (401, 403):
        print(f"LOI AUTH/CHAN: HTTP {st} | {rec[:120]}")
        sys.exit(3)
    items = rec if isinstance(rec, list) else rec.get('value', [])
    files = [it for it in items if it.get('token')]
    if a.limit:
        files = files[:a.limit]
    print(f"get-files: HTTP {st}, {len(items)} item(s), {len(files)} co token download")

    # 3) tai song song 3, pacing
    t0 = time.time()
    ok = err = 0
    manifest = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {}
        for i, it in enumerate(files):
            name = re.sub(r'[^\w.\- ]+', '_', it.get('name') or f"file_{i}")
            url = f"{BASE}/files/downloads/files?token={it['token']}&api-version=1.1"
            futs[pool.submit(paced_download, url, tok,
                             os.path.join(outdir, name), it.get('size', 0),
                             0.8 * (i % 3))] = name
        for n, fu in enumerate(as_completed(futs), 1):
            path, size, msg = fu.result()
            if size > 0:
                ok += 1
                manifest.append({"name": os.path.basename(path), "size": size})
            else:
                err += 1
                print(f"  ERR {futs[fu]}: {msg}", flush=True)
            if n % 50 == 0:
                print(f"  {n}/{len(files)} | ok={ok} err={err} | {time.time()-t0:.0f}s",
                      flush=True)
    json.dump(manifest, open(os.path.join(outdir, '_manifest.json'), 'w'), indent=1)
    total_mb = sum(m['size'] for m in manifest) / 1e6
    print(f"DONE {a.name}: {ok} file, {err} loi, {total_mb:.0f}MB in {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
