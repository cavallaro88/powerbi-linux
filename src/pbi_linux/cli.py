# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from . import __version__, assets, launch, provision, desktop, resources, legacy_html, signin, connectors, patches, text_pickers, onboarding
from .common import Error, Paths, busy, read_json, check_digest, atomic_json, digest


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
            components = {'runtime': manifest.get('version', 'unknown'),
                          'powerbi': installed.get('powerbi_version', manifest.get('sources', {}).get('powerbi', {}).get('version', 'unknown'))}
            provision.require_recipe(installed, installed['runtime'])
            for name in ('wine','dxvk'):
                components[name] = manifest.get('sources',{}).get(name,{})
            components['memory'] = provision.settings(paths)
            try:
                connector = connectors.status(installed['prefix'])
                components['connectors'] = [connector]
                add('connectors', connector['state'] != 'installed' or connector['verified'], connector['detail'])
            except (Error, OSError, KeyError, ValueError) as exc:
                add('connectors', False, str(exc))
            for name, sha in installed['patches'].items():
                check_digest(Path(installed['prefix'])/provision.BIN/name, sha)
            add('integrity', True, 'Runtime and installed patches verified')
            source = provision.verified_webview(Path(installed['prefix']),Path(installed['runtime']))
            components['webview2'] = source.parent.name
            add('pe-cache', provision.pe_cache.valid(source, paths.cache/'pe'/Path(installed['prefix']).name), 'Run repair if the cache is stale')
            try:
                missing = legacy_html.missing_registrations(installed['prefix'])
                issues = []
                if missing:
                    issues.append('Missing registry entries: ' + ', '.join(missing))
                if installed['patches'].get('Microsoft.Mashup.Client.UI.dll') != legacy_html.patched_hash(components['powerbi']):
                    issues.append('Legacy HTML assembly patch is missing or outdated')
                add('legacy-html', not issues,
                    '; '.join(issues) + '; close Desktop and run pbi-linux repair' if issues else
                    'Wine HTML registrations, credential dialog, source list, permissions serializer and Options layout patches are present')
            except (Error, OSError, ValueError) as exc:
                add('legacy-html', False, str(exc))
            try:
                assembly = Path(installed['prefix']) / provision.BIN / 'Microsoft.PowerBI.Client.Windows.dll'
                patched = signin.resource_hash(assembly.read_bytes()) == signin.RESOURCE_PATCHED_SHA256
                add('sign-in-dialog', patched,
                    'Email dialog serializer patch is present' if patched else
                    'Email dialog serializer is outdated; close Desktop and run pbi-linux repair')
                cache_patched = patches.CACHE_COMPAT in installed['patches'] and b'PowerBICacheCompatibility' in assembly.read_bytes()
                add('cache-restore', cache_patched,
                    'Linguistic JSON normalization is present' if cache_patched else
                    'Cache compatibility patch is missing; close Desktop and run repair')
                frame_patched = patches.WINDOW_FRAME in installed['patches'] and b'PowerBIWindowFrame' in assembly.read_bytes()
                add('window-frame', frame_patched,
                    'Custom client frame and transparent resize zones are present' if frame_patched else
                    'Window frame correction is missing; close Desktop and run repair')
            except (Error, OSError, ValueError) as exc:
                add('sign-in-dialog', False, str(exc))
            try:
                picker_patched = (installed['patches'].get(text_pickers.DOCUMENT) == text_pickers.PATCHED_SHA256
                                  and digest(Path(installed['prefix']) / provision.BIN / text_pickers.DOCUMENT)
                                  == text_pickers.PATCHED_SHA256)
                add('text-pickers', picker_patched,
                    'In-page font and size selectors are present' if picker_patched else
                    'Text picker correction is missing; close Desktop and run repair')
            except (Error, OSError, ValueError) as exc:
                add('text-pickers', False, str(exc))
        except (Error, OSError, KeyError) as exc:
            add('integrity', False, str(exc))
    return {'schema':1, 'version':__version__, 'ok':all(c['ok'] for c in checks), 'checks':checks, 'components':components,
            'limitations':['Cloud publishing, real-server TLS and untested connector operations are not certified',
                           'The general OneLake source chooser has not been revalidated after browser sign-in; direct Text/CSV passed',
                           'Synthetic model validation does not certify every enterprise report or connector']}


