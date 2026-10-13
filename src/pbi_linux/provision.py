# SPDX-License-Identifier: GPL-3.0-or-later
"""Transactional per-user provisioning, snapshots and explicit maintenance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
import zipfile
from . import assets, patches, pe_cache, webview, resources
from .common import Error, atomic_json, busy, check_digest, digest, read_json, run, wine_env

BIN = 'drive_c/Program Files/Microsoft Power BI Desktop/bin'
FLAGS = resources.BASE_BROWSER_FLAGS


def resource_root():
    override = os.environ.get('PBI_LINUX_RESOURCE_DIR')
    return Path(override) if override else Path(__file__).resolve().parents[2]


def settings(paths):
    return resources.load(paths)


def webview_config(runtime=None):
    if runtime is not None:
        return read_json(Path(runtime)/'runtime.json')['sources']['webview2']
    return read_json(resource_root()/'runtime/sources.lock.json')['webview2']


def verified_webview(prefix, runtime=None):
    expected=webview_config(runtime)
    if expected.get('distribution')=='fixed':
        directory=webview.folder(prefix,expected)
        if not directory.is_dir():
            raise Error('Fixed WebView2 runtime is not provisioned; run repair')
        return webview.verify(directory,expected)
    source=pe_cache.webview(prefix)
    if source.parent.name != expected['runtime_version']:
        raise Error('Unvalidated WebView2 version: '+source.parent.name+'; expected '+expected['runtime_version'])
    check_digest(source,expected['runtime_dll_sha256'])
    check_digest(source.with_name('msedgewebview2.exe'),expected['runtime_exe_sha256'])
    return source


def active(paths):
    result = read_json(paths.active)
    for key, base in [('prefix', paths.data/'profiles'), ('runtime', paths.data/'runtimes')]:
        file = Path(result[key])
        if not file.is_absolute() or not file.resolve().is_relative_to(base.resolve()):
            raise Error('Invalid managed installation path')
    return result


def idle(paths):
    if busy(paths):
        raise Error('Close all managed Power BI windows before maintenance')


def snapshot(source, target):
    if target.exists():
        raise Error('Snapshot target already exists')
    target.mkdir(parents=True, mode=0o700)
    try:
        run(['cp', '-a', '--reflink=auto', str(source) + '/.', target], timeout=1800)
    except Error:
        shutil.rmtree(target)
        raise


def install_runtime(paths, archive, checksum):
    archive = Path(archive).resolve()
    check_digest(archive, checksum)
    destination = paths.data / 'runtimes' / checksum
    if destination.exists():
        assets.verify_runtime(destination)
        return destination
    pending = destination.with_name('.' + checksum + '-' + uuid.uuid4().hex)
    try:
        assets.extract_runtime(archive, pending)
        os.replace(pending, destination)
    finally:
        if pending.exists():
            shutil.rmtree(pending)
    return destination


def registry(wine, env, key, name, kind, value, log):
    run([wine, 'reg.exe', 'add', key, '/v', name, '/t', kind, '/d', value, '/f'], env=env, log=log)


def stop_server(runtime, env, log):
    # A provisioning prefix is owned by this transaction, never the user's active session.
    subprocess.run([str(runtime/'bin/wineserver'), '-k'], env=env, capture_output=True)
    run([runtime/'bin/wineserver', '-w'], env=env, timeout=30, log=log)


def configure(prefix, runtime, paths, log):
    from . import legacy_html
    env, wine = wine_env(prefix), runtime/'bin/wine'
    env['WINEDLLOVERRIDES'] = 'winemenubuilder.exe=d;msxml3,msxml6,msxml6r=b'
    legacy_html.register(prefix, runtime, log)
    registry(wine, env, r'HKCU\Software\Wine\DllOverrides', 'winemenubuilder.exe', 'REG_SZ', '', log)
    registry(wine, env, r'HKCU\Software\Wine\Drivers', 'Graphics', 'REG_SZ', 'wayland', log)
    registry(wine, env, r'HKCU\Software\Wine\AppDefaults\msedgewebview2.exe', 'Version', 'REG_SZ', 'win7', log)
    registry(wine, env, r'HKCU\Software\Microsoft\Avalon.Graphics', 'DisableHWAcceleration', 'REG_DWORD', '1', log)
    # Desktop's documented policy: validated releases are managed by this project.
    registry(wine, env, r'HKLM\Software\Microsoft\Microsoft Power BI Desktop',
             'DisableUpdateNotification', 'REG_DWORD', '1', log)
    registry(wine, env, r'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments',
             'PBIDesktop.exe', 'REG_SZ', resources.browser_flags(settings(paths)), log)
    browser=webview_config(runtime)
    if browser.get('distribution')=='fixed':
        payload=assets.download(browser['url'],browser['sha256'],paths.cache/'downloads')
        source=webview.install(prefix,payload,browser,log)
        fixed_path='C:\\powerbi-linux-webview\\'+source.parent.name
        registry(wine,env,r'HKLM\Software\Policies\Microsoft\Edge\WebView2\BrowserExecutableFolder',
                 '*','REG_SZ',fixed_path,log)
    system32 = prefix/'drive_c/windows/system32'
    for file in (runtime/'dxvk').glob('*.dll'):
        shutil.copy2(file, system32/file.name)
    config = read_json(resource_root()/'runtime/sources.lock.json')
    archive = assets.download(config['selawik']['url'], config['selawik']['sha256'], paths.cache/'downloads')
    fonts = prefix/'drive_c/windows/Fonts'
    fonts.mkdir(exist_ok=True)
    shutil.copy2(resource_root()/'LICENSES/Selawik.txt', fonts/'Selawik-LICENSE.txt')
    with zipfile.ZipFile(archive) as zip_file:
        for name in zip_file.namelist():
            if name.lower().endswith('.ttf'):
                (fonts/Path(name).name).write_bytes(zip_file.read(name))
    replacements = {'Segoe UI':'Selawik', 'Segoe UI Semibold':'Selawik Semibold',
                    'Segoe UI Light':'Selawik Light', 'Segoe UI Semilight':'Selawik Semilight',
                    'Tahoma':'Selawik', 'MS Shell Dlg':'Selawik', 'MS Shell Dlg 2':'Selawik',
                    'MS Sans Serif':'Selawik', 'Microsoft Sans Serif':'Selawik'}
    for name, face in replacements.items():
        registry(wine, env, r'HKCU\Software\Wine\Fonts\Replacements', name, 'REG_SZ', face, log)
    # LOGFONTW fields: height, width, escapement, orientation, weight; byte flags; face.
    import struct
    face = 'Selawik'.encode('utf-16-le').ljust(64, b'\0')
    for name in ('MessageFont', 'StatusFont', 'CaptionFont', 'SmCaptionFont', 'MenuFont', 'IconFont'):
        raw = struct.pack('<5i8B', -12, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0) + face
        registry(wine, env, r'HKCU\Control Panel\Desktop\WindowMetrics', name, 'REG_BINARY', raw.hex(), log)
    return patches.install(prefix, runtime, log)


def activate(paths, prefix, runtime, hashes, runtime_sha):
    if paths.active.exists():
        atomic_json(paths.previous, active(paths))
    atomic_json(paths.active, {'schema':1, 'prefix':str(prefix), 'runtime':str(runtime),
                              'runtime_sha256':runtime_sha, 'patches':hashes,
                              'installed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    atomic_json(paths.settings, settings(paths))


def setup(paths, args):
    if not args.accept_license:
        raise Error('Read docs/legal.md and Microsoft installer terms; then supply --accept-license')
    config = read_json(resource_root()/'runtime/sources.lock.json')
    # Validate user-supplied files BEFORE creating an installation or running Wine.
    check_digest(args.installer, config['powerbi']['sha256'])
    browser=config['webview2']
    payload=Path(args.webview_runtime).resolve() if args.webview_runtime else assets.download(
        browser['url'],browser['sha256'],paths.cache/'downloads')
    check_digest(payload,browser['sha256'])
    dotnet = Path(args.dotnet_installer).resolve() if args.dotnet_installer else assets.download(
        config['dotnet48']['url'], config['dotnet48']['sha256'], paths.cache/'downloads')
    check_digest(dotnet, config['dotnet48']['sha256'])
    dotnet40 = Path(args.dotnet40_installer).resolve() if args.dotnet40_installer else assets.download(
        config['dotnet40']['url'], config['dotnet40']['sha256'], paths.cache/'downloads')
    check_digest(dotnet40, config['dotnet40']['sha256'])
    gecko = {arch:assets.download(config['gecko-'+arch]['url'], config['gecko-'+arch]['sha256'],
                                paths.cache/'downloads') for arch in ('x86','x86_64')}
    with paths.lock():
        idle(paths)
        if paths.active.exists():
            raise Error('Already installed; use update or repair')
        runtime = install_runtime(paths, args.runtime, args.runtime_sha256)
        if webview_config(runtime)!=browser:
            raise Error('Runtime and CLI WebView2 recipes differ; use matching release inputs')
        # A stable pending prefix makes interrupted setup resumable at stage boundaries.
        fingerprint = digest(args.installer) + args.runtime_sha256 + browser['sha256']
        import hashlib
        generation = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
        prefix = paths.data/'profiles'/generation
        prefix.mkdir(parents=True, exist_ok=True, mode=0o700)
        progress = prefix/'provision.json'
        state = read_json(progress) if progress.exists() else {'stages':[]}
        log = paths.state/'setup.log'
        env = wine_env(prefix)
        wine = runtime/'bin/wine'
        inputs = prefix/'drive_c/powerbi-linux-inputs'
        inputs.mkdir(parents=True, exist_ok=True)
        for name, source in [('dotnet40.exe',dotnet40),('dotnet48.exe',dotnet),
                             ('powerbi.exe',Path(args.installer).resolve())]:
            target = inputs/name
            if not target.exists() or digest(target) != digest(source):
                run(['cp','--reflink=auto',source,target],timeout=120)
        init_env = dict(env, WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree,mshtml=')
        net_env = dict(env, WINEDLLOVERRIDES='winemenubuilder.exe=d;fusion=b;mscoree=n;msxml3,msxml6,msxml6r=b')
        stages = [('wineboot', [wine, 'wineboot.exe', '-u'], init_env),
                  ('wayland', [wine,'reg.exe','add',r'HKCU\Software\Wine\Drivers','/v','Graphics','/d','wayland','/f'],env),
                  ('win7', [wine, 'winecfg.exe', '-v', 'win7'], env),
                  ('dotnet40', [wine, inputs/'dotnet40.exe', '/q', '/norestart'], dict(env,WINEDLLOVERRIDES='winemenubuilder.exe=d;fusion=b')),
                  ('dotnet40-install-key', [wine,'reg.exe','add',r'HKLM\Software\Microsoft\NET Framework Setup\NDP\v4\Full','/v','Install','/t','REG_DWORD','/d','1','/f'],env),
                  ('dotnet40-version-key', [wine,'reg.exe','add',r'HKLM\Software\Microsoft\NET Framework Setup\NDP\v4\Full','/v','Version','/t','REG_SZ','/d','4.0.30319','/f'],env),
                  ('mscoree', [wine,'reg.exe','add',r'HKCU\Software\Wine\DllOverrides','/v','mscoree','/d','native','/f'],env),
                  ('dotnet48', [wine, inputs/'dotnet48.exe', '/q', '/norestart'], net_env),
                  ('win10', [wine, 'winecfg.exe', '-v', 'win10'], env),
                  ('gecko-x86', [wine,'msiexec.exe','/i', 'Z:'+str(gecko['x86']).replace('/','\\'),'/qn'], env),
                  ('gecko-x86_64', [wine,'msiexec.exe','/i','Z:'+str(gecko['x86_64']).replace('/','\\'),'/qn'], env),
                  ('powerbi', [wine, inputs/'powerbi.exe', '-quiet', '-norestart', 'ACCEPT_EULA=1',
                               'DISABLE_UPDATE_NOTIFICATION=1'], env)]
        try:
            for name, command, stage_env in stages:
                if name in state['stages']:
                    continue
                print('Installing ' + name + '...', flush=True)
                # Windows ERROR_SUCCESS_REBOOT_REQUIRED (3010) arrives through
                # Wine's Unix exit status as 194. Only installers may return it.
                codes=(0,194) if name in ('dotnet40','dotnet48','powerbi') else (0,)
                run(command, env=stage_env, timeout=1800, log=log, success_codes=codes)
                stop_server(runtime, env, log)
                state['stages'].append(name)
                atomic_json(progress, state)
            # Make a supplied offline CAB available to configure without copying
            # it into the prefix or downloading it again.
            downloads=paths.cache/'downloads'
            downloads.mkdir(parents=True,exist_ok=True)
            cached=downloads/browser['sha256']
            if not cached.exists():
                run(['cp','--reflink=auto',payload,cached],timeout=120)
            hashes = configure(prefix, runtime, paths, log)
            stop_server(runtime, env, log)
            source = verified_webview(prefix,runtime)
            pe_cache.prepare(source, paths.cache/'pe'/generation)
            # Completed setup can retain verified downloads outside the prefix;
            # installer copies are unnecessary in every future repair snapshot.
            shutil.rmtree(inputs)
            activate(paths, prefix, runtime, hashes, args.runtime_sha256)
        finally:
            stop_server(runtime, env, log)
        from .desktop import integrate
        integrate(paths, args.make_default)
    print('Power BI installed. Run pbi-linux open or use the desktop menu.')


def maintain(paths, args):
    with paths.lock():
        idle(paths)
        old = active(paths)
        runtime = Path(old['runtime'])
        runtime_sha = old['runtime_sha256']
        if args.command == 'update':
            runtime = install_runtime(paths, args.runtime, args.runtime_sha256)
            runtime_sha = args.runtime_sha256
        prefix = paths.data/'profiles'/('snapshot-' + uuid.uuid4().hex[:16])
        snapshot(Path(old['prefix']), prefix)
        log, env = paths.state/'maintenance.log', wine_env(prefix)
        try:
            init_env = dict(env, WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree,mshtml=')
            run([runtime/'bin/wine', 'wineboot.exe', '-u'], env=init_env, log=log)
            hashes = configure(prefix, runtime, paths, log)
            stop_server(runtime, env, log)
            pe_cache.prepare(verified_webview(prefix,runtime), paths.cache/'pe'/prefix.name)
            activate(paths, prefix, runtime, hashes, runtime_sha)
        finally:
            stop_server(runtime, env, log)
        from .desktop import integrate
        integrate(paths)
    print('Installation activated; the previous profile is available with rollback.')


def rollback(paths):
    with paths.lock():
        idle(paths)
        previous = read_json(paths.previous)
        # Validate paths and artifacts before committing the pointer swap.
        for key, base in [('prefix', paths.data/'profiles'), ('runtime', paths.data/'runtimes')]:
            if not Path(previous[key]).resolve().is_relative_to(base.resolve()):
                raise Error('Invalid rollback path')
        assets.verify_runtime(previous['runtime'])
        for name, sha in previous['patches'].items():
            check_digest(Path(previous['prefix'])/BIN/name, sha)
        current = active(paths)
        atomic_json(paths.active, previous)
        atomic_json(paths.previous, current)
    print('Previous installation restored.')
