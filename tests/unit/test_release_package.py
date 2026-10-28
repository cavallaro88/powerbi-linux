# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep CLI package versions, the setup pin and shipped payload honest per release."""
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RELEASE = '0.1.0-19'
DEB_VERSION = '0.1.0-19~experimental1'


def control_fields():
    return dict(line.split(': ', 1) for line in (ROOT / 'packaging/debian/control').read_text().splitlines()
                if line and not line.startswith(' ') and ': ' in line)


class ReleasePackageTest(unittest.TestCase):

    def test_package_versions_match_the_prepared_revision(self):
        spec = (ROOT / 'packaging/powerbi-linux.spec').read_text()
        self.assertIn('Version:        0.1.0\n', spec)
        self.assertIn('Release:        19%{?dist}', spec)
        fields = control_fields()
        self.assertEqual(fields['Version'], DEB_VERSION)
        self.assertIn('experimental', fields['Description'].lower())
        changelog = (ROOT / 'packaging/debian/changelog').read_text()
        first = changelog.splitlines()[0]
        self.assertEqual(first, 'powerbi-linux (' + DEB_VERSION + ') experimental; urgency=medium')
        self.assertLess(changelog.index(DEB_VERSION), changelog.index('0.1.0-18~experimental2'))
        self.assertTrue((ROOT / 'docs/releases' / ('v' + RELEASE + '.md')).is_file())

    def test_setup_manifest_never_ships_a_placeholder_runtime_pin(self):
        manifest = json.loads((ROOT / 'packaging/setup.json').read_text())
        self.assertEqual(manifest['schema'], 1)
        build_default = re.search(r"--runtime-version', default='([^']+)'",
                                  (ROOT / 'runtime/build.py').read_text()).group(1)
        if manifest['status'] == 'ready':
            from pbi_linux import onboarding
            onboarding.validate_runtime_download(manifest['runtime'])
            self.assertEqual(manifest['runtime']['version'], build_default)
        else:
            self.assertEqual(manifest['status'], 'pending')
            self.assertTrue(manifest.get('reason'), 'A pending manifest must explain what is missing')
            self.assertIsNone(manifest.get('runtime'), 'A pending manifest must not pin an unverified runtime')
            self.assertIn(build_default, manifest['reason'])

    def test_no_runtime_or_odbc_binary_is_packaged(self):
        packages = ('src', 'runtime', 'connectors', 'packaging', 'docs')
        binaries = [str(path.relative_to(ROOT)) for name in packages
                    for path in (ROOT / name).rglob('*')
                    if path.is_file() and path.suffix.lower() in ('.dll', '.exe', '.msi', '.msix', '.pfx')]
        self.assertEqual(binaries, [], 'Packages must not ship Windows binaries, installers or signing keys')
        connectors = (ROOT / 'src/pbi_linux/connectors.py').read_text().lower()
        self.assertNotIn('redshift', connectors, 'The experimental ODBC bridge is not a shipped connector')


if __name__ == '__main__':
    unittest.main()
