# SPDX-License-Identifier: GPL-3.0-or-later
"""Filesystem, subprocess and verification primitives shared by the CLI."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

class Error(Exception):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check_digest(path, expected):
    if not re.fullmatch('[a-f0-9]{64}', expected or '') or digest(path) != expected:
        raise Error('Checksum verification failed: ' + Path(path).name)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise Error('Cannot read metadata: ' + str(path)) from exc


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def installation_token(data):
    data = Path(data).resolve()
    default = (Path.home() / '.local/share/powerbi-linux').resolve()
    return '' if data == default else hashlib.sha256(str(data).encode()).hexdigest()[:16]


class Paths:
    def __init__(self):
        home = Path.home()
        self.data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'powerbi-linux'
        self.config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'powerbi-linux'
        self.cache = Path(os.environ.get('XDG_CACHE_HOME', home / '.cache')) / 'powerbi-linux'
        self.state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'powerbi-linux'
        token = installation_token(self.data)
        session_name = 'powerbi-linux' + ('-' + token if token else '')
        self.session = Path(os.environ.get('XDG_RUNTIME_DIR', self.state / 'session')) / session_name
        for base in (self.data, self.config, self.cache, self.state, self.session):
            if not base.is_absolute():
                raise Error('XDG directories must be absolute')
        self.settings = self.config / 'settings.json'
        self.active = self.data / 'active.json'
        self.previous = self.data / 'previous.json'
        self.maintenance = self.state / 'maintenance.json'
        self.socket = self.session / 'session.sock'

    def create(self):
        for directory in (self.data, self.config, self.cache, self.state, self.session):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def lock(self, name='maintenance'):
        self.create()
        with (self.session / (name + '.lock')).open('a') as lock:
            os.chmod(lock.name, 0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Error('Another ' + name + ' operation is running') from exc
            yield


def run(args, *, env=None, cwd=None, timeout=120, log=None, success_codes=(0,)):
    try:
        if log:
            with Path(log).open('ab') as out:
                result = subprocess.run([str(x) for x in args], env=env, cwd=cwd,
                                        stdout=out, stderr=out, timeout=timeout)
        else:
            result = subprocess.run([str(x) for x in args], env=env, cwd=cwd,
                                    text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Error('Command could not complete: ' + Path(str(args[0])).name) from exc
    if result.returncode not in success_codes:
        raise Error('Command failed: ' + Path(str(args[0])).name + '; see the operation log')
    return getattr(result, 'stdout', '') or ''


def wine_env(prefix):
    # Fedora's unixODBC package supplies the versioned runtime library; an
    # unversioned libodbc.so would unnecessarily require development headers.
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG='-all',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;msxml3,msxml6,msxml6r=b', LIB_ODBC_DRIVER_MANAGER='libodbc.so.2')
    for key in list(env):
        if key.startswith(('PBI_', 'COMPlus_', 'APPDOMAIN_MANAGER_', 'WEBVIEW2_')):
            env.pop(key, None)
    for key in ('DISPLAY', 'XAUTHORITY', 'WINELOADER', 'WINESERVER', 'WINEDLLPATH', 'WINEARCH'):
        env.pop(key, None)
    return env


def busy(paths):
    # All Wine processes in any managed prefix, including launches outside our broker.
    profiles = str(paths.data / 'profiles') + '/'
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            env = (proc / 'environ').read_bytes().split(b'\0')
            if any(x.startswith(b'WINEPREFIX=' + profiles.encode()) for x in env):
                return True
        except (OSError, PermissionError):
            continue
    return False
