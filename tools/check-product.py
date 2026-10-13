#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run repeatable product checks and report failures separately from missing coverage."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Paths, Error, busy, read_json

# These are independent coverage obligations, not successes inferred from unit tests.
UI_GAPS = [
    'Compositor pointer delivery, modal focus and dropdown interaction',
    'Data source list and Edit Permissions OK/Cancel persistence',
    'Unsaved-report Save/Discard/Cancel in actual Desktop',
    'Refresh cancellation and independently verified saved data',
    'Desktop file associations and multiple documents',
    'Large-model refresh and prolonged session for the exact runtime checksum',
]


def qa_environment(root, original=None):
    """Native checks must use a distinct installation, never an active user profile."""
    root = Path(root).resolve()
    original = dict(os.environ if original is None else original)
    production = Paths()
    env = dict(original)
    for kind, subdir in [('DATA', 'data'), ('CONFIG', 'config'), ('CACHE', 'cache'),
                         ('STATE', 'state'), ('RUNTIME', 'run')]:
        env['XDG_' + kind + '_HOME' if kind != 'RUNTIME' else 'XDG_RUNTIME_DIR'] = str(root / subdir)
    display = env.get('WAYLAND_DISPLAY')
    if display and not Path(display).is_absolute():
        env['WAYLAND_DISPLAY'] = str(Path(original.get('XDG_RUNTIME_DIR', '/nonexistent')) / display)
    data = root / 'data/powerbi-linux'
    if data.resolve() == production.data.resolve():
        raise Error('QA installation must differ from the current user installation')
    metadata = read_json(data / 'active.json')
    prefix = Path(metadata['prefix'])
    if not prefix.resolve().is_relative_to(data.resolve() / 'profiles'):
        raise Error('QA prefix escapes the dedicated QA data directory')
    if production.active.exists() and prefix.resolve() == Path(read_json(production.active)['prefix']).resolve():
        raise Error('QA installation points at the production prefix')
    if not prefix.is_dir():
        raise Error('QA prefix is missing; provision the dedicated installation first')
    env['PYTHONPATH'] = str(ROOT / 'src')
    return env, metadata


def execute(name, command, output, env, timeout):
    started = time.monotonic()
    log = output / (name + '.log')
    result = {'name': name, 'status': 'failed', 'log': log.name}
    with log.open('w') as stream:
        try:
            process = subprocess.Popen([str(x) for x in command], cwd=ROOT, env=env,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
                result.update(status='passed' if code == 0 else 'failed', exit_code=code)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                result['reason'] = 'Deadline exceeded; missing evidence is not a pass'
        except OSError as exc:
            result.update(status='blocked', reason=type(exc).__name__ + ': ' + str(exc))
    result['seconds'] = round(time.monotonic() - started, 3)
    return result


def report(output, cases, coverage, metadata=None):
    failed = any(c['status'] == 'failed' for c in cases)
    blocked = any(c['status'] == 'blocked' for c in cases)
    result = {'schema': 1, 'status': 'failed' if failed else 'blocked' if blocked else 'passed',
              'scope': 'Only the requested checks; not full release certification',
              'checks': cases, 'not_certified': coverage}
    if metadata:
        result['runtime_sha256'] = metadata['runtime_sha256']
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    suite = ET.Element('testsuite', name='powerbi-linux', tests=str(len(cases)),
                       failures=str(sum(c['status'] == 'failed' for c in cases)),
                       skipped=str(sum(c['status'] == 'blocked' for c in cases)))
    for case in cases:
        node = ET.SubElement(suite, 'testcase', name=case['name'], time=str(case.get('seconds', 0)))
        if case['status'] != 'passed':
            ET.SubElement(node, 'failure' if case['status'] == 'failed' else 'skipped',
                          message=case.get('reason', 'Check exited unsuccessfully'))
    ET.ElementTree(suite).write(output / 'junit.xml', encoding='utf-8', xml_declaration=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite', choices=['quick', 'components'], default='quick')
    p.add_argument('--qa-root', type=Path, help='Dedicated QA XDG root, required for native components')
    p.add_argument('--output', type=Path, help='New evidence directory')
    a = p.parse_args()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = (a.output or ROOT / '.local/check-product' / stamp).resolve()
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    cases = []
    commands = [
        ('unit', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/unit', '-v'], 180),
        ('syntax', [sys.executable, '-m', 'compileall', '-q', 'src', 'tools', 'runtime/build.py', 'tests/automation'], 30),
        ('desktop-entry', ['desktop-file-validate', 'packaging/powerbi-linux.desktop'], 15),
        ('source-export', [sys.executable, 'tools/export-source.py', str(output / 'source-export')], 60),
    ]
    for name, command, timeout in commands:
        case = execute(name, command, output, env, timeout)
        cases.append(case)
        print(name + ': ' + case['status'], flush=True)
    metadata = None
    if a.suite == 'components':
        try:
            if not a.qa_root:
                raise Error('Native checks require --qa-root with a separately provisioned installation')
            qa_env, metadata = qa_environment(a.qa_root)
            # busy() takes only a data path; avoid changing process-global XDG state.
            from types import SimpleNamespace
            qa_paths = SimpleNamespace(data=Path(qa_env['XDG_DATA_HOME']) / 'powerbi-linux')
            if busy(qa_paths):
                raise Error('QA Wine is already in use; no existing session will be stopped')
            if not qa_env.get('WAYLAND_DISPLAY'):
                raise Error('Native components require the QA graphical Wayland session')
        except (Error, KeyError, OSError) as exc:
            cases.append({'name': 'native-preflight', 'status': 'blocked', 'reason': str(exc)})
        else:
            for name, command, timeout in [
                ('qa-doctor', [sys.executable, '-m', 'pbi_linux', 'doctor', '--json'], 60),
                ('cursor-resource', [sys.executable, 'tools/test-cursor-resource.py', '--runtime', metadata['runtime']], 180),
                ('store-rating', [sys.executable, 'tools/test-store-rating.py'], 90),
                ('legacy-html', [sys.executable, 'tools/test-legacy-html.py'], 90),
                ('html-int64', [sys.executable, 'tools/test-html-int64.py'], 90),
                ('signin-settings', [sys.executable, 'tools/test-signin-settings.py'], 180),
                ('save-dialog', [sys.executable, 'tools/test-save-dialog.py'], 360),
            ]:
                case = execute(name, command, output, qa_env, timeout)
                cases.append(case)
                print(name + ': ' + case['status'], flush=True)
                if case['status'] != 'passed':
                    cases.append({'name': 'remaining-native-checks', 'status': 'blocked',
                                  'reason': 'Earlier native check failed; inspect the dedicated QA session before retrying'})
                    break
    coverage = list(UI_GAPS)
    coverage.insert(0, 'Options 22-tab audit requires its diagnostic bridge; see tests/automation/options-audit.py')
    result = report(output, cases, coverage, metadata)
    print(result['status'].upper() + ': ' + str(output / 'result.json'))
    print('Full UI/release certification: pending (' + str(len(coverage)) + ' explicit coverage gaps)')
    return 1 if result['status'] == 'failed' else 2 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
