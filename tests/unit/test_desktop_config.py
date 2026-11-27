# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, patches, provision

CONFIG = (b'<?xml version="1.0" encoding="utf-8"?>\r\n<configuration>\r\n'
          b'  <startup useLegacyV2RuntimeActivationPolicy="true">\r\n'
          b'    <supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.7.2" />\r\n'
          b'  </startup>\r\n  <runtime>\r\n'
          b'    <assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1" />\r\n'
          b'  </runtime>\r\n</configuration>\r\n')


class DesktopConfigTests(unittest.TestCase):
    def test_manager_is_named_first_in_the_runtime_section(self):
        patched = patches.patch_config(CONFIG)
        self.assertEqual(patched, CONFIG.replace(
            b'  <runtime>\r\n',
            b'  <runtime>\r\n'
            b'    <appDomainManagerAssembly value="PowerBICompositionManager" />\r\n'
            b'    <appDomainManagerType value="CompositionManager" />\r\n'))

    def test_line_endings_follow_the_file(self):
        source = CONFIG.replace(b'\r\n', b'\n')
        self.assertNotIn(b'\r', patches.patch_config(source))

    def test_unexpected_configurations_are_refused(self):
        for source in (patches.patch_config(CONFIG),
                       CONFIG.replace(b'  <runtime>\r\n', b''),
                       CONFIG.replace(b'</configuration>', b'<runtime>\r\n</runtime></configuration>')):
            with self.assertRaises(common.Error):
                patches.patch_config(source)


    def test_a_short_copy_is_refused(self):
        # An interrupted backup keeps the <runtime> line but no longer parses.
        with self.assertRaisesRegex(common.Error, 'Incomplete or damaged Desktop configuration'):
            patches.patch_config(CONFIG[:CONFIG.index(b'</runtime>')])

    def test_backup_is_renamed_into_place_only_when_complete(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            source, backup = Path(directory) / 'source', Path(directory) / 'originals' / 'name'
            source.write_bytes(CONFIG)
            def interrupted(src, dst):
                Path(dst).write_bytes(CONFIG[:10])
                raise KeyboardInterrupt
            with patch.object(patches.shutil, 'copy2', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    patches._backup(source, backup)
            self.assertFalse(backup.exists())
            patches._backup(source, backup)
            self.assertEqual(backup.read_bytes(), CONFIG)
            self.assertEqual(sorted(p.name for p in backup.parent.iterdir()), ['name'])

class DesktopConfigChecksumTests(unittest.TestCase):
    """Rule 5: PBIDesktop.exe.config is changed only when its exact original is known."""

    def install(self, recipe, config, backup=None, configs=None):
        """Run patches.install on synthetic files with every Wine step stubbed."""
        import tempfile
        from unittest.mock import patch
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        prefix = Path(directory.name)
        app = prefix / provision.BIN
        app.mkdir(parents=True)
        (prefix / 'runtime/helpers').mkdir(parents=True)
        originals = {}
        for name in patches.ORIGINALS:
            (app / name).write_bytes(('synthetic ' + name).encode())
            originals[name] = common.digest(app / name)
        document = app / patches.text_pickers.DOCUMENT
        document.parent.mkdir(parents=True)
        document.write_bytes(b'synthetic editor')
        (app / patches.DESKTOP_CONFIG).write_bytes(config)
        if backup is not None:
            (prefix / 'powerbi-linux-originals').mkdir()
            (prefix / 'powerbi-linux-originals' / patches.DESKTOP_CONFIG).write_bytes(backup)
        with (patch.object(patches, recipe, originals),
              patch.object(patches, 'CONFIG_ORIGINALS', configs or patches.CONFIG_ORIGINALS),
              patch.object(patches.legacy_html, 'patch_ui', return_value=b'ui'),
              patch.object(patches.options_show, 'patch_ui', return_value=b'ui'),
              patch.object(patches.dialog_serializers, 'patch_ui', return_value=b'ui'),
              patch.object(patches.signin, 'patch_windows', return_value=b'desktop'),
              patch.object(patches.autorecovery, 'patch_windows', return_value=b'desktop'),
              patch.object(patches.text_pickers, 'patch_document', return_value=b'editor'),
              patch.object(patches.tooltips, 'patch_document', return_value=b'tooltips'),
              patch.object(patches, 'build_native_dialog'), patch.object(patches, 'build_cache_compatibility'),
              patch.object(patches, 'build_window_frame'), patch.object(patches.signin, 'configure_browser'),
              patch.object(patches, 'self_token', return_value=b'server'),
              patch.object(patches, 'run', side_effect=self.run_tool)):
            results = patches.install(prefix, prefix / 'runtime', prefix / 'setup.log')
        return prefix, app, results

    @staticmethod
    def run_tool(command, **kwargs):
        # The helper DLLs exist, and each patcher writes its output (the fourth argument).
        helpers = Path(str(command[1])).parent
        if helpers.name == 'powerbi-linux-setup':
            for name in ('WinRTStubs.dll', 'PowerBIDiagnostics.dll', 'PowerBICompositionManager.dll',
                         patches.NATIVE_DIALOG, patches.CACHE_COMPAT, patches.WINDOW_FRAME):
                (helpers / name).write_bytes(b'helper')
        if len(command) > 3 and str(command[3]).startswith('Z:'):
            Path(str(command[3])[2:].replace(chr(92), '/')).write_bytes(b'patched')

    def test_verified_builds_refuse_an_unknown_configuration(self):
        for recipe in ('ORIGINALS_2160', 'ORIGINALS_2159_1231'):
            with self.subTest(recipe), self.assertRaisesRegex(common.Error, 'Checksum verification failed'):
                self.install(recipe, CONFIG)

    def test_verified_builds_name_the_manager_in_a_known_configuration(self):
        import hashlib
        known = {'2.160.1151.0': hashlib.sha256(CONFIG).hexdigest()}
        prefix, app, results = self.install('ORIGINALS_2160', CONFIG, configs=known)
        self.assertEqual((app / patches.DESKTOP_CONFIG).read_bytes(), patches.patch_config(CONFIG))
        self.assertEqual((prefix / 'powerbi-linux-originals' / patches.DESKTOP_CONFIG).read_bytes(), CONFIG)
        self.assertEqual(results[patches.DESKTOP_CONFIG], common.digest(app / patches.DESKTOP_CONFIG))

    def test_unverified_builds_keep_their_configuration(self):
        for recipe in ('ORIGINALS', 'CURRENT_ORIGINALS'):
            with self.subTest(recipe):
                prefix, app, results = self.install(recipe, CONFIG)
                self.assertEqual((app / patches.DESKTOP_CONFIG).read_bytes(), CONFIG)
                self.assertFalse((prefix / 'powerbi-linux-originals' / patches.DESKTOP_CONFIG).exists())
                self.assertNotIn(patches.DESKTOP_CONFIG, results)

    def test_an_unverified_build_gets_its_original_configuration_back(self):
        # An earlier repair changed it before the checksum was required.
        prefix, app, results = self.install('ORIGINALS', patches.patch_config(CONFIG), backup=CONFIG)
        self.assertEqual((app / patches.DESKTOP_CONFIG).read_bytes(), CONFIG)
        self.assertNotIn(patches.DESKTOP_CONFIG, results)

    def test_only_the_verified_builds_have_a_configuration_checksum(self):
        self.assertEqual(sorted(patches.CONFIG_ORIGINALS), ['2.159.1231.0', '2.160.1151.0'])
        self.assertEqual(patches.config_original(patches.ORIGINALS_2160), patches.CONFIG_ORIGINALS['2.160.1151.0'])
        self.assertEqual(patches.config_original(patches.ORIGINALS_2159_1231),
                         patches.CONFIG_ORIGINALS['2.159.1231.0'])
        self.assertIsNone(patches.config_original(patches.ORIGINALS))
        self.assertIsNone(patches.config_original(patches.CURRENT_ORIGINALS))


if __name__ == '__main__':
    unittest.main()
