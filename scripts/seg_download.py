"""Segmented parallel downloader for GitHub release assets (Range-based).
Usage: python3 seg_download.py <url> <outfile> [n_conns=16] [seg_mb=16]
Resume-safe: completed segments recorded in <outfile>.state.json."""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def head_size(url):
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req, timeout=30) as r:
        return int(r.headers['Content-Length'])


def fetch_range(url, a, b, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={'Range': f'bytes={a}-{b}'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            if t == tries - 1:
                raise
            time.sleep(1.5 * (t + 1))


def main():
    url, out = sys.argv[1], sys.argv[2]
    nconn = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    seg_bytes = int(sys.argv[4]) * 1024 * 1024 if len(sys.argv) > 4 else 16 * 1024 * 1024
    size = head_size(url)
    nseg = (size + seg_bytes - 1) // seg_bytes
    state_path = out + '.state.json'
    done = set()
    if os.path.exists(state_path):
        done = set(json.load(open(state_path)))
        print(f'resume: {len(done)}/{nseg} segments done')
    if not os.path.exists(out) or os.path.getsize(out) != size:
        with open(out, 'wb') as f:
            f.truncate(size)
    t0 = time.time()
    downloaded = 0
    lock_write = __import__('threading').Lock()

    def work(i):
        a = i * seg_bytes
        b = min(size, a + seg_bytes) - 1
        data = fetch_range(url, a, b)
        with open(out, 'r+b') as f:
            f.seek(a)
            f.write(data)
        with lock_write:
            st = json.load(open(state_path)) if os.path.exists(state_path) else []
            st.append(i)
            json.dump(st, open(state_path, 'w'))

    with ThreadPoolExecutor(max_workers=nconn) as pool:
        futs = {pool.submit(work, i): i for i in range(nseg) if i not in done}
        for k, fu in enumerate(as_completed(futs), 1):
            fu.result()
            downloaded += 1
            if k % 20 == 0 or k == len(futs):
                el = time.time() - t0
                print(f'  {len(done)+k}/{nseg} seg | {el:.0f}s | '
                      f'{(k*seg_bytes/1e6)/max(el,0.1):.1f}MB/s', flush=True)
    os.remove(state_path)
    print(f'DONE {out} {size/1e9:.2f}GB in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
