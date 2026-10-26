#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the experimental DEB without user installations or proprietary inputs."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ('src', 'runtime', 'connectors', 'packaging', 'docs', 'LICENSE', 'LICENSES', 'README.md')
BUILDER_IMAGE = 'docker.io/library/debian@sha256:4876fdea29cac1a33a3195f1eb1952feb1fca7dd6dd00be3e2f1879cf20d34d2'


def ignored(directory, names):
    return [name for name in names if name in ('__pycache__', '.git', '.pbi', 'results', '.env')
            or name.startswith('.env.')
            or name.lower().endswith(('.pyc', '.log', '.dmp', '.pbix', '.exe', '.dll', '.so', '.snk', '.pfx', '.pem'))]


def stage(destination):
    destination = destination.resolve()
    if (destination.exists() or ROOT.is_relative_to(destination)
            or any(destination.is_relative_to(ROOT / name) for name in PAYLOAD)):
        raise ValueError('Staging requires a new directory outside packaged input paths')
    destination.mkdir(parents=True)
    data = destination / 'usr/share/powerbi-linux'
    data.mkdir(parents=True)
    for name in PAYLOAD:
        source = ROOT / name
        # Never follow a source symlink into private host data.
        if source.is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob('*'))):
            raise ValueError('Symlinks are not permitted in DEB source inputs: ' + name)
        if source.is_dir():
            shutil.copytree(source, data / name, ignore=ignored)
        else:
            shutil.copy2(source, data / name)
    files = [('packaging/pbi-linux', 'usr/bin/pbi-linux', 0o755),
             ('packaging/powerbi-linux.desktop', 'usr/share/applications/powerbi-linux.desktop', 0o644),
             ('packaging/powerbi-linux.xml', 'usr/share/mime/packages/powerbi-linux.xml', 0o644),
             ('packaging/powerbi-linux.svg', 'usr/share/icons/hicolor/scalable/apps/powerbi-linux.svg', 0o644),
             ('packaging/debian/control', 'DEBIAN/control', 0o644),
             ('packaging/debian/postinst', 'DEBIAN/postinst', 0o755),
             ('packaging/debian/prerm', 'DEBIAN/prerm', 0o755),
             ('packaging/debian/postrm', 'DEBIAN/postrm', 0o755),
             ('packaging/debian/copyright', 'usr/share/doc/powerbi-linux/copyright', 0o644)]
    for source, target, mode in files:
        target = destination / target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, target)
        target.chmod(mode)
        (data / source).chmod(mode)
    for source, target in (('packaging/debian/changelog', 'usr/share/doc/powerbi-linux/changelog.Debian.gz'),
                           ('packaging/pbi-linux.1', 'usr/share/man/man1/pbi-linux.1.gz')):
        target = destination / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress((ROOT / source).read_bytes(), mtime=0))
    size = sum(p.stat().st_size for p in (destination / 'usr').rglob('*') if p.is_file())
    control = destination / 'DEBIAN/control'
    control.write_text(control.read_text() + 'Installed-Size: ' + str((size + 1023) // 1024) + '\n')
    sums = []
    for file in sorted((destination / 'usr').rglob('*')):
        if file.is_file():
            md5 = hashlib.md5(file.read_bytes(), usedforsecurity=False).hexdigest()
            sums.append(md5 + '  ' + str(file.relative_to(destination)))
    (destination / 'DEBIAN/md5sums').write_text('\n'.join(sums) + '\n')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-only', type=Path, help='Stage into a new directory without dpkg-deb')
    parser.add_argument('--local', action='store_true', help='Use the installed dpkg-deb instead of a container')
    parser.add_argument('--engine', choices=('podman', 'docker'), default='podman')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/deb', help='Artifact directory (existing packages are not overwritten)')
    args = parser.parse_args()
    if args.stage_only:
        print(stage(args.stage_only))
        return
    fields = dict(line.split(': ', 1) for line in (ROOT / 'packaging/debian/control').read_text().splitlines()
                  if line and not line.startswith(' ') and ': ' in line)
    filename = '{Package}_{Version}_{Architecture}.deb'.format(**fields)
    if Path(filename).name != filename:
        raise ValueError('Invalid package filename in control metadata')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / filename
    checksum = artifact.with_suffix('.deb.sha256')
    if artifact.exists() or checksum.exists():
        raise SystemExit('Artifact already exists; choose a new version or output directory')
    with tempfile.TemporaryDirectory(prefix='.deb-', dir=output) as temporary:
        work = Path(temporary)
        staged = stage(work / 'stage')
        command = ['dpkg-deb', '--root-owner-group', '-Zxz', '--build']
        if args.local:
            subprocess.run([*command, str(staged), str(work / filename)], check=True)
        else:
            container = [args.engine, 'run', '--rm', '--network=none', '--cap-drop=ALL',
                         '--security-opt=no-new-privileges', '--user', str(os.getuid()) + ':' + str(os.getgid())]
            if args.engine == 'podman':
                container.append('--userns=keep-id')
            container += ['-v', str(work) + ':/work:Z', BUILDER_IMAGE]
            subprocess.run([*container, *command, '/work/stage', '/work/' + filename], check=True)
        (work / filename).replace(artifact)
    with artifact.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    checksum.write_text(sha + '  ' + filename + '\n')
    print(artifact)
    print(checksum)


if __name__ == '__main__':
    main()
