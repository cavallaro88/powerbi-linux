# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from . import __version__, assets, launch, provision, desktop
from .common import Error, Paths, busy, read_json, check_digest, atomic_json


def doctor(paths):
    checks = []
    components = {}
    def add(name, ok, detail):
        checks.append({'name':name, 'ok':bool(ok), 'detail':detail})
    release = Path('/etc/os-release').read_text()
    add('fedora', '\nID=fedora\n' in '\n'+release, 'Fedora 44 is the tested target; other Fedora releases are experimental')
    add('architecture', os.uname().machine == 'x86_64', os.uname().machine)
    display = os.environ.get('WAYLAND_DISPLAY', '')
    socket = Path(display) if display.startswith('/') else Path(os.environ.get('XDG_RUNTIME_DIR', '/nonexistent'))/display
    add('wayland', display and socket.is_socket(), 'Native Wayland session required')
    for tool in ('systemd-run','ntlm_auth','cabextract'):
        add(tool, shutil.which(tool), tool + ' must be installed')
    for library in ('libvulkan.so.1','libodbc.so.2'):
        try:
            ctypes.CDLL(library)
            add(library,True,'Host library is available')
        except OSError:
            add(library,False,'Install RPM dependencies with DNF')
    bus = subprocess.run(['systemctl','--user','show-environment'], capture_output=True, timeout=5)
    add('user-service-manager', bus.returncode == 0, 'A working systemd user session is required')
    add('installation', paths.active.exists(), 'Run setup to create a managed installation')
    if paths.active.exists():
        try:
            installed = provision.active(paths)
            manifest = assets.verify_runtime(installed['runtime'])
            components = {'runtime':manifest.get('version','unknown'), 'powerbi':'2.158.1177.0'}
            for name in ('wine','dxvk'):
                components[name] = manifest.get('sources',{}).get(name,{})
            components['memory'] = provision.settings(paths)
            for name, sha in installed['patches'].items():
                check_digest(Path(installed['prefix'])/provision.BIN/name, sha)
            add('integrity', True, 'Runtime and installed patches verified')
            source = provision.verified_webview(Path(installed['prefix']),Path(installed['runtime']))
            components['webview2'] = source.parent.name
            add('pe-cache', provision.pe_cache.valid(source, paths.cache/'pe'/Path(installed['prefix']).name), 'Run repair if the cache is stale')
        except (Error, OSError, KeyError) as exc:
            add('integrity', False, str(exc))
    return {'schema':1, 'version':__version__, 'ok':all(c['ok'] for c in checks), 'checks':checks, 'components':components,
            'limitations':['Microsoft sign-in and cloud publishing are unavailable',
                           'The general OneLake source chooser is blocked; use Get Data > Text/CSV for local CSV files',
                           'Synthetic model validation does not certify every enterprise report or connector']}


def parser():
    p = argparse.ArgumentParser(prog='pbi-linux', description='Community Power BI compatibility tools for Fedora')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('setup', help='Create a per-user installation from verified inputs')
    for name in ('installer','runtime','runtime-sha256'):
        setup.add_argument('--'+name, required=True)
    setup.add_argument('--webview-runtime',help='Optional offline fixed-version CAB matching the release lock')
    setup.add_argument('--dotnet-installer')
    setup.add_argument('--dotnet40-installer')
    setup.add_argument('--accept-license', action='store_true')
    setup.add_argument('--make-default', action='store_true')
    opening = sub.add_parser('open', help='Open a report or an empty Desktop window')
    opening.add_argument('file', nargs='?')
    opening.add_argument('--diagnostics', action='store_true', help='Opt in to local CDP for a disposable developer test session')
    opening.add_argument('--desktop', action='store_true', help=argparse.SUPPRESS)
    diagnosis = sub.add_parser('doctor', help='Check prerequisites and installation integrity')
    diagnosis.add_argument('--json', action='store_true')
    sub.add_parser('repair', help='Repair a snapshot while preserving the current installation')
    profile=sub.add_parser('profile',help='Set memory limits for the next session')
    profile.add_argument('name',choices=('normal','large'))
    update = sub.add_parser('update', help='Activate an explicitly supplied runtime release')
    update.add_argument('--runtime', required=True)
    update.add_argument('--runtime-sha256', required=True)
    sub.add_parser('rollback', help='Restore the previous installation')
    uninstall = sub.add_parser('uninstall', help='Remove per-user desktop integration; preserve data by default')
    uninstall.add_argument('--purge', action='store_true', help='Delete managed prefixes, runtime, cache and settings')
    session = sub.add_parser('_session', help='Internal session service')
    session.add_argument('--diagnostics', action='store_true')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    paths = Paths()
    try:
        if args.command == 'setup':
            provision.setup(paths, args)
        elif args.command == 'open':
            launch.open_file(paths, args.file, diagnostics=args.diagnostics)
        elif args.command == 'doctor':
            result = doctor(paths)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                for check in result['checks']:
                    print(('OK   ' if check['ok'] else 'FAIL ') + check['name'] + ': ' + check['detail'])
            return 0 if result['ok'] else 1
        elif args.command in ('repair','update'):
            provision.maintain(paths, args)
        elif args.command == 'profile':
            with paths.lock():
                config=provision.settings(paths)
                config.update(memory_profile=args.name,webview_heap_mb=512,
                              memory_max='10G' if args.name=='large' else '6G',
                              swap_max='4G' if args.name=='large' else '2G')
                atomic_json(paths.settings,config)
            print('Memory profile '+args.name+' selected. Close and reopen Power BI to apply it.')
        elif args.command == 'rollback':
            provision.rollback(paths)
        elif args.command == 'uninstall':
            with paths.lock():
                provision.idle(paths)
                desktop.remove(paths)
                if args.purge:
                    for directory in (paths.data, paths.cache, paths.config):
                        if directory.is_symlink():
                            raise Error('Refusing to purge a symlinked managed directory')
                        if directory.exists():
                            shutil.rmtree(directory)
            print('Desktop integration removed.' + (' Managed data deleted.' if args.purge else ' Managed data preserved.'))
        elif args.command == '_session':
            launch.broker(paths, diagnostics=args.diagnostics)
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        message = str(exc)
        print('pbi-linux: ' + message, file=sys.stderr)
        if getattr(args, 'desktop', False) and shutil.which('zenity'):
            subprocess.run(['zenity','--error','--title=Power BI Desktop','--text='+message], capture_output=True)
        return 1
    return 0
