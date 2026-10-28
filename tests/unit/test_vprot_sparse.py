# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the exact helper shipped in the Wine patch, without Wine or reports."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
NAME = 'wine-11.18-vprot-sparse-zero.patch'


class SparseVprotTests(unittest.TestCase):
    def test_patch_is_in_preparation_and_hash_registry(self):
        tree = ast.parse((ROOT / 'runtime/build.py').read_text())
        patches = next(ast.literal_eval(node.value) for node in tree.body
                       if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'WINE_PATCHES' for t in node.targets))
        self.assertIn(NAME, patches)
        patch = ROOT / 'runtime/patches' / NAME
        registry = json.loads((ROOT / 'runtime/patches.lock.json').read_text())
        self.assertEqual(registry[NAME], hashlib.sha256(patch.read_bytes()).hexdigest())

    @unittest.skipUnless(shutil.which('gcc'), 'native gcc needed for Linux madvise harness')
    def test_helper_boundaries_nonzero_and_failure_fallback(self):
        patch = (ROOT / 'runtime/patches' / NAME).read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        start = added.index('static void fill_page_vprot(')
        end = added.index('\n}', start) + 2
        helper = added[start:end]
        harness = (ROOT / 'tests/fixtures/vprot-fill-harness.c').read_text()
        self.assertEqual(harness.count('/* CANDIDATE_HELPER */'), 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'harness.c'
            exe = Path(directory) / 'harness'
            source.write_text(harness.replace('/* CANDIDATE_HELPER */', helper))
            subprocess.run(['gcc', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(exe)],
                           check=True, capture_output=True, timeout=30)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=30)
            self.assertIn('PASS differential_cases=6360', result.stdout)


if __name__ == '__main__':
    unittest.main()
