# SPDX-License-Identifier: GPL-3.0-or-later
"""A user service owns all Wine processes; a private socket accepts file opens."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from .common import Error, Paths, busy, installation_token, check_digest, read_json, run, wine_processes
from .provision import active, BIN, settings, verified_webview
from .theme import ThemeSync
from . import patches, pe_cache, resources, platforms

def session_unit(data):
    token = installation_token(data)
    return 'pbi-linux-session' + ('-' + token if token else '') + '.service'


def __getattr__(name):
    # UNIT is computed on use, so a bad XDG variable reaches main's error
    # message instead of failing the import with a traceback.
    if name == 'UNIT':
        return session_unit(Paths().data)
    raise AttributeError('module ' + repr(__name__) + ' has no attribute ' + repr(name))


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
    if patches.DESKTOP_CONFIG not in installation['patches']:
        # A profile repaired before PBIDesktop.exe.config named the manager. The CLR
        # clears these variables after reading them, so only this first Desktop gets
        # the manager; a Desktop it starts itself crashes. Repair moves it into the config.
        env.update(APPDOMAIN_MANAGER_ASM=patches.MANAGER_ASSEMBLY, APPDOMAIN_MANAGER_TYPE=patches.MANAGER_TYPE)
    env.update(WINEPREFIX=str(prefix), WINEDEBUG='-all,err+all', PBI_COMPOSITION='1',
               PBI_CULTURE_WORKAROUND='1', PBI_CGROUP_MEMORY='1',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;msxml3,msxml6,msxml6r=b;d3d9,d3d10core,d3d11,dxgi,dcomp=n,b',
               LIB_ODBC_DRIVER_MANAGER='libodbc.so.2',
               DXVK_LOG_PATH=str(paths.state), DXVK_LOG_LEVEL='error')
    config = settings(paths)
    env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = resources.browser_flags(config)
    cache = paths.cache/'pe'/prefix.name
    browser=verified_webview(prefix,runtime)
    if browser.parent.parent.name=='powerbi-linux-webview':
        env['WEBVIEW2_BROWSER_EXECUTABLE_FOLDER']='C:\\powerbi-linux-webview\\'+browser.parent.name
    if pe_cache.refresh(browser, cache):
        env['PBI_PE_SECTION_CACHE'] = str(cache)
    else:
        # Missing or stale backing must never be used, and open never rebuilds it.
        print('PE cache is stale; using the regular Wine loader. Run pbi-linux repair.', file=sys.stderr)
    for name, sha in installation['patches'].items():
        check_digest(prefix/BIN/name, sha)
    return env


STUCK_HELP = 'If Power BI is stuck, run pbi-linux stop to force it to quit (unsaved changes are lost)'


def request(paths, filename, diagnostics=False):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(20)
        sock.connect(str(paths.socket))
        try:
            sock.sendall(json.dumps({'file':filename,'diagnostics':diagnostics}).encode() + b'\n')
            response = bytearray()
            while not response.endswith(b'\n'):
                chunk = sock.recv(4096)
                if not chunk or len(response) > 65536:
                    raise Error('Invalid session response')
                response.extend(chunk)
        except (TimeoutError, ConnectionResetError, BrokenPipeError) as exc:
            raise Error('The Power BI session did not answer. Try again in a few seconds. ' + STUCK_HELP) from exc
        value = json.loads(response)
        if not value.get('ok'):
            raise Error(value.get('error', 'Power BI launch failed'))
        return value


def desktop_running(prefix, processes=Path('/proc')):
    """True while a PBIDesktop process of this prefix exists, whoever started it.

    Desktop starts another Desktop itself for File > Open with a report already
    open, for a recent file and for a restart; the broker never sees those start.
    """
    marker = b'WINEPREFIX=' + str(prefix).encode()
    for process in processes.iterdir():
        if not process.name.isdigit():
            continue
        try:
            # Wine shows the Windows path as the command line; the loader's own
            # arguments (wine PBIDesktop.exe ...) are visible until it does.
            arguments = (process / 'cmdline').read_bytes().split(b'\0')[:2]
            if not any(re.split(rb'[\\/]', value)[-1].lower() == b'pbidesktop.exe' for value in arguments):
                continue
            if marker in (process / 'environ').read_bytes().split(b'\0'):
                return True
        except OSError:
            continue  # Gone, or another user's process.
    return False


# A launch holds its lock while a closing session finishes (SESSION_WAIT), the
# next one starts (START_WAIT) and answers (20 s).
SESSION_WAIT = 20
START_WAIT = 45
LAUNCH_WAIT = SESSION_WAIT + START_WAIT + 20
# How long stop lets Wine shut down cleanly before it kills what is left.
STOP_WAIT = 10


def wait_for_closing_session(paths):
    """Let a broker that is still shutting Wine down finish first.

    The broker holds the session lock for its whole life. Its last step kills
    the prefix's Wine server, which would also kill Wine processes started for
    a new session or for maintenance in those seconds.
    """
    try:
        with paths.lock('session', wait=SESSION_WAIT):
            pass
    except Error as exc:
        raise Error('Power BI is still closing. Try again in a few seconds. ' + STUCK_HELP) from exc


def starting(paths):
    """True while open holds the launch lock, which only a session start takes."""
    try:
        with paths.lock('launch'):
            return False
    except Error:
        return True


def stop(paths):
    """Force-quit this installation's Power BI: every window closes without saving.

    A session start holds the maintenance lock for at most LAUNCH_WAIT, so stop
    waits for it instead of refusing; a repair or update is never interrupted.
    """
    busy = 'Another maintenance operation is running'
    waited_for_start = False
    for wait in (5, LAUNCH_WAIT):
        if wait == LAUNCH_WAIT:
            if not starting(paths):
                break
            waited_for_start = True
            print('A session start is still running; stop waits up to ' + str(LAUNCH_WAIT) +
                  ' more seconds for it to finish.', file=sys.stderr, flush=True)
        try:
            with paths.lock('maintenance', wait=wait):
                _stop(paths)
            return
        except Error as exc:
            if str(exc) != busy:
                raise
    if waited_for_start:
        raise Error('Power BI is still starting or another operation took over; '
                    'run pbi-linux stop again in a moment')
    raise Error('A repair or update is still running; wait for it to finish, then run pbi-linux stop again')


def _stop(paths):
    unit = session_unit(paths.data)
    stopped = subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True, text=True, timeout=60)
    # 5: no such unit. Any other failure: still end the Wine processes below.
    problem = '' if stopped.returncode in (0, 5) else (stopped.stderr.strip() or 'systemctl failed')
    # Wine started outside the session (an interrupted repair, a manual run).
    for profile_prefix, runtime in leftover_prefixes(paths):
        env = dict(os.environ, WINEPREFIX=str(profile_prefix))
        subprocess.run([runtime/'bin/wineserver', '-k'], env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10)
    deadline = time.monotonic() + STOP_WAIT
    while busy(paths) and time.monotonic() < deadline:
        time.sleep(.2)
    for pid in wine_processes(paths):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + min(5, STOP_WAIT)
    while busy(paths) and time.monotonic() < deadline:
        time.sleep(.2)
    if busy(paths):
        raise Error('Some Power BI processes are still running' + (' (' + unit + ': ' + problem + ')' if problem else '') +
                    '; log out and back in to end them')
    if not problem:
        paths.socket.unlink(missing_ok=True)


def leftover_prefixes(paths):
    """(prefix, runtime) for each managed prefix that still has Wine processes."""
    try:
        installation = active(paths)
    except (Error, OSError):
        return []
    prefix, runtime = Path(installation['prefix']), Path(installation['runtime'])
    return [(prefix, runtime)] if busy(paths) and (runtime/'bin/wineserver').exists() else []


def open_file(paths, value, diagnostics=False):
    filename = file_argument(value)
    unit = session_unit(paths.data)
    # Two reports opened together (several files selected, a second double-click
    # during a cold start) take turns: the second waits for the first to bring the
    # session up instead of being refused as if maintenance were running. Maintenance
    # itself still excludes a launch at once, in both directions.
    with paths.lock('launch', wait=LAUNCH_WAIT), paths.lock('maintenance'):
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
        wait_for_closing_session(paths)
        if busy(paths):
            raise Error('This installation already has Wine processes without a reachable session. '
                        'Close its Power BI windows before reopening. ' + STUCK_HELP)
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
        # OOMPolicy=continue: the kernel killing one renderer or container for memory
        # must not stop the whole session and every open report with it.
        command = ['systemd-run', '--user', '--unit='+unit, '--collect',
                   '-p', 'Type=exec', '-p', 'KillMode=mixed', '-p', 'TimeoutStopSec=10s', '-p', 'TimeoutAbortSec=1s', '-p', 'LimitCORE=0',
                   '-p', 'OOMPolicy=continue']
        for prop in resources.service_properties(config):
            command += ['-p', prop]
        for name in ('PATH','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_RUNTIME_DIR','XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_CURRENT_DESKTOP','PBI_LINUX_RESOURCE_DIR'):
            if name in os.environ:
                command.append('--setenv='+name+'='+os.environ[name])
        command.append('--setenv=PYTHONPATH='+str(Path(__file__).resolve().parent.parent))
        # -P: the service runs in the home folder; a stray json.py there must not load first.
        command += [sys.executable, '-P', '-m', 'pbi_linux', '_session']
        if diagnostics:
            command.append('--diagnostics')
        run(command)
        # The broker verifies the installation (about 1.5 GB of hashes) before it
        # listens; a slow or cold disk needs more than a few seconds.
        deadline = time.monotonic()+START_WAIT
        while time.monotonic() < deadline:
            if paths.socket.exists():
                try:
                    return request(paths, filename, diagnostics)
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
            elif subprocess.run(['systemctl', '--user', 'is-active', '--quiet', unit], timeout=10).returncode:
                # The broker already exited (a failed check); --collect removed the unit.
                raise Error('Session stopped while starting; see journalctl --user -u ' + unit +
                            '. If it reports a checksum error, run pbi-linux repair')
            time.sleep(.1)
        raise Error('Session could not start; see journalctl --user -u '+unit)


def broker(paths, diagnostics=False):
    paths.create()
    # Held until this broker has stopped its Wine server; see wait_for_closing_session.
    with paths.lock('session', wait=SESSION_WAIT):
        _broker(paths, diagnostics)


def _broker(paths, diagnostics):
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
        # Created 0600, not chmodded after bind: no moment with wider access. No
        # other thread runs yet, so the process-wide umask affects nothing else.
        umask = os.umask(0o177)
        try:
            server.bind(str(paths.socket))
        finally:
            os.umask(umask)
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
                # A Desktop that Desktop started itself keeps the session alive too:
                # ending it would stop the Wine server under a report with unsaved work.
                if children or (started and desktop_running(prefix)):
                    idle_since = time.monotonic()
                elif time.monotonic()-idle_since > (10 if started else 30):
                    break
                try:
                    client, _ = server.accept()
                except TimeoutError:  # The 1 s timeout.
                    continue
                except OSError:  # A transient failure (EMFILE): retry, but do not spin.
                    time.sleep(1)
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
                    except Exception as exc:  # noqa: BLE001 - one bad request must not end the session
                        answer = {'ok':False, 'error':str(exc) or type(exc).__name__}
                    try:
                        client.sendall(json.dumps(answer).encode()+b'\n')
                    except OSError:
                        # The client gave up (Ctrl+C, its timeout). Leaving the loop here
                        # would stop the Wine server under every open report.
                        pass
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
    # Once the last Desktop of this prefix exits, systemd stops this service's remaining
    # processes. Other prefixes and services are outside its control group.
