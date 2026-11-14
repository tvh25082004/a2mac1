"""Create/refresh GitHub Release cad-captures-v1 with all download/CAPTURES_*.zip assets.
Asset names derive from car names; if a zip with the same name changed size on disk vs
remote, the remote asset is replaced (so resume sessions update partial cars automatically).
Release body + per-car counts come from data/cad_skip_list.json manifest."""
import glob
import json
import os
import time
import urllib.request

TOKEN = os.environ.get('GH_PAT', '')  # never hardcode; export GH_PAT before running
REPO = 'tvh25082004/a2mac1'
API = f'https://api.github.com/repos/{REPO}'
TAG = 'cad-captures-v1'
mf = json.load(open('/home/z/my-project/data/cad_skip_list.json')).get('manifest', {})


def api(method, path, payload=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(payload).encode() if payload else None,
                                 headers={'Authorization': f'token {TOKEN}',
                                          'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    assets = sorted(glob.glob('/home/z/my-project/download/CAPTURES_*.zip'))
    if not assets:
        print('khong co CAPTURES_*.zip nao trong download/')
        return
    lines = ['Per-part PNG captures rendered from the A2MAC1 3D STL set (4 standard views: '
             'iso / front / side / top, shaded, white background, part name in the title). '
             'One zip per vehicle line, each with an index.csv (partId, material label, STL size).', '']
    for car, m in sorted(mf.items()):
        done, total = len(m.get('ids', [])), m.get('total_files', 0)
        st = 'complete set' if done >= total else f'{done:,}/{total:,} (resume pending)'
        lines.append(f'- {car}: {st}')
    lines += ['', 'Regeneration: scripts/session_pipeline.sh (download -> render -> package -> upload -> tracker).']
    body = '\n'.join(lines)

    try:
        rel = api('POST', '/releases', {'tag_name': TAG, 'name': 'CAD Part Captures (PNG, 4 views)', 'body': body})
        print('created release:', rel['html_url'])
    except urllib.error.HTTPError as e:
        if e.code != 422:
            raise
        rel = api('GET', f'/releases/tags/{TAG}')
        api('PATCH', f'/releases/{rel["id"]}', {'body': body, 'name': 'CAD Part Captures (PNG, 4 views)'})
        print('release exists (body refreshed):', rel['html_url'])

    upload_url = rel['upload_url'].split('{')[0]
    remote = {a['name']: a for a in api('GET', f'/releases/{rel["id"]}/assets?per_page=100')}
    for path in assets:
        name = os.path.basename(path)
        size = os.path.getsize(path)
        if name in remote:
            if remote[name]['size'] == size:
                print(f'{name}: unchanged, skip')
                continue
            req = urllib.request.Request(remote[name]['url'], method='DELETE',
                                         headers={'Authorization': f'token {TOKEN}'})
            urllib.request.urlopen(req, timeout=60)
            print(f'{name}: replaced (size changed {remote[name]["size"]} -> {size})')
        t0 = time.time()
        print(f'uploading {name} ({size/1e6:.1f}MB)...', flush=True)
        req = urllib.request.Request(f'{upload_url}?name={name}', data=open(path, 'rb').read(),
                                     method='POST',
                                     headers={'Authorization': f'token {TOKEN}',
                                              'Content-Type': 'application/zip'})
        with urllib.request.urlopen(req, timeout=1800) as r:
            print(f'  -> {json.load(r)["state"]} in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
