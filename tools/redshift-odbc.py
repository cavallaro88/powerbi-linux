#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build/probe the experimental ODBC forwarder without installing it or connecting."""
import argparse
import datetime
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pbi_linux import assets, provision
from pbi_linux.common import Error, Paths, atomic_json, check_digest, digest, read_json, wine_env

RECIPE = ROOT / 'connectors/redshift/experiment.json'
DEFINITION = RECIPE.with_name('PRIVATE_ODBC32.def')


def exports(source, recipe):
    """Reject code/stubs, changed targets and silently incomplete Engine coverage."""
    lines = [line.strip() for line in source.splitlines()
             if line.strip() and not line.lstrip().startswith(';')]
    if lines[:2] != ['LIBRARY PRIVATE_ODBC32', 'EXPORTS']:
        raise Error('Unexpected forwarder library definition')
    names = []
    for line in lines[2:]:
        match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)=odbc32\.\1', line)
        if not match:
            raise Error('Only named exports forwarded to Wine odbc32 are allowed')
        names.append(match[1])
    if (len(names) != recipe['export_count'] or len(set(names)) != len(names)
            or not set(recipe['required_engine_exports']).issubset(names)
            or set(recipe['unsupported_original_exports']).intersection(names)):
        raise Error('Incorrect export coverage')
    return names


def validate_pe(data):
    """Check the expected native x64 DLL format and absent entrypoint."""
    try:
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        signature = data[pe:pe + 4]
        machine = struct.unpack_from('<H', data, pe + 4)[0]
        characteristics = struct.unpack_from('<H', data, pe + 22)[0]
        magic = struct.unpack_from('<H', data, pe + 24)[0]
        entry = struct.unpack_from('<I', data, pe + 40)[0]
    except struct.error as exc:
        raise Error('Invalid forwarder PE header') from exc
    if (data[:2] != b'MZ' or signature != b'PE\0\0' or machine != 0x8664
            or not characteristics & 0x2000 or magic != 0x20b or entry != 0):
        raise Error('Expected an x64 PE DLL with no entrypoint')


def build(output, compiler):
    recipe = read_json(RECIPE)
    check_digest(DEFINITION, recipe['definition_sha256'])
    exports(DEFINITION.read_text(), recipe)
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    dll = output / 'PRIVATE_ODBC32.dll'
    version = subprocess.run([compiler, '--version'], capture_output=True, text=True,
                             check=True, timeout=10).stdout.splitlines()[0]
    # GNU ld otherwise hashes the output path into ImageBase, changing the DLL
    # checksum between build directories even with a zero timestamp.
    command = [compiler, '-shared', '-nostdlib', '-Wl,--entry,0',
               '-Wl,--image-base,0x2ff730000',
               '-Wl,--no-insert-timestamp', '-s', str(DEFINITION), '-o', str(dll)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output / 'build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise Error('Forwarder build failed; see build.log')
    validate_pe(dll.read_bytes())
    atomic_json(output / 'candidate.json', {
        'schema': 1, 'recipe_sha256': digest(RECIPE), 'compiler': version,
        'dll_sha256': digest(dll), 'definition_sha256': digest(DEFINITION),
        'scope': 'Experimental named forwarder; no installation or network operation',
    })
    print('Built experimental forwarder: ' + str(output))


def probe(output, baseline, candidate):
    recipe = read_json(RECIPE)
    check_digest(baseline, recipe['original_manager_sha256'])
    metadata = read_json(candidate / 'candidate.json')
    if metadata.get('schema') != 1 or metadata.get('recipe_sha256') != digest(RECIPE):
        raise Error('Candidate was built with a different recipe')
    dll = candidate / 'PRIVATE_ODBC32.dll'
    check_digest(dll, metadata['dll_sha256'])
    validate_pe(dll.read_bytes())
    paths = Paths()
    with paths.lock():
        provision.idle(paths)
        installed = provision.active(paths)
        runtime, prefix = Path(installed['runtime']), Path(installed['prefix'])
        assets.verify_runtime(runtime)
        app = prefix / provision.BIN
        check_digest(app / 'Microsoft.MashupEngine.dll', recipe['engine_sha256'])
        for name, sha in recipe['bundled_driver_sha256'].items():
            check_digest(app / 'ODBC Drivers' / name, sha)
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        wine, env = runtime / 'bin/wine', wine_env(prefix)
        win = lambda p: 'Z:' + str(p.resolve()).replace('/', '\\')
        exe = output / 'OdbcEnvironmentProbe.exe'
        results = {'passed': False, 'network_attempted': False,
                   'runtime_sha256': installed['runtime_sha256'],
                   'candidate_sha256': digest(dll), 'report_modified': False}
        try:
            commands = [
                ('compile', [r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
                             '/nologo', '/optimize+', '/out:' + win(exe),
                             win(ROOT / 'tests/e2e/odbc-environment.cs')]),
                ('baseline', [win(exe), win(app), win(baseline), 'env-failure']),
                ('candidate', [win(exe), win(app), win(dll), 'success']),
            ]
            for label, command in commands:
                result = subprocess.run([str(wine), *command], env=env,
                                        capture_output=True, text=True, timeout=45)
                (output / (label + '.log')).write_text(result.stdout + result.stderr)
                if result.returncode:
                    raise Error('Offline ODBC ' + label + ' failed; see probe logs')
            results['passed'] = True
        finally:
            atomic_json(output / 'result.json', results)
    print('Offline baseline/candidate passed: ' + str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    building = sub.add_parser('build', help='Compile own source; does not install')
    building.add_argument('--compiler', default='x86_64-w64-mingw32-gcc')
    testing = sub.add_parser('probe', help='Compare actual Engine ENV constructors; no SQL/login')
    testing.add_argument('--baseline', type=Path, required=True,
                         help='Untouched pinned Microsoft PRIVATE_ODBC32.dll backup')
    testing.add_argument('--candidate', type=Path, required=True,
                         help='Build directory containing candidate.json and DLL')
    parser.add_argument('--output', type=Path,
                        help='New evidence directory; defaults to ignored .local/odbc-bridge')
    args = parser.parse_args()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = (args.output or ROOT / '.local/odbc-bridge' / (stamp + '-' + args.operation)).resolve()
    try:
        if args.operation == 'build':
            build(output, args.compiler)
        else:
            probe(output, args.baseline.resolve(), args.candidate.resolve())
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
