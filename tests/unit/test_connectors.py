# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import json
from types import SimpleNamespace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import connectors, common, provision


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'provider.nupkg'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('lib/net48/MySql.Data.dll', b'synthetic provider fixture')
        self.package = {'id': 'MySql.Data', 'url': 'https://example.invalid/provider.nupkg', 'sha256': common.digest(self.archive),
                        'assembly': 'lib/net48/MySql.Data.dll',
                        'assembly_sha256': hashlib.sha256(b'synthetic provider fixture').hexdigest()}
        self.recipe = {'schema': 1, 'connector': 'mysql', 'version': '8.0.33', 'packages': [self.package]}

    def test_corrupted_package_is_rejected_before_extracting(self):
        self.archive.write_bytes(b'corrupted download')
        target = self.root / 'out'
        target.mkdir()
        with self.assertRaises(common.Error):
            connectors.extract({'MySql.Data': self.archive}, self.recipe, target)
        self.assertEqual(list(target.iterdir()), [])

    def test_traversal_member_cannot_escape_staging(self):
        self.package['assembly'] = '../escape.dll'
        with self.assertRaisesRegex(common.Error, 'Unsafe provider'):
            connectors.extract({'MySql.Data': self.archive}, self.recipe, self.root)
        self.assertFalse((self.root.parent / 'escape.dll').exists())

    def test_incorrect_assembly_hash_is_rejected(self):
        self.package['assembly_sha256'] = '0' * 64
        with self.assertRaisesRegex(common.Error, 'assembly checksum'):
            connectors.extract({'MySql.Data': self.archive}, self.recipe, self.root)
        self.assertFalse((self.root / 'MySql.Data.dll').exists())

    def test_external_and_broken_symlink_providers_are_not_owned(self):
        provider = self.root / connectors.PROVIDERS
        provider.mkdir(parents=True)
        (provider / 'MySql.config').symlink_to(self.root / 'missing')
        self.assertEqual(connectors.status(self.root)['state'], 'external')

    def test_uninstalled_optional_provider_does_not_fail(self):
        self.assertEqual(connectors.status(self.root)['state'], 'not-installed')

    def test_vendor_global_registration_is_detected_without_private_folder(self):
        config = self.root / 'drive_c/windows/Microsoft.NET/Framework64/v4.0.30319/Config/machine.config'
        config.parent.mkdir(parents=True)
        config.write_bytes(connectors.configuration('8.0.33'))
        self.assertEqual(connectors.status(self.root)['state'], 'external')

    def test_managed_registration_tampering_is_detected(self):
        provider = self.root / connectors.PROVIDERS
        provider.mkdir(parents=True)
        file = provider / 'MySql.config'
        file.write_bytes(connectors.configuration('8.0.33'))
        common.atomic_json(self.root / connectors.STATE, {'schema': 1, 'connector': 'mysql', 'version': '8.0.33',
                          'files': {'MySql.config': common.digest(file)}})
        self.assertTrue(connectors.status(self.root)['verified'])
        file.write_text('changed registration')
        with self.assertRaises(common.Error):
            connectors.status(self.root)

    def test_busy_session_prevents_downloads_or_installation(self):
        paths = common.Paths()
        with patch.object(paths, 'lock', return_value=self._lock()), \
                patch.object(connectors, 'recipe', return_value=self.recipe), \
                patch.object(provision, 'idle', side_effect=common.Error('busy')), \
                patch.object(connectors.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'busy'):
                connectors.install(paths, accept_license=True)
            download.assert_not_called()

    def test_activation_failure_removes_only_new_connector_files(self):
        prefix = self.root / 'prefix'
        provider = prefix / connectors.PROVIDERS
        provider.mkdir(parents=True)
        unrelated = provider / 'OtherVendor.config'
        unrelated.write_text('preserve unrelated provider')
        paths = SimpleNamespace(cache=self.root / 'cache', lock=self._lock)
        with patch.object(connectors, 'recipe', return_value=self.recipe), \
                patch.object(provision, 'idle'), \
                patch.object(provision, 'active', return_value={'prefix': str(prefix)}), \
                patch.object(connectors.assets, 'download', return_value=self.archive), \
                patch.object(connectors, 'atomic_json', side_effect=common.Error('activation failed')):
            with self.assertRaisesRegex(common.Error, 'activation failed'):
                connectors.install(paths, accept_license=True)
        self.assertEqual(unrelated.read_text(), 'preserve unrelated provider')
        self.assertFalse((provider / 'MySql').exists())
        self.assertFalse((provider / 'MySql.config').exists())
        self.assertFalse((prefix / connectors.STATE).exists())

    @staticmethod
    def _lock():
        import contextlib
        return contextlib.nullcontext()


if __name__ == '__main__':
    unittest.main()
