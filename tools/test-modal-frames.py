#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test that browser frames reach their host while its main window is disabled by a modal dialog.

Runs in a fresh, disposable Wine prefix and shows a small disposable window for a few seconds."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets
from pbi_linux.common import Paths, read_json, wine_env

CHECKS = 3


def main():
    # check-product ends an overdue check with SIGTERM: exit through finally so
    # the own prefix is stopped and removed and result.json is still written.
    signal.signal(signal.SIGTERM, lambda number, frame: sys.exit(128 + number))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, help='Verified runtime; defaults to the installed runtime')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    args = parser.parse_args()
    runtime = (args.runtime or Path(read_json(Paths().active)['runtime'])).resolve()
    manifest = assets.verify_runtime(runtime)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = ROOT / '.local/modal-frames' / stamp
    output.mkdir(parents=True, mode=0o700)
    prefix = output / 'prefix'
    executable = output / 'modal-frames-probe.exe'
    compiler = shutil.which('x86_64-w64-mingw32-gcc')
    source = ROOT / 'tests/e2e/modal-frames-probe.c'
    if compiler:
        command = [compiler, '-O2', '-Wall', '-municode', str(source), '-o', str(executable), '-luser32', '-lgdi32']
    else:
        command = [args.engine, 'run', '--rm', '--user', str(os.getuid()) + ':' + str(os.getgid()),
                   '-e', 'HOME=/tmp/pbi-modal-frames-probe', '-v', str(ROOT) + ':/work:z', '-w', '/work',
                   'pbi-linux-builder:0.1.0', 'x86_64-w64-mingw32-gcc', '-O2', '-Wall', '-municode',
                   'tests/e2e/modal-frames-probe.c', '-o', '/work/' + str(executable.relative_to(ROOT)),
                   '-luser32', '-lgdi32']
    result = {'passed': False, 'runtime_version': manifest['version'],
              'scope': 'Own windows and frames in one process of an own prefix; no Desktop or browser',
              'real_report_modified': False, 'architecture': 'x86_64'}
    environment = wine_env(prefix)
    environment['WINEDLLOVERRIDES'] += ';mscoree,mshtml=d'
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (output / 'compile.log').write_text(p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError('Probe compilation failed; see ' + str(output))
        p = subprocess.run([str(runtime / 'bin/wine'), str(executable)], env=environment,
                           capture_output=True, text=True, timeout=90)
        (output / 'probe.log').write_text(p.stdout + p.stderr)
        counts = re.search(r'RESULT passed=(\d+) failed=(\d+)', p.stdout)
        if counts:
            result.update(checks_passed=int(counts[1]), checks_failed=int(counts[2]))
        if p.returncode or not counts or counts[2] != '0' or int(counts[1]) != CHECKS:
            raise RuntimeError('Modal frame checks failed; see ' + str(output))
        result['passed'] = True
    finally:
        stopped = True
        if prefix.exists():
            try:
                subprocess.run([str(runtime / 'bin/wineserver'), '-k'], env=environment,
                               capture_output=True, timeout=10)
                wait = subprocess.run([str(runtime / 'bin/wineserver'), '-w'], env=environment,
                                      capture_output=True, timeout=15)
                stopped = wait.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                stopped = False
            if stopped:
                shutil.rmtree(prefix)
        result['own_prefix_removed'] = not prefix.exists()
        if not stopped:
            result.update(passed=False, teardown_error='Own prefix did not stop; retained for inspection')
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError('Test or teardown failed; see ' + str(output))
    print('PASS: %d modal frame checks. Evidence: %s' % (CHECKS, output))


if __name__ == '__main__':
    main()
