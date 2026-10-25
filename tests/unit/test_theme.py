# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import common, theme


class ThemeTests(unittest.TestCase):
    def test_gnome_preferences_and_unavailable_settings(self):
        for value, expected in (("'prefer-dark'", 'dark'), ("'prefer-light'", 'light'),
                                ("'default'", 'light'), ("'unknown'", None), ('', None)):
            with self.subTest(value=value), patch.object(theme.subprocess, 'run',
                    return_value=SimpleNamespace(returncode=0, stdout=value + '\n')) as run:
                self.assertEqual(theme.preference(), expected)
                self.assertEqual(run.call_args.kwargs['timeout'], 1)
        with patch.object(theme.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            self.assertIsNone(theme.preference())
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('gsettings', 1)):
            with patch.object(theme.subprocess, 'run', side_effect=error):
                self.assertIsNone(theme.preference())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = SimpleNamespace(state=root, session=root)
        self.bridge = theme.ThemeSync(self.paths, root / 'runtime',
            {'WINEPREFIX': str(root / 'prefix'), 'APPDOMAIN_MANAGER_ASM': 'manager',
             'APPDOMAIN_MANAGER_TYPE': 'CompositionManager'})
        self.addCleanup(self.bridge.close)
        self.bridge.helper = root / 'helper.exe'

    def test_unavailable_preference_does_not_change_prefix(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='GNOME'), \
                patch.object(theme, 'preference', return_value=None), patch.object(theme, 'run') as run:
            self.bridge.start()
        run.assert_not_called()
        self.assertIsNone(self.bridge.thread)

    def test_other_desktops_do_not_read_stale_gnome_settings(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='KDE'), \
                patch.object(theme, 'preference') as preference:
            self.bridge.start()
        preference.assert_not_called()

    def test_changes_are_applied_once_and_missing_reads_keep_last_value(self):
        with patch.object(theme, 'run') as run:
            for value in ('dark', 'dark', None, 'light', 'light', 'dark'):
                self.bridge.sync(value)
        self.assertEqual([call.args[0][-1] for call in run.call_args_list], ['dark', 'light', 'dark'])
        self.assertEqual(run.call_args.kwargs['env'], {'WINEPREFIX': self.bridge.env['WINEPREFIX']})

    def test_failed_write_is_retried(self):
        with patch.object(theme, 'run', side_effect=[None, common.Error('busy'), None]) as run:
            self.bridge.sync('light')
            with self.assertRaises(common.Error):
                self.bridge.sync('dark')
            self.assertEqual(self.bridge.current, 'light')
            self.bridge.sync('dark')
        self.assertEqual(run.call_count, 3)
        self.assertEqual(self.bridge.current, 'dark')

    def test_start_compiles_private_helper_and_close_stops_worker_before_cleanup(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='ubuntu:GNOME'), \
                patch.object(theme, 'preference', return_value='dark'), \
                patch.object(theme, 'run') as run:
            self.bridge.start()
            folder = Path(self.bridge.directory.name)
            self.assertTrue((folder / 'PowerBIThemeSync.cs').is_file())
            self.assertEqual(run.call_args_list[0].args[0][1], theme.COMPILER)
            self.assertEqual(run.call_args_list[1].args[0][-1], 'dark')
            worker = self.bridge.thread
            self.assertTrue(worker.is_alive())
            self.bridge.close()
            self.assertFalse(worker.is_alive())
            self.assertFalse(folder.exists())

    def test_compiler_failure_does_not_block_launch_or_leave_session_files(self):
        with patch.dict(os.environ, XDG_CURRENT_DESKTOP='GNOME'), \
                patch.object(theme, 'preference', return_value='dark'), \
                patch.object(theme, 'run', side_effect=common.Error('compile failed')):
            self.bridge.start()
        self.assertIsNone(self.bridge.directory)
        self.assertIsNone(self.bridge.thread)
        self.assertIn('synchronization unavailable', (self.paths.state / 'session.log').read_text())

    def test_worker_retries_after_failure_and_stops_without_an_extra_write(self):
        attempted = threading.Event()
        values = []
        def sync(value):
            values.append(value)
            if len(values) == 1:
                raise common.Error('temporary failure')
            self.bridge.stop.set()
            attempted.set()
        with patch.object(theme, 'POLL_SECONDS', 0.001), \
                patch.object(theme, 'preference', return_value='dark'), \
                patch.object(self.bridge, 'sync', side_effect=sync):
            self.bridge.thread = threading.Thread(target=self.bridge._watch)
            self.bridge.thread.start()
            self.assertTrue(attempted.wait(2))
            self.bridge.close()
        self.assertEqual(values, ['dark', 'dark'])


if __name__ == '__main__':
    unittest.main()
