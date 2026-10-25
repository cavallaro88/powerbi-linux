# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import struct
import unittest

from pbi_linux.common import Error, read_json, check_digest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('odbc_bridge', ROOT / 'tools/redshift-odbc.py')
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class OdbcBridgeTest(unittest.TestCase):
    def setUp(self):
        self.recipe = read_json(BRIDGE.RECIPE)
        self.source = BRIDGE.DEFINITION.read_text()

    def test_reviewed_exports_cover_pinned_engine_without_private_stubs(self):
        check_digest(BRIDGE.DEFINITION, self.recipe['definition_sha256'])
        names = BRIDGE.exports(self.source, self.recipe)
        self.assertEqual(len(names), 170)
        self.assertEqual(len(self.recipe['required_engine_exports']), 38)
        self.assertNotIn('SQLCompleteAsync', names)
        self.assertNotIn('SQLCancelHandle', names)

    def test_redirected_export_is_rejected(self):
        source = self.source.replace('SQLAllocHandle=odbc32.SQLAllocHandle',
                                     'SQLAllocHandle=other.SQLAllocHandle')
        with self.assertRaisesRegex(Error, 'Only named exports'):
            BRIDGE.exports(source, self.recipe)

    def test_missing_required_export_or_duplicate_is_rejected(self):
        with self.assertRaisesRegex(Error, 'coverage'):
            BRIDGE.exports(self.source.replace('SQLAllocHandle=odbc32.SQLAllocHandle',
                                              'UnusedName=odbc32.UnusedName'), self.recipe)
        with self.assertRaisesRegex(Error, 'coverage'):
            BRIDGE.exports(self.source + '\nSQLAllocEnv=odbc32.SQLAllocEnv\n', self.recipe)

    def test_wrong_library_and_ordinal_alias_are_rejected(self):
        with self.assertRaises(Error):
            BRIDGE.exports(self.source.replace('LIBRARY PRIVATE_ODBC32', 'LIBRARY odbc32'), self.recipe)
        with self.assertRaises(Error):
            BRIDGE.exports(self.source + '\nSQLAsync=odbc32.SQLAsync @200\n', self.recipe)

    def test_pe_check_rejects_x86_entrypoints_non_dlls_and_truncation(self):
        data = bytearray(512)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 0x80)
        data[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<H', data, 0x84, 0x8664)
        struct.pack_into('<H', data, 0x96, 0x2000)
        struct.pack_into('<H', data, 0x98, 0x20b)
        BRIDGE.validate_pe(data)
        for offset, value in [(0x84, 0x14c), (0x96, 0), (0x98, 0x10b), (0xa8, 1)]:
            changed = bytearray(data)
            struct.pack_into('<H', changed, offset, value)
            with self.assertRaises(Error):
                BRIDGE.validate_pe(changed)
        with self.assertRaises(Error):
            BRIDGE.validate_pe(b'MZ')


if __name__ == '__main__':
    unittest.main()
