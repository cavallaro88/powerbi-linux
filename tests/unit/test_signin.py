# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, patches, signin


class SignInTests(unittest.TestCase):
    def test_unknown_desktop_is_rejected_before_resource_search(self):
        with self.assertRaisesRegex(common.Error, 'Unsupported Desktop assembly'):
            signin.patch_windows(b'unsupported assembly')

    def test_matching_file_hash_does_not_allow_unknown_script_contents(self):
        source = b'x' * signin._NAME_OFFSET + signin._NAME + b'unknown script'
        with self.assertRaisesRegex(common.Error, 'Unsupported email dialog contents'):
            signin.patch_windows(source, hashlib.sha256(source).hexdigest())

    def test_duplicate_resource_name_is_rejected(self):
        source = signin._NAME * 2
        with self.assertRaisesRegex(common.Error, 'Unsupported email dialog resource'):
            signin.patch_windows(source, hashlib.sha256(source).hexdigest())

    def test_invalid_email_recipe_leaves_all_application_files_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            app = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
            app.mkdir(parents=True)
            originals = {}
            for name in patches.ORIGINALS:
                (app / name).write_bytes(('original ' + name).encode())
                originals[name] = common.digest(app / name)
            with patch.object(patches, 'ORIGINALS', originals), \
                    patch.object(patches.legacy_html, 'patch_ui', return_value=b'html-patch'):
                with self.assertRaisesRegex(common.Error, 'Unsupported Desktop assembly'):
                    patches.install(prefix, Path('/runtime'), prefix / 'log')
            for name, sha in originals.items():
                self.assertEqual(common.digest(app / name), sha)
            self.assertEqual(list((prefix / 'powerbi-linux-originals').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
