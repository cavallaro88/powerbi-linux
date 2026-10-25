# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, patches, text_pickers, tooltips


class TooltipGuards(unittest.TestCase):
    def test_unknown_document_is_rejected(self):
        with self.assertRaisesRegex(common.Error, 'Unsupported tooltip document'):
            tooltips.patch_document(b'unknown document')

    def test_changed_recipe_is_rejected_even_for_patched_input(self):
        source = b'synthetic already patched'
        with patch.object(tooltips, 'PATCHED_SHA256', hashlib.sha256(source).hexdigest()), \
                patch.object(tooltips, 'FRAGMENT', tooltips.FRAGMENT + b'altered'):
            with self.assertRaisesRegex(common.Error, 'Unsupported tooltip recipe'):
                tooltips.patch_document(source)

    def test_only_authored_fragment_is_added_and_result_is_idempotent(self):
        source = b'<html><head></head><body><svg><title>42</title></svg></body></html>'
        expected = source.replace(b'</head>', tooltips.FRAGMENT + b'</head>')
        with patch.object(tooltips, 'ORIGINAL_SHA256', hashlib.sha256(source).hexdigest()), \
                patch.object(tooltips, 'PATCHED_SHA256', hashlib.sha256(expected).hexdigest()):
            result = tooltips.patch_document(source)
            self.assertEqual(result.replace(tooltips.FRAGMENT, b''), source)
            self.assertEqual(tooltips.patch_document(result), result)

    def test_missing_or_ambiguous_insertion_point_is_rejected(self):
        for source in [b'<html>no head</html>', b'</head></head>']:
            with patch.object(tooltips, 'ORIGINAL_SHA256', hashlib.sha256(source).hexdigest()):
                with self.assertRaisesRegex(common.Error, 'Unexpected tooltip document structure'):
                    tooltips.patch_document(source)

    def test_wrong_output_hash_is_rejected(self):
        source = b'<html><head></head></html>'
        with patch.object(tooltips, 'ORIGINAL_SHA256', hashlib.sha256(source).hexdigest()):
            with self.assertRaisesRegex(common.Error, 'Unexpected tooltip patch output'):
                tooltips.patch_document(source)

    def test_tooltip_preflight_failure_leaves_application_unchanged(self):
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
            picker.write_bytes(b'synthetic original document')
            with patch.object(patches, 'ORIGINALS', originals), \
                    patch.object(patches.legacy_html, 'patch_ui', return_value=b'html'), \
                    patch.object(patches.signin, 'patch_windows', return_value=b'email'), \
                    patch.object(text_pickers, 'patch_document', return_value=b'unsupported tooltip input'), \
                    patch.object(patches, 'run') as run:
                with self.assertRaisesRegex(common.Error, 'Unsupported tooltip document'):
                    patches.install(prefix, prefix/'runtime', prefix/'log')
                run.assert_not_called()
            for name, expected in originals.items():
                self.assertEqual(common.digest(app/name), expected)
            self.assertEqual(picker.read_bytes(), b'synthetic original document')
            self.assertEqual(list((prefix/'powerbi-linux-originals').iterdir()), [])
