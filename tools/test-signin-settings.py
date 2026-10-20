#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise Desktop's settings API against a synthetic User.zip only."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux.common import Paths, wine_env


def main():
    active = json.loads(Paths().active.read_text())
    prefix, runtime = Path(active['prefix']), Path(active['runtime'])
    app = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    out = ROOT / '.local/signin-settings' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, mode=0o700)
    fixture = out / 'settings'
    fixture.mkdir()
    archive = fixture / 'User.zip'
    parts = {
        '[Content_Types].xml': b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="text/xml"/><Default Extension="bin" ContentType="application/octet-stream"/></Types>',
        'UserInterface/Settings.xml': b'<UISettingsConfig><Entries><Entry Type="UseSystemBrowserForAuthentication" Value="l0"/><Entry Type="UnrelatedSyntheticSetting" Value="skeep-me"/></Entries></UISettingsConfig>',
        'Credentials/Credentials.bin': b'SYNTHETIC sentinel; no account data',
        'FeatureSwitches/FeatureSwitches.xml': b'<SyntheticFixture/>',
    }
    with zipfile.ZipFile(archive, 'w') as z:
        for name, data in parts.items():
            z.writestr(name, data)
    env = wine_env(prefix)
    wine = runtime / 'bin/wine'
    windows = lambda path: 'Z:' + str(path).replace('/', '\\')

    def run(name, args, expected=0):
        r = subprocess.run([str(wine), *map(str, args)], env=env, capture_output=True,
                           text=True, timeout=45)
        (out / (name + '.log')).write_text(r.stdout + r.stderr)
        if r.returncode != expected:
            raise RuntimeError(name + ' failed; see ' + str(out))
        return r.stdout

    helper = out / 'ConfigureSignIn.exe'
    run('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                    '/nologo', '/out:' + windows(helper), windows(ROOT / 'src/helpers/ConfigureSignIn.cs')])
    args = [windows(app), windows(fixture)]
    before = archive.read_bytes()
    assert 'System authentication browser: disabled' in run('check-disabled', [helper, '--check', *args], expected=1)
    assert archive.read_bytes() == before, 'Read-only check modified the fixture'
    run('enable', [helper, '--enable', *args])
    run('check-enabled-new-process', [helper, '--check', *args])
    run('enable-again', [helper, '--enable', *args])
    with zipfile.ZipFile(archive) as z:
        for name in ('Credentials/Credentials.bin', 'FeatureSwitches/FeatureSwitches.xml'):
            assert z.read(name) == parts[name], 'Unrelated package part changed'
        settings = {e.attrib['Type']: e.attrib['Value'] for e in
                    ET.fromstring(z.read('UserInterface/Settings.xml')).iter('Entry')}
        assert settings['UseSystemBrowserForAuthentication'] == 'l1'
        assert settings['UnrelatedSyntheticSetting'] == 'skeep-me'
    before = archive.read_bytes()
    run('reject-unknown-operation', [helper, '--unknown', *args], expected=2)
    assert archive.read_bytes() == before
    result = {'passed': True, 'native_settings_api': True, 'fresh_process_persistence': True,
              'unrelated_parts_preserved': True, 'real_user_settings_modified': False}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Evidence:', out)


if __name__ == '__main__':
    main()