def parser():
    p = argparse.ArgumentParser(prog='pbi-linux', description='Community Power BI compatibility tools for Fedora')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='command', required=True)
    setup = sub.add_parser('setup', help='Guide installation using validated release downloads or local files')
    for name in ('installer','runtime','runtime-sha256'):
        setup.add_argument('--'+name, help={'installer':'Optional official Power BI x64 EXE matching the validated version',
                           'runtime':'Optional local project runtime archive (requires --runtime-sha256)',
                           'runtime-sha256':'SHA-256 of the supplied runtime archive'}[name])
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
    connector = sub.add_parser('connector', help='Install or inspect optional original database providers')
    connector.add_argument('operation', choices=('status', 'install'))
    connector.add_argument('name', choices=('mysql',))
    connector.add_argument('--accept-license', action='store_true')
    profile=sub.add_parser('profile',help='Show or set optional resource limits for the next session')
    profile.add_argument('name',nargs='?',choices=('unlimited','normal','large'))
    def option_type(parse):
        def check(value):
            try:
                return parse(value)
            except Error as exc:
                raise argparse.ArgumentTypeError(str(exc)) from exc
        return check
    profile.add_argument('--memory-max',type=option_type(resources.memory_limit),help='RAM limit: unlimited (default), 6G, 1024M, etc.')
    profile.add_argument('--swap-max',type=option_type(lambda v:resources.memory_limit(v,swap=True)),help='Swap limit: unlimited (default), 2G, or 0 to disable swap')
    profile.add_argument('--cpu-quota',type=option_type(resources.cpu_limit),help='CPU quota: unlimited (default); 100%% equals one logical CPU')
    profile.add_argument('--webview-heap',dest='webview_heap_mb',type=option_type(resources.heap_limit),help='V8 old-space cap: auto (default) or 128–8192 MiB')
    profile.add_argument('--renderer-process-limit',type=option_type(resources.renderer_limit),help='auto (default) or 1–128 renderer processes')
    profile.add_argument('--browser-mode',choices=('standard','economy'),help='standard (default) or opt-in economy browser flags')
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
            provision.setup(paths, onboarding.prepare(paths, args))
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
        elif args.command == 'connector':
            if args.operation == 'install':
                result = connectors.install(paths, accept_license=args.accept_license)
            else:
                result = connectors.status(provision.active(paths)['prefix'])
            print(json.dumps(result, indent=2))
        elif args.command in ('repair','update'):
            provision.maintain(paths, args)
        elif args.command == 'profile':
            changes={key:getattr(args,key) for key in ('memory_max','swap_max','cpu_quota',
                     'webview_heap_mb','renderer_process_limit','browser_mode') if getattr(args,key) is not None}
            if args.name is None and not changes:
                print(json.dumps(provision.settings(paths),indent=2))
                return 0
            with paths.lock():
                config=provision.settings(paths)
                if args.name is not None:
                    config.update(resources.preset(args.name))
                config.update(changes)
                if changes:
                    config['memory_profile']='custom'
                atomic_json(paths.settings,resources.validate(config))
            print('Resource profile '+config['memory_profile']+' selected. Close all Power BI windows and reopen to apply it.')
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
    except KeyboardInterrupt:
        message = 'Setup interrupted. Run setup again with the same inputs to resume completed stages.' if args.command == 'setup' else 'Operation interrupted.'
        print('pbi-linux: ' + message, file=sys.stderr)
        return 130
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        message = str(exc)
        print('pbi-linux: ' + message, file=sys.stderr)
        if getattr(args, 'desktop', False) and shutil.which('zenity'):
            subprocess.run(['zenity','--error','--title=Power BI Desktop','--text='+message], capture_output=True)
        return 1
    return 0
