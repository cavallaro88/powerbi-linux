#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test Desktop's custom-caption base with disposable forms; never opens a report."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Paths, read_json, wine_env, digest
from pbi_linux import assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly-dir', type=Path, help='Directory containing a private Desktop candidate')
    parser.add_argument('--baseline', action='store_true', help='Expect original frame; requires --assembly-dir')
    parser.add_argument('--hold', action='store_true', help='Keep only the probe open for compositor tests, up to five minutes')
    args = parser.parse_args()
    if args.baseline and not args.assembly_dir:
        parser.error('--baseline requires an explicit --assembly-dir')
    installed = read_json(Paths().active)
    runtime = Path(installed['runtime'])
    assets.verify_runtime(runtime)
    app = Path(installed['prefix']) / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    target = args.assembly_dir.resolve() if args.assembly_dir else app
    output = ROOT / '.local/window-frame-tests' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    win = lambda path: 'Z:' + str(path).replace('/', chr(92))
    executable = output / 'window-frame-probe.exe'
    mode = 'baseline' if args.baseline else 'candidate'
    env = wine_env(installed['prefix'])
    result = {'passed': False, 'mode': mode, 'report_opened': False,
              'scope': 'Disposable forms using the actual custom-caption base, not a full UI/release gate',
              'runtime_sha256': installed['runtime_sha256'],
              'assembly_sha256': digest(target / 'Microsoft.PowerBI.Client.Windows.dll')}
    helper = target / 'PowerBIWindowFrame.dll'
    if helper.is_file():
        result['helper_sha256'] = digest(helper)
    try:
        commands = [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                         '/nologo', '/optimize+', '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll',
                         '/out:' + win(executable), win(ROOT / 'tests/e2e/window-frame-probe.cs')]),
            ('probe', [win(executable), win(target), win(app), mode] + (['--hold'] if args.hold else [])),
        ]
        for label, command in commands:
            completed = subprocess.run([str(runtime / 'bin/wine'), *command], env=env,
                                       capture_output=True, text=True,
                                       timeout=320 if args.hold and label == 'probe' else 45)
            (output / (label + '.log')).write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise RuntimeError(label + ' failed; see ' + str(output))
            if label == 'probe':
                if 'READY hwnd=' not in completed.stdout:
                    raise RuntimeError('Missing completed fixture checks')
                result['checks_passed'] = completed.stdout.count('PASS ')
        result['passed'] = True
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: custom frame, resize zones and control cases. Evidence:', output)


if __name__ == '__main__':
    main()
