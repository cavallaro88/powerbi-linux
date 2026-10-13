#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare actual Wine DPI helper arithmetic before/after a candidate source patch."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wine-source', type=Path, default=ROOT/'sources/wine')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT/'.local/dpi-arithmetic'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    cc = shutil.which('cc')
    if not cc:
        raise SystemExit('A native C compiler is required; missing checks are not passes')
    stage = output/'wine'
    (stage/'server').mkdir(parents=True)
    source = stage/'server/user.h'
    shutil.copyfile(args.wine_source/'server/user.h', source)
    pattern = r'static inline int scale_dpi\( int val, struct ratio dpi_from, struct ratio dpi_to \)\n\{.*?\n\}'
    results = {}
    for label in ('baseline', 'candidate'):
        if label == 'candidate':
            applied = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i',
                str(ROOT/'runtime/candidates/neutron-server-signed-dpi.patch')],
                cwd=stage, capture_output=True, text=True, timeout=10)
            (output/'apply.log').write_text(applied.stdout+applied.stderr)
            if applied.returncode:
                raise SystemExit('Candidate did not apply to this source; inspect apply.log')
        match = re.search(pattern, source.read_text(), re.S)
        if not match:
            raise SystemExit('Unsupported Wine scale_dpi signature')
        case = output/label
        case.mkdir()
        (case/'dpi-helper.h').write_text(match.group()+'\n')
        exe = case/'probe'
        subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(case),
                        str(ROOT/'tests/e2e/dpi-arithmetic-probe.c'), '-o', str(exe)], check=True, timeout=30)
        run = subprocess.run([str(exe.resolve())], capture_output=True, text=True, timeout=10)
        if run.returncode not in (0, 1):
            raise SystemExit('Arithmetic probe did not complete normally')
        results[label] = json.loads(run.stdout)
    passed = results['baseline']['failed'] > 0 and results['candidate']['failed'] == 0
    report = dict(passed=passed, cases=results, production_enabled=False,
                  source_sha256=hashlib.sha256((args.wine_source/'server/user.h').read_bytes()).hexdigest(),
                  candidate_sha256=hashlib.sha256((ROOT/'runtime/candidates/neutron-server-signed-dpi.patch').read_bytes()).hexdigest(),
                  scope='Actual source helper compiled in isolation; not a Wine server build or compositor certification')
    (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
