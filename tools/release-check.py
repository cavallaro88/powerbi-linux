#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject a public runtime release without evidence for every required scenario."""
import argparse
import hashlib
import json
from pathlib import Path
REQUIRED=('clean_install','desktop_pbix','pbip_relative_paths','pbir_relative_paths','csv_visual',
          'large_ui_refresh_and_visuals','save_reopen','soak_2h','interrupted_setup',
          'update_repair_rollback','uninstall_associations')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('runtime',type=Path)
p.add_argument('evidence',type=Path)
a=p.parse_args()
try:
    evidence=json.loads(a.evidence.read_text())
    h=hashlib.sha256()
    with a.runtime.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    errors=[]
    if evidence.get('runtime_sha256')!=h.hexdigest():errors.append('Evidence does not match the runtime archive')
    if evidence.get('fedora_version')!='44' or evidence.get('arch')!='x86_64' or evidence.get('display')!='wayland':
        errors.append('Evidence must identify Fedora 44 x86_64 and native Wayland')
    cases=evidence.get('cases',{})
    for name in REQUIRED:
        case=cases.get(name,{})
        if case.get('status')!='passed' or not case.get('evidence'):
            errors.append(name+': passing evidence is missing')
    if cases.get('soak_2h',{}).get('seconds',0)<7200:errors.append('Soak duration is below two hours')
    if evidence.get('runtime_provenance')!='clean-source-build':errors.append('Imported investigation runtime cannot certify a release')
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)
    print('Release evidence complete for this runtime checksum.')
except (OSError,ValueError,TypeError) as exc:
    raise SystemExit('Invalid release evidence: '+str(exc))
