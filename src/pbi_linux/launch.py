# SPDX-License-Identifier: GPL-3.0-or-later
"""A user service owns all Wine processes; a private socket accepts file opens."""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from .common import Error, Paths, busy, installation_token, check_digest, read_json, run
from .provision import active, BIN, settings, verified_webview
from .theme import ThemeSync
from . import pe_cache, resources, platforms

def session_unit(data):
    token = installation_token(data)
    return 'pbi-linux-session' + ('-' + token if token else '') + '.service'


UNIT = session_unit(Paths().data)


def file_argument(value):
    if not value:
        return None
    path = Path(value).expanduser().absolute()
    if path.suffix.lower() not in ('.pbix', '.pbip', '.pbir') or not path.is_file():
        raise Error('Select an existing PBIX, PBIP or PBIR file')
    # Retain the logical path: project-relative links should resolve as the user opened them.
    return str(path)


def environment(paths, installation):
    runtime, prefix = Path(installation['runtime']), Path(installation['prefix'])
    env = dict(os.environ)
    for name in list(env):
        if name.startswith(('PBI_', 'COMPlus_', 'APPDOMAIN_MANAGER_', 'WEBVIEW2_')):
            env.pop(name, None)
    env.pop('DISPLAY', None)
    env.pop('XAUTHORITY', None)
    for name in ('WINELOADER', 'WINESERVER', 'WINEDLLPATH', 'WINEARCH'):
        env.pop(name, None)
    env.update(WINEPREFIX=str(prefix), WINEDEBUG='-all,err+all', PBI_COMPOSITION='1',
               PBI_CULTURE_WORKAROUND='1', PBI_CGROUP_MEMORY='1',
               APPDOMAIN_MANAGER_ASM='PowerBICompositionManager', APPDOMAIN_MANAGER_TYPE='CompositionManager',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;msxml3,msxml6,msxml6r=b;d3d9,d3d10core,d3d11,dxgi,dcomp=n,b',
               LIB_ODBC_DRIVER_MANAGER='libodbc.so.2',
               DXVK_LOG_PATH=str(paths.state), DXVK_LOG_LEVEL='error')
    config = settings(paths)
    env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = resources.browser_flags(config)
    cache = paths.cache/'pe'/prefix.name
    browser=verified_webview(prefix,runtime)
    if browser.parent.parent.name=='powerbi-linux-webview':
        env['WEBVIEW2_BROWSER_EXECUTABLE_FOLDER']='C:\\powerbi-linux-webview\\'+browser.parent.name
    if pe_cache.valid(browser, cache):
        env['PBI_PE_SECTION_CACHE'] = str(cache)
    else:
        # Missing or stale backing must never be used, and open never rebuilds it.
        print('PE cache is stale; using the regular Wine loader. Run pbi-linux repair.', file=sys.stderr)
    for name, sha in installation['patches'].items():
        check_digest(prefix/BIN/name, sha)
    return env


def request(paths, filename, diagnostics=False):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(20)
        sock.connect(str(paths.socket))
        sock.sendall(json.dumps({'file':filename,'diagnostics':diagnostics}).encode() + b'\n')
        response = bytearray()
        while not response.endswith(b'\n'):
            chunk = sock.recv(4096)
            if not chunk or len(response) > 65536:
                raise Error('Invalid session response')
            response.extend(chunk)
        value = json.loads(response)
        if not value.get('ok'):
            raise Error(value.get('error', 'Power BI launch failed'))
        return value


def open_file(paths, value, diagnostics=False):
    filename = file_argument(value)
    unit = session_unit(paths.data)
    with paths.lock('maintenance'):
        if paths.maintenance.exists():
            raise Error('In-place maintenance did not finish. Run repair or repeat update '
                        'before opening Power BI; no automatic rollback is available.')
        if not paths.active.is_file():
            raise Error('Power BI is not set up for this user. Run pbi-linux setup --help to prepare the installation.')
        installation = active(paths)
        from .desktop import refresh_icon
        refresh_icon(paths, installation)
        if paths.socket.exists():
            try:
                return request(paths, filename, diagnostics)
            except (ConnectionRefusedError, FileNotFoundError):
                paths.socket.unlink(missing_ok=True)
        if busy(paths):
            raise Error('This installation already has Wine processes without a reachable session. Close its Power BI windows before reopening')
        supported, detail = platforms.status()
        if not supported:
            raise Error(detail)
        if os.uname().machine != 'x86_64':
            raise Error('Only x86_64 is supported')
        display = os.environ.get('WAYLAND_DISPLAY', '')
        socket_path = Path(display) if display.startswith('/') else Path(os.environ.get('XDG_RUNTIME_DIR', '/nonexistent'))/display
        if not display or not socket_path.is_socket():
            raise Error('A native Wayland desktop session is required')
        if not shutil.which('ntlm_auth'):
            raise Error(platforms.ntlm_help())
        config = settings(paths)
        # Forward only graphical session variables to the service; its process does not
        # inherit arbitrary WINEPREFIX, debugging or diagnostic overrides.
        command = ['systemd-run', '--user', '--unit='+unit, '--collect',
                   '-p', 'Type=exec', '-p', 'KillMode=mixed', '-p', 'TimeoutStopSec=10s', '-p', 'TimeoutAbortSec=1s', '-p', 'LimitCORE=0']
        for prop in resources.service_properties(config):
            command += ['-p', prop]
        for name in ('PATH','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_CURRENT_DESKTOP','PBI_LINUX_RESOURCE_DIR'):
            if name in os.environ:
                command.append('--setenv='+name+'='+os.environ[name])
        command.append('--setenv=PYTHONPATH='+str(Path(__file__).resolve().parent.parent))
        command += [sys.executable, '-m', 'pbi_linux', '_session']
        if diagnostics:
            command.append('--diagnostics')
        run(command)
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            if paths.socket.exists():
                try:
                    return request(paths, filename, diagnostics)
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
            time.sleep(.1)
        raise Error('Session could not start; see journalctl --user -u '+unit)


