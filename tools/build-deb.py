#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the local Pop!_OS 24.04 experiment without invoking CI or publishing."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-16pop1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='Use the installed dpkg-deb')
    parser.add_argument('--engine', choices=('docker', 'podman'), default='docker')
    parser.add_argument('--image', default='ubuntu:24.04', help='Container supplying dpkg-deb')
    args = parser.parse_args()
    work = ROOT/'build/deb'/('powerbi-linux_' + VERSION + '_amd64')
    if work.exists():
        shutil.rmtree(work)
    share = work/'usr/share/powerbi-linux'
    share.mkdir(parents=True)
    for name in ('src', 'runtime', 'connectors', 'packaging', 'docs', 'LICENSE', 'LICENSES', 'README.md'):
        source, target = ROOT/name, share/name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(source, target)
    for source, target in (
        ('packaging/pbi-linux', 'usr/bin/pbi-linux'),
        ('packaging/powerbi-linux.desktop', 'usr/share/applications/powerbi-linux.desktop'),
        ('packaging/powerbi-linux.xml', 'usr/share/mime/packages/powerbi-linux.xml'),
        ('packaging/powerbi-linux.svg', 'usr/share/icons/hicolor/scalable/apps/powerbi-linux.svg'),
        ('packaging/debian/copyright', 'usr/share/doc/powerbi-linux/copyright'),
    ):
        destination = work/target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/source, destination)
    (work/'usr/bin/pbi-linux').chmod(0o755)
    control = work/'DEBIAN'
    control.mkdir()
    files = sorted(file for file in (work/'usr').rglob('*') if file.is_file())
    size = (sum(file.stat().st_size for file in files) + 1023) // 1024
    template = (ROOT/'packaging/debian/control').read_text()
    (control/'control').write_text(template.replace('@VERSION@', VERSION).replace('@INSTALLED_SIZE@', str(size)))
    for name in ('postinst', 'postrm'):
        shutil.copy2(ROOT/'packaging/debian'/name, control/name)
        (control/name).chmod(0o755)
    (control/'md5sums').write_text(''.join(
        hashlib.md5(file.read_bytes(), usedforsecurity=False).hexdigest() + '  ' +
        str(file.relative_to(work)) + '\n' for file in files))
    output = ROOT/'dist/popos-24.04'/VERSION/('powerbi-linux_' + VERSION + '_amd64.deb')
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.local:
        command = ['dpkg-deb', '--root-owner-group', '--build', str(work), str(output)]
    else:
        command = [args.engine, 'run', '--rm', '--user', str(os.getuid()) + ':' + str(os.getgid()),
                   '-v', str(ROOT) + ':/work:z', args.image,
                   'dpkg-deb', '--root-owner-group', '--build',
                   '/work/' + str(work.relative_to(ROOT)), '/work/' + str(output.relative_to(ROOT))]
    subprocess.run(command, check=True)
    output.with_suffix('.deb.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  ' + output.name + '\n')
    print(output)


if __name__ == '__main__':
    main()
