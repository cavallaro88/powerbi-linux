# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import platforms


class DesktopTargets(unittest.TestCase):
    def test_only_fedora_is_accepted(self):
        for text in ('ID=pop\nVERSION_ID="24.04"', 'ID=ubuntu\nVERSION_ID="24.04"',
                     'ID=linuxmint\nVERSION_ID="24.04"\nID_LIKE="ubuntu debian"', ''):
            with self.subTest(text=text):
                self.assertFalse(platforms.status(platforms.release(text))[0])

    def test_existing_fedora_support_is_preserved(self):
        for version in ('44', '43', ''):
            self.assertTrue(platforms.status({'ID':'fedora', 'VERSION_ID':version})[0])

    def test_os_release_is_parsed_as_data_without_shell_execution(self):
        info = platforms.release('ID=fedora\nVERSION_ID="44"\nPRETTY_NAME="Fedora Linux 44"\n')
        self.assertEqual(info['PRETTY_NAME'], 'Fedora Linux 44')
        self.assertFalse(platforms.status(platforms.release('ID="fedora\nVERSION_ID=44'))[0])
