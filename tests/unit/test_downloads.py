# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import hashlib
import http.client
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import assets, common


class DownloadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cache = Path(temp.name) / 'downloads'
        self.payload = b'complete verified download'
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.url = 'https://download.microsoft.com/fixture.exe'

    def response(self, payload=None, *, url=None, size=None):
        data = self.payload if payload is None else payload
        result = io.BytesIO(data)
        result.url = url or self.url
        result.headers = {} if size is None else {'Content-Length': str(size)}
        return result

    def test_verified_payload_is_reused_without_network(self):
        with patch.object(assets.urllib.request, 'urlopen', return_value=self.response()) as request:
            target = assets.download(self.url, self.sha, self.cache)
            self.assertEqual(target.read_bytes(), self.payload)
            self.assertEqual(assets.download(self.url, self.sha, self.cache), target)
        request.assert_called_once()
        self.assertEqual(list(self.cache.iterdir()), [target])

    def test_wrong_payload_removes_partial_file(self):
        with patch.object(assets.urllib.request, 'urlopen', return_value=self.response(b'wrong')):
            with self.assertRaisesRegex(common.Error, 'Checksum'):
                assets.download(self.url, self.sha, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_truncated_response_can_be_retried(self):
        short = self.response(b'incomplete', size=len(self.payload))
        with patch.object(assets.urllib.request, 'urlopen', side_effect=[short, self.response()]) as request:
            with self.assertRaisesRegex(common.Error, 'Incomplete download'):
                assets.download(self.url, self.sha, self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])
            self.assertEqual(assets.download(self.url, self.sha, self.cache).read_bytes(), self.payload)
        self.assertEqual(request.call_count, 2)

    def test_network_errors_are_actionable_and_leave_no_partial_file(self):
        for error in (URLError('connection unavailable'), TimeoutError(),
                      http.client.IncompleteRead(b'part', 20)):
            with self.subTest(error=error), patch.object(assets.urllib.request, 'urlopen', side_effect=error):
                with self.assertRaisesRegex(common.Error, 'check your connection and rerun setup'):
                    assets.download(self.url, self.sha, self.cache)
                self.assertEqual(list(self.cache.iterdir()), [])

    def test_insecure_download_and_redirect_are_rejected(self):
        with self.assertRaisesRegex(common.Error, 'HTTPS'):
            assets.download('http://example.com/fixture', self.sha, self.cache)
        with patch.object(assets.urllib.request, 'urlopen', return_value=self.response(url='http://example.com/fixture')):
            with self.assertRaisesRegex(common.Error, 'insecure'):
                assets.download(self.url, self.sha, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_progress_goes_to_stderr_without_corrupting_output(self):
        progress = io.StringIO()
        with patch.object(assets.urllib.request, 'urlopen', return_value=self.response(size=len(self.payload))), \
                patch.object(assets.time, 'monotonic', side_effect=[0, 3]), contextlib.redirect_stderr(progress):
            target = assets.download(self.url, self.sha, self.cache)
        self.assertIn('MiB /', progress.getvalue())
        self.assertEqual(target.read_bytes(), self.payload)

    def test_corrupted_cached_content_is_not_trusted(self):
        self.cache.mkdir()
        (self.cache / self.sha).write_bytes(b'tampered')
        with patch.object(assets.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(common.Error, 'Checksum'):
                assets.download(self.url, self.sha, self.cache)
        request.assert_not_called()
