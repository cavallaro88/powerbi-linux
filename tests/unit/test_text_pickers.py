# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, patches, text_pickers


class TextPickerGuards(unittest.TestCase):
    def test_unknown_document_is_rejected(self):
        with self.assertRaisesRegex(common.Error, 'Unsupported text picker document'):
            text_pickers.patch_document(b'unknown vendor document')

    def test_changed_recipe_is_rejected_even_for_already_patched_input(self):
        source = b'synthetic patched stylesheet'
        with patch.object(text_pickers, 'PATCHED_SHA256', hashlib.sha256(source).hexdigest()), \
                patch.object(text_pickers, 'STYLE', text_pickers.STYLE + b'altered'):
            with self.assertRaisesRegex(common.Error, 'Unsupported text picker recipe'):
                text_pickers.patch_document(source)

    def test_supported_source_is_preserved_and_repair_is_idempotent(self):
        source = b'<html><head><title>synthetic</title></head><body>fixture</body></html>'
        expected = source.replace(b'</head>', text_pickers.STYLE + b'</head>')
        with patch.object(text_pickers, 'ORIGINAL_SHA256', hashlib.sha256(source).hexdigest()), \
                patch.object(text_pickers, 'PATCHED_SHA256', hashlib.sha256(expected).hexdigest()):
            result = text_pickers.patch_document(source)
            self.assertEqual(result.replace(text_pickers.STYLE, b''), source)
            self.assertEqual(text_pickers.patch_document(result), result)

    def test_rejected_picker_preflight_does_not_replace_any_application_file(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            app = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
            app.mkdir(parents=True)
            originals = {}
            for name in patches.ORIGINALS:
                file = app / name
                file.write_bytes(('synthetic ' + name).encode())
                originals[name] = common.digest(file)
            picker = app / text_pickers.DOCUMENT
            picker.parent.mkdir(parents=True)
            picker.write_bytes(b'unsupported stylesheet')
            with patch.object(patches, 'ORIGINALS', originals), \
                    patch.object(patches.legacy_html, 'patch_ui', return_value=b'html'), \
                    patch.object(patches.signin, 'patch_windows', return_value=b'email'), \
                    patch.object(patches, 'run') as run:
                with self.assertRaisesRegex(common.Error, 'Unsupported text picker document'):
                    patches.install(prefix, Path('/unused-runtime'), prefix / 'log')
                run.assert_not_called()
            for name, sha in originals.items():
                self.assertEqual(common.digest(app / name), sha)
            self.assertEqual(picker.read_bytes(), b'unsupported stylesheet')
            self.assertEqual(list((prefix / 'powerbi-linux-originals').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
