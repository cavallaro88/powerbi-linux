# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, launch


class BrokerTests(unittest.TestCase):
    """The broker with Wine faked: one bad client must never end the session."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        variables = {'XDG_' + kind + '_HOME': str(root / kind.lower()) for kind in ('DATA', 'CONFIG', 'CACHE', 'STATE')}
        variables['XDG_RUNTIME_DIR'] = str(root / 'run')
        for value in variables.values():
            Path(value).mkdir()
        environment = patch.dict(os.environ, variables)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('XDG_CURRENT_DESKTOP', None)
        self.paths = common.Paths()
        self.prefix = self.paths.data / 'profiles/test'
        (self.prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin').mkdir(parents=True)
        self.report = root / 'My report & ü.pbix'
        self.report.write_bytes(b'report')
        self.desktops, self.wineserver, self.commands, self.desktop_env = [], [], [], []
        self.offset = 0.0

    def run_broker(self, client, diagnostics=False):
        def popen(args, **kwargs):
            self.desktop_env.append(kwargs.get('env') or {})
            process = subprocess.Popen(['sleep', '60'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.desktops.append(process)
            return process
        def run(args, **kwargs):
            self.wineserver.append(Path(str(args[0])).name)
        clock = types.SimpleNamespace(monotonic=lambda: time.monotonic() + self.offset, sleep=time.sleep)
        fake = types.SimpleNamespace(Popen=popen, run=run, DEVNULL=subprocess.DEVNULL,
                                     TimeoutExpired=subprocess.TimeoutExpired)
        installation = {'prefix': str(self.prefix), 'runtime': str(self.paths.data / 'runtimes/test'), 'patches': {}}
        result = {}
        def drive():
            try:
                while not self.paths.socket.exists():
                    time.sleep(.02)
                result['client'] = client()
            except BaseException as exc:  # noqa: BLE001 - reported by the assertion below
                result['error'] = exc
            finally:
                for process in self.desktops:
                    process.kill()
                    process.wait()
                self.offset = 1000.0  # past the idle grace period
        thread = threading.Thread(target=drive, daemon=True)
        with patch.object(launch, 'active', return_value=installation), \
                patch.object(launch, 'environment', return_value={'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS': '', 'WINEDEBUG': '-all'}), \
                patch.object(launch, 'run', side_effect=self.record), \
                patch.object(launch, 'subprocess', fake), patch.object(launch, 'time', clock):
            thread.start()
            launch.broker(self.paths, diagnostics)
        thread.join(10)
        self.assertNotIn('error', result, result.get('error'))
        return result['client']

    def record(self, args, **kwargs):
        self.commands.append([str(arg) for arg in args])
        return 'Z:\\report.pbix\n'

    def send(self, payload, *, wait=True):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(10)
            sock.connect(str(self.paths.socket))
            if payload is not None:
                sock.sendall(payload)
            if not wait:
                return None
            return json.loads(sock.makefile('rb').readline())

    def test_clients_that_leave_or_send_nonsense_do_not_end_the_session(self):
        def client():
            first = launch.request(self.paths, str(self.report))
            self.send(None, wait=False)  # connects and leaves at once
            self.send(json.dumps({'file': str(self.report), 'diagnostics': False}).encode() + b'\n', wait=False)
            answers = [self.send(b'[1]\n'), self.send(b'{"file": 5}\n'), self.send(b'not json\n')]
            time.sleep(.3)
            alive = [process.poll() is None for process in self.desktops]
            last = launch.request(self.paths, str(self.report))
            return first, answers, alive, list(self.wineserver), last
        first, answers, alive, wineserver_before_end, last = self.run_broker(client)
        self.assertTrue(first['ok'])
        self.assertEqual([answer['ok'] for answer in answers], [False, False, False])
        self.assertTrue(all(alive))
        # The broker stops the Wine server only when it ends, never because of a client.
        self.assertEqual(wineserver_before_end, [])
        self.assertTrue(last['ok'])
        self.assertIn('wineserver', self.wineserver)

    def test_the_session_lock_is_held_while_the_broker_runs(self):
        def client():
            with self.assertRaises(common.Error):
                with self.paths.lock('session'):
                    pass
            return True
        self.assertTrue(self.run_broker(client))
        with self.paths.lock('session'):
            pass

    def test_only_this_user_can_reach_the_session(self):
        def client():
            return (self.paths.socket.stat().st_mode & 0o777, self.paths.session.stat().st_mode & 0o777)
        self.assertEqual(self.run_broker(client), (0o600, 0o700))

    def devtools_ports(self, diagnostics):
        def client():
            return launch.request(self.paths, str(self.report), diagnostics)['ok']
        self.assertTrue(self.run_broker(client, diagnostics))
        seen = [' '.join(command) for command in self.commands]
        seen += [env.get('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', '') for env in self.desktop_env]
        return [text for text in seen if 'remote-debugging' in text]

    def test_a_normal_session_opens_no_devtools_port(self):
        # Neither the WebView2 policy written at session start nor Desktop's environment.
        self.assertEqual(self.devtools_ports(False), [])

    def test_only_diagnostics_open_a_devtools_port(self):
        self.assertNotEqual(self.devtools_ports(True), [])


if __name__ == '__main__':
    unittest.main()
