#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test an offline HTML page and its native callback in an installed prefix."""
import datetime
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from pbi_linux.common import Paths, read_json, wine_env


def main():
    installed = read_json(Paths().active)
    prefix, runtime = Path(installed['prefix']), Path(installed['runtime'])
    if not prefix.is_dir():
        raise RuntimeError('Installed profile is missing')
    output = root / '.local/legacy-html' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, mode=0o700)
    wine = runtime / 'bin/wine'
    env = wine_env(prefix)
    source = root / 'tests/e2e/legacy-html-probe.cs'
    executable = output / 'LegacyHtmlProbe.exe'
    win = lambda path: 'Z:' + str(path).replace('/', chr(92))
    print('Opening an offline test window; no action is sent to Desktop.', flush=True)
    result = {'passed': False, 'scope': 'offline HTML, JavaScript and native callback',
              'desktop_dialog_validated': False, 'installation_modified': False}
    try:
        commands = [
            ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                         '/nologo', '/platform:x64', '/r:System.Windows.Forms.dll',
                         '/r:System.Drawing.dll', '/out:' + win(executable), win(source)], 30),
            ('probe', [win(executable)], 25),
        ]
        for name, args, timeout in commands:
            completed = subprocess.run([str(wine), *args], env=env, capture_output=True,
                                       text=True, timeout=timeout)
            (output / (name + '.log')).write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise RuntimeError(name + ' failed; see ' + str(output))
            if name == 'probe' and 'PASS HTML body, JavaScript and native callback' not in completed.stdout:
                raise RuntimeError('Probe did not confirm all checks')
        result['passed'] = True
    finally:
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: offline HTML, JavaScript and native callback. Evidence: ' + str(output))


if __name__ == '__main__':
    main()
