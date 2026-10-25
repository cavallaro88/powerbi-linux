#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the theme bridge and original Desktop service in a disposable prefix."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Paths, digest, read_json, wine_env
from pbi_linux import theme


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path, help='Disposable copy under .local/')
    parser.add_argument('--runtime', required=True, type=Path)
    args = parser.parse_args()
    prefix, runtime = args.prefix.resolve(), args.runtime.resolve()
    if not prefix.is_relative_to(ROOT / '.local') or not (prefix / 'system.reg').is_file():
        parser.error('Use a populated disposable prefix under the repository .local/ directory')
    production = Paths().active
    if production.exists() and prefix == Path(read_json(production)['prefix']).resolve():
        parser.error('The production prefix cannot be used for this test')
    output = ROOT / '.local/theme-tests' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    env = wine_env(prefix)
    wine = runtime / 'bin/wine'
    win = lambda path: 'Z:' + str(path).replace('/', chr(92))
    bridge = theme.ThemeSync(SimpleNamespace(state=output, session=output), runtime, env)
    result = {'passed': False, 'report_opened': False,
              'scope': 'Synthetic WinForms receiver and original Desktop ThemeService, not the full report UI',
              'assembly_sha256': digest(prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin/Microsoft.PowerBI.Client.Windows.dll')}
    try:
        # Test the actual Python startup/compiler path, including native Wayland.
        bridge.start()
        if bridge.thread is None or bridge.current is None:
            raise RuntimeError('GNOME preference or theme helper unavailable; see session.log')
        probe = output / 'ThemeSyncProbe.exe'
        commands = [
            ('compile', [theme.COMPILER, '/nologo', '/r:System.Windows.Forms.dll',
                         '/out:' + win(probe), win(ROOT / 'tests/e2e/theme-sync-probe.cs')]),
            ('probe', [win(probe), win(prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'),
                       win(bridge.helper)]),
        ]
        # Stop the host watcher before the synthetic test deliberately changes
        # this copy's Windows preference. Retain its compiled helper until done.
        bridge.stop.set()
        bridge.thread.join()
        for label, command in commands:
            completed = subprocess.run([str(wine), *command], env=env, text=True,
                                       capture_output=True, timeout=60)
            (output / (label + '.log')).write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise RuntimeError(label + ' failed; see ' + str(output))
            if label == 'probe':
                result['checks_passed'] = completed.stdout.count('PASS ')
                if result['checks_passed'] != 13:
                    raise RuntimeError('Incomplete native probe output')
        result['passed'] = True
    finally:
        bridge.close()
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: startup, native notification, System transitions and manual choices. Evidence:', output)


if __name__ == '__main__':
    main()
