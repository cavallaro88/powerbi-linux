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
from pbi_linux import legacy_html, patches, signin, text_pickers
from pbi_linux.common import Error, check_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('originals', type=Path, help='Unmodified Desktop bin directory or preserved originals')
    parser.add_argument('--version', choices=('2.158.1177.0', '2.159.883.0'), required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON evidence file; no Microsoft binaries are written')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Evidence output must be a new file')
    originals = patches.CURRENT_ORIGINALS if args.version == '2.159.883.0' else patches.ORIGINALS
    result = {'schema': 1, 'date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'powerbi_version': args.version, 'scope': 'Offline original-file/resource guards only; not native UI or release certification',
              'status': 'failed', 'files': {}}
    try:
        # Verify all originals before running a transformation.
        for name, expected in originals.items():
            check_digest(args.originals / name, expected)
        for name, transform in (
            ('Microsoft.Mashup.Client.UI.dll', legacy_html.patch_ui),
            ('Microsoft.PowerBI.Client.Windows.dll', lambda data: signin.patch_windows(data, originals['Microsoft.PowerBI.Client.Windows.dll'])),
            ('msmdsrv.exe', patches.self_token),
        ):
            source = (args.originals / name).read_bytes()
            output = transform(source)
            if len(output) != len(source):
                raise Error('A fixed-size assembly patch changed the file length')
            result['files'][name] = {'original_sha256': hashlib.sha256(source).hexdigest(),
                                      'patched_sha256': hashlib.sha256(output).hexdigest(), 'length_preserved': True}
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
