# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, launch, provision


class ProcessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        environment = patch.dict(os.environ, {'XDG_DATA_HOME': str(self.root / 'data'),
                                              'XDG_STATE_HOME': str(self.root / 'state'),
                                              'XDG_RUNTIME_DIR': str(self.root / 'run')})
        environment.start()
        self.addCleanup(environment.stop)
        self.paths = common.Paths()
        self.prefix = self.paths.data / 'profiles/test'

    def start(self, program):
        """A process that looks managed: WINEPREFIX inside the managed profiles."""
        process = subprocess.Popen(program, env=dict(os.environ, WINEPREFIX=str(self.prefix)),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        return process

    def until(self, condition):
        deadline = time.monotonic() + 5
        while not condition() and time.monotonic() < deadline:
            time.sleep(.05)
        return condition()

    def test_a_shell_that_exported_wineprefix_is_not_wine(self):
        shell = self.start(['sleep', '30'])
        time.sleep(.2)
        self.assertNotIn(shell.pid, list(common.wine_processes(self.paths)))
        self.assertFalse(common.busy(self.paths))

    def test_a_wine_program_counts_and_stop_ends_it(self):
        wine = self.root / 'data/runtimes/test/bin/wine-preloader'
        wine.parent.mkdir(parents=True)
        # A copy, so /proc/PID/exe points into the managed runtime.
        wine.write_bytes(Path('/usr/bin/sleep').read_bytes())
        wine.chmod(0o755)
        process = self.start([str(wine), '30'])
        self.assertTrue(self.until(lambda: process.pid in list(common.wine_processes(self.paths))))
        self.assertTrue(common.busy(self.paths))
        stopped = subprocess.CompletedProcess([], 5, '', '')
        with patch.object(launch.subprocess, 'run', return_value=stopped) as run, \
                patch.object(launch, 'STOP_WAIT', 0.5):
            launch.stop(self.paths)
        self.assertEqual(run.call_args_list[0].args[0][:3], ['systemctl', '--user', 'stop'])
        self.assertTrue(self.until(lambda: process.poll() is not None))

    def test_a_systemd_failure_is_reported_only_if_wine_survives(self):
        failed = subprocess.CompletedProcess([], 1, '', 'Access denied')
        with patch.object(launch.subprocess, 'run', return_value=failed):
            launch.stop(self.paths)  # nothing was running
            with patch.object(launch, 'busy', return_value=True), patch.object(launch, 'STOP_WAIT', 0.1), \
                    patch.object(launch, 'wine_processes', return_value=[]):
                with self.assertRaisesRegex(common.Error, 'Access denied.*log out'):
                    launch.stop(self.paths)

    def test_stop_never_interrupts_a_repair(self):
        with self.paths.lock('maintenance'), patch.object(launch.subprocess, 'run') as run:
            with self.assertRaisesRegex(common.Error, 'repair or update is still running'):
                launch.stop(self.paths)
        run.assert_not_called()

    def test_stop_waits_for_a_session_start_instead_of_refusing(self):
        import threading
        held, release = threading.Event(), threading.Event()
        def start():
            with self.paths.lock('launch'), self.paths.lock('maintenance'):
                held.set()
                release.wait(10)
        starter = threading.Thread(target=start)
        starter.start()
        self.addCleanup(starter.join)
        self.addCleanup(release.set)
        held.wait(5)
        threading.Timer(6, release.set).start()  # Past stop's first 5 s wait.
        with patch.object(launch, '_stop') as stopped, patch.object(launch, 'LAUNCH_WAIT', 20):
            launch.stop(self.paths)
        stopped.assert_called_once_with(self.paths)

    def test_a_start_that_outlasts_the_wait_is_not_called_a_repair(self):
        with self.paths.lock('launch'), self.paths.lock('maintenance'):
            with patch.object(launch, '_stop') as stopped, patch.object(launch, 'LAUNCH_WAIT', 0.3):
                with self.assertRaisesRegex(common.Error, 'still starting'):
                    launch.stop(self.paths)
        stopped.assert_not_called()

    def test_maintenance_waits_for_a_closing_session_then_refuses_kindly(self):
        with self.paths.lock('session'), patch.object(launch, 'SESSION_WAIT', 0.2):
            with self.assertRaisesRegex(common.Error, 'still closing.*pbi-linux stop'):
                provision.idle(self.paths)
        provision.idle(self.paths)


if __name__ == '__main__':
    unittest.main()
