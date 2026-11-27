# SPDX-License-Identifier: GPL-3.0-or-later
"""Precompute readonly PE backing; identity keys match the Wine patch."""
import contextlib
import fcntl
import os
import struct
import uuid
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


def _lock_file(cache):
    return os.fdopen(os.open(cache / '.lock', os.O_RDWR | os.O_CREAT, 0o600))


@contextlib.contextmanager
def _locked(cache, lock=None):
    """One writer at a time: prune deletes the link names a refresh is still using."""
    with lock or _lock_file(cache) as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        yield


def prepare(source, cache):
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    with _locked(cache):
        _prepare(source, cache)


def _prepare(source, cache):
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
                # A run killed after chmod leaves a read-only temp file behind.
                temp.unlink(missing_ok=True)
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
    _prune(cache, entries)


def _check(source, cache):
    """Return the manifest and its sections keyed to the source's current identity.

    None unless the source still has the content the cache was built from and
    every cache file is read-only with its recorded hash.
    """
    try:
        manifest = read_json(cache/'manifest.json')
        sections = manifest['sections']
        if not sections or digest(source) != manifest['source_sha256']:
            return None
        st = source.stat()
        current = []
        for item in sections:
            file = cache / item['file']
            if file.stat().st_mode & 0o222 or digest(file) != item['sha256']:
                return None
            current.append(dict(item, file=identity(st, item['offset'], item['size'])))
        return manifest, current
    except (Error, OSError, KeyError, TypeError, ValueError):
        return None  # A damaged manifest (an offset that is not a number) is stale too.


def status(source, cache):
    """'current' when Wine's lookup finds the cache, 'moved' when refresh() can
    rename it to the source's identity, otherwise 'stale'."""
    checked = _check(source, cache)
    if checked is None:
        return 'stale'
    return 'current' if checked[0]['sections'] == checked[1] else 'moved'


def valid(source, cache):
    return status(source, cache) == 'current'


def refresh(source, cache):
    """Use a cache whose content still matches after the source's identity changed.

    The key holds the source's device, inode and ctime, as Wine's lookup does.
    btrfs gives a subvolume its device number when it is mounted, so after some
    reboots the key no longer matched, Desktop ran without the cache and doctor
    failed until a repair rebuilt the same bytes. The files hold only the source's
    sections, and the source's hash still matches, so renaming them to the current
    identity gives what a rebuild would.
    """
    try:
        lock = _lock_file(cache)
    except OSError:
        # A cache that cannot be written is still used when nothing needs renaming.
        return status(source, cache) == 'current'
    with _locked(cache, lock):
        try:
            return _refresh(source, cache)
        except OSError:
            return False


def _refresh(source, cache):
    checked = _check(source, cache)
    if checked is None:
        return False
    manifest, current = checked
    try:
        if manifest['sections'] != current:
            for old, new in zip(manifest['sections'], current):
                if old['file'] != new['file']:
                    temp = cache / ('.' + new['file'] + '.' + uuid.uuid4().hex)
                    os.link(cache / old['file'], temp)
                    os.replace(temp, cache / new['file'])
            atomic_json(cache/'manifest.json', dict(manifest, sections=current))
        _prune(cache, current)
        return True
    except OSError:
        return False


def _prune(cache, sections):
    # Files of earlier identities or sources are never read again, nor are the
    # link names refresh() leaves when it is stopped between link and rename.
    keep = {item['file'] for item in sections}
    for file in cache.iterdir():
        name = file.name
        if ((name.endswith(('.bin', '.bin.tmp')) or (name.startswith('.') and '.bin.' in name))
                and name not in keep):
            file.unlink(missing_ok=True)
