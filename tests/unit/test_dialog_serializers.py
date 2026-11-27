# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, dialog_serializers, patches

FLOATING, DROPFORM = dialog_serializers.RESOURCES


def synthetic(resource):
    """A stand-in with the real layout: header, marker, indented body, the call, the anchor."""
    head = b'/' * (resource.marker_offset - 2) + b'\r\n'
    lines = [resource.marker, b'    var a = 1;\r\n', resource.call[0]]
    lines.append(resource.walker_before or resource.walker_after)
    lines.extend(text + b'\r\n' for text in resource.removed)
    return (head + b''.join(lines)).ljust(resource.size, b' ')


def assembly(*resources):
    data = b'MZ before'
    for body in resources:
        data += struct.pack('<I', len(body)) + body + b'between'
    return data


def expected(resource, body):
    updated = body.replace(resource.call[0], resource.call[1])
    anchor = resource.walker_before or resource.walker_after
    walker = dialog_serializers._WALKER + b'\r\n'
    updated = updated.replace(anchor, walker + anchor if resource.walker_before else anchor + walker)
    for text in resource.removed:
        updated = updated.replace(text + b'\r\n', b'\r\n')
    lines = [line.lstrip(b' ') for line in updated.rstrip(b' ').split(b'\r\n')]
    return b'\r\n'.join(lines).ljust(resource.size, b' ')


class DialogSerializerTests(unittest.TestCase):
    def guarded(self):
        """Pin both resources' hashes to the synthetic stand-ins."""
        bodies = [synthetic(resource) for resource in (FLOATING, DROPFORM)]
        outputs = [expected(resource, body) for resource, body in zip((FLOATING, DROPFORM), bodies)]
        stack = []
        for resource, body, output in zip((FLOATING, DROPFORM), bodies, outputs):
            for name, value in (('original', hashlib.sha256(body).hexdigest()),
                                ('patched', hashlib.sha256(output).hexdigest())):
                pinned = patch.object(resource, name, value)
                pinned.start()
                stack.append(pinned)
        for pinned in stack:
            self.addCleanup(pinned.stop)
        return bodies, outputs

    def test_both_serializers_get_the_walker_in_place(self):
        bodies, outputs = self.guarded()
        source = assembly(*bodies)
        result = dialog_serializers.patch_ui(source)
        self.assertEqual(result, assembly(*outputs))
        self.assertEqual(len(result), len(source))
        self.assertTrue(dialog_serializers.patched(result))
        self.assertFalse(dialog_serializers.patched(source))
        self.assertEqual(dialog_serializers.patch_ui(result), result)
        # The fallback now walks with toJS, never ko.toJSON over the host.
        self.assertNotIn(b'ko.toJSON', result)
        self.assertEqual(result.count(b'function toJS(v,k,o)'), 2)

    def test_missing_or_duplicate_marker_is_refused(self):
        bodies, _ = self.guarded()
        for source in (assembly(bodies[1]), assembly(bodies[0], bodies[0], bodies[1])):
            with self.subTest(size=len(source)):
                with self.assertRaisesRegex(common.Error, 'Unsupported floating dialog serializer resource'):
                    dialog_serializers.patch_ui(source)

    def test_a_wrong_length_prefix_is_refused(self):
        bodies, _ = self.guarded()
        source = bytearray(assembly(*bodies))
        source[9:13] = struct.pack('<I', FLOATING.size + 1)
        with self.assertRaisesRegex(common.Error, 'Invalid floating dialog serializer resource offset'):
            dialog_serializers.patch_ui(bytes(source))

    def test_unknown_contents_are_refused(self):
        self.guarded()
        body = synthetic(FLOATING).replace(b'var a = 1;', b'var a = 2;')
        with self.assertRaisesRegex(common.Error, 'Unsupported floating dialog serializer contents'):
            dialog_serializers.patch_ui(assembly(body, synthetic(DROPFORM)))

    def test_unexpected_output_is_refused(self):
        bodies, _ = self.guarded()
        with patch.object(FLOATING, 'patched', '0' * 64):
            with self.assertRaisesRegex(common.Error, 'Unexpected floating dialog serializer patch output'):
                dialog_serializers.patch_ui(assembly(*bodies))

    def test_the_walker_skips_objects_that_are_not_jscript_objects(self):
        walker = dialog_serializers._WALKER
        self.assertTrue(walker.startswith(b'function toJS(v,k,o){'))
        self.assertIn(b'!(v instanceof Object))return;', walker)
        self.assertIn(b'ko.isObservable(v)', walker)

    def test_only_2159_1231_writes_the_combined_hash(self):
        self.assertEqual(patches.ui_patched_hash('2.159.1231.0'), patches.options_show.UI_PATCHED_SHA256['2.159.1231.0'])
        for version in ('2.158.1177.0', '2.159.883.0'):
            self.assertEqual(patches.ui_patched_hash(version), patches.legacy_html.patched_hash(version))

    def install_until_failure(self, recipe_name):
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
                    patch.object(patches, 'run') as run:
                with self.assertRaises(common.Error) as raised:
                    patches.install(prefix, Path('/unused-runtime'), prefix / 'log')
                run.assert_not_called()
            for name, sha in originals.items():
                self.assertEqual(common.digest(app / name), sha)
            return str(raised.exception)

    def test_verified_builds_refuse_an_unknown_serializer_before_replacing_files(self):
        for recipe_name in ('ORIGINALS_2159_1231', 'ORIGINALS_2160'):
            with self.subTest(recipe=recipe_name):
                self.assertIn('Unsupported floating dialog serializer resource',
                              self.install_until_failure(recipe_name))

    def test_other_builds_leave_the_serializers_alone(self):
        for recipe_name in ('ORIGINALS', 'CURRENT_ORIGINALS'):
            with self.subTest(recipe=recipe_name), \
                    patch.object(patches.dialog_serializers, 'patch_ui') as serializers, \
                    patch.object(patches.options_show, 'patch_ui') as options, \
                    patch.object(patches.signin, 'patch_windows', return_value=b'email'):
                # Setup goes on to the next guard, the text picker document.
                self.assertIn('Unsupported text picker document', self.install_until_failure(recipe_name))
                serializers.assert_not_called()
                options.assert_not_called()


if __name__ == '__main__':
    unittest.main()
