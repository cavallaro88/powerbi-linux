# SPDX-License-Identifier: GPL-3.0-or-later
"""Precompute readonly PE backing; identity keys match the Wine patch."""
import os
from pathlib import Path
import struct
from .common import Error, atomic_json, digest, read_json


def identity(st, offset, size):
    return '-'.join(format(n, 'x') for n in (st.st_dev, st.st_ino, st.st_ctime_ns // 10**9,
                     st.st_ctime_ns % 10**9, st.st_size, offset, size)) + '.bin'


def webview(prefix):
    base = prefix / 'drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application'
    files = list(base.glob('*/msedge.dll'))
    if not files:
        raise Error('WebView2 runtime is not installed')
    def version(file):
        try:
            return tuple(int(n) for n in file.parent.name.split('.'))
        except ValueError:
            return (0,)
    return max(files, key=version)


def prepare(source, cache):
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    st = source.stat()
    with source.open('rb') as stream:
        header = stream.read(4096)
    try:
        pe = struct.unpack_from('<I', header, 0x3c)[0]
        if header[pe:pe+4] != b'PE\0\0':
            raise ValueError()
        count, optional = struct.unpack_from('<H', header, pe+6)[0], struct.unpack_from('<H', header, pe+20)[0]
        table = pe + 24 + optional
        if table + 40 * count > len(header):
            raise ValueError()
        entries = []
        with source.open('rb') as stream:
            for i in range(count):
                base = table + 40*i
                virtual, _, raw, offset = struct.unpack_from('<IIII', header, base+8)
                mapped = ((virtual or raw)+4095) & ~4095
                size = min(raw, mapped)
                if offset % 4096 == 0 or size < 16*1024**2:
                    continue
                if offset + size > st.st_size:
                    raise ValueError()
                name = identity(st, offset, size)
                target, temp = cache / name, cache / (name + '.tmp')
                with temp.open('wb') as out:
                    out.write(b'PBICACH1' + bytes(4088))
                    stream.seek(offset)
                    left = size
                    while left:
                        chunk = stream.read(min(left, 1024**2))
                        if not chunk:
                            raise ValueError()
                        out.write(chunk)
                        left -= len(chunk)
                    out.write(bytes(mapped-size))
                temp.chmod(0o400)
                os.replace(temp, target)
                entries.append({'file': name, 'offset': offset, 'size': size, 'sha256': digest(target)})
    except (ValueError, struct.error) as exc:
        raise Error('Invalid WebView2 PE image; cache not activated') from exc
    atomic_json(cache/'manifest.json', {'source': str(source), 'source_sha256': digest(source), 'sections': entries})


def valid(source, cache):
    try:
        manifest = read_json(cache/'manifest.json')
        if digest(source) != manifest['source_sha256'] or not manifest['sections']:
            return False
        st = source.stat()
        for item in manifest['sections']:
            if identity(st, item['offset'], item['size']) != item['file']:
                return False
            file = cache / item['file']
            if file.stat().st_mode & 0o222 or digest(file) != item['sha256']:
                return False
        return True
    except (Error, OSError, KeyError):
        return False
