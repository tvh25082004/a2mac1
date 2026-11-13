"""Create GitHub Release cad-captures-v1 and upload the capture zips as assets."""
import json, os, sys, time, urllib.request

TOKEN = os.environ.get('GH_PAT', '')  # never hardcode; export GH_PAT before running
REPO = 'tvh25082004/a2mac1'
API = f'https://api.github.com/repos/{REPO}'
ASSETS = [
    ('/home/z/my-project/download/CAPTURES_VinFast_VF6_Plus_2024.zip',
     'PNG captures (4 views) of all 1,670 STL parts of VinFast VF6 Plus 2024, rendered '
     'locally from the A2MAC1 CAD set. index.csv maps every partId + material.'),
    ('/home/z/my-project/download/CAPTURES_VinFast_VF8_Plus_2023.zip',
     'PNG captures (4 views) of the 69 STL parts of VinFast VF8 Plus 2023 downloaded so '
     'far, rendered locally from the A2MAC1 CAD set. index.csv included.'),
]


def api(method, path, payload=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(payload).encode() if payload else None,
                                 headers={'Authorization': f'token {TOKEN}',
                                          'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    body = ('Per-part PNG captures rendered from the A2MAC1 3D STL set (4 standard views: '
            'iso / front / side / top, shaded, white background, part name in the title). '
            'One zip per vehicle line, each with an index.csv (partId, material label, STL size).\n\n'
            '- VinFast VF6 Plus 2024: 1,670 parts (complete set)\n'
            '- VinFast VF8 Plus 2023: 69 parts (first batch; rest pending A2MAC1 unblock)\n\n'
            'Regeneration scripts: scripts/render_all_captures.py + package_captures.py in the repo.')
    try:
        rel = api('POST', '/releases', {'tag_name': 'cad-captures-v1',
                                        'name': 'CAD Part Captures (PNG, 4 views) - VF6 1670 + VF8 69',
                                        'body': body})
        print('created release:', rel['html_url'])
    except urllib.error.HTTPError as e:
        if e.code == 422:  # tag already exists
            rel = api('GET', '/releases/tags/cad-captures-v1')
            print('release exists:', rel['html_url'])
            for a in rel['assets']:
                print('  existing asset:', a['name'])
        else:
            raise
    upload_url = rel['upload_url'].split('{')[0]
    for path, _ in ASSETS:
        name = os.path.basename(path)
        size = os.path.getsize(path)
        existing = {a['name'] for a in api('GET', f'/releases/{rel["id"]}/assets?per_page=100')}
        if name in existing:
            print(f'{name}: already uploaded, skip')
            continue
        t0 = time.time()
        print(f'uploading {name} ({size/1e6:.0f}MB)...', flush=True)
        req = urllib.request.Request(f'{upload_url}?name={name}',
                                     data=open(path, 'rb').read(),
                                     method='POST',
                                     headers={'Authorization': f'token {TOKEN}',
                                              'Content-Type': 'application/zip'})
        with urllib.request.urlopen(req, timeout=1800) as r:
            asset = json.load(r)
        print(f'  -> {asset["state"]} in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
