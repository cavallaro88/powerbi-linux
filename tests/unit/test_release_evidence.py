# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('release_check', Path(__file__).resolve().parents[2] / 'tools/release-check.py')
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.runtime = Path(temp.name) / 'runtime.tar.xz'
        manifest = {'sources': {'powerbi': {'version': '2.159.883.0'},
                                'webview2': {'runtime_version': '154.0.4258.62'}}}
        payload = json.dumps(manifest).encode()
        with tarfile.open(self.runtime, 'w:xz') as archive:
            member = tarfile.TarInfo('runtime.json')
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        self.evidence = {'runtime_sha256': hashlib.sha256(self.runtime.read_bytes()).hexdigest(),
                         'powerbi_version': '2.159.883.0', 'webview2_version': '154.0.4258.62',
                         'fedora_version': '44', 'arch': 'x86_64', 'display': 'wayland',
                         'runtime_provenance': 'clean-source-build',
                         'cases': {name: {'status': 'passed', 'evidence': 'synthetic-proof'} for name in release_check.REQUIRED}}
        self.evidence['cases']['soak_2h']['seconds'] = 7200

    def test_complete_matching_tuple_is_accepted(self):
        self.assertEqual(release_check.validate(self.runtime, self.evidence), [])

    def test_old_application_evidence_cannot_certify_the_new_recipe(self):
        self.evidence['powerbi_version'] = '2.158.1177.0'
        self.assertTrue(any('powerbi_version' in e for e in release_check.validate(self.runtime, self.evidence)))

    def test_wrong_webview_or_missing_tuple_is_rejected(self):
        for key in ('powerbi_version', 'webview2_version'):
            evidence = copy.deepcopy(self.evidence)
            del evidence[key]
            self.assertTrue(any(key in e for e in release_check.validate(self.runtime, evidence)))

    def test_matching_versions_do_not_replace_native_scenarios_or_duration(self):
        self.evidence['cases']['clean_install']['status'] = 'pending'
        self.evidence['cases']['soak_2h']['seconds'] = 100
        errors = release_check.validate(self.runtime, self.evidence)
        self.assertTrue(any('clean_install' in e for e in errors))
        self.assertTrue(any('two hours' in e for e in errors))
