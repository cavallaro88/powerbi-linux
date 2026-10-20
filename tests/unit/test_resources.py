# SPDX-License-Identifier: GPL-3.0-or-later
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pbi_linux import cli, common, provision, resources


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {key:str(root/key) for key in
            ('XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR')})
        self.env.start()
        self.paths = common.Paths()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.main(['profile', *args])

    def test_default_does_not_force_browser_or_cpu_limits(self):
        config = provision.settings(self.paths)
        self.assertEqual(config['memory_profile'], 'unlimited')
        self.assertEqual(resources.service_properties(config),
                         ['MemoryMax=infinity', 'MemorySwapMax=infinity'])
        flags = resources.browser_flags(config)
        for forced in ('max_old_space_size', 'renderer-process-limit', 'low-end',
                       'process-per-site', 'SpareRendererForSitePerProcess'):
            self.assertNotIn(forced, flags)
        self.assertIn('--use-angle=d3d11', flags)
        self.assertFalse(self.paths.settings.exists())

    def test_exact_legacy_presets_migrate_without_writing_on_read(self):
        for name, ram, swap in [('normal','6G','2G'), ('large','10G','4G')]:
            common.atomic_json(self.paths.settings, {'memory_profile':name,
                'memory_max':ram,'swap_max':swap,'webview_heap_mb':512,'extra':'preserve'})
            before = self.paths.settings.read_bytes()
            config = provision.settings(self.paths)
            self.assertEqual(config['memory_max'], 'infinity')
            self.assertEqual(config['webview_heap_mb'], 'auto')
            self.assertEqual(config['extra'], 'preserve')
            self.assertEqual(self.paths.settings.read_bytes(), before)

    def test_custom_legacy_values_and_new_explicit_presets_are_preserved(self):
        common.atomic_json(self.paths.settings, {'memory_max':'8G','swap_max':'3G','webview_heap_mb':1024})
        self.assertEqual(provision.settings(self.paths)['memory_max'], '8G')
        self.assertEqual(provision.settings(self.paths)['webview_heap_mb'], 1024)
        for name in ('normal','large'):
            self.assertEqual(self.invoke(name), 0)
            self.assertEqual(provision.settings(self.paths), resources.preset(name))
        self.assertEqual(self.invoke('unlimited'), 0)
        self.assertEqual(provision.settings(self.paths), resources.DEFAULTS)

    def test_cli_individual_limits_auto_reset_and_partial_updates(self):
        self.assertEqual(self.invoke('--memory-max','8G','--swap-max','0','--cpu-quota','200%',
            '--webview-heap','1024','--renderer-process-limit','3','--browser-mode','economy'), 0)
        config = provision.settings(self.paths)
        self.assertEqual(resources.service_properties(config),
            ['MemoryMax=8G','MemorySwapMax=0','CPUQuota=200%'])
        flags = resources.browser_flags(config)
        self.assertIn('--js-flags=--max_old_space_size=1024', flags)
        self.assertIn('--renderer-process-limit=3', flags)
        self.assertIn('--enable-low-end-device-mode', flags)
        self.assertEqual(self.invoke('--webview-heap','auto','--browser-mode','standard'), 0)
        config = provision.settings(self.paths)
        self.assertEqual(config['memory_max'], '8G')
        self.assertEqual(config['cpu_quota'], '200%')
        flags = resources.browser_flags(config)
        self.assertNotIn('max_old_space_size', flags)
        self.assertNotIn('low-end', flags)
        self.assertIn('--renderer-process-limit=3', flags)
        self.assertEqual(self.invoke('--renderer-process-limit','auto','--memory-max','unlimited',
            '--swap-max','unlimited','--cpu-quota','unlimited'), 0)
        self.assertEqual(resources.browser_flags(provision.settings(self.paths)), resources.BASE_BROWSER_FLAGS)

    def test_invalid_cli_option_does_not_change_settings(self):
        self.invoke('unlimited')
        before = self.paths.settings.read_bytes()
        for option,value in [('--memory-max','0'),('--swap-max','-1G'),('--cpu-quota','0%'),
                             ('--webview-heap','0'),('--renderer-process-limit','0')]:
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.invoke(option+'='+value)
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(self.paths.settings.read_bytes(), before)

    def test_show_profile_is_read_only_and_invalid_json_settings_are_rejected(self):
        self.assertEqual(self.invoke(), 0)
        self.assertFalse(self.paths.settings.exists())
        for value in ([], {'webview_heap_mb':True}, {'swap_max':'-1G'}, {'browser_mode':'unknown'}):
            common.atomic_json(self.paths.settings, value)
            with self.subTest(value=value), self.assertRaises(common.Error):
                provision.settings(self.paths)


if __name__ == '__main__':
    unittest.main()
