# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / 'tools/build-deb.py'


class DebianPackaging(unittest.TestCase):
    def test_python_bytecode_is_cleaned_before_package_files_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / 'stage'
            subprocess.run([sys.executable, str(BUILDER), '--stage-only', str(stage)],
                           check=True, capture_output=True)
            hook = stage / 'DEBIAN/prerm'
            self.assertTrue(hook.is_file(), 'Python cleanup must run before dpkg removes the .py file inventory')
            self.assertIn('py3clean -p powerbi-linux', hook.read_text())

    def test_stage_has_package_verification_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / 'stage'
            subprocess.run([sys.executable, str(BUILDER), '--stage-only', str(stage)],
                           check=True, capture_output=True)
            sums = stage / 'DEBIAN/md5sums'
            self.assertTrue(sums.is_file(), 'dpkg verification metadata is missing')
            self.assertIn('  usr/bin/pbi-linux\n', sums.read_text())
            self.assertIn('Installed-Size: ', (stage / 'DEBIAN/control').read_text())
            self.assertTrue((stage / 'usr/share/doc/powerbi-linux/changelog.Debian.gz').is_file())
            self.assertTrue((stage / 'usr/share/man/man1/pbi-linux.1.gz').is_file())

    def test_builder_offers_native_and_container_build_modes(self):
        result = subprocess.run([sys.executable, str(BUILDER), '--help'],
                                capture_output=True, text=True, check=True)
        self.assertIn('--local', result.stdout)
        self.assertIn('--engine', result.stdout)
        self.assertIn('--output', result.stdout)

    @unittest.skipUnless(shutil.which('dpkg-deb') and os.environ.get('PBI_PACKAGE_BUILD_TESTS') == '1',
                         'Archive construction is opt-in for post-merge packaging only')
    def test_native_build_contains_the_staged_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            subprocess.run([sys.executable, str(BUILDER), '--local', '--output', str(output)],
                           check=True, capture_output=True)
            packages = list(output.glob('*.deb'))
            self.assertEqual(len(packages), 1)
            fields = subprocess.check_output(['dpkg-deb', '--field', str(packages[0])], text=True)
            self.assertIn('Architecture: amd64', fields)
            payload = Path(directory) / 'extracted'
            subprocess.run(['dpkg-deb', '--extract', str(packages[0]), str(payload)], check=True)
            self.assertTrue(os.access(payload / 'usr/bin/pbi-linux', os.X_OK))
            self.assertTrue(packages[0].with_suffix('.deb.sha256').is_file())

    def test_stage_has_desktop_cache_hooks_but_no_provisioning_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / 'stage'
            subprocess.run([sys.executable, str(BUILDER), '--stage-only', str(stage)],
                           check=True, capture_output=True)
            for name in ('postinst', 'postrm'):
                hook = stage / 'DEBIAN' / name
                self.assertTrue(hook.is_file(), name + ' is missing')
                self.assertTrue(os.access(hook, os.X_OK))
                text = hook.read_text()
                self.assertIn('update-desktop-database', text)
                self.assertIn('update-mime-database', text)
                for forbidden in ('pbi-linux setup', 'wine ', 'curl ', 'wget ', '/home/', 'settings.json'):
                    self.assertNotIn(forbidden, text)

    def test_stage_installs_launcher_and_resources_without_user_profile(self):
        self.assertTrue(BUILDER.is_file(), 'The experimental DEB builder is not implemented')
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / 'stage'
            subprocess.run([sys.executable, str(BUILDER), '--stage-only', str(stage)],
                           check=True, capture_output=True, text=True)
            self.assertTrue(os.access(stage / 'usr/bin/pbi-linux', os.X_OK))
            for name in ('src/pbi_linux/cli.py', 'runtime/sources.lock.json',
                         'packaging/setup.json', 'LICENSES/Wine.txt'):
                self.assertTrue((stage / 'usr/share/powerbi-linux' / name).is_file(), name)
            self.assertTrue((stage / 'usr/share/applications/powerbi-linux.desktop').is_file())
            self.assertTrue((stage / 'usr/share/mime/packages/powerbi-linux.xml').is_file())
            self.assertTrue((stage / 'usr/share/icons/hicolor/scalable/apps/powerbi-linux.svg').is_file())
            self.assertFalse((stage / 'home').exists())
            self.assertFalse((stage / 'etc').exists())
            self.assertFalse(any(p.name in ('settings.json', 'active.json', 'previous.json')
                                 or p.suffix in ('.exe', '.dll', '.pyc') for p in stage.rglob('*')))
            control = (stage / 'DEBIAN/control').read_text()
            self.assertIn('Architecture: amd64', control)
            self.assertIn('experimental', control.lower())
            self.assertIn('python3 (>= 3.12)', control)
            self.assertIn('winbind', control)


if __name__ == '__main__':
    unittest.main()
