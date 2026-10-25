#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check a registered Windows x64 ODBC driver offline; never install or connect."""
import argparse
import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import provision
from pbi_linux.common import Error, Paths, atomic_json, wine_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver', required=True, help='Exact registered Windows driver name')
    parser.add_argument('--dsn', help='Optional exact existing DSN expected to reference this driver')
    parser.add_argument('--output', type=Path, help='New private evidence directory')
    args = parser.parse_args()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = (args.output or ROOT / '.local/odbc-driver' / stamp).resolve()
    paths = Paths()
    try:
        with paths.lock():
            provision.idle(paths)
            installed = provision.active(paths)
            output.mkdir(parents=True, mode=0o700, exist_ok=False)
            env, wine = wine_env(installed['prefix']), str(Path(installed['runtime']) / 'bin/wine')
            win = lambda p: 'Z:' + str(p.resolve()).replace('/', '\\')
            exe = output / 'OdbcDriverProbe.exe'
            result = {'passed': False, 'network_attempted': False, 'driver': args.driver,
                      'runtime_sha256': installed['runtime_sha256'],
                      'dsn_checked': args.dsn is not None, 'report_modified': False}
            try:
                commands = [
                    ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                                 '/nologo', '/optimize+', '/out:' + win(exe),
                                 win(ROOT / 'tests/e2e/odbc-driver.cs')]),
                    ('probe', [win(exe), args.driver] + ([args.dsn] if args.dsn else [])),
                ]
                for label, command in commands:
                    response = subprocess.run([wine, *command], env=env, capture_output=True,
                                              text=True, timeout=45)
                    (output / (label + '.log')).write_text(response.stdout + response.stderr)
                    if response.returncode:
                        raise Error('ODBC ' + label + ' failed; see ' + str(output / (label + '.log')))
                result['passed'] = True
            finally:
                atomic_json(output / 'result.json', result)
        print('Offline driver check passed: ' + str(output))
        return 0
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
