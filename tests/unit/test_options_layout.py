# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import options_layout, legacy_html
from pbi_linux.common import Error


class OptionsInteractionGuards(unittest.TestCase):
    def test_unrecognized_input_is_refused_before_transform(self):
        source = b'unsupported assembly'
        with patch.object(options_layout, '_transform') as transform:
            with self.assertRaisesRegex(Error, 'Unsupported HTML assembly'):
                options_layout.patch(source)
        transform.assert_not_called()
        self.assertEqual(source, b'unsupported assembly')

    def test_version_specific_entrypoint_cannot_upgrade_another_recipe(self):
        source = b'owned synthetic 2.158 baseline'
        sha = hashlib.sha256(source).hexdigest()
        with patch.dict(options_layout.BASELINES, {sha: ('2.158.1177.0', 0)}), \
                patch.object(options_layout, 'patch') as transform:
            with self.assertRaisesRegex(Error, 'Unsupported 2.159'):
                legacy_html.patch_ui_2159(source)
        transform.assert_not_called()

    def fixture(self):
        # Owned synthetic resources only; no Microsoft assembly/code is shipped.
        jquery = (b'// Copyright Synthetic fixture\n'
                  b'var untouchedSecurityCheck = true;\n// removable explanation\n')
        options = (b'_groupTabControl.load($(".o-group-options")).then(function(){var oldLayout="' +
                   b'synthetic layout ' * 20 + b'";oldFit();});\r\nKoFloatingDialog.show();\r\n')
        source = b'PE sentinel' + b'x' * 128
        jq_offset = len(source)
        source += jquery.ljust(options_layout.JQUERY_SIZE, b' ')
        source += b'unrelated resource sentinel'
        op_offset = len(source)
        source += options.ljust(options_layout.OPTIONS_SIZE, b' ')
        source += b'IL and metadata sentinel'
        overrides = {
            'JQUERY_OFFSET': jq_offset,
            'OPTIONS_OFFSET': op_offset,
            'OPTIONS_BASE_SHA256': hashlib.sha256(options.ljust(options_layout.OPTIONS_SIZE, b' ')).hexdigest(),
        }
        for name, value in overrides.items():
            context = patch.object(options_layout, name, value)
            context.start()
            self.addCleanup(context.stop)
        return source, jq_offset, op_offset

    def test_only_two_resource_ranges_can_change(self):
        source, jq, op = self.fixture()
        result = options_layout._transform_resources(source, 0)
        self.assertEqual(len(result), len(source))
        self.assertEqual(result[:jq], source[:jq])
        self.assertEqual(result[jq + options_layout.JQUERY_SIZE:op], source[jq + options_layout.JQUERY_SIZE:op])
        self.assertEqual(result[op + options_layout.OPTIONS_SIZE:], source[op + options_layout.OPTIONS_SIZE:])
        self.assertIn(b'Copyright Synthetic fixture', result)
        self.assertIn(b'var untouchedSecurityCheck = true;', result)
        self.assertIn(b'powerbiOptionsLayout(_groupTabControl)', result)

    def test_shifted_resource_layout_preserves_prefix_and_other_bytes(self):
        source, _, _ = self.fixture()
        padding = b'2.159 layout shift'.ljust(256, b'.')
        shifted = padding + source
        result = options_layout._transform_resources(shifted, 256)
        self.assertEqual(result[:256], padding)
        self.assertEqual(result[256:], options_layout._transform_resources(source, 0))

    def test_changed_resource_is_rejected(self):
        source, _, op = self.fixture()
        source = source[:op] + b'!' + source[op + 1:]
        with self.assertRaisesRegex(Error, 'Unexpected Options interaction resource'):
            options_layout._transform_resources(source, 0)

    def test_oversized_helper_is_refused(self):
        source, _, _ = self.fixture()
        with patch.object(Path, 'read_bytes', return_value=b'var huge = "' + b'x' * 5000 + b'";'):
            with self.assertRaisesRegex(Error, 'exceeds its resources'):
                options_layout._transform_resources(source, 0)

    def test_wrong_final_checksum_is_refused(self):
        source, _, _ = self.fixture()
        sha = hashlib.sha256(source).hexdigest()
        with patch.dict(options_layout.BASELINES, {sha: ('synthetic', 0)}), \
                patch.dict(options_layout.PATCHED, {'synthetic': '0' * 64}), \
                patch.object(options_layout, '_native_resize', side_effect=lambda value, delta: value):
            with self.assertRaisesRegex(Error, 'Unexpected Options interaction assembly output'):
                options_layout.patch(source)


class NativeResizeGuards(unittest.TestCase):
    def fixture(self):
        import struct
        source = bytearray(b'x' * 1500)
        source[100:229] = b'original method'.ljust(129, b' ')
        struct.pack_into('<I', source, 1000, 0x1234)
        plan = (100, hashlib.sha256(source[100:229]).hexdigest(), b'new method'.ljust(129, b'\0'), (1000, 0x1234, 0x5678))
        context = patch.dict(options_layout._NATIVE, {0: plan})
        context.start()
        self.addCleanup(context.stop)
        return bytes(source)

    def test_native_patch_changes_only_its_slot_and_method_rva(self):
        import struct
        source = self.fixture()
        result = options_layout._native_resize(source, 0)
        self.assertEqual(len(source), len(result))
        self.assertEqual(source[:100], result[:100])
        self.assertEqual(source[229:1000], result[229:1000])
        self.assertEqual(source[1004:], result[1004:])
        self.assertEqual(struct.unpack_from('<I', result, 1000)[0], 0x5678)

    def test_changed_method_body_is_refused(self):
        source = self.fixture()
        source = source[:100] + b'!' + source[101:]
        with self.assertRaisesRegex(Error, 'Unsupported native Options resize'):
            options_layout._native_resize(source, 0)

    def test_changed_method_rva_is_refused(self):
        source = self.fixture()
        source = source[:1000] + b'xxxx' + source[1004:]
        with self.assertRaisesRegex(Error, 'Unsupported native Options resize'):
            options_layout._native_resize(source, 0)
