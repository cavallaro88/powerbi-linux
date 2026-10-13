#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate the reviewed Neutron range, optionally against a local upstream checkout."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate(ledger, checkout=None):
    lock = json.loads((ROOT/'runtime/sources.lock.json').read_text())
    if ledger['baseline'] != lock['neutron']['commit']:
        raise ValueError('Production Neutron base changed; review the range again')
    commits, patches = ledger['commits'], ledger['patches']
    if len(commits) != ledger['commit_count'] or len({c['commit'] for c in commits}) != len(commits):
        raise ValueError('Missing or duplicate commit decisions')
    if len(patches) != ledger['changed_patch_files'] or len({p['id'] for p in patches}) != len(patches):
        raise ValueError('Missing or duplicate patch decisions')
    if dict(Counter(p['status'] for p in patches)) != ledger['patch_decision_counts']:
        raise ValueError('Patch decision summary is stale')
    ids = {p['id'] for p in patches}
    for commit in commits:
        if not commit['decision'] or not commit['reason'] or not set(commit['patch_decisions']).issubset(ids):
            raise ValueError('Unreviewed commit or unknown patch decision')
    for patch in patches:
        if not patch['reason'] or patch['status'] == 'pending-review':
            raise ValueError('Unreviewed patch')
    for candidate in ledger['staged_candidates']:
        name = candidate['candidate']
        if Path(name).name != name or candidate['production_enabled']:
            raise ValueError('Candidate escaped its scope or was enabled without an adoption review')
        if hashlib.sha256((ROOT/'runtime/candidates'/name).read_bytes()).hexdigest() != candidate['sha256']:
            raise ValueError('Candidate changed since review: ' + name)
    if checkout:
        def git(*args):
            return subprocess.check_output(['git', '-C', str(checkout), *args], timeout=30)
        if git('rev-parse', 'HEAD').decode().strip() != ledger['reviewed_head']:
            raise ValueError('Checkout HEAD differs from reviewed revision; assess new commits before claiming sync')
        actual = git('rev-list', ledger['baseline']+'..'+ledger['reviewed_head']).decode().splitlines()
        if set(actual) != {c['commit'] for c in commits}:
            raise ValueError('Upstream commit range does not match the reviewed range')
        for patch in patches:
            actual_hash = hashlib.sha256(git('show', ledger['reviewed_head']+':'+patch['path'])).hexdigest()
            if actual_hash != patch['sha256']:
                raise ValueError('Upstream patch differs from review: ' + patch['id'])
    return {'passed': True, 'reviewed_commits': len(commits), 'reviewed_patch_files': len(patches),
            'reviewed_head': ledger['reviewed_head'], 'decisions': ledger['patch_decision_counts'],
            'staged_candidates': len(ledger['staged_candidates']),
            'upstream_checkout_verified': bool(checkout), 'production_runtime_patches_enabled': False,
            'scope': 'Review/provenance consistency; not compilation or GUI certification'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, help='Optional existing neutron-wine Git checkout; never fetched or modified')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = validate(json.loads((ROOT/'runtime/upstream/neutron-2026-10-18.json').read_text()), args.checkout)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit('Neutron audit failed: ' + str(exc)) from exc
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
