# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from pbi_linux import build_provenance as provenance


class BuildProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('runtime/patches', 'src/helpers', 'src/pbi_linux', 'LICENSES',
                     'sources/wine', 'sources/dxvk', 'sources/dnlib', 'dist/runtime/bin'):
            (self.root / name).mkdir(parents=True)
        for name in ('LICENSE', 'src/helpers/helper.cs', 'src/pbi_linux/build_provenance.py',
                     'runtime/build-inside.sh', 'sources/wine/source.c', 'sources/dxvk/source.cpp',
                     'sources/dnlib/library', 'dist/runtime/bin/wine'):
            (self.root / name).write_text('original')
        (self.root / 'runtime/patches/fix.patch').write_text('reviewed')
        self.registry()

    def registry(self):
        value = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (self.root / 'runtime/patches').glob('*.patch')}
        (self.root / 'runtime/patches.lock.json').write_text(json.dumps(value))

    def successful(self):
        started = provenance.begin(self.root, '0.1.4', 'image-a')
        provenance.record_success(self.root, started)

    def test_unknown_or_modified_patch_is_rejected(self):
        (self.root / 'runtime/patches/diagnostic.patch').write_text('forgotten')
        with self.assertRaises(SystemExit): provenance.reviewed_patches(self.root)
        (self.root / 'runtime/patches/diagnostic.patch').unlink()
        (self.root / 'runtime/patches/fix.patch').write_text('changed')
        with self.assertRaises(SystemExit): provenance.reviewed_patches(self.root)

    def test_git_untracked_or_dirty_patches_are_rejected(self):
        def git(*args):
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True,
                           env=dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1'))
        git('init')
        with self.assertRaises(SystemExit): provenance.reviewed_patches(self.root)
        git('add', 'runtime')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'Reviewed fixture')
        provenance.reviewed_patches(self.root)
        (self.root / 'runtime/patches/fix.patch').write_text('changed')
        self.registry()
        with self.assertRaises(SystemExit): provenance.reviewed_patches(self.root)

    def test_failed_new_build_invalidates_previous_success(self):
        self.successful()
        provenance.begin(self.root, '0.1.4', 'image-a')
        with self.assertRaises(SystemExit): provenance.verify(self.root, '0.1.4', 'image-a')

    def test_version_builder_and_source_changes_invalidate_receipt(self):
        self.successful()
        provenance.verify(self.root, '0.1.4', 'image-a')
        for version, image in [('0.1.5', 'image-a'), ('0.1.4', 'image-b')]:
            with self.assertRaises(SystemExit): provenance.verify(self.root, version, image)
        (self.root / 'sources/wine/source.c').write_text('edited without updating marker')
        with self.assertRaises(SystemExit): provenance.verify(self.root, '0.1.4', 'image-a')

    def test_inputs_changed_during_build_cannot_record_success(self):
        started = provenance.begin(self.root, '0.1.4', 'image-a')
        (self.root / 'src/helpers/helper.cs').write_text('changed')
        with self.assertRaises(SystemExit): provenance.record_success(self.root, started)
        self.assertFalse((self.root / 'build/runtime-build-success.json').exists())

    def test_payload_tampering_and_unknown_extra_file_are_rejected(self):
        self.successful()
        extra = self.root / 'dist/runtime/debug.dll'
        extra.write_text('forgotten')
        with self.assertRaises(SystemExit): provenance.verify(self.root, '0.1.4', 'image-a')
        extra.unlink()
        (self.root / 'dist/runtime/bin/wine').write_text('replaced')
        with self.assertRaises(SystemExit): provenance.verify(self.root, '0.1.4', 'image-a')

    def test_packaging_metadata_allows_repeat_packaging(self):
        self.successful()
        (self.root / 'dist/runtime/licenses').mkdir()
        (self.root / 'dist/runtime/licenses/project.txt').write_text('notice')
        (self.root / 'dist/runtime/runtime.json').write_text('{}')
        provenance.verify(self.root, '0.1.4', 'image-a')

    def test_external_symlink_input_cannot_escape_the_fingerprint(self):
        (self.root / 'sources/wine/external').symlink_to(self.root / 'LICENSE')
        with self.assertRaises(SystemExit): provenance.begin(self.root, '0.1.4', 'image-a')


if __name__ == '__main__':
    unittest.main()
