#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise a real DEB only inside an explicitly disposable root container."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (os.geteuid() != 0 or os.environ.get('PBI_DEB_DISPOSABLE') != '1'
            or not any(Path(p).exists() for p in ('/run/.containerenv', '/.dockerenv'))):
        parser.error('Refusing package changes outside an explicitly disposable root container')
    package = args.package.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checks = []
    result = {'schema': 1, 'scope': 'Package lifecycle only; no Wine/Microsoft setup or graphical certification',
              'os_release': Path('/etc/os-release').read_text(),
              'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(), 'checks': checks}

    def run(name, command):
        if command[0] == 'apt-get':
            # Minimal official images can exclude man pages through dpkg config.
            # Include this payload so dpkg --verify tests the complete DEB.
            command = ['apt-get', '-o', 'Dpkg::Options::=--path-include=/usr/share/man/*',
                       '-o', 'Dpkg::Options::=--path-include=/usr/share/doc/powerbi-linux/*', *command[1:]]
        p = subprocess.run([str(v) for v in command], text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=dict(os.environ, DEBIAN_FRONTEND='noninteractive'), timeout=300)
        checks.append({'name': name, 'exit_code': p.returncode, 'output': p.stdout})
        print(name + ': ' + str(p.returncode), flush=True)
        if p.returncode:
            raise RuntimeError(name + ' failed:\n' + p.stdout)
        return p.stdout

    # Deliberately synthetic user files; package hooks must not edit them.
    home = Path('/home/powerbi-deb-fixture')
    files = {home / '.local/share/powerbi-linux/profiles/sentinel/teste.pbix': b'synthetic report sentinel',
             home / '.config/powerbi-linux/settings.json': b'{"user_setting":"preserve"}',
             home / '.cache/powerbi-linux/sentinel': b'preserve cache'}
    for p, data in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def preserved():
        for p, data in files.items():
            assert p.read_bytes() == data, 'User data changed: ' + str(p)
        assert not (Path.home() / '.local/share/powerbi-linux/active.json').exists(), 'A package hook provisioned a prefix'

    try:
        # Check archive owners before installation; no chown or root build required.
        with tempfile.TemporaryFile() as payload:
            subprocess.run(['dpkg-deb', '--fsys-tarfile', str(package)], stdout=payload, check=True)
            payload.seek(0)
            with tarfile.open(fileobj=payload) as archive:
                assert all(m.uid == 0 and m.gid == 0 for m in archive.getmembers()), 'Non-root archive owner'
        run('install', ['apt-get', 'install', '-y', '--no-install-recommends', package])
        preserved()
        run('cli-version', ['pbi-linux', '--version'])
        run('desktop-entry', ['desktop-file-validate', '/usr/share/applications/powerbi-linux.desktop'])
        entry = configparser.ConfigParser(interpolation=None)
        entry.read('/usr/share/applications/powerbi-linux.desktop')
        assert entry['Desktop Entry']['Exec'].startswith('pbi-linux open')
        assert shutil.which('pbi-linux')
        assert Path('/usr/share/icons/hicolor/scalable/apps/powerbi-linux.svg').is_file()
        assert Path('/usr/share/mime/application/x-powerbi-pbix.xml').is_file()
        assert not run('dpkg-verify', ['dpkg', '--verify', 'powerbi-linux']).strip()
        code = ('from types import SimpleNamespace; from pathlib import Path; '
                'from pbi_linux import resources, platforms; '
                'c=resources.load(SimpleNamespace(settings=Path("/nonexistent-powerbi-settings"))); '
                'assert c["memory_max"]==c["swap_max"]==c["cpu_quota"]=="infinity"; '
                'assert c["webview_heap_mb"]==c["renderer_process_limit"]=="auto"; '
                'assert c["browser_mode"]=="standard"; '
                'accepted, detail=platforms.status(); assert accepted and "experimental" in detail; '
                'print(detail); print(c)')
        run('experimental-platform-and-unchanged-defaults',
            ['env', 'PYTHONPATH=/usr/share/powerbi-linux/src', 'python3', '-c', code])
        run('reinstall', ['apt-get', 'install', '-y', '--reinstall', package])
        preserved()
        # A metadata-only newer package verifies an actual dpkg upgrade path.
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            folder.chmod(0o755)
            stage = folder / 'stage'
            run('extract-upgrade-fixture', ['dpkg-deb', '--raw-extract', package, stage])
            control = stage / 'DEBIAN/control'
            text = control.read_text()
            version = run('read-version', ['dpkg-deb', '--field', package, 'Version']).strip()
            upgraded = version + '+qa1'
            control.write_text(text.replace('Version: ' + version + '\n', 'Version: ' + upgraded + '\n'))
            candidate = folder / 'powerbi-upgrade.deb'
            run('build-upgrade-fixture', ['dpkg-deb', '--root-owner-group', '-Zxz', '--build', stage, candidate])
            run('upgrade', ['apt-get', 'install', '-y', candidate])
            assert run('installed-upgraded-version', ['dpkg-query', '-W', '-f=${Version}', 'powerbi-linux']) == upgraded
            preserved()
        run('remove', ['apt-get', 'remove', '-y', 'powerbi-linux'])
        preserved()
        assert not Path('/usr/bin/pbi-linux').exists()
        assert not Path('/usr/share/applications/powerbi-linux.desktop').exists()
        run('install-again', ['apt-get', 'install', '-y', package])
        run('purge', ['apt-get', 'purge', '-y', 'powerbi-linux'])
        preserved()
        assert not Path('/usr/share/powerbi-linux').exists()
        result['status'] = 'passed'
    except Exception as exc:
        result.update(status='failed', error=str(exc))
        raise
    finally:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: ' + str(args.output), flush=True)


if __name__ == '__main__':
    main()
