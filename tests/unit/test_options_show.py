# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, options_show, patches

SHOW = options_show._SHOW


def synthetic():
    """A stand-in with the real layout: header, marker, the show call, padding."""
    head = b'/' * (options_show._MARKER_OFFSET - 2) + b'\r\n'
    body = head + options_show._MARKER + b'_groupTabControl.load();\r\n' + SHOW + b'}\r\n'
    return body.ljust(options_show._SIZE, b' ')


def assembly(*bodies, size=options_show._SIZE):
    data = b'MZ before'
    for body in bodies:
        data += struct.pack('<I', size) + body + b'between'
    return data


class OptionsShowTests(unittest.TestCase):
    def guarded(self):
        """Pin the resource hashes to the synthetic stand-in."""
        body = synthetic()
        output = body.rstrip(b' ').replace(SHOW, SHOW + options_show._ON_SHOW).ljust(options_show._SIZE, b' ')
        for name, value in (('_ORIGINAL', hashlib.sha256(body).hexdigest()),
                            ('_PATCHED', hashlib.sha256(output).hexdigest())):
            pinned = patch.object(options_show, name, value)
            pinned.start()
            self.addCleanup(pinned.stop)
        return body, output

    def test_the_page_calls_on_show_after_showing_without_auto_size(self):
        body, output = self.guarded()
        source = assembly(body)
        result = options_show.patch_ui(source)
        self.assertEqual(result, assembly(output))
        self.assertEqual(len(result), len(source))
        self.assertTrue(options_show.patched(result))
        self.assertFalse(options_show.patched(source))
        self.assertEqual(options_show.patch_ui(result), result)
        # Auto-size stays off; the host is told the page is ready on the next tick.
        call = result.index(SHOW) + len(SHOW)
        self.assertTrue(result[call:].startswith(b'TrackedTimer.setTimeout(function(){KoFloatingDialog.host.onShow();'))
        self.assertNotIn(b'enableWindowAutoSize:true', result)

    def test_missing_or_duplicate_marker_is_refused(self):
        body, _ = self.guarded()
        for source in (b'MZ nothing here', assembly(body, body)):
            with self.subTest(size=len(source)):
                with self.assertRaisesRegex(common.Error, 'Unsupported Options dialog resource'):
                    options_show.patch_ui(source)

    def test_a_wrong_length_prefix_is_refused(self):
        body, _ = self.guarded()
        with self.assertRaisesRegex(common.Error, 'Invalid Options dialog resource offset'):
            options_show.patch_ui(assembly(body, size=options_show._SIZE + 1))

    def test_unknown_contents_are_refused(self):
        self.guarded()
        body = synthetic().replace(b'load();', b'load(1);')
        with self.assertRaisesRegex(common.Error, 'Unsupported Options dialog contents'):
            options_show.patch_ui(assembly(body))

    def test_unexpected_output_is_refused(self):
        body, _ = self.guarded()
        with patch.object(options_show, '_PATCHED', '0' * 64):
            with self.assertRaisesRegex(common.Error, 'Unexpected Options dialog patch output'):
                options_show.patch_ui(assembly(body))

    def test_verified_builds_apply_it_after_the_serializers(self):
        for recipe_name in ('ORIGINALS_2159_1231', 'ORIGINALS_2160'):
            with self.subTest(recipe=recipe_name):
                self.check_order(recipe_name)

    def check_order(self, recipe_name):
        order = []
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            app = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
            app.mkdir(parents=True)
            originals = {}
            for name in patches.ORIGINALS:
                (app / name).write_bytes(('synthetic ' + name).encode())
                originals[name] = common.digest(app / name)
            def serializers(data):
                order.append(('serializers', data))
                return b'serialized'
            def options(data):
                order.append(('options', data))
                raise common.Error('stop here')
            with patch.object(patches, recipe_name, originals), \
                    patch.object(patches.legacy_html, 'patch_ui', return_value=b'html'), \
                    patch.object(patches.dialog_serializers, 'patch_ui', side_effect=serializers), \
                    patch.object(patches.options_show, 'patch_ui', side_effect=options), \
                    patch.object(patches, 'run') as run:
                with self.assertRaisesRegex(common.Error, 'stop here'):
                    patches.install(prefix, Path('/unused-runtime'), prefix / 'log')
                run.assert_not_called()
            # Nothing was replaced before the guard failed.
            for name, sha in originals.items():
                self.assertEqual(common.digest(app / name), sha)
        self.assertEqual(order, [('serializers', b'html'), ('options', b'serialized')])

    def test_setup_writes_the_assembly_with_the_options_fix(self):
        for version in patches.DIALOG_RECIPES:
            self.assertEqual(patches.ui_patched_hash(version), options_show.UI_PATCHED_SHA256[version])


if __name__ == '__main__':
    unittest.main()
