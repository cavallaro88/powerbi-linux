# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import platforms


class DesktopTargets(unittest.TestCase):
    def test_pop_and_ubuntu_2404_are_explicit_experimental_targets(self):
        for name in ('pop', 'ubuntu'):
            with self.subTest(name=name):
                info = platforms.release('ID=' + name + '\nVERSION_ID="24.04"\n')
                accepted, detail = platforms.status(info)
                self.assertTrue(accepted)
                self.assertIn('experimental', detail)

    def test_older_pop_and_other_derivatives_are_not_silently_accepted(self):
        for text in ('ID=pop\nVERSION_ID="22.04"', 'ID=ubuntu\nVERSION_ID="22.04"',
                     'ID=linuxmint\nVERSION_ID="24.04"\nID_LIKE="ubuntu debian"', ''):
            with self.subTest(text=text):
                self.assertFalse(platforms.status(platforms.release(text))[0])

    def test_existing_fedora_support_is_preserved(self):
        for version in ('44', '43', ''):
            self.assertTrue(platforms.status({'ID':'fedora', 'VERSION_ID':version})[0])

    def test_os_release_is_parsed_as_data_without_shell_execution(self):
        info = platforms.release('ID=pop\nVERSION_ID="24.04"\nPRETTY_NAME="Pop!_OS 24.04"\n')
        self.assertEqual(info['PRETTY_NAME'], 'Pop!_OS 24.04')
        self.assertFalse(platforms.status(platforms.release('ID="pop\nVERSION_ID=24.04'))[0])
