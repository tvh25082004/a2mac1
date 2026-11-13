"""Extract a small STL member from a remote ZIP (GitHub Release asset) via HTTP Range requests,
without downloading the whole bundle. Uses zipfile over a seekable HTTP-range file object."""
import sys, io, urllib.request, zipfile

URL = 'https://github.com/tvh25082004/a2mac1/releases/download/cad-v1/CAD-bundle-01.zip'


class HTTPRangeFile(io.RawIOBase):
    """Minimal seekable read-only file over HTTP Range (zip needs: end seek + member bytes)."""

    def __init__(self, url):
        self.url = url
        self._pos = 0
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=30) as r:
            self.size = int(r.headers['Content-Length'])
        self._fetches = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self._pos = offset
        elif whence == io.SEEK_CUR:
            self._pos += offset
        elif whence == io.SEEK_END:
            self._pos = self.size + offset
        return self._pos

    def tell(self):
        return self._pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self._pos
        if n == 0 or self._pos >= self.size:
            return b''
        n = min(n, self.size - self._pos)
        end = self._pos + n - 1
        req = urllib.request.Request(
            self.url, headers={'Range': f'bytes={self._pos}-{end}'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        self._fetches += 1
        self._pos += len(data)
        return data


def main():
    f = HTTPRangeFile(URL)
    print(f'bundle size: {f.size/1e9:.2f} GB')
    z = zipfile.ZipFile(f)
    names = z.namelist()
    stls = [n for n in names if n.lower().endswith('.stl')]
    print('tong member:', len(names), '| stl:', len(stls), '| folder goc:', stls[0].split("/")[0])
    # chon 3 part nho de render demo (ten + kich thuoc)
    infos = sorted(((z.getinfo(n).file_size, n) for n in stls))[:400]
    picks = [infos[0], infos[len(infos)//2], infos[len(infos)-400]]
    for size, name in picks:
        out = '/tmp/' + name.replace('/', '__')
        with z.open(name) as src, open(out, 'wb') as dst:
            dst.write(src.read())
        print(f'OK {name} ({size/1e6:.2f} MB) -> {out}')
    print('so lan fetch HTTP:', f._fetches)


if __name__ == '__main__':
    main()
