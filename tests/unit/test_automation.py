# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

suite = module('product_check_suite', ROOT / 'tools/check-product.py')
options = module('product_options_audit', ROOT / 'tests/automation/options-audit.py')

class AutomationTests(unittest.TestCase):
    def test_blocked_report_cannot_become_a_passing_suite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            r = suite.report(p, [{'name':'native','status':'blocked','reason':'no QA prefix'}], ['pointer'])
            self.assertEqual(r['status'], 'blocked')
            self.assertIn('<skipped', (p/'junit.xml').read_text())
            r = suite.report(p, [{'name':'one','status':'blocked'}, {'name':'two','status':'failed'}], [])
            self.assertEqual(r['status'], 'failed')

    def test_native_preflight_rejects_a_prefix_symlink_outside_qa(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            env = {k:str(base/'production'/k) for k in ('XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR')}
            qa = base/'qa'
            managed = qa/'data/powerbi-linux'
            (managed/'profiles').mkdir(parents=True)
            foreign = base/'real-prefix';foreign.mkdir()
            linked = managed/'profiles/disguised';linked.symlink_to(foreign, target_is_directory=True)
            (managed/'active.json').write_text(json.dumps({'prefix':str(linked)}))
            with patch.dict(os.environ, env):
                with self.assertRaises(suite.Error):suite.qa_environment(qa)

    def test_native_preflight_keeps_the_real_desktop_runtime_directory(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            qa = base / 'qa'
            managed = qa / 'data/powerbi-linux'
            prefix = managed / 'profiles/test'
            prefix.mkdir(parents=True)
            (managed / 'active.json').write_text(json.dumps({'prefix': str(prefix)}))
            original = {'XDG_RUNTIME_DIR': str(base / 'desktop-run'), 'WAYLAND_DISPLAY': 'wayland-1'}
            env, _ = suite.qa_environment(qa, original)
            self.assertEqual(env['XDG_RUNTIME_DIR'], original['XDG_RUNTIME_DIR'])
            self.assertEqual(env['XDG_DATA_HOME'], str(qa / 'data'))
            self.assertEqual(env['WAYLAND_DISPLAY'], str(base / 'desktop-run/wayland-1'))

    def test_expired_check_is_a_failure(self):
        with tempfile.TemporaryDirectory() as d:
            r = suite.execute('slow', [sys.executable,'-c','import time;time.sleep(30)'], Path(d), os.environ.copy(), .05)
            self.assertEqual(r['status'], 'failed')
            self.assertIn('Deadline exceeded', r['reason'])

    def test_an_incomplete_footer_or_clipped_pane_fails_options(self):
        value = {'selected':['GLOBAL',0], 'panes':[{'width':700,'height':980}],
                 'footer':[{'text':'OK','inside':True},{'text':'Cancel','inside':True}],
                 'navigation':{'client':658,'scroll':669,'overflow':'auto','inside':True,
                               'lastReachable':True,'labelSelection':'none','editable':True},
                 'scrollPane':{'client':658,'scroll':1000,'overflow':'auto','inside':True}, 'errors':[]}
        self.assertTrue(options.valid_tab(value,'GLOBAL',0))
        value['scrollPane']['inside'] = False
        self.assertFalse(options.valid_tab(value,'GLOBAL',0))
        value['scrollPane']['inside'] = True
        value['footer'].pop()
        self.assertFalse(options.valid_tab(value,'GLOBAL',0))

    def test_unreachable_navigation_or_blocked_editable_fields_fail_options(self):
        import copy
        value = {'selected':['GLOBAL',0], 'panes':[{'width':700,'height':300}],
                 'footer':[{'text':'OK','inside':True},{'text':'Cancel','inside':True}],
                 'scrollPane':{'client':300,'scroll':1000,'overflow':'auto','inside':True},
                 'navigation':{'client':300,'scroll':669,'overflow':'auto','inside':True,
                               'lastReachable':True,'labelSelection':'none','editable':True}, 'errors':[]}
        self.assertTrue(options.valid_tab(value,'GLOBAL',0))
        for key, bad in [('lastReachable',False),('editable',False),('labelSelection','auto'),('overflow','hidden')]:
            case = copy.deepcopy(value)
            case['navigation'][key] = bad
            self.assertFalse(options.valid_tab(case,'GLOBAL',0),key)

    def test_stale_or_foreign_bridge_output_never_passes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d);p.chmod(0o700)
            (p/'response.txt').write_text('SCOPE synthetic-options\nSCRIPT {"nonce":"old","value":true}\n')
            with self.assertRaises(RuntimeError):options.Bridge(p, timeout=.02).request('true')
            (p/'response.txt').unlink();(p/'request.txt').unlink()
            target = p/'external';target.touch();(p/'request.txt').symlink_to(target)
            with self.assertRaises(RuntimeError):options.Bridge(p)

    def test_empty_option_catalog_is_not_a_pass(self):
        class Empty:
            def request(self, script):return []
        with self.assertRaises(RuntimeError):options.audit(Empty())

if __name__ == '__main__':unittest.main()
