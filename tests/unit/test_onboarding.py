# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import cli, common, onboarding, provision


class GuidedSetupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.payload = self.root / 'downloaded Power BI São Paulo.exe'
        self.payload.write_bytes(b'synthetic verified input')
        self.sha = common.digest(self.payload)
        env = patch.dict(os.environ, {f'XDG_{name}_HOME': str(self.root / name.lower())
                         for name in ('DATA', 'CONFIG', 'CACHE', 'STATE')})
        env.start()
        self.addCleanup(env.stop)
        self.paths = common.Paths()
        self.lock = {'powerbi': {'version': '2.158.1177.0', 'sha256': self.sha},
                     'webview2': {'runtime_version': '154.0.4258.62', 'sha256': self.sha},
                     'dotnet40': {'sha256': self.sha}, 'dotnet48': {'sha256': self.sha}}
        base = 'https://github.com/cavallaro88/powerbi-linux/releases/download/runtime-v1.0.0/'
        self.manifest = {'schema': 1, 'status': 'ready', 'powerbi': {
            **self.lock['powerbi'], 'url': 'https://download.microsoft.com/fixed/PowerBI.exe'},
            'runtime': {'version': '1.0.0', 'sha256': self.sha, 'url': base + 'runtime.tar.xz',
                        'source_url': base + 'sources.tar.xz', 'evidence_url': base + 'evidence.json'}}
        for directory in ('runtime', 'packaging'):
            (self.root / directory).mkdir()
        (self.root / 'runtime/sources.lock.json').write_text(json.dumps(self.lock))
        self.save_manifest()
        resource = patch.object(provision, 'resource_root', return_value=self.root)
        resource.start()
        self.addCleanup(resource.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def save_manifest(self):
        (self.root / 'packaging/setup.json').write_text(json.dumps(self.manifest))

    def args(self, *options):
        return cli.parser().parse_args(['setup', *options])

    def local(self, *options):
        return self.args('--installer', str(self.payload), '--runtime', str(self.payload),
                         '--runtime-sha256', self.sha, *options)

    def test_setup_warns_about_silent_installers_before_downloads(self):
        output = io.StringIO()
        def download(*args):
            self.assertIn('several minutes', output.getvalue())
            self.assertIn('without terminal output', output.getvalue())
            self.assertIn('does not by itself mean setup has frozen', output.getvalue())
            return self.payload
        with contextlib.redirect_stdout(output), patch.object(onboarding.assets, 'download', side_effect=download):
            onboarding.prepare(self.paths, self.args('--accept-license'))

    def test_ready_release_downloads_pinned_inputs_and_keeps_original_args(self):
        args = self.args('--accept-license')
        with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
            resolved = onboarding.prepare(self.paths, args)
        self.assertEqual(download.call_count, 2)
        self.assertEqual(download.call_args_list[0].args[:2],
                         (self.manifest['runtime']['url'], self.sha))
        self.assertEqual(download.call_args_list[1].args[:2],
                         (self.manifest['powerbi']['url'], self.sha))
        self.assertEqual(resolved.runtime_sha256, self.sha)
        self.assertEqual(resolved.installer, str(self.payload))
        self.assertIsNone(args.installer)
        self.assertFalse(self.paths.active.exists())

    def test_unpublished_release_fails_before_download_or_acceptance(self):
        self.manifest.update(status='pending', reason='Runtime binary is not published', runtime=None)
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download, patch('builtins.input') as prompt:
            with self.assertRaisesRegex(common.Error, 'Runtime binary is not published'):
                onboarding.prepare(self.paths, self.args())
        download.assert_not_called()
        prompt.assert_not_called()

    def test_source_only_runtime_cannot_enable_automatic_setup(self):
        self.manifest['runtime']['source_url'] = 'https://github.com/cavallaro88/powerbi-linux/tree/main'
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'fixed project release assets'):
                onboarding.prepare(self.paths, self.args('--accept-license'))
        download.assert_not_called()

    def test_pending_release_preserves_fully_local_inputs_with_spaces_and_accents(self):
        self.manifest.update(status='pending', reason='no public binary', runtime=None)
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            resolved = onboarding.prepare(self.paths, self.local('--accept-license', '--make-default'))
        self.assertEqual(resolved.installer, str(self.payload))
        self.assertTrue(resolved.make_default)
        download.assert_not_called()

    def test_local_installer_only_downloads_the_runtime(self):
        with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
            onboarding.prepare(self.paths, self.args('--installer', str(self.payload), '--accept-license'))
        download.assert_called_once_with(self.manifest['runtime']['url'], self.sha, self.paths.cache / 'downloads')

    def test_explicit_runtime_can_download_official_installer_before_public_release(self):
        self.manifest.update(status='pending', runtime=None)
        self.save_manifest()
        with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
            resolved = onboarding.prepare(self.paths, self.args(
                '--runtime', str(self.payload), '--runtime-sha256', self.sha, '--accept-license'))
        download.assert_called_once_with(self.manifest['powerbi']['url'], self.sha, self.paths.cache / 'downloads')
        self.assertEqual(resolved.runtime, str(self.payload))

    def test_corrupt_local_runtime_cannot_start_installer_download_in_pending_release(self):
        self.manifest.update(status='pending', runtime=None)
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'Checksum'):
                onboarding.prepare(self.paths, self.args(
                    '--runtime', str(self.payload), '--runtime-sha256', 'a' * 64, '--accept-license'))
        download.assert_not_called()

    def test_explicit_runtime_requires_its_checksum(self):
        for options in [('--runtime', str(self.payload)), ('--runtime-sha256', self.sha)]:
            with self.subTest(options=options), patch.object(onboarding.assets, 'download') as download:
                with self.assertRaisesRegex(common.Error, 'together'):
                    onboarding.prepare(self.paths, self.args(*options))
                download.assert_not_called()

    def test_wrong_local_installer_rejected_before_runtime_download(self):
        bad = self.root / 'newer.exe'
        bad.write_bytes(b'unsupported newer Microsoft installer')
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'expected version 2.158.1177.0'):
                onboarding.prepare(self.paths, self.args('--installer', str(bad), '--accept-license'))
        download.assert_not_called()

    def test_wrong_runtime_or_offline_prerequisite_rejected_before_download(self):
        bad = self.root / 'wrong.cab'
        bad.write_bytes(b'wrong input')
        for args in [self.args('--runtime', str(bad), '--runtime-sha256', self.sha, '--accept-license'),
                     self.local('--webview-runtime', str(bad), '--accept-license')]:
            with patch.object(onboarding.assets, 'download') as download:
                with self.assertRaisesRegex(common.Error, 'Checksum'):
                    onboarding.prepare(self.paths, args)
                download.assert_not_called()

    def test_no_terminal_requires_explicit_license_acceptance(self):
        with patch.object(sys.stdin, 'isatty', return_value=False), patch('builtins.input') as prompt, \
                patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, '--accept-license'):
                onboarding.prepare(self.paths, self.args())
        prompt.assert_not_called()
        download.assert_not_called()

    def test_interactive_acceptance_and_refusal(self):
        for answer, accepted in [('yes', True), ('', False), ('no', False)]:
            with self.subTest(answer=answer), patch.object(sys.stdin, 'isatty', return_value=True), \
                    patch('builtins.input', return_value=answer), \
                    patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
                if accepted:
                    self.assertTrue(onboarding.prepare(self.paths, self.args()).accept_license)
                    self.assertEqual(download.call_count, 2)
                else:
                    with self.assertRaisesRegex(common.Error, 'canceled'):
                        onboarding.prepare(self.paths, self.args())
                    download.assert_not_called()

    def test_eof_or_interrupt_at_terms_cancels_without_download(self):
        for failure in (EOFError, KeyboardInterrupt):
            with patch.object(sys.stdin, 'isatty', return_value=True), \
                    patch('builtins.input', side_effect=failure), patch.object(onboarding.assets, 'download') as download:
                with self.assertRaisesRegex(common.Error, 'canceled'):
                    onboarding.prepare(self.paths, self.args())
                download.assert_not_called()

    def test_existing_profile_is_preserved_before_download(self):
        common.atomic_json(self.paths.active, {'sentinel': 'preserve existing installation'})
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'already installed'):
                onboarding.prepare(self.paths, self.args('--accept-license'))
        download.assert_not_called()
        self.assertEqual(common.read_json(self.paths.active)['sentinel'], 'preserve existing installation')

    def test_recipe_checksum_mismatch_blocks_release_selection(self):
        self.manifest['powerbi']['sha256'] = 'a' * 64
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'checksum differ'):
                onboarding.prepare(self.paths, self.args('--accept-license'))
        download.assert_not_called()

    def test_non_microsoft_installer_url_is_rejected(self):
        self.manifest['powerbi']['url'] = 'https://untrusted.example/PowerBI.exe'
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'download.microsoft.com'):
                onboarding.prepare(self.paths, self.args('--accept-license'))
        download.assert_not_called()

    def test_cli_passes_resolved_arguments_to_provisioning(self):
        resolved = self.local('--accept-license')
        with patch.object(cli, 'Paths', return_value=self.paths), \
                patch.object(onboarding, 'prepare', return_value=resolved) as prepare, \
                patch.object(provision, 'setup') as setup:
            self.assertEqual(cli.main(['setup', '--accept-license']), 0)
        self.assertIsNone(prepare.call_args.args[1].runtime)
        setup.assert_called_once_with(self.paths, resolved)

    def test_foreign_recipe_is_rejected_before_profile_snapshot(self):
        runtime = self.root / 'runtime-input'
        runtime.mkdir()
        common.atomic_json(runtime / 'runtime.json', {'sources': {'powerbi': {'version': 'new-unsupported'}}})
        with self.assertRaisesRegex(common.Error, 'recipe differs'):
            provision.require_recipe({}, runtime)

    def test_interrupted_setup_reports_how_to_resume_without_traceback(self):
        error = io.StringIO()
        with patch.object(cli, 'Paths', return_value=self.paths), \
                patch.object(onboarding, 'prepare', return_value=self.local('--accept-license')), \
                patch.object(provision, 'setup', side_effect=KeyboardInterrupt), \
                contextlib.redirect_stderr(error):
            self.assertEqual(cli.main(['setup', '--accept-license']), 130)
        self.assertIn('same inputs to resume', error.getvalue())
        self.assertNotIn('Traceback', error.getvalue())

    def test_legacy_profile_and_recorded_version_survive_activation(self):
        runtime = self.paths.data / 'runtimes/legacy'
        runtime.mkdir(parents=True)
        common.atomic_json(runtime / 'runtime.json', {'sources': {'powerbi': self.lock['powerbi']}})
        provision.require_recipe({}, runtime)
        prefix = self.paths.data / 'profiles/fixture'
        provision.activate(self.paths, prefix, runtime, {}, self.sha)
        metadata = common.read_json(self.paths.active)
        self.assertEqual(metadata['powerbi_version'], self.lock['powerbi']['version'])
        self.assertEqual(metadata['recipe_id'], 'powerbi-' + self.lock['powerbi']['version'])

    def update_args(self, *options):
        return cli.parser().parse_args(['update', *options])

    def test_update_uses_the_published_runtime_by_default(self):
        with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
            resolved = onboarding.update_inputs(self.paths, self.update_args())
        download.assert_called_once_with(self.manifest['runtime']['url'], self.sha,
                                         self.paths.cache / 'downloads')
        self.assertEqual(resolved.runtime, str(self.payload))
        self.assertEqual(resolved.runtime_sha256, self.sha)

    def test_update_requires_explicit_inputs_without_a_published_runtime(self):
        self.manifest.update(status='pending', reason='Runtime binary is not published', runtime=None)
        self.save_manifest()
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'Runtime binary is not published'):
                onboarding.update_inputs(self.paths, self.update_args())
        download.assert_not_called()

    def test_update_rejects_source_only_or_half_explicit_inputs(self):
        with patch.object(onboarding.assets, 'download') as download:
            with self.assertRaisesRegex(common.Error, 'together'):
                onboarding.update_inputs(self.paths, self.update_args('--runtime', str(self.payload)))
            with self.assertRaisesRegex(common.Error, 'together'):
                onboarding.update_inputs(self.paths, self.update_args('--runtime-sha256', self.sha))
        download.assert_not_called()
        self.manifest['runtime']['evidence_url'] = 'https://github.com/cavallaro88/powerbi-linux/tree/main'
        self.save_manifest()
        with self.assertRaisesRegex(common.Error, 'fixed project release assets'):
            onboarding.update_inputs(self.paths, self.update_args())

    def test_update_verifies_an_explicit_archive_before_activation(self):
        resolved = onboarding.update_inputs(self.paths, self.update_args(
            '--runtime', str(self.payload), '--runtime-sha256', self.sha))
        self.assertEqual(resolved.runtime, str(self.payload))
        with self.assertRaisesRegex(common.Error, 'Checksum'):
            onboarding.update_inputs(self.paths, self.update_args(
                '--runtime', str(self.payload), '--runtime-sha256', 'a' * 64))

    def install(self, version, sha):
        runtime = self.root / 'runtimes' / sha
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / 'runtime.json').write_text(json.dumps({'version': version}))
        self.paths.data.mkdir(parents=True, exist_ok=True)
        self.paths.active.write_text(json.dumps({'runtime': str(runtime), 'runtime_sha256': sha}))

    def test_update_does_not_replace_a_newer_or_local_runtime_unasked(self):
        # The published runtime here is 1.0.0. A local build can carry corrections
        # the published one lacks, and a default local build even reuses its label.
        # 'local' also sorts below published pre-releases (0.1.7-local.12 < 0.1.7-pr-integration.1),
        # so a local build is kept whatever its label's precedence.
        for version in ('1.0.1-local.1', '1.0.0', '1.1.0-beta.1', 'custom', None,
                        '1.0.0-local.12', '0.9.9-local.1', '0.9.9-rc.1.local.2+build.1'):
            self.install(version, 'b' * 64)
            with patch.object(onboarding.assets, 'download') as download:
                with self.assertRaisesRegex(common.Error, '--published'):
                    onboarding.update_inputs(self.paths, self.update_args())
            download.assert_not_called()
        with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
            resolved = onboarding.update_inputs(self.paths, self.update_args('--published'))
        download.assert_called_once()
        self.assertEqual(resolved.runtime_sha256, self.sha)
        with self.assertRaisesRegex(common.Error, 'not both'):
            onboarding.update_inputs(self.paths, self.update_args(
                '--published', '--runtime', str(self.payload), '--runtime-sha256', self.sha))

    def test_update_replaces_an_older_release_and_reapplies_the_published_one(self):
        for version, sha in (('0.9.9', 'b' * 64), ('1.0.0-beta.2', 'b' * 64), ('1.0.0', self.sha)):
            self.install(version, sha)
            with patch.object(onboarding.assets, 'download', return_value=self.payload) as download:
                onboarding.update_inputs(self.paths, self.update_args())
            download.assert_called_once()

    def test_runtime_labels_follow_semantic_version_precedence(self):
        labels = ['0.1.5', '0.1.6-beta.1', '0.1.6-beta.2', '0.1.6-beta.10', '0.1.6-rc.1', '0.1.6',
                  '0.1.7-local.6', '0.1.7', '0.2.0']
        order = [onboarding.runtime_order(label) for label in labels]
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(set(order)), len(order))
        self.assertEqual(onboarding.runtime_order('0.1.6+build.3'), onboarding.runtime_order('0.1.6'))
        for label in ('', None, 'latest', '1.0', '1.0.0.0'):
            self.assertIsNone(onboarding.runtime_order(label))

    def test_local_runtime_labels_are_recognised(self):
        for label in ('0.1.7-local.12', '0.1.7-local', '0.1.7-rc.1.local.2+build.1'):
            self.assertTrue(onboarding.locally_built(label), label)
        for label in ('0.1.7', '0.1.7-pr-integration.1', '0.1.7-locale.1', '0.1.7+local', '', None, 'local'):
            self.assertFalse(onboarding.locally_built(label), label)

    def test_replaced_microsoft_installer_is_explained(self):
        # Microsoft serves each new Desktop build from the same address.
        def download(url, sha, cache):
            if 'microsoft' in url:
                raise common.ChecksumError('Checksum verification failed: .download-abc123')
            return self.payload
        with patch.object(onboarding.assets, 'download', side_effect=download):
            with self.assertRaises(common.Error) as raised:
                onboarding.prepare(self.paths, self.args('--accept-license'))
        message = str(raised.exception)
        self.assertIn('2.158.1177.0', message)
        self.assertIn('--installer', message)
        self.assertIn(onboarding.DOWNLOAD_PAGE, message)
        self.assertNotIn('.download-', message)

    def test_interrupted_installer_download_keeps_its_own_message(self):
        def download(url, sha, cache):
            if 'microsoft' in url:
                raise common.Error('Download failed; check your connection and rerun setup')
            return self.payload
        with patch.object(onboarding.assets, 'download', side_effect=download):
            with self.assertRaisesRegex(common.Error, 'check your connection'):
                onboarding.prepare(self.paths, self.args('--accept-license'))
