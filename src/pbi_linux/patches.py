# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import shutil
from .common import Error, check_digest, digest, run, wine_env
from . import legacy_html, signin

ORIGINALS = {
    'Microsoft.PowerBI.Client.Shared.dll': '1dc130d913b92f315b81aa5162e8fa74e8a0279742f988561680111d5189ff78',
    'Microsoft.PowerBI.Client.Windows.dll': '5284e48755ca5d0911f8af46650d1aa12a36389f008e6005ac5f188071808cd4',
    'msmdsrv.exe': '7975dcb62edd6e53cc16fe808f66dbf0551cb155069138d68080c4bd32e92a1d',
    'Microsoft.Mashup.Client.UI.dll': legacy_html.UI_ORIGINAL_SHA256,
}

NATIVE_DIALOG = 'PowerBISaveDialog.dll'


def build_native_dialog(helpers, wine, env, log, key):
    # Own sources ship in the RPM; the pinned Wine runtime need not be rebuilt.
    sources = Path(__file__).resolve().parents[1] / 'helpers'
    for name in ('PowerBISaveDialog.cs', 'PatchSavePrompt.cs'):
        shutil.copy2(sources / name, helpers / name)
    compiler = r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    run([wine, compiler, '/nologo', '/optimize+', '/target:library',
         r'/out:unsigned\PowerBISaveDialog.dll', '/r:System.Windows.Forms.dll',
         '/r:System.Drawing.dll', 'PowerBISaveDialog.cs'], env=env, cwd=helpers, log=log)
    run([wine, compiler, '/nologo', '/optimize+', '/r:dnlib.dll', '/r:System.Core.dll',
         '/out:PatchSavePrompt.exe', 'PatchSavePrompt.cs'], env=env, cwd=helpers, log=log)
    run([wine, helpers / 'PatchSavePrompt.exe', '--sign-dialog',
         r'C:\powerbi-linux-setup\unsigned\PowerBISaveDialog.dll',
         r'C:\powerbi-linux-setup\PowerBISaveDialog.dll',
         'Z:' + str(key).replace('/', '\\')], env=env, log=log)


def self_token(source):
    data = bytearray(source)
    if data[0x16f0c4:0x16f0cd] != bytes.fromhex('ff 15 3e 69 2f 02 48 8b c8'):
        raise Error('Unexpected impersonation call site')
    if data[0x16f0cd:0x16f0d3] != bytes.fromhex('ff 15 0d 75 2f 02'):
        raise Error('Unexpected impersonation call')
    offset, name = 0x2e803fa, b'ImpersonateAnonymousToken\0'
    if data[offset:offset+len(name)] != name:
        raise Error('Unexpected impersonation import')
    data[0x16f0c4:0x16f0cd] = bytes.fromhex('b9 02 00 00 00 90 90 90 90')
    data[offset:offset+len(name)] = b'ImpersonateSelf\0'.ljust(len(name), b'\0')
    return bytes(data)


def install(prefix, runtime, log):
    bin_dir = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    wine, env = runtime / 'bin/wine', wine_env(prefix)
    env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;msxml3,msxml6,msxml6r=b'
    backups = prefix / 'powerbi-linux-originals'
    backups.mkdir(exist_ok=True)
    # Validate every input before replacing any file.
    for name, expected in ORIGINALS.items():
        backup = backups / name
        check_digest(backup if backup.exists() else bin_dir / name, expected)
    # Resolve the guarded resource recipe before replacing any application file.
    # A stale recipe must fail alongside input validation, not after other patches.
    ui_name = 'Microsoft.Mashup.Client.UI.dll'
    ui_source = backups / ui_name
    if not ui_source.exists():
        ui_source = bin_dir / ui_name
    patched_ui = legacy_html.patch_ui(ui_source.read_bytes())
    windows_name = 'Microsoft.PowerBI.Client.Windows.dll'
    windows_source = backups / windows_name
    if not windows_source.exists():
        windows_source = bin_dir / windows_name
    patched_windows = signin.patch_windows(windows_source.read_bytes())
    for name in ORIGINALS:
        backup = backups / name
        if not backup.exists():
            shutil.copy2(bin_dir / name, backup)
    helpers = prefix / 'drive_c/powerbi-linux-setup'
    helpers.mkdir(exist_ok=True)
    for source in (runtime / 'helpers').iterdir():
        if source.is_file():
            shutil.copy2(source, helpers / source.name)
    key = helpers / 'stubs.snk'
    windows_input = helpers / 'Desktop-email-dialog-input.dll'
    if not key.exists():
        run([wine, helpers / 'MakeKey.exe', r'C:\powerbi-linux-setup\stubs.snk'], env=env, log=log)
    try:
        csc = r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
        (helpers/'unsigned').mkdir(exist_ok=True)
        run([wine, csc, '/nologo', '/target:library', r'/out:unsigned\WinRTStubs.dll',
             'WinRTStubs.cs'], env=env, cwd=helpers, log=log)
        # Native csc strong-name signing fails on Wine (CS1548/8013141e). dnlib
        # signs the same assembly with the locally generated key.
        run([wine,helpers/'SignStubs.exe',r'C:\powerbi-linux-setup\unsigned\WinRTStubs.dll',
             r'C:\powerbi-linux-setup\WinRTStubs.dll',r'C:\powerbi-linux-setup\stubs.snk'],env=env,log=log)
        build_native_dialog(helpers, wine, env, log, key)
        windows_input.write_bytes(patched_windows)
        for patcher, name in [('PatchShared.exe', 'Microsoft.PowerBI.Client.Shared.dll'),
                              ('PatchWinRT.exe', 'Microsoft.PowerBI.Client.Windows.dll')]:
            out = helpers / name
            source = windows_input if patcher == 'PatchWinRT.exe' else backups / name
            args = [wine, helpers / patcher, 'Z:' + str(source).replace('/', '\\'),
                    'Z:' + str(out).replace('/', '\\')]
            if patcher == 'PatchWinRT.exe':
                args.append('Z:' + str(key).replace('/', '\\'))
            run(args, env=env, log=log)
            if patcher == 'PatchWinRT.exe':
                native_out = helpers / (name + '.native')
                run([wine, helpers / 'PatchSavePrompt.exe',
                     *['Z:' + str(file).replace('/', '\\') for file in (
                         out, native_out, bin_dir / 'Microsoft.Mashup.Client.UI.dll', helpers / NATIVE_DIALOG)]],
                    env=env, log=log)
                os.replace(native_out, out)
            os.replace(out, bin_dir / name)
        patched = self_token((backups / 'msmdsrv.exe').read_bytes())
        out = bin_dir / 'msmdsrv.exe.new'
        out.write_bytes(patched)
        os.replace(out, bin_dir / 'msmdsrv.exe')
        name = 'Microsoft.Mashup.Client.UI.dll'
        out = bin_dir / (name + '.new')
        out.write_bytes(patched_ui)
        os.replace(out, bin_dir / name)
        for name in ('WinRTStubs.dll', 'PowerBIDiagnostics.dll', 'PowerBICompositionManager.dll', NATIVE_DIALOG):
            shutil.copy2(helpers / name, bin_dir / name)
        run([wine, helpers/'EnableModernEditor.exe'], env=env, log=log)
        signin.configure_browser(prefix, wine, env, helpers, log)
    finally:
        key.unlink(missing_ok=True)
        windows_input.unlink(missing_ok=True)
    return {name: digest(bin_dir/name) for name in (*ORIGINALS, 'WinRTStubs.dll',
                                                   'PowerBIDiagnostics.dll', 'PowerBICompositionManager.dll', NATIVE_DIALOG)}
