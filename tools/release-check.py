#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject a runtime release without evidence for its exact application tuple."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

REQUIRED = ('clean_install', 'desktop_pbix', 'pbip_relative_paths', 'pbir_relative_paths',
            'csv_visual', 'large_ui_refresh_and_visuals', 'save_reopen', 'soak_2h',
            'interrupted_setup', 'update_repair_in_place', 'uninstall_associations')


def validate(runtime, evidence):
    checksum = hashlib.sha256()
    with runtime.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            checksum.update(block)
    errors = []
    if evidence.get('runtime_sha256') != checksum.hexdigest():
        errors.append('Evidence does not match the runtime archive')
    with tarfile.open(runtime) as archive:
        member = archive.getmember('runtime.json')
        if not member.isfile() or member.size > 8 * 1024**2:
            raise ValueError('Invalid runtime manifest entry')
        with archive.extractfile(member) as stream:
            manifest = json.load(stream)
    sources = manifest.get('sources', {})
    expected = {'powerbi_version': sources.get('powerbi', {}).get('version'),
                'webview2_version': sources.get('webview2', {}).get('runtime_version')}
    for field, version in expected.items():
        if not version or evidence.get(field) != version:
            errors.append(field + ': evidence must match the runtime source recipe')
    if (evidence.get('fedora_version') != '44' or evidence.get('arch') != 'x86_64' or
            evidence.get('display') != 'wayland'):
        errors.append('Evidence must identify Fedora 44 x86_64 and native Wayland')
    cases = evidence.get('cases', {})
    for name in REQUIRED:
        case = cases.get(name, {})
        if case.get('status') != 'passed' or not case.get('evidence'):
            errors.append(name + ': passing evidence is missing')
    if cases.get('soak_2h', {}).get('seconds', 0) < 7200:
        errors.append('Soak duration is below two hours')
    if evidence.get('runtime_provenance') != 'clean-source-build':
        errors.append('Imported investigation runtime cannot certify a release')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    try:
        errors = validate(args.runtime, json.loads(args.evidence.read_text()))
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError) as exc:
        parser.exit(1, 'Invalid release evidence: ' + str(exc) + '\n')
    if errors:
        print('\n'.join(errors))
        return 1
    print('Release evidence complete for this runtime checksum, Power BI and WebView2 versions.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
