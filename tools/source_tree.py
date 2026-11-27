# SPDX-License-Identifier: GPL-3.0-or-later
"""Which entries of a checkout may enter a package or a source export.

A checkout also holds caches, build output, local secrets and binaries that Git
ignores. The DEB, RPM and export builders copy whole directories, so they share
this one list instead of keeping three that drift apart.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = frozenset(('__pycache__', '.git', '.pbi', 'results', '.env'))
SUFFIXES = ('.pyc', '.log', '.dmp', '.abf', '.pbix', '.exe', '.dll', '.so', '.snk', '.pfx', '.pem')
# makepkg keeps its work directories and the built packages beside the PKGBUILD.
# pkg/ is unreadable while check() runs, and afterwards holds absolute symlinks.
MAKEPKG = ROOT / 'packaging/arch'


def excluded(path):
    """True for an entry that never ships, whatever the builder."""
    path = Path(path)
    name = path.name
    return (name in NAMES or name.startswith('.env.') or name.lower().endswith(SUFFIXES)
            or (path.parent == MAKEPKG and (name in ('pkg', 'src') or '.pkg.tar.' in name)))


def archive_filter(top, root=None):
    """A tarfile filter for an archive of the checkout under the directory top.

    Drops excluded entries, and clamps modes to 0755/0644: the RPM spec installs
    with cp -a, and modes as some mounts report them (0777) would leave the
    installed code writable by every local user.
    """
    def member(info):
        if excluded((root or ROOT) / Path(info.name).relative_to(top)):
            return None
        info.mode = 0o755 if info.isdir() or info.mode & 0o111 else 0o644
        return info
    return member


def ignored(directory, names):
    """The shutil.copytree callback form of excluded()."""
    return [name for name in names if excluded(Path(directory) / name)]


def symlinks(source):
    """Symlinks a copy of source would follow or ship. Excluded entries are not entered."""
    source = Path(source)
    if source.is_symlink():
        return [source]
    found = []
    for directory, folders, files in os.walk(source):
        folders[:] = [name for name in folders if not excluded(Path(directory) / name)]
        for name in folders + files:
            path = Path(directory) / name
            if path.is_symlink() and not excluded(path):
                found.append(path)
    return found


def refuse_symlinks(names):
    """Never follow or ship a source symlink: it can point into private host data."""
    for name in names:
        found = symlinks(ROOT / name)
        if found:
            raise ValueError('Symlinks are not permitted in packaged source inputs: ' +
                             str(found[0].relative_to(ROOT)))
