# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, patches


class NativeDialogProvisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / 'profile'
        self.bin = self.prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
        self.bin.mkdir(parents=True)
        self.originals = {name: ('original:' + name).encode() for name in patches.ORIGINALS}
        for name, data in self.originals.items():
            (self.bin / name).write_bytes(data)
        self.runtime = self.root / 'runtime'
        (self.runtime / 'helpers').mkdir(parents=True)
        self.helpers = self.prefix / 'drive_c/powerbi-linux-setup'
        self.recipe = patch.object(patches, 'ORIGINALS', {
            name: common.digest(self.bin / name) for name in self.originals
        })
        self.recipe.start()
        self.addCleanup(self.recipe.stop)

    def run_until(self, failure):
        def run(command, **kwargs):
            tool = Path(str(command[1])).name
            if tool == 'MakeKey.exe':
                (self.helpers / 'stubs.snk').write_bytes(b'synthetic private key')
            elif tool in ('PatchShared.exe', 'PatchWinRT.exe'):
                output = Path(str(command[3])[2:].replace(chr(92), '/'))
                output.write_bytes(b'other-patch-output')
            if failure(command):
                raise common.Error('Injected native dialog failure')
        # This fixture exercises later native-dialog failures; the independent
        # HTML resource guard is covered by test_legacy_html.
        with patch.object(patches.legacy_html, 'patch_ui', return_value=b'html-patch'), \
                patch.object(patches, 'run', side_effect=run):
            with self.assertRaises(common.Error):
                patches.install(self.prefix, self.runtime, self.root / 'log')
        self.assertFalse((self.helpers / 'stubs.snk').exists())
        self.assertFalse((self.bin / patches.NATIVE_DIALOG).exists())
        for name, data in self.originals.items():
            self.assertEqual((self.prefix / 'powerbi-linux-originals' / name).read_bytes(), data)

    def test_failed_native_compile_preserves_application_files_and_removes_key(self):
        self.run_until(lambda command: 'PowerBISaveDialog.cs' in command)
        for name, data in self.originals.items():
            self.assertEqual((self.bin / name).read_bytes(), data)

    def test_rejected_native_patch_does_not_replace_desktop_dll(self):
        self.run_until(lambda command: Path(str(command[1])).name == 'PatchSavePrompt.exe' and
                       '--sign-dialog' not in command)
        name = 'Microsoft.PowerBI.Client.Windows.dll'
        self.assertEqual((self.bin / name).read_bytes(), self.originals[name])


if __name__ == '__main__':
    unittest.main()
