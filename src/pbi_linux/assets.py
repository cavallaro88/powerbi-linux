# SPDX-License-Identifier: GPL-3.0-or-later
"""Verified downloads and constrained runtime extraction."""
import os
import re
from pathlib import Path, PurePosixPath
import http.client
import tarfile
import tempfile
import sys
import time
import urllib.request
import urllib.error
from .common import Error, check_digest, read_json, digest


def download(url, expected, cache):
    if not re.fullmatch('[a-f0-9]{64}', expected or ''):
        raise Error('Invalid download checksum')
    if not url.startswith('https://'):
        raise Error('Downloads must use HTTPS')
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = cache / expected
    if target.exists():
        check_digest(target, expected)
        return target
    fd, name = tempfile.mkstemp(dir=cache, prefix='.download-')
    try:
        with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(url, timeout=60) as response:
            if not response.url.startswith('https://'):
                raise Error('Download redirected to an insecure URL')
            size = response.headers.get('Content-Length', '')
            total = int(size) if size.isdigit() else None
            received, last = 0, time.monotonic()
            while block := response.read(1024 * 1024):
                out.write(block)
                received += len(block)
                now = time.monotonic()
                if now - last >= 2:
                    detail = f'{received / 1024**2:.0f} MiB'
                    if total:
                        detail += f' / {total / 1024**2:.0f} MiB'
                    print('Downloading: ' + detail, file=sys.stderr, flush=True)
                    last = now
            if total is not None and received != total:
                raise Error('Incomplete download; rerun setup to retry')
        check_digest(name, expected)
        os.replace(name, target)
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
        raise Error('Download failed; check your connection and rerun setup. Verified downloads are reused') from exc
    finally:
        Path(name).unlink(missing_ok=True)
    return target


def extract_runtime(archive, target):
    target.mkdir(parents=True, mode=0o700)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if sum(max(x.size, 0) for x in members) > 4 * 1024**3:
            raise Error('Runtime archive exceeds the 4 GiB extraction limit')
        names = set()
        for item in members:
            path = PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or item.name in names:
                raise Error('Unsafe or duplicate runtime archive path')
            names.add(item.name)
            if not (item.isfile() or item.isdir() or item.issym()):
                raise Error('Unsupported runtime archive entry')
            if item.issym():
                link = PurePosixPath(item.linkname)
                if link.is_absolute():
                    raise Error('Absolute runtime symlink')
                resolved = (target / item.name).parent.joinpath(item.linkname).resolve()
                if not resolved.is_relative_to(target.resolve()):
                    raise Error('Runtime symlink escapes the archive')
        # No archive member may traverse a symlink, regardless of member ordering.
        symlinks = {PurePosixPath(m.name) for m in members if m.issym()}
        for m in members:
            if any(p in symlinks for p in PurePosixPath(m.name).parents):
                raise Error('Runtime member traverses a symlink')
        tar.extractall(target, members=members, filter='data')
    return verify_runtime(target)


def verify_runtime(root):
    root = Path(root)
    manifest = read_json(root / 'runtime.json')
    if manifest.get('schema') != 1 or manifest.get('arch') != 'x86_64':
        raise Error('Unsupported runtime manifest')
    for name, expected in manifest['files'].items():
        file = root / name
        if not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
            raise Error('Runtime file is missing or escapes its root')
        check_digest(file, expected)
    for name in ('bin/wine', 'bin/wineserver', 'bin/winepath', 'helpers/PowerBICompositionManager.dll'):
        if name not in manifest['files']:
            raise Error('Incomplete runtime: ' + name)
    return manifest