def broker(paths, diagnostics=False):
    paths.create()
    installation = active(paths)
    env = environment(paths, installation)
    prefix, runtime = Path(installation['prefix']), Path(installation['runtime'])
    flags = env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS']
    if diagnostics:
        captures = paths.state/'diagnostic-captures'
        captures.mkdir(exist_ok=True, mode=0o700)
        env['PBI_WAYLAND_CAPTURE_DIR'] = str(captures)
        env['PBI_DIAGNOSTICS'] = '1'
        env['PBI_COMPOSITION_DIAG'] = '1'
        env['WINEDEBUG'] += ',warn+dcomp'
        flags += ' --remote-debugging-port=0'
        env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = flags
    # Elevated WebView2 hosts can ignore environment overrides. Set the effective
    # prefix policy once at session startup so heap/test settings really apply.
    run([runtime/'bin/wine', 'reg.exe', 'add',
         r'HKLM\Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments',
         '/v', 'PBIDesktop.exe', '/t', 'REG_SZ', '/d', flags, '/f'], env=env, log=paths.state/'session.log')
    children = []
    started = False
    theme_sync = ThemeSync(paths, runtime, env)
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(paths.socket))
        os.chmod(paths.socket, 0o600)
        server.listen(8)
        server.settimeout(1)
        def terminate(signum, frame):
            raise SystemExit(0)
        previous_term = signal.signal(signal.SIGTERM, terminate)
        try:
            theme_sync.start()
            idle_since = time.monotonic()
            while True:
                children = [c for c in children if c.poll() is None]
                if children:
                    idle_since = time.monotonic()
                elif time.monotonic()-idle_since > (10 if started else 30):
                    break
                try:
                    client, _ = server.accept()
                except socket.timeout:
                    continue
                with client:
                    client.settimeout(5)
                    try:
                        body = bytearray()
                        while not body.endswith(b'\n'):
                            chunk = client.recv(4096)
                            if not chunk or len(body) > 65536:
                                raise Error('Invalid open request')
                            body.extend(chunk)
                        value = json.loads(body)
                        if bool(value.get('diagnostics', False)) != diagnostics:
                            raise Error('Close the current session before switching diagnostic mode')
                        filename = file_argument(value.get('file'))
                        args = [runtime/'bin/wine', 'PBIDesktop.exe']
                        if filename:
                            converted = run([runtime/'bin/winepath', '-w', filename], env=env).strip()
                            args.append(converted)
                        log_path = paths.state/'session.log'
                        with log_path.open('ab') as log:
                            child = subprocess.Popen([str(x) for x in args], cwd=prefix/BIN, env=env,
                                                     stdout=log, stderr=log, stdin=subprocess.DEVNULL)
                        children.append(child)
                        started = True
                        idle_since = time.monotonic()
                        answer = {'ok':True, 'pid':child.pid}
                    except (Error, ValueError, OSError) as exc:
                        answer = {'ok':False, 'error':str(exc)}
                    client.sendall(json.dumps(answer).encode()+b'\n')
        finally:
            theme_sync.close()
            paths.socket.unlink(missing_ok=True)
            # Stop this prefix's server before systemd escalates to SIGKILL.
            # A normal Desktop exit and `systemctl stop` follow the same path.
            # Other prefixes have different servers and remain unaffected.
            try:
                subprocess.run([runtime/'bin/wineserver','-k'],env=env,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
                subprocess.run([runtime/'bin/wineserver','-w'],env=env,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            except (OSError,subprocess.TimeoutExpired):
                # The cgroup still provides the bounded final cleanup.
                pass
            signal.signal(signal.SIGTERM, previous_term)
    # Once the last tracked Desktop exits, systemd stops this service's remaining
    # processes. Other prefixes and services are outside its control group.
