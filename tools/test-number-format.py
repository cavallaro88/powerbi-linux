#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check DAX FORMAT scaling commas, decimal rounding and currency conversion in the installed runtime."""
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
    installed = read_json(Paths().active)
    runtime = Path(installed['runtime'])
    assets.verify_runtime(runtime)
    output = ROOT / '.local/number-format' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    win = lambda p: 'Z:' + str(p).replace('/', chr(92))
    exe = output / 'NumberFormatProbe.exe'
    env = wine_env(installed['prefix'])
    result = {'passed': False, 'runtime': runtime.name,
              'scope': 'oleaut32 VarFormat scaling commas and VarDecRound, oledb32 VARIANT to currency'}
    try:
        for label, args in [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                         '/nologo', '/out:' + win(exe), win(ROOT / 'tests/e2e/number-format-probe.cs')]),
            ('probe', [win(exe)]),
        ]:
            r = subprocess.run([str(runtime / 'bin/wine'), *args], env=env,
                               capture_output=True, text=True, timeout=60)
            (output / (label + '.log')).write_text(r.stdout + r.stderr)
            if label == 'probe':
                print(r.stdout, end='')
            if r.returncode:
                raise RuntimeError(label + ' failed; see ' + str(output))
            if label == 'probe' and 'COMPLETED: number formats' not in r.stdout:
                raise RuntimeError('Missing completion evidence')
        result['passed'] = True
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: number formats, decimal rounding and currency conversion. Evidence:', output)


if __name__ == '__main__':
    main()
