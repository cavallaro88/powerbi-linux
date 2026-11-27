# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import source_tree


class SourceTree(unittest.TestCase):
    def test_makepkg_output_is_excluded_only_beside_the_pkgbuild(self):
        names = ['PKGBUILD', 'pkg', 'src', 'powerbi-linux-0.1.0-19-x86_64.pkg.tar.zst']
        self.assertEqual(source_tree.ignored(str(ROOT / 'packaging/arch'), names), names[1:])
        self.assertEqual(source_tree.ignored(str(ROOT / 'packaging'), ['arch', 'pkg', 'src']), [])
        self.assertFalse(source_tree.excluded(ROOT / 'src'))

    def test_local_state_and_binaries_are_excluded(self):
        for name in ('__pycache__', '.env', '.env.local', 'results', '.pbi', 'cache.abf',
                     'Report.pbix', 'helper.DLL', 'session.log', 'key.pem'):
            self.assertTrue(source_tree.excluded(ROOT / 'docs' / name), name)
        for name in ('PKGBUILD', 'environment.md', 'results.md'):
            self.assertFalse(source_tree.excluded(ROOT / 'docs' / name), name)

    def test_every_tracked_file_is_selected(self):
        if not (ROOT / '.git').exists() or not shutil.which('git'):
            self.skipTest('not a Git checkout')
        # CI checks the tree out as another user; Git then needs the directory named as safe.
        listing = subprocess.run(['git', '-c', 'safe.directory=' + str(ROOT), '-C', str(ROOT), 'ls-files', '-z'],
                                 capture_output=True, text=True)
        if listing.returncode:
            self.skipTest('Git cannot list this checkout: ' + listing.stderr.strip())
        tracked = listing.stdout.split('\0')
        self.assertGreater(len(tracked), 100)
        dropped = [name for name in tracked if name and any(
            source_tree.excluded(ROOT / Path(*Path(name).parts[:depth]))
            for depth in range(1, len(Path(name).parts) + 1))]
        self.assertEqual(dropped, [])

    def test_symlinks_are_found_outside_excluded_entries_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # What a finished makepkg run leaves: the package tree links to
            # absolute paths of the installed package.
            (root / 'arch/pkg/usr/share/licenses').mkdir(parents=True)
            (root / 'arch/pkg/usr/share/licenses/LICENSE').symlink_to('/usr/share/powerbi-linux/LICENSE')
            (root / 'arch/PKGBUILD').write_text('')
            with mock.patch.object(source_tree, 'MAKEPKG', root / 'arch'):
                self.assertEqual(source_tree.symlinks(root), [])
                (root / 'arch/notes').symlink_to('/etc')
                (root / 'docs').mkdir()
                (root / 'docs/passwd').symlink_to('/etc/passwd')
                self.assertEqual(sorted(source_tree.symlinks(root)),
                                 [root / 'arch/notes', root / 'docs/passwd'])
                self.assertEqual(source_tree.symlinks(root / 'docs/passwd'), [root / 'docs/passwd'])

    def test_refusal_names_the_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs').mkdir()
            (root / 'docs/link').symlink_to('/etc')
            with mock.patch.object(source_tree, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'docs/link'):
                    source_tree.refuse_symlinks(('docs',))
                (root / 'docs/link').unlink()
                source_tree.refuse_symlinks(('docs',))

    def test_rpm_source_archive_omits_excluded_entries(self):
        # The member filter tools/build-rpm.py uses, on a synthetic tree.
        self.assertIn('filter=member', (ROOT / 'tools/build-rpm.py').read_text())
        self.assertIn('member=archive_filter(TOP)', (ROOT / 'tools/build-rpm.py').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'packaging/arch/pkg').mkdir(parents=True)
            (root / 'packaging/arch/pkg/file').write_text('x')
            (root / 'packaging/arch/PKGBUILD').write_text('x')
            (root / 'packaging/arch/PKGBUILD').chmod(0o777)
            (root / 'packaging/run').write_text('x')
            (root / 'packaging/run').chmod(0o777)
            (root / 'packaging/arch/powerbi-linux-0.1.0-19-x86_64.pkg.tar.zst').write_text('x')
            (root / 'packaging/__pycache__').mkdir()
            with mock.patch.object(source_tree, 'MAKEPKG', root / 'packaging/arch'):
                with tarfile.open(root / 'out.tar', 'w') as tar:
                    tar.add(root / 'packaging', arcname='top/packaging',
                            filter=source_tree.archive_filter('top', root))
            with tarfile.open(root / 'out.tar') as tar:
                modes = {info.name: info.mode for info in tar.getmembers()}
            self.assertEqual(sorted(modes), ['top/packaging', 'top/packaging/arch',
                                             'top/packaging/arch/PKGBUILD', 'top/packaging/run'])
            self.assertEqual(modes['top/packaging/arch'], 0o755)
            self.assertEqual(modes['top/packaging/run'], 0o755)
            # 0777 from a permissive mount: executable stays 0755, never world-writable.
            self.assertEqual(modes['top/packaging/arch/PKGBUILD'], 0o755)


if __name__ == '__main__':
    unittest.main()
