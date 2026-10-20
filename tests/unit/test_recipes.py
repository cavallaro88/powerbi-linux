# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, legacy_html, launch, patches, provision, recipes


class VersionedRecipeTests(unittest.TestCase):
    def test_official_installer_hash_selects_its_recipe(self):
        default = recipes.powerbi('2.159.883.0')
        for version in ('2.158.1177.0', '2.159.883.0'):
            source = recipes.powerbi(version)
            self.assertEqual(recipes.installer(source['sha256'], default)['version'], version)
        with self.assertRaisesRegex(common.Error, 'Unsupported Power BI installer'):
            recipes.installer('a' * 64, default)

    def test_recipe_entries_cannot_be_modified_by_a_caller(self):
        entry = recipes.powerbi('2.159.883.0')
        entry['version'] = 'different'
        self.assertEqual(recipes.powerbi('2.159.883.0')['version'], '2.159.883.0')

    def test_html_integrity_is_selected_per_installed_version(self):
        self.assertEqual(legacy_html.patched_hash('2.158.1177.0'), legacy_html.UI_PATCHED_SHA256)
        self.assertEqual(legacy_html.patched_hash('2.159.883.0'), legacy_html.UI_2159_PATCHED_SHA256)
        with self.assertRaises(common.Error):
            legacy_html.patched_hash('unknown')
        with self.assertRaisesRegex(common.Error, 'Unsupported 2.159'):
            legacy_html.patch_ui_2159(b'wrong assembly')

    def test_mixed_application_versions_fail_before_any_application_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            app = prefix / provision.BIN
            app.mkdir(parents=True)
            inputs = {}
            for name in patches.CURRENT_ORIGINALS:
                path = app / name
                path.write_bytes(('synthetic current ' + name).encode())
                inputs[name] = common.digest(path)
            registered = dict(inputs)
            registered['Microsoft.Mashup.Client.UI.dll'] = 'a' * 64
            with patch.object(patches, 'CURRENT_ORIGINALS', registered):
                with self.assertRaisesRegex(common.Error, 'Checksum verification failed'):
                    patches.install(prefix, Path('/runtime'), prefix / 'log')
            self.assertEqual(list((prefix / 'powerbi-linux-originals').iterdir()), [])
            for name, expected in inputs.items():
                self.assertEqual(common.digest(app / name), expected)

    def test_supported_app_version_is_independent_of_runtime_default_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            common.atomic_json(runtime / 'runtime.json', {'sources': {'powerbi': recipes.powerbi('2.159.883.0')}})
            provision.require_recipe({'powerbi_version': '2.158.1177.0', 'recipe_id': 'powerbi-2.158.1177.0'}, runtime)
            with self.assertRaises(common.Error):
                provision.require_recipe({'powerbi_version': 'unregistered'}, runtime)
            with self.assertRaises(common.Error):
                provision.require_recipe({'powerbi_version': '2.158.1177.0', 'recipe_id': 'foreign'}, runtime)

    def test_qa_services_are_separate_and_default_service_keeps_its_name(self):
        default = Path.home() / '.local/share/powerbi-linux'
        self.assertEqual(launch.session_unit(default), 'pbi-linux-session.service')
        with tempfile.TemporaryDirectory() as directory:
            first = launch.session_unit(Path(directory) / 'first')
            second = launch.session_unit(Path(directory) / 'second')
            self.assertNotEqual(first, second)
            self.assertNotEqual(first, launch.session_unit(default))
            self.assertEqual(first, launch.session_unit(Path(directory) / 'first'))
            self.assertRegex(first, r'^pbi-linux-session-[a-f0-9]{16}\.service$')

    def test_private_installations_share_desktop_ipc_without_sharing_session_sockets(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(base / 'desktop-run'),
                                         'XDG_DATA_HOME': str(base / 'first')}):
                first = common.Paths()
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(base / 'desktop-run'),
                                         'XDG_DATA_HOME': str(base / 'second')}):
                second = common.Paths()
            self.assertEqual(first.session.parent, base / 'desktop-run')
            self.assertEqual(second.session.parent, base / 'desktop-run')
            self.assertNotEqual(first.socket, second.socket)
            self.assertNotEqual(first.session / 'maintenance.lock', second.session / 'maintenance.lock')


if __name__ == '__main__':
    unittest.main()
