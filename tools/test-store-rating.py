#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the offline Store rating entrypoint; never publishes a report."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets
from pbi_linux.common import Paths, read_json, wine_env, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly-dir', type=Path, help='Optional private candidate directory')
    a = parser.parse_args()
    installed = read_json(Paths().active)
    runtime = Path(installed['runtime'])
    assets.verify_runtime(runtime)
    app = Path(installed['prefix']) / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    target = a.assembly_dir.resolve() if a.assembly_dir else app
    output = ROOT / '.local/store-rating' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    win = lambda p: 'Z:' + str(p).replace('/', chr(92))
    exe = output / 'RatingProbe.exe'
    env = wine_env(installed['prefix'])
    result = {'passed': False, 'scope': 'Offline Store rating entrypoint with null dependencies',
              'publication_tested': False, 'report_modified': False,
              'assembly_sha256': digest(target / 'Microsoft.PowerBI.Client.Windows.dll')}
    try:
        for label, args in [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                         '/nologo', '/out:' + win(exe), win(ROOT / 'tests/e2e/store-rating-probe.cs')]),
            ('probe', [win(exe), win(target), win(app)]),
        ]:
            r = subprocess.run([str(runtime / 'bin/wine'), *args], env=env,
                               capture_output=True, text=True, timeout=35)
            (output / (label + '.log')).write_text(r.stdout + r.stderr)
            if r.returncode:
                raise RuntimeError(label + ' failed; see ' + str(output))
            if label == 'probe' and 'COMPLETED: rating entrypoint' not in r.stdout:
                raise RuntimeError('Missing completion evidence')
        result['passed'] = True
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: offline Store rating entrypoint. Evidence:', output)


if __name__ == '__main__':
    main()
