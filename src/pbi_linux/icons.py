# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract the installed application's original PNG icon; no Microsoft asset ships here."""
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import zlib
from .common import Error, atomic_json, read_json


def application_png(data):
    """Read bounded PE icon resources and select the largest PNG in the app group."""
    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise ValueError('Truncated icon resource')
        return struct.unpack_from(fmt, data, offset)
    if len(data) > 16 * 1024**2 or data[:2] != b'MZ':
        raise ValueError('Invalid application image')
    pe = unpack('<I', 0x3c)[0]
    if data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Invalid PE header')
    sections, optional_size = unpack('<H', pe+6)[0], unpack('<H', pe+20)[0]
    optional = pe+24
    magic = unpack('<H', optional)[0]
    if magic not in (0x10b, 0x20b) or not 1 <= sections <= 96:
        raise ValueError('Unsupported PE format')
    directory = optional+(112 if magic == 0x20b else 96)+16
    if directory+8 > optional+optional_size:
        raise ValueError('Missing resource directory')
    resource_rva, resource_size = unpack('<II', directory)
    ranges = [unpack('<IIII', optional+optional_size+i*40+8) for i in range(sections)]
    def file_offset(rva, size):
        for virtual_size, address, raw_size, offset in ranges:
            delta = rva-address
            if 0 <= delta and delta+size <= raw_size and offset+delta+size <= len(data):
                return offset+delta
        raise ValueError('Resource outside file-backed section')
    base = file_offset(resource_rva, resource_size)
    def entries(offset):
        if offset < 0 or offset+16 > resource_size:
            raise ValueError('Invalid resource directory offset')
        named, ids = unpack('<HH', base+offset+12)
        count = named+ids
        if count > 1024 or offset+16+8*count > resource_size:
            raise ValueError('Invalid resource entry count')
        return [unpack('<II', base+offset+16+i*8) for i in range(count)]
    def resources(kind):
        roots = [ptr for key, ptr in entries(0) if key == kind]
        result = {}
        if not roots:
            return result
        if len(roots) != 1 or not roots[0] & 0x80000000:
            raise ValueError('Invalid resource type')
        for key, ptr in entries(roots[0] & 0x7fffffff):
            if key & 0x80000000:
                continue
            if not ptr & 0x80000000:
                raise ValueError('Invalid resource language directory')
            languages = entries(ptr & 0x7fffffff)
            for _, leaf in sorted(languages, key=lambda item: item[0] != 0):
                if leaf & 0x80000000 or leaf+16 > resource_size:
                    raise ValueError('Invalid resource data entry')
                rva, size = unpack('<II', base+leaf)
                if size > 4*1024**2:
                    raise ValueError('Oversized icon')
                start = file_offset(rva, size)
                result.setdefault(key, data[start:start+size])
        return result
    groups, images = resources(14), resources(3)
    if not groups:
        raise ValueError('Application has no icon group')
    group = groups.get(32512, groups[min(groups)])
    if len(group) < 6:
        raise ValueError('Truncated icon group')
    reserved, kind, count = struct.unpack_from('<HHH', group)
    if reserved or kind != 1 or not 1 <= count <= 256 or len(group) != 6+14*count:
        raise ValueError('Unsupported icon group')
    candidates = []
    for i in range(count):
        resource = struct.unpack_from('<H', group, 6+i*14+12)[0]
        image = images.get(resource, b'')
        if image[:8] != b'\x89PNG\r\n\x1a\n':
            continue
        if len(image) < 33 or image[8:16] != b'\0\0\0\rIHDR':
            raise ValueError('Invalid PNG icon header')
        width, height = struct.unpack_from('>II', image, 16)
        if not 1 <= width <= 1024 or not 1 <= height <= 1024:
            raise ValueError('Invalid PNG icon dimensions')
        pos, ended = 8, False
        while pos+12 <= len(image):
            size = struct.unpack_from('>I', image, pos)[0]
            end = pos+12+size
            if end > len(image) or zlib.crc32(image[pos+4:end-4]) != struct.unpack_from('>I', image, end-4)[0]:
                raise ValueError('Invalid PNG icon chunk')
            if image[pos+4:pos+8] == b'IEND':
                ended = end == len(image) and size == 0
                break
            pos = end
        if not ended:
            raise ValueError('Incomplete PNG icon')
        candidates.append((width*height, image))
    if not candidates:
        raise ValueError('Application has no supported PNG icon')
    return max(candidates, key=lambda item: item[0])[1]


def install_original(paths, prefix):
    """Install user artwork from the verified local app, independently of its profile path."""
    source = Path(prefix)/'drive_c/Program Files/Microsoft Power BI Desktop/bin/PBIDesktop.exe'
    target = paths.data.parent/'icons/hicolor/512x512/apps/powerbi-linux.png'
    manifest = paths.cache/'desktop-icon.json'
    if not source.is_file() or source.stat().st_size > 16*1024**2 or target.is_symlink():
        return None
    try:
        data = source.read_bytes()
        source_sha = hashlib.sha256(data).hexdigest()
        try:
            old = read_json(manifest) if manifest.exists() else {}
        except Error:
            old = {}
        if not isinstance(old, dict):
            old = {}
        if (old.get('source_sha256') == source_sha and target.is_file() and
                old.get('icon_sha256') == hashlib.sha256(target.read_bytes()).hexdigest()):
            return target
        image = application_png(data)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, pending = tempfile.mkstemp(dir=target.parent, prefix='.powerbi-icon-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(image)
            os.replace(pending, target)
        finally:
            Path(pending).unlink(missing_ok=True)
        atomic_json(manifest, {'source_sha256': source_sha,
                              'icon_sha256': hashlib.sha256(image).hexdigest()})
        return target
    except (Error, OSError, ValueError, struct.error):
        # Artwork failure must not prevent opening a report; keep the packaged fallback.
        return None
