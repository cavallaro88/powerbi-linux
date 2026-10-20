#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test cross-process cursor resources in a fresh, disposable Wine prefix."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets
from pbi_linux.common import Paths, read_json, wine_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, help='Verified runtime; defaults to the installed runtime')
    parser.add_argument('--engine', choices=['docker', 'podman'], default='docker')
    args = parser.parse_args()
    runtime = (args.runtime or Path(read_json(Paths().active)['runtime'])).resolve()
    manifest = assets.verify_runtime(runtime)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = ROOT / '.local/cursor-resource' / stamp
    output.mkdir(parents=True, mode=0o700)
    prefix = output / 'prefix'
    executable = output / 'CursorResourceProbe.exe'
    compiler = shutil.which('x86_64-w64-mingw32-gcc')
    source = ROOT / 'tests/e2e/cursor-resource-probe.c'
    if compiler:
        command = [compiler, '-O2', '-Wall', '-municode', str(source), '-o', str(executable), '-luser32', '-lgdi32']
    else:
        command = [args.engine, 'run', '--rm', '--user', str(os.getuid()) + ':' + str(os.getgid()),
                   '-e', 'HOME=/tmp/pbi-cursor-probe', '-v', str(ROOT) + ':/work:z', '-w', '/work',
                   'pbi-linux-builder:0.1.0', 'x86_64-w64-mingw32-gcc', '-O2', '-Wall', '-municode',
                   'tests/e2e/cursor-resource-probe.c', '-o', '/work/' + str(executable.relative_to(ROOT)),
                   '-luser32', '-lgdi32']
    result = {'passed': False, 'runtime_version': manifest['version'],
              'scope': 'Own message-only windows in two processes; no Desktop or physical pointer input',
              'real_report_modified': False, 'compositor_cursor_certified': False, 'architecture': 'x86_64'}
    environment = wine_env(prefix)
    environment['WINEDLLOVERRIDES'] += ';mscoree,mshtml=d'
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=90)
        (output / 'compile.log').write_text(p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError('Probe compilation failed; see ' + str(output))
        p = subprocess.run([str(runtime / 'bin/wine'), str(executable)], env=environment,
                           capture_output=True, text=True, timeout=50)
        (output / 'probe.log').write_text(p.stdout + p.stderr)
        if p.returncode or 'RESULT passed=12 failed=0' not in p.stdout:
            raise RuntimeError('Cursor resource checks failed; see ' + str(output))
        result.update(passed=True, checks_passed=12)
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
    print('PASS: 12 cursor resource checks. Evidence:', output)


if __name__ == '__main__':
    main()
