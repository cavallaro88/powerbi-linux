# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
from itertools import permutations
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, legacy_html, launch, patches, provision, recipes


class VersionedRecipeTests(unittest.TestCase):
    def test_official_installer_hash_selects_its_recipe(self):
        default = recipes.powerbi('2.160.1151.0')
        for version in recipes.POWERBI:
            source = recipes.powerbi(version)
            self.assertEqual(recipes.installer(source['sha256'], default)['version'], version)
        with self.assertRaisesRegex(common.Error, 'Unsupported Power BI installer'):
            recipes.installer('a' * 64, default)

    def test_only_the_default_recipe_has_a_download(self):
        # The unversioned Microsoft URL is replaced in place by each build.
        lock = common.read_json(Path(__file__).resolve().parents[2] / 'runtime/sources.lock.json')
        self.assertEqual(lock['powerbi'], recipes.powerbi('2.160.1151.0'))
        self.assertNotIn('url', recipes.powerbi('2.159.1231.0'))
        self.assertNotIn('url', recipes.powerbi('2.159.883.0'))
        self.assertNotIn('url', recipes.powerbi('2.158.1177.0'))

    def test_each_recipe_guards_one_complete_set_of_originals(self):
        self.assertEqual(set(patches.RECIPES), set(recipes.POWERBI))
        windows = 'Microsoft.PowerBI.Client.Windows.dll'
        for version, originals in patches.RECIPES.items():
            with self.subTest(version=version):
                self.assertEqual(set(originals), set(patches.ORIGINALS))
                self.assertIs(patches.originals_for(originals[windows]), originals)
        self.assertIs(patches.originals_for('a' * 64), patches.ORIGINALS)
        self.assertEqual(patches.ORIGINALS_2159_1231['msmdsrv.exe'], patches.CURRENT_ORIGINALS['msmdsrv.exe'])

    def test_recipe_entries_cannot_be_modified_by_a_caller(self):
        entry = recipes.powerbi('2.159.883.0')
        entry['version'] = 'different'
        self.assertEqual(recipes.powerbi('2.159.883.0')['version'], '2.159.883.0')

    def test_html_integrity_is_selected_per_installed_version(self):
        self.assertEqual(legacy_html.patched_hash('2.158.1177.0'), legacy_html.UI_PATCHED_SHA256)
        self.assertEqual(legacy_html.patched_hash('2.159.883.0'), legacy_html.UI_2159_PATCHED_SHA256)
        self.assertEqual(legacy_html.patched_hash('2.159.1231.0'), legacy_html.UI_2159_1231_PATCHED_SHA256)
        self.assertEqual(legacy_html.patched_hash('2.160.1151.0'), legacy_html.UI_2160_PATCHED_SHA256)
        self.assertEqual(len({legacy_html.UI_PATCHED_SHA256, legacy_html.UI_2159_PATCHED_SHA256,
                              legacy_html.UI_2159_1231_PATCHED_SHA256, legacy_html.UI_2160_PATCHED_SHA256}), 4)
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

    def test_supported_builds_reject_each_others_files(self):
        windows = 'Microsoft.PowerBI.Client.Windows.dll'
        names = ('ORIGINALS', 'CURRENT_ORIGINALS', 'ORIGINALS_2159_1231', 'ORIGINALS_2160')
        for selected, other in permutations(names, 2):
            with self.subTest(selected=selected, other=other), tempfile.TemporaryDirectory() as directory:
                prefix = Path(directory)
                app = prefix / provision.BIN
                app.mkdir(parents=True)
                first, second = {}, {}
                for name in patches.ORIGINALS:
                    path = app / name
                    path.write_bytes(('first build ' + name).encode())
                    first[name] = common.digest(path)
                    path.write_bytes(('second build ' + name).encode())
                    second[name] = common.digest(path)
                # The Desktop assembly of one build beside the other build's files.
                (app / windows).write_bytes(('first build ' + windows).encode())
                with patch.object(patches, selected, first), patch.object(patches, other, second):
                    self.assertIs(patches.originals_for(first[windows]), first)
                    with self.assertRaisesRegex(common.Error, 'Checksum verification failed'):
                        patches.install(prefix, Path('/runtime'), prefix / 'log')
                self.assertEqual(list((prefix / 'powerbi-linux-originals').iterdir()), [])
                self.assertEqual(common.digest(app / windows), first[windows])

    def test_supported_app_version_is_independent_of_runtime_default_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            common.atomic_json(runtime / 'runtime.json', {'sources': {'powerbi': recipes.powerbi('2.159.883.0')}})
            provision.require_recipe({'powerbi_version': '2.158.1177.0', 'recipe_id': 'powerbi-2.158.1177.0'}, runtime)
            provision.require_recipe({'powerbi_version': '2.160.1151.0', 'recipe_id': 'powerbi-2.160.1151.0'}, runtime)
            with self.assertRaises(common.Error):
                provision.require_recipe({'powerbi_version': 'unregistered'}, runtime)
            with self.assertRaises(common.Error):
                provision.require_recipe({'powerbi_version': '2.158.1177.0', 'recipe_id': 'foreign'}, runtime)

    def test_new_cli_stages_its_winrt_shim_over_an_older_runtime_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix, runtime = root / 'prefix', root / 'runtime'
            app = prefix / provision.BIN
            app.mkdir(parents=True)
            originals = {}
            for name in patches.ORIGINALS:
                (app / name).write_bytes(('synthetic ' + name).encode())
                originals[name] = common.digest(app / name)
            document = app / patches.text_pickers.DOCUMENT
            document.parent.mkdir(parents=True)
            document.write_bytes(b'synthetic editor')
            (app / patches.DESKTOP_CONFIG).write_bytes(b'synthetic config')
            (runtime / 'helpers').mkdir(parents=True)
            (runtime / 'helpers/WinRTStubs.cs').write_text('obsolete runtime shim')
            with (patch.object(patches, 'ORIGINALS_2160', originals),
                  patch.object(patches, 'CONFIG_ORIGINALS', {'2.160.1151.0': common.digest(app / patches.DESKTOP_CONFIG)}),
                  patch.object(patches, 'patch_config', return_value=b'config'),
                  patch.object(patches.legacy_html, 'patch_ui', return_value=b'ui'),
                  patch.object(patches.dialog_serializers, 'patch_ui', side_effect=lambda data: data),
                  patch.object(patches.options_show, 'patch_ui', side_effect=lambda data: data),
                  patch.object(patches.signin, 'patch_windows', return_value=b'desktop'),
                  patch.object(patches.autorecovery, 'patch_windows', side_effect=lambda data: data),
                  patch.object(patches.text_pickers, 'patch_document', return_value=b'editor'),
                  patch.object(patches.tooltips, 'patch_document', return_value=b'tooltips'),
                  patch.object(patches, 'run', side_effect=RuntimeError('stop before invoking Wine'))):
                with self.assertRaisesRegex(RuntimeError, 'stop before invoking Wine'):
                    patches.install(prefix, runtime, root / 'setup.log')
            staged = prefix / 'drive_c/powerbi-linux-setup/WinRTStubs.cs'
            current = Path(patches.__file__).resolve().parents[1] / 'helpers/WinRTStubs.cs'
            self.assertEqual(staged.read_bytes(), current.read_bytes())
            self.assertNotEqual(staged.read_bytes(), (runtime / 'helpers/WinRTStubs.cs').read_bytes())

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
