#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check .NET Int64 transfer into an own IE11 HTML page; no Desktop settings."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets
from pbi_linux.common import Paths, read_json, wine_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, help='Optional verified candidate runtime, without activating it')
    args = parser.parse_args()
    installed = read_json(Paths().active)
    runtime = (args.runtime or Path(installed['runtime'])).resolve()
    manifest = assets.verify_runtime(runtime)
    output = ROOT / '.local/html-int64' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    executable, report = output / 'HtmlInt64Probe.exe', output / 'values.log'
    win = lambda p: 'Z:' + str(p).replace('/', chr(92))
    env = wine_env(installed['prefix'])
    result = {'passed': False, 'runtime_version': manifest['version'],
              'scope': 'Own offline IE11 document: Int32/Double controls, signed Int64 positive/negative, 2^40 and maximum safe JS integer',
              'settings_modified': False, 'desktop_dialog_certified': False}
    try:
        commands = [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                         '/nologo', '/platform:x64', '/r:System.Windows.Forms.dll',
                         '/r:System.Drawing.dll', '/out:' + win(executable),
                         win(ROOT / 'tests/e2e/html-int64-probe.cs')], 35),
            ('probe', [win(executable), win(report)], 20),
        ]
        for label, arguments, timeout in commands:
            process = subprocess.run([str(runtime / 'bin/wine'), *arguments], env=env,
                                     text=True, capture_output=True, timeout=timeout)
            (output / (label + '.log')).write_text(process.stdout + process.stderr)
            if process.returncode:
                raise RuntimeError(label + ' failed; see ' + str(output))
        values = report.read_text()
        if 'documentMode=11' not in values or values.count('"sameValue":true') != 7 or 'ERROR' in values:
            raise RuntimeError('Numeric checks were not all confirmed; see ' + str(output))
        result['passed'] = True
        result['cases_passed'] = 7
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: seven .NET/HTML numeric cases. Evidence:', output)


if __name__ == '__main__':
    main()
