#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check guarded Desktop resources offline, without installing or activating them."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import autorecovery, dialog_serializers, legacy_html, options_show, patches, signin, text_pickers
from pbi_linux.common import Error, check_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('originals', type=Path, help='Unmodified Desktop bin directory or preserved originals')
    parser.add_argument('--version', choices=tuple(patches.RECIPES), required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON evidence file; no Microsoft binaries are written')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Evidence output must be a new file')
    originals = patches.RECIPES[args.version]
    # The dialog patches are verified on the builds in DIALOG_RECIPES only, as in setup.
    verified = args.version in patches.DIALOG_RECIPES
    windows = autorecovery.patch_windows if verified else (lambda data: data)
    dialogs = ((lambda data: options_show.patch_ui(dialog_serializers.patch_ui(data)))
               if verified else (lambda data: data))
    result = {'schema': 1, 'date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'powerbi_version': args.version, 'scope': 'Offline original-file/resource guards only; not native UI or release certification',
              'status': 'failed', 'files': {}}
    try:
        # Verify all originals before running a transformation.
        for name, expected in originals.items():
            check_digest(args.originals / name, expected)
        for name, transform in (
            ('Microsoft.Mashup.Client.UI.dll', lambda data: dialogs(legacy_html.patch_ui(data))),
            ('Microsoft.PowerBI.Client.Windows.dll', lambda data: windows(signin.patch_windows(data, originals['Microsoft.PowerBI.Client.Windows.dll']))),
            ('msmdsrv.exe', patches.self_token),
        ):
            source = (args.originals / name).read_bytes()
            output = transform(source)
            if len(output) != len(source):
                raise Error('A fixed-size assembly patch changed the file length')
            result['files'][name] = {'original_sha256': hashlib.sha256(source).hexdigest(),
                                      'patched_sha256': hashlib.sha256(output).hexdigest(), 'length_preserved': True}
        # PBIDesktop.exe.config is changed only for builds whose original is known.
        config_hash = patches.CONFIG_ORIGINALS.get(args.version)
        config = args.originals / patches.DESKTOP_CONFIG
        if config_hash:
            check_digest(config, config_hash)
            source = config.read_bytes()
            output = patches.patch_config(source)
            result['files'][patches.DESKTOP_CONFIG] = {'original_sha256': config_hash,
                                                       'patched_sha256': hashlib.sha256(output).hexdigest()}
        else:
            result['desktop_config'] = 'not changed: no verified original for this build'
        picker = args.originals / text_pickers.DOCUMENT
        if picker.is_file():
            source = picker.read_bytes()
            output = text_pickers.patch_document(source)
            result['files'][text_pickers.DOCUMENT] = {'original_sha256': hashlib.sha256(source).hexdigest(),
                                                       'patched_sha256': hashlib.sha256(output).hexdigest()}
        else:
            result['text_picker'] = 'not checked: document is not in this originals directory'
        result['status'] = 'passed'
    except (Error, OSError) as exc:
        result['error'] = str(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'].upper() + ': ' + str(args.output))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
