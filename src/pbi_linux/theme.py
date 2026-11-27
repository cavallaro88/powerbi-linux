# SPDX-License-Identifier: GPL-3.0-or-later
"""Bridge the host's color preference to Desktop's original Windows theme handler."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from .common import Error, run

POLL_SECONDS = 2
# Desktops whose light/dark preference is org.gnome.desktop.interface color-scheme.
# Hyprland has no setting of its own: the session (Omarchy on every theme change)
# sets this key and the desktop portal reports it to applications. Elsewhere the
# key can be a stale leftover, so other desktops are skipped.
DESKTOPS = frozenset(('GNOME', 'HYPRLAND'))
COMPILER = r'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'


def preference():
    """Return light/dark, or None when the host preference is unavailable."""
    try:
        result = subprocess.run(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
            capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    return {"'prefer-dark'": 'dark', "'prefer-light'": 'light',
            "'default'": 'light'}.get(result.stdout.strip())


class ThemeSync:
    """One bounded worker per broker; failure must never prevent opening reports."""
    def __init__(self, paths, runtime, env):
        self.paths = paths
        self.wine = Path(runtime) / 'bin/wine'
        self.env = {key: value for key, value in env.items()
                    if not key.startswith('APPDOMAIN_MANAGER_')}
        self.stop = threading.Event()
        self.ready = threading.Event()  # Set once the first write was made or given up.
        self.thread = None
        self.directory = None
        self.current = None
        self.failed = False

    def _log(self, message):
        with (self.paths.state / 'session.log').open('a') as stream:
            stream.write('Host theme: ' + message + '\n')

    def start(self):
        if not DESKTOPS.intersection(os.environ.get('XDG_CURRENT_DESKTOP', '').upper().split(':')):
            self.ready.set()
            return
        # The first write needs two Wine process starts (compiler, helper). The broker
        # must not make the report wait for them, so the worker does all of it.
        self.thread = threading.Thread(target=self._run, name='host-theme', daemon=True)
        self.thread.start()

    def _run(self):
        try:
            selected = preference()
            if selected is None:
                self._log('preference unavailable; keeping the existing Windows preference')
                return
            try:
                # Rebuild from packaged source in the private session directory.
                # No runtime rebuild, profile repair or mutable executable cache.
                self.directory = tempfile.TemporaryDirectory(prefix='theme-', dir=self.paths.session)
                folder = Path(self.directory.name)
                source = Path(__file__).resolve().parents[1] / 'helpers/PowerBIThemeSync.cs'
                shutil.copy2(source, folder / source.name)
                self.helper = folder / 'PowerBIThemeSync.exe'
                run([self.wine, COMPILER, '/nologo', '/optimize+', '/out:PowerBIThemeSync.exe',
                     source.name], env=self.env, cwd=folder, timeout=8,
                    log=self.paths.state / 'session.log')
                if not self.stop.is_set():
                    self.sync(selected)
            except (Error, OSError) as error:
                self._log('synchronization unavailable: ' + str(error))
                if self.directory is not None:
                    self.directory.cleanup()
                    self.directory = None
                return
        finally:
            self.ready.set()
        self._watch()

    def sync(self, selected):
        if selected is None or selected == self.current:
            return
        run([self.wine, self.helper, selected], env=self.env, timeout=4,
            log=self.paths.state / 'session.log')
        self.current = selected
        self.failed = False
        self._log('applied ' + selected)

    def _watch(self):
        while not self.stop.wait(POLL_SECONDS):
            try:
                self.sync(preference())
            except (Error, OSError) as error:
                if not self.failed:
                    self._log('update failed; will retry: ' + str(error))
                self.failed = True

    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join()  # Each read/write has a timeout; finish before wineserver -k.
            self.thread = None
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None
