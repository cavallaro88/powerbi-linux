# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import autorecovery, common, patches


def synthetic_resource():
    """A stand-in with the real layout: header, name marker, indented body, anchor, source map."""
    head = b'/' * autorecovery._NAME_OFFSET
    body = (autorecovery._NAME + b'(function () {\r\n    var a = 1;\r\n        var b = 2;\r\n' +
            autorecovery._ANCHOR + b'})();\r\n' + autorecovery._SOURCE_MAP)
    return (head + body).ljust(autorecovery._SIZE, b' ')


def expected_output(resource):
    start = autorecovery._NAME_OFFSET
    body = (autorecovery._NAME + b'(function () {\r\nvar a = 1;\r\nvar b = 2;\r\n' + autorecovery._HOOK +
            autorecovery._ANCHOR.lstrip(b' ') + b'})();\r\n')
    return (resource[:start] + body).ljust(autorecovery._SIZE, b' ')


class AutoRecoveryTests(unittest.TestCase):
    def test_missing_or_duplicate_marker_is_rejected(self):
        for source in (b'no dialog here', autorecovery._NAME * 2):
            with self.subTest(source=source[:20]):
                with self.assertRaisesRegex(common.Error, 'Unsupported Auto recovery dialog resource'):
                    autorecovery.patch_windows(source)

    def test_marker_without_room_for_its_header_is_rejected(self):
        with self.assertRaisesRegex(common.Error, 'Invalid Auto recovery dialog resource offset'):
            autorecovery.patch_windows(autorecovery._NAME + b'x' * autorecovery._SIZE)

    def test_unknown_script_contents_are_rejected(self):
        source = b'x' * autorecovery._NAME_OFFSET + autorecovery._NAME + b'unknown script' * 200
        with self.assertRaisesRegex(common.Error, 'Unsupported Auto recovery dialog contents'):
            autorecovery.patch_windows(source)

    def test_hook_lands_before_the_anchor_and_keeps_sizes_and_marker_offset(self):
        resource = synthetic_resource()
        expected = expected_output(resource)
        source = b'PE before' + resource + b'PE after'
        with patch.object(autorecovery, 'RESOURCE_ORIGINAL_SHA256', hashlib.sha256(resource).hexdigest()), \
                patch.object(autorecovery, 'RESOURCE_PATCHED_SHA256', hashlib.sha256(expected).hexdigest()):
            result = autorecovery.patch_windows(source)
            self.assertEqual(result, b'PE before' + expected + b'PE after')
            # The marker keeps its offset, so doctor and a second repair find the patched resource.
            self.assertEqual(autorecovery.resource_hash(result), autorecovery.RESOURCE_PATCHED_SHA256)
            self.assertEqual(autorecovery.patch_windows(result), result)

    def test_unexpected_output_is_rejected(self):
        resource = synthetic_resource()
        with patch.object(autorecovery, 'RESOURCE_ORIGINAL_SHA256', hashlib.sha256(resource).hexdigest()):
            with self.assertRaisesRegex(common.Error, 'Unexpected Auto recovery dialog patch output'):
                autorecovery.patch_windows(resource)

    def install_until_failure(self, recipe_name, **mocks):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            app = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
            app.mkdir(parents=True)
            originals = {}
            for name in patches.ORIGINALS:
                (app / name).write_bytes(('synthetic ' + name).encode())
                originals[name] = common.digest(app / name)
            picker = app / patches.text_pickers.DOCUMENT
            picker.parent.mkdir(parents=True)
            picker.write_bytes(b'unsupported stylesheet')
            with patch.object(patches, recipe_name, originals), \
                    patch.object(patches.legacy_html, 'patch_ui', return_value=b'html'), \
                    patch.object(patches.dialog_serializers, 'patch_ui', side_effect=lambda data: data), \
                    patch.object(patches.options_show, 'patch_ui', side_effect=lambda data: data), \
                    patch.object(patches.signin, 'patch_windows', return_value=b'email'), \
                    patch.object(patches, 'run') as run:
                with self.assertRaises(common.Error) as raised:
                    patches.install(prefix, Path('/unused-runtime'), prefix / 'log')
                run.assert_not_called()
            for name, sha in originals.items():
                self.assertEqual(common.digest(app / name), sha)
            self.assertEqual(list((prefix / 'powerbi-linux-originals').iterdir()), [])
            return str(raised.exception)

    def test_verified_builds_reject_an_unknown_dialog_before_replacing_files(self):
        for recipe_name in ('ORIGINALS_2159_1231', 'ORIGINALS_2160'):
            with self.subTest(recipe=recipe_name):
                message = self.install_until_failure(recipe_name)
                self.assertIn('Unsupported Auto recovery dialog resource', message)

    def test_other_builds_leave_the_dialog_alone(self):
        for recipe_name in ('ORIGINALS', 'CURRENT_ORIGINALS'):
            with self.subTest(recipe=recipe_name), \
                    patch.object(patches.autorecovery, 'patch_windows') as dialog:
                # Setup goes on to the next guard, the text picker document.
                message = self.install_until_failure(recipe_name)
                self.assertIn('Unsupported text picker document', message)
                dialog.assert_not_called()


if __name__ == '__main__':
    unittest.main()
