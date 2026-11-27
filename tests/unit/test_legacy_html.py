# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, legacy_html, patches


def registry_text(values):
    return 'WINE REGISTRY Version 2\n\n' + '\n\n'.join(
        '[' + ('Software\\Classes\\' + key).replace('\\', '\\\\') + '] 1792014000\n'
        '#time=1dd000000000000\n"CLSID"="' + value + '"'
        for key, value in values.items()) + '\n'


class LegacyHtmlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.prefix = Path(self.temp.name)
        (self.prefix / 'user.reg').write_text(registry_text({}))

    def test_com_class_alone_does_not_make_html_navigation_available(self):
        (self.prefix / 'system.reg').write_text(registry_text({
            r'CLSID\{25336920-03F9-11CF-8FD0-00AA00686F13}': 'HTML Document',
        }))
        self.assertEqual(set(legacy_html.missing_registrations(self.prefix)),
                         set(legacy_html.REGISTRATIONS))

    def test_unknown_html_assembly_is_rejected_without_modification(self):
        source = b'unsupported assembly'
        with self.assertRaisesRegex(common.Error, 'Unsupported legacy HTML assembly'):
            legacy_html.patch_ui(source)
        self.assertEqual(source, b'unsupported assembly')

    def test_source_list_patch_rejects_unknown_assembly(self):
        with self.assertRaisesRegex(common.Error, 'Unsupported HTML assembly'):
            legacy_html.patch_source_list(b'unknown assembly')

    def test_permissions_serializer_rejects_unknown_assembly(self):
        source = b'unknown assembly'
        with self.assertRaisesRegex(common.Error, 'Unsupported HTML assembly'):
            legacy_html.patch_permissions(source)
        self.assertEqual(source, b'unknown assembly')

    def test_options_layout_rejects_unknown_assembly(self):
        with self.assertRaisesRegex(common.Error, 'Unsupported HTML assembly'):
            legacy_html.patch_options(b'unknown assembly')

    def test_invalid_resource_recipe_does_not_replace_other_application_files(self):
        import hashlib
        app = self.prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
        app.mkdir(parents=True)
        originals = {}
        for name in patches.ORIGINALS:
            data = ('original ' + name).encode()
            (app / name).write_bytes(data)
            originals[name] = hashlib.sha256(data).hexdigest()
        with patch.object(patches, 'ORIGINALS', originals):
            with self.assertRaisesRegex(common.Error, 'Unsupported legacy HTML assembly'):
                patches.install(self.prefix, Path('/runtime'), self.prefix / 'log')
        for name, expected in originals.items():
            self.assertEqual(common.digest(app / name), expected)
        self.assertEqual(list((self.prefix / 'powerbi-linux-originals').iterdir()), [])

    def test_complete_registration_accepts_guid_case_and_shared_keys(self):
        (self.prefix / 'system.reg').write_text(registry_text({
            key: value.lower() for key, value in legacy_html.REGISTRATIONS.items()
        }))
        self.assertEqual(legacy_html.missing_registrations(self.prefix), [])

    def test_user_class_override_cannot_hide_a_broken_handler(self):
        (self.prefix / 'system.reg').write_text(registry_text(legacy_html.REGISTRATIONS))
        (self.prefix / 'user.reg').write_text(registry_text({
            r'PROTOCOLS\Handler\about': '{00000000-0000-0000-0000-000000000000}',
        }))
        self.assertEqual(legacy_html.missing_registrations(self.prefix),
                         [r'PROTOCOLS\Handler\about'])

    def test_successful_regsvr_with_wrong_handler_is_rejected(self):
        # A successful DLL registration is insufficient if the effective HKCR
        # entry remains broken or a user override masks the system value.
        with patch.object(legacy_html, 'run', return_value='CLSID REG_SZ {wrong}'):
            with self.assertRaisesRegex(common.Error, 'Legacy HTML registration failed'):
                legacy_html.register(self.prefix, Path('/runtime'), self.prefix / 'log')

    def scroll_fixture(self, padding):
        """A stand-in assembly: the source list resource at its 2.159.1231.0 location."""
        import hashlib
        start = legacy_html._SOURCES_OFFSET + 328
        resource = (b'function initialize() {\r\n' + legacy_html._SOURCES_SHOW + b'}\r\n').ljust(
            legacy_html._SOURCES_SIZE - padding, b'x') + b' ' * padding
        source = b'A' * start + resource + b'Z' * 64
        expected = resource.rstrip(b' ').replace(
            legacy_html._SOURCES_SHOW, legacy_html._SOURCES_SCROLL_HOOK + legacy_html._SOURCES_SHOW
        ).ljust(legacy_html._SOURCES_SIZE, b' ')
        output = source[:start] + expected + source[start + legacy_html._SOURCES_SIZE:]
        sha = lambda data: hashlib.sha256(data).hexdigest()
        guards = patch.multiple(
            legacy_html, _UI_2159_1231_OPTIONS_SHA256=sha(source), _SOURCES_PATCHED=sha(resource),
            _SOURCES_SCROLL_PATCHED=sha(expected), UI_2159_1231_PATCHED_SHA256=sha(output))
        return source, output, start, guards

    def test_scroll_bar_step_changes_only_the_source_list_resource(self):
        source, output, start, guards = self.scroll_fixture(len(legacy_html._SOURCES_SCROLL_HOOK))
        with guards:
            result = legacy_html._patch_sources_scroll(source)
            self.assertEqual(legacy_html._patch_sources_scroll(result), result)
        self.assertEqual(result, output)
        self.assertEqual(len(result), len(source))
        self.assertEqual(result[:start], source[:start])
        self.assertEqual(result[start + legacy_html._SOURCES_SIZE:], source[start + legacy_html._SOURCES_SIZE:])
        resource = result[start:start + legacy_html._SOURCES_SIZE]
        self.assertLess(resource.index(legacy_html._SOURCES_SCROLL_HOOK), resource.index(legacy_html._SOURCES_SHOW))

    def test_scroll_bar_step_leaves_other_assemblies_unchanged(self):
        from pbi_linux import options_layout
        self.assertEqual(legacy_html._patch_sources_scroll(b'another build'), b'another build')
        # Only 2.159.1231.0 and 2.160.1151.0 have the step; the older builds end at the Options recipe.
        self.assertEqual(legacy_html.patched_hash('2.158.1177.0'), options_layout.PATCHED['2.158.1177.0'])
        self.assertEqual(legacy_html.patched_hash('2.159.883.0'), options_layout.PATCHED['2.159.883.0'])
        self.assertNotEqual(legacy_html.patched_hash('2.159.1231.0'), options_layout.PATCHED['2.159.1231.0'])
        self.assertNotEqual(legacy_html.patched_hash('2.160.1151.0'), options_layout.PATCHED['2.160.1151.0'])

    def test_scroll_bar_step_refuses_a_resource_without_room(self):
        source, _, _, guards = self.scroll_fixture(len(legacy_html._SOURCES_SCROLL_HOOK) - 1)
        with guards, self.assertRaisesRegex(common.Error, 'exceeds its resource'):
            legacy_html._patch_sources_scroll(source)

    def test_scroll_bar_step_refuses_a_changed_resource(self):
        source, _, _, guards = self.scroll_fixture(len(legacy_html._SOURCES_SCROLL_HOOK))
        with guards, patch.object(legacy_html, '_SOURCES_PATCHED', '0' * 64):
            with self.assertRaisesRegex(common.Error, 'Unexpected data source list resource'):
                legacy_html._patch_sources_scroll(source)

    def test_scroll_bar_step_refuses_an_unexpected_output(self):
        source, _, _, guards = self.scroll_fixture(len(legacy_html._SOURCES_SCROLL_HOOK))
        with guards, patch.object(legacy_html, 'UI_2159_1231_PATCHED_SHA256', '0' * 64):
            with self.assertRaisesRegex(common.Error, 'Unexpected data source scroll bar assembly output'):
                legacy_html._patch_sources_scroll(source)


if __name__ == '__main__':
    unittest.main()
