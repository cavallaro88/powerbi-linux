#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check linguistic JSON normalization using own objects; no report or server access."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets
from pbi_linux.common import Paths, read_json, wine_env, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--helper', type=Path, help='Optional signed private candidate helper')
    a = p.parse_args()
    installed = read_json(Paths().active)
    runtime, prefix = Path(installed['runtime']), Path(installed['prefix'])
    assets.verify_runtime(runtime)
    app = prefix/'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    helper = a.helper or app/'PowerBICacheCompatibility.dll'
    output = ROOT/'.local/cache-compatibility'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    copied = output/'PowerBICacheCompatibility.dll'
    shutil.copy2(helper, copied)
    win = lambda f: 'Z:' + str(f).replace('/', chr(92))
    exe = output/'CacheCompatibilityProbe.exe'
    result = {'passed': False, 'scope': 'Own JSON strings and fake culture objects',
              'report_modified': False, 'model_restore_certified': False,
              'helper_sha256': digest(copied)}
    try:
        for label, command in [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe', '/nologo',
                         '/r:' + win(copied), '/out:' + win(exe),
                         win(ROOT/'tests/e2e/cache-compatibility-probe.cs')]),
            ('probe', [win(exe), win(app)]),
        ]:
            r = subprocess.run([str(runtime/'bin/wine'), *command], env=wine_env(prefix),
                               capture_output=True, text=True, timeout=35)
            (output/(label+'.log')).write_text(r.stdout+r.stderr)
            if r.returncode:
                raise RuntimeError(label+' failed; see '+str(output))
            if label == 'probe' and ('RESULT passed=10' not in r.stdout or 'FAIL ' in r.stdout):
                raise RuntimeError('Missing normalization evidence')
        result.update(passed=True, checks_passed=10)
    finally:
        (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PASS: ten JSON normalization checks. Evidence:', output)


if __name__ == '__main__':
    main()
