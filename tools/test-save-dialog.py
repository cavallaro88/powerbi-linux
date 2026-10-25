#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile and test a native question in synthetic forms; do not activate a patch."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'src'))
    from pbi_linux.common import Paths
    active = json.loads(Paths().active.read_text())
    prefix, runtime = Path(active['prefix']), Path(active['runtime'])
    bin_dir = prefix / 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
    desktop = bin_dir / 'Microsoft.PowerBI.Client.Windows.dll'
    before = digest(desktop)
    if before != active['patches'][desktop.name]:
        raise RuntimeError('Installed Desktop differs from its recorded hash')
    preview_input = desktop
    # An installed native confirmation is intentionally rejected by the patcher
    # as already patched. Test the preserved supported original in that case.
    remap_required = 'PowerBISaveDialog.dll' in active['patches']
    if remap_required:
        sys.path.insert(0, str(root / 'src'))
        from pbi_linux.patches import ORIGINALS, CURRENT_ORIGINALS
        preview_input = prefix / 'powerbi-linux-originals' / desktop.name
        if digest(preview_input) not in (ORIGINALS[desktop.name], CURRENT_ORIGINALS[desktop.name]):
            raise RuntimeError('Preserved original Desktop differs from the supported input')
    out = root / '.local/save-dialog' / datetime.datetime.now().strftime('test-%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, mode=0o700)
    fixture = out / 'fixture'
    fixture.mkdir()
    inputs = out / 'inputs'
    inputs.mkdir()
    shutil.copy2(runtime / 'helpers/dnlib.dll', out / 'dnlib.dll')
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG='-all',
               WINEDLLOVERRIDES='winemenubuilder.exe=d')
    for name in list(env):
        if name.startswith(('APPDOMAIN_MANAGER_', 'PBI_', 'COMPlus_', 'WEBVIEW2_')) or name in (
            'DISPLAY', 'XAUTHORITY', 'WINELOADER', 'WINESERVER', 'WINEDLLPATH', 'WINEARCH'
        ):
            env.pop(name, None)
    wine = runtime / 'bin/wine'
    compiler = r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    key = out / 'test.snk'

    def win(path):
        return 'Z:' + str(path).replace('/', chr(92))

    def run(name, args, *, failure=False, timeout=45):
        completed = subprocess.run([str(wine), *map(str, args)], env=env,
                                   capture_output=True, text=True, timeout=timeout)
        (out / (name + '.log')).write_text(completed.stdout + completed.stderr)
        if (completed.returncode == 0) == failure:
            raise RuntimeError(name + ' unexpected result; see ' + str(out / (name + '.log')))
        return completed.stdout

    def compile(name, source, destination, references=(), library=False):
        run(name, [compiler, '/nologo', '/optimize+', '/target:' + ('library' if library else 'exe'),
                   '/out:' + win(destination), *['/r:' + str(r) for r in references], win(source)])

    print('Testes sintéticos automáticos: pequenas janelas abrirão e fecharão sozinhas.', flush=True)
    print('Nenhuma opção será escolhida no seu Power BI; nenhuma correção será ativada.', flush=True)
    result = {'passed': False, 'actual_desktop_patch_activated': False,
              'existing_user_report_closed': False, 'desktop_save_discard_e2e_verified': False,
              'preview_input': 'original-backup' if remap_required else 'installed-desktop',
              'preview_requires_winrt_remapping': remap_required}
    try:
        patcher = out / 'PatchSavePrompt.exe'
        compile('compile-patcher', root / 'src/helpers/PatchSavePrompt.cs', patcher,
                [win(out / 'dnlib.dll'), 'System.Core.dll'])
        unsigned = inputs / 'PowerBISaveDialog.dll'
        native = out / 'PowerBISaveDialog.dll'
        compile('compile-dialog', root / 'src/helpers/PowerBISaveDialog.cs', unsigned,
                ['System.Windows.Forms.dll', 'System.Drawing.dll'], library=True)
        run('make-test-key', [runtime / 'helpers/MakeKey.exe', win(key)])
        run('sign-dialog', [patcher, '--sign-dialog', win(unsigned), win(native), win(key)])
        preview = out / 'Microsoft.PowerBI.Client.Windows.preview.dll'
        run('patch-desktop-preview', [patcher, win(preview_input), win(preview),
                                     win(bin_dir / 'Microsoft.Mashup.Client.UI.dll'), win(native)])
        fake_ui = fixture / 'Microsoft.Mashup.Client.UI.dll'
        fake_original = inputs / 'Microsoft.PowerBI.Client.Windows.dll'
        fake_patched = fixture / fake_original.name
        compile('compile-fixture-ui', root / 'tests/fixtures/save-dialog-ui.cs', fake_ui, library=True)
        compile('compile-fixture-desktop', root / 'tests/fixtures/save-dialog-desktop.cs', fake_original,
                [win(fake_ui), 'System.Windows.Forms.dll', 'System.Drawing.dll'], library=True)
        run('patch-fixture', [patcher, win(fake_original), win(fake_patched), win(fake_ui), win(native)])
        shutil.copy2(native, fixture / native.name)
        probe = fixture / 'SaveDialogProbe.exe'
        compile('compile-probe', root / 'tests/e2e/save-dialog-probe.cs', probe,
                [win(fake_ui), win(fake_patched), 'System.Windows.Forms.dll', 'System.Drawing.dll', 'System.Core.dll'])
        output = run('synthetic-native-dialogs', [probe], timeout=120)
        for action, expected in [('Save', 6), ('Discard', 7), ('Cancel', 2), ('Enter', 2), ('Escape', 2), ('Close', 2)]:
            if 'PASS ' + action + '=' + str(expected) not in output:
                raise RuntimeError('Missing successful action: ' + action)
        rejected = out / 'rejected.dll'
        run('reject-unsigned-dialog', [patcher, win(fake_original), win(rejected), win(fake_ui), win(unsigned)], failure=True)
        run('reject-already-patched', [patcher, win(fake_patched), win(rejected), win(fake_ui), win(native)], failure=True)
        run('reject-unrelated-assembly', [patcher, win(fake_ui), win(rejected), win(fake_ui), win(native)], failure=True)
        if rejected.exists():
            raise RuntimeError('Rejected input created an output')
        result.update(passed=True, synthetic_patched_method_verified=True,
                      localized_labels_verified=True, safe_default_verified=True,
                      owner_reenabled_verified=True, malformed_inputs_rejected=True,
                      preview_sha256=digest(preview), dialog_sha256=digest(native),
                      synthetic_dialog_output=output.strip())
    finally:
        key.unlink(missing_ok=True)
        result.update(original_sha256=before, original_preserved=digest(desktop) == before)
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        (out.parent / 'latest.txt').write_text(str(out) + '\n')
    if not result['original_preserved']:
        raise RuntimeError('Installed Desktop changed outside this test')
    print('Testes concluídos: ' + str(out), flush=True)
    print('Instalação preservada. Salvar/descartar no Desktop real ainda não foi validado.', flush=True)


if __name__ == '__main__':
    main()
