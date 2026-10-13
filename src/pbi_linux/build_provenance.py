# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject unreviewed patches and packaging stale or incomplete runtime builds."""
import hashlib
import json
from pathlib import Path
import subprocess

from .common import atomic_json


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def files(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory)
        if any(part in ('.git', '__pycache__') for part in relative.parts) or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(directory.resolve()):
                raise SystemExit('Build tree contains a symlink outside its fingerprinted directory')
            result[str(relative)] = {'link': str(path.readlink())}
        elif path.is_file():
            result[str(relative)] = {'sha256': _hash(path.read_bytes()),
                                     'mode': path.stat().st_mode & 0o777}
    return result


def reviewed_patches(root):
    registry = root / 'runtime/patches.lock.json'
    expected = json.loads(registry.read_text())
    actual = {p.name: _hash(p.read_bytes()) for p in (root / 'runtime/patches').glob('*.patch')}
    if not actual or actual != expected:
        raise SystemExit('Unreviewed runtime patches: filenames/hashes differ from patches.lock.json')
    if (root / '.git').exists():
        paths = ['runtime/patches', 'runtime/patches.lock.json']
        tracked = set(subprocess.check_output(
            ['git', 'ls-files', '-z', '--', *paths], cwd=root).decode().split('\0'))
        required = {'runtime/patches/' + name for name in actual} | {'runtime/patches.lock.json'}
        if not required.issubset(tracked):
            raise SystemExit('Commit reviewed runtime patches and their registry before building')
        changed = subprocess.check_output(['git', 'diff', 'HEAD', '--', *paths], cwd=root)
        if changed:
            raise SystemExit('Runtime patches/registry have uncommitted changes')
    return actual


def inputs(root, version, builder_id):
    reviewed_patches(root)
    snapshot = {}
    for name in ('runtime', 'src/helpers', 'src/pbi_linux/build_provenance.py',
                 'LICENSE', 'LICENSES', 'sources/wine', 'sources/dxvk', 'sources/dnlib'):
        path = root / name
        if not path.exists():
            raise SystemExit('Missing build input: ' + name)
        if path.is_dir():
            snapshot[name] = files(path)
        else:
            snapshot[name] = _hash(path.read_bytes())
    return {'version': version, 'builder_image_id': builder_id,
            'input_sha256': _hash(json.dumps(snapshot, sort_keys=True).encode())}


def begin(root, version, builder_id):
    # Invalidate before any preparation/compilation that could fail.
    (root / 'build/runtime-build-success.json').unlink(missing_ok=True)
    return inputs(root, version, builder_id)


def record_success(root, started):
    current = inputs(root, started['version'], started['builder_image_id'])
    if current != started:
        raise SystemExit('Build inputs changed during compilation; no successful receipt recorded')
    payload = files(root / 'dist/runtime')
    if not payload:
        raise SystemExit('No runtime payload was built')
    atomic_json(root / 'build/runtime-build-success.json', dict(current, payload=payload))


def verify(root, version, builder_id):
    receipt = root / 'build/runtime-build-success.json'
    if not receipt.is_file():
        raise SystemExit('No successful full runtime build recorded; rebuild before packaging')
    try:
        value = json.loads(receipt.read_text())
        current = inputs(root, version, builder_id)
        if any(value.get(k) != v for k, v in current.items()):
            raise SystemExit('Successful build does not match version, builder or current inputs')
        actual = files(root / 'dist/runtime')
        payload = value['payload']
        if not payload or any(actual.get(k) != v for k, v in payload.items()):
            raise SystemExit('Compiled runtime payload changed after the successful build')
        # Packaging adds only these provenance/license files; never accept a
        # forgotten DLL or diagnostic executable that was not in the build.
        metadata = {'runtime.json', 'builder-packages.tsv', 'compiler.txt', 'toolchain.json'}
        extra = set(actual) - set(payload)
        if any(k not in metadata and not k.startswith('licenses/') for k in extra):
            raise SystemExit('Unexpected files were added to the compiled runtime payload')
    except (ValueError, KeyError, TypeError) as exc:
        raise SystemExit('Invalid successful-build receipt; rebuild before packaging') from exc
    return value
