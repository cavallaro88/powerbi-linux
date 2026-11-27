# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, pe_cache

SECTION_OFFSET, SECTION_SIZE = 0x600, 16 * 1024**2 + 0x200


def synthetic_pe(path, fill=b'\x5a'):
    """One section large and unaligned enough to be cached, like msedge.dll's."""
    header = bytearray(SECTION_OFFSET)
    header[0:2] = b'MZ'
    struct.pack_into('<I', header, 0x3c, 0x80)
    header[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', header, 0x80 + 6, 1)
    struct.pack_into('<H', header, 0x80 + 20, 0)
    struct.pack_into('<IIII', header, 0x80 + 24 + 8, SECTION_SIZE, 0x1000, SECTION_SIZE, SECTION_OFFSET)
    path.write_bytes(bytes(header) + fill * SECTION_SIZE)


class PeCacheTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source, self.cache = self.root / 'msedge.dll', self.root / 'cache'
        synthetic_pe(self.source)

    def move_identity(self):
        # A new inode with the same bytes stands in for a new device number
        # after a reboot (btrfs numbers subvolumes when they are mounted).
        copy = self.root / 'copy.dll'
        shutil.copy2(self.source, copy)
        copy.replace(self.source)

    def bins(self):
        return sorted(p.name for p in self.cache.glob('*.bin*'))

    def test_prepared_cache_is_current(self):
        pe_cache.prepare(self.source, self.cache)
        self.assertEqual(pe_cache.status(self.source, self.cache), 'current')
        self.assertTrue(pe_cache.valid(self.source, self.cache))
        self.assertEqual(len(self.bins()), 1)

    def test_moved_source_is_renamed_not_left_stale(self):
        pe_cache.prepare(self.source, self.cache)
        before = self.bins()
        self.move_identity()
        self.assertFalse(pe_cache.valid(self.source, self.cache))
        self.assertEqual(pe_cache.status(self.source, self.cache), 'moved')
        self.assertTrue(pe_cache.refresh(self.source, self.cache))
        self.assertTrue(pe_cache.valid(self.source, self.cache))
        after = self.bins()
        self.assertEqual(len(after), 1)
        self.assertNotEqual(after, before)
        # The renamed file is still read-only, as Wine requires.
        self.assertFalse((self.cache / after[0]).stat().st_mode & 0o222)

    def test_changed_source_is_never_renamed(self):
        pe_cache.prepare(self.source, self.cache)
        synthetic_pe(self.source, fill=b'\x33')
        self.assertEqual(pe_cache.status(self.source, self.cache), 'stale')
        self.assertFalse(pe_cache.refresh(self.source, self.cache))

    def test_damaged_cache_file_is_never_used(self):
        pe_cache.prepare(self.source, self.cache)
        file = self.cache / self.bins()[0]
        file.chmod(0o600)
        with file.open('r+b') as stream:
            stream.seek(5000)
            stream.write(b'x')
        file.chmod(0o400)
        self.move_identity()
        self.assertEqual(pe_cache.status(self.source, self.cache), 'stale')
        self.assertFalse(pe_cache.refresh(self.source, self.cache))

    def test_rebuild_survives_a_read_only_leftover_and_drops_old_files(self):
        pe_cache.prepare(self.source, self.cache)
        old = self.bins()[0]
        self.move_identity()
        name = pe_cache.identity(self.source.stat(), SECTION_OFFSET, SECTION_SIZE)
        leftover = self.cache / (name + '.tmp')
        leftover.write_bytes(b'partial')
        leftover.chmod(0o400)
        pe_cache.prepare(self.source, self.cache)
        self.assertEqual(self.bins(), [name])
        self.assertNotEqual(name, old)
        self.assertTrue(pe_cache.valid(self.source, self.cache))

    def test_damaged_manifest_is_stale_not_an_exception(self):
        pe_cache.prepare(self.source, self.cache)
        manifest = common.read_json(self.cache / 'manifest.json')
        for offset in ('0x600', 1.5, None):
            with self.subTest(offset=offset):
                manifest['sections'][0]['offset'] = offset
                common.atomic_json(self.cache / 'manifest.json', manifest)
                self.assertEqual(pe_cache.status(self.source, self.cache), 'stale')
                self.assertFalse(pe_cache.refresh(self.source, self.cache))

    def test_a_link_left_by_an_interrupted_refresh_is_pruned(self):
        pe_cache.prepare(self.source, self.cache)
        leftover = self.cache / ('.' + self.bins()[0] + '.' + 'ab' * 16)
        leftover.write_bytes(b'x')
        self.move_identity()
        self.assertTrue(pe_cache.refresh(self.source, self.cache))
        self.assertFalse(leftover.exists())
        self.assertTrue((self.cache / 'manifest.json').exists())

    def test_refresh_waits_for_another_writer(self):
        import threading, time
        pe_cache.prepare(self.source, self.cache)
        self.move_identity()
        held, release = threading.Event(), threading.Event()
        def writer():
            with pe_cache._locked(self.cache):
                held.set()
                release.wait(5)
        thread = threading.Thread(target=writer)
        thread.start()
        held.wait(5)
        threading.Timer(0.5, release.set).start()
        started = time.monotonic()
        self.assertTrue(pe_cache.refresh(self.source, self.cache))
        self.assertGreaterEqual(time.monotonic() - started, 0.4)
        thread.join()
        self.assertTrue(pe_cache.valid(self.source, self.cache))

    def test_a_cache_that_cannot_be_written_is_used_as_it_is(self):
        pe_cache.prepare(self.source, self.cache)
        with patch.object(pe_cache, '_lock_file', side_effect=PermissionError):
            self.assertTrue(pe_cache.refresh(self.source, self.cache))
            self.move_identity()
            self.assertFalse(pe_cache.refresh(self.source, self.cache))

    def test_the_lock_file_is_private_and_kept(self):
        pe_cache.prepare(self.source, self.cache)
        self.move_identity()
        self.assertTrue(pe_cache.refresh(self.source, self.cache))
        self.assertEqual((self.cache / '.lock').stat().st_mode & 0o777, 0o600)

    def test_missing_manifest_is_stale(self):
        self.assertEqual(pe_cache.status(self.source, self.cache), 'stale')
        self.assertFalse(pe_cache.refresh(self.source, self.cache))
        self.assertRaises(common.Error, common.read_json, self.cache / 'manifest.json')


if __name__ == '__main__':
    unittest.main()
