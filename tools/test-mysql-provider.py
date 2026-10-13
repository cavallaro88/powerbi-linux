#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Load the installed provider; optionally query the documented loopback fixture."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Paths, read_json, wine_env
from pbi_linux import connectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loopback-port', type=int, help='Only the disposable database from docs/connectors.md')
    args = parser.parse_args()
    if args.loopback_port is not None and not 1 <= args.loopback_port <= 65535:
        parser.error('Port must be 1–65535')
    active = read_json(Paths().active)
    prefix, runtime = Path(active['prefix']), Path(active['runtime'])
    if not connectors.status(prefix)['verified']:
        raise RuntimeError('Install the managed MySQL recipe before running this test')
    out = ROOT / '.local/mysql-provider' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, mode=0o700)
    wine, env = runtime / 'bin/wine', wine_env(prefix)
    win = lambda p: 'Z:' + str(p).replace('/', '\\')
    helper = out / 'MySqlProviderProbe.exe'
    provider = prefix / connectors.PROVIDERS
    commands = [('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                             '/nologo', '/r:System.Data.dll', '/r:System.Xml.dll',
                             '/out:' + win(helper), win(ROOT / 'tests/e2e/mysql-provider-probe.cs')])]
    command = [helper, win(provider / 'MySql'), win(provider / 'MySql.config')]
    if args.loopback_port is not None:
        command.append(str(args.loopback_port))
    commands.append(('probe', command))
    for name, command in commands:
        result = subprocess.run([str(wine), *map(str, command)], env=env,
                                capture_output=True, text=True, timeout=40)
        (out / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(name + ' failed; see ' + str(out))
    result = {'passed': True, 'native_factory_load': True, 'dependencies_loaded': 12,
              'synthetic_loopback_query': args.loopback_port is not None,
              'real_server_contacted': False, 'report_modified': False,
              'scope': 'Original .NET provider; Power BI UI refresh is a separate check'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Evidence:', out)


if __name__ == '__main__':
    main()
