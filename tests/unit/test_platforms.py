# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import platforms


class DesktopTargets(unittest.TestCase):
    def test_derivatives_and_unknown_targets_are_not_accepted(self):
        for text in ('ID=pop\nVERSION_ID="24.04"',
                     'ID=linuxmint\nVERSION_ID="24.04"\nID_LIKE="ubuntu debian"', ''):
            with self.subTest(text=text):
                self.assertFalse(platforms.status(platforms.release(text))[0])

    def test_deb_targets_are_explicitly_experimental(self):
        for name, version in (('ubuntu', '24.04'), ('ubuntu', '26.04'), ('debian', '13')):
            with self.subTest(name=name, version=version):
                accepted, detail = platforms.status({'ID': name, 'VERSION_ID': version})
                self.assertTrue(accepted)
                self.assertIn('experimental', detail.lower())

    def test_existing_fedora_support_is_preserved(self):
        for version in ('44', '43', ''):
            self.assertTrue(platforms.status({'ID':'fedora', 'VERSION_ID':version})[0])

    def test_unlisted_deb_versions_remain_rejected(self):
        for name, version in (('ubuntu', '22.04'), ('ubuntu', '25.10'), ('debian', '12'),
                              ('ubuntu', ''), ('debian', 'testing'), ('arch', '')):
            self.assertFalse(platforms.status({'ID': name, 'VERSION_ID': version})[0])

    def test_ntlm_guidance_uses_native_package_name(self):
        for name in ('ubuntu', 'debian'):
            with patch.object(platforms, 'release', return_value={'ID': name}):
                self.assertIn('apt install winbind', platforms.ntlm_help())
        with patch.object(platforms, 'release', return_value={'ID': 'fedora'}):
            self.assertIn('samba-winbind-clients', platforms.ntlm_help())

    def test_os_release_is_parsed_as_data_without_shell_execution(self):
        info = platforms.release('ID=fedora\nVERSION_ID="44"\nPRETTY_NAME="Fedora Linux 44"\n')
        self.assertEqual(info['PRETTY_NAME'], 'Fedora Linux 44')
        self.assertFalse(platforms.status(platforms.release('ID="fedora\nVERSION_ID=44'))[0])
