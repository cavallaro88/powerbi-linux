# SPDX-License-Identifier: GPL-3.0-or-later
import os
import configparser
from pathlib import Path
import shutil
import shlex
import subprocess
from .common import atomic_json, read_json
from . import icons
from .provision import resource_root

DESKTOP_ID = 'powerbi-linux.desktop'
MIMES = ['application/x-powerbi-pbix', 'application/x-powerbi-pbip', 'application/x-powerbi-pbir']


def refresh_icon(paths, installation=None):
    """Keep the original installed Power BI icon across RPM/profile updates."""
    entry = paths.data.parent/'applications'/DESKTOP_ID
    if not entry.is_file() or entry.is_symlink():
        return
    if installation is None:
        if not paths.active.exists():
            return
        installation = read_json(paths.active)
    icon = icons.install_original(paths, installation['prefix'])
    if icon is None:
        return
    try:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read(entry)
        if not parser.has_section('Desktop Entry') or parser.get('Desktop Entry', 'Hidden', fallback='false') == 'true':
            return
        if parser.get('Desktop Entry', 'Icon', fallback='') != str(icon):
            parser.set('Desktop Entry', 'Icon', str(icon))
            pending = entry.with_suffix('.desktop.pending')
            with pending.open('w') as out:
                parser.write(out, space_around_delimiters=False)
            os.replace(pending, entry)
    except (OSError, UnicodeError, configparser.Error):
        return


def remove_legacy_wine_entries(paths):
    """Remove only Wine-generated launchers pointing into our profile tree.

    Older recipes let winemenubuilder export entries for temporary snapshots.
    Keep launchers for other prefixes and MIME definitions with other users.
    """
    data=paths.data.parent
    apps=data/'applications'
    candidates=list(apps.glob('wine-extension-*.desktop'))+list(apps.glob('wine-protocol-*.desktop'))
    candidates+=list((apps/'wine').rglob('*.desktop'))
    removed=[]
    mime_candidates=set()
    for file in candidates:
        if file.is_symlink():
            continue
        parser=configparser.ConfigParser(interpolation=None,strict=False)
        parser.optionxform=str
        try:
            parser.read(file)
            command=shlex.split(parser.get('Desktop Entry','Exec',fallback=''))
        except (OSError,ValueError,configparser.Error):
            continue
        prefixes=[value.split('=',1)[1] for value in command if value.startswith('WINEPREFIX=')]
        if not any(Path(value).is_absolute() and Path(value).resolve().is_relative_to((paths.data/'profiles').resolve())
                   for value in prefixes):
            continue
        mime_candidates.update(value for value in parser.get('Desktop Entry','MimeType',fallback='').split(';')
                               if value.startswith('application/x-wine-extension-'))
        removed.append(str(file.relative_to(data)))
        file.unlink()
    search=[apps]
    search.extend(Path(base)/'applications' for base in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')
                  if base and Path(base).is_absolute() and Path(base)!=data)
    referenced=set()
    if mime_candidates:
        for directory in search:
            for file in directory.rglob('*.desktop'):
                parser=configparser.ConfigParser(interpolation=None,strict=False)
                try:
                    parser.read(file)
                    referenced.update(parser.get('Desktop Entry','MimeType',fallback='').split(';'))
                except (OSError,UnicodeError,configparser.Error):
                    continue
        for mime in mime_candidates-referenced:
            extension=mime.removeprefix('application/x-wine-extension-')
            if not extension or not extension.isalnum():
                continue
            file=data/'mime/packages'/('x-wine-extension-'+extension+'.xml')
            if file.is_file() and not file.is_symlink():
                file.unlink()
                removed.append(str(file.relative_to(data)))
    return removed


def integrate(paths, make_default=False):
    remove_legacy_wine_entries(paths)
    data = paths.data.parent
    files = [(resource_root()/'packaging'/DESKTOP_ID, data/'applications'/DESKTOP_ID),
             (resource_root()/'packaging/powerbi-linux.xml', data/'mime/packages/powerbi-linux.xml'),
             (resource_root()/'packaging/powerbi-linux.svg', data/'icons/hicolor/scalable/apps/powerbi-linux.svg')]
    for source, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    refresh_icon(paths)
    saved = read_json(paths.config/'desktop.json') if (paths.config/'desktop.json').exists() else {'defaults':{}}
    if make_default and shutil.which('xdg-mime'):
        for mime in MIMES:
            current = subprocess.run(['xdg-mime', 'query', 'default', mime], text=True, capture_output=True).stdout.strip()
            if current != DESKTOP_ID:
                saved['defaults'].setdefault(mime, current)
            subprocess.run(['xdg-mime', 'default', DESKTOP_ID, mime], check=True)
    atomic_json(paths.config/'desktop.json', saved)
    for command, target in [('update-desktop-database', data/'applications'), ('update-mime-database', data/'mime')]:
        if shutil.which(command):
            subprocess.run([command, str(target)], capture_output=True, check=True)


def remove(paths):
    remove_legacy_wine_entries(paths)
    config = paths.config/'desktop.json'
    saved = read_json(config) if config.exists() else {'defaults':{}}
    if shutil.which('xdg-mime'):
        for mime in MIMES:
            previous=saved['defaults'].get(mime,'')
            current = subprocess.run(['xdg-mime', 'query', 'default', mime], text=True, capture_output=True).stdout.strip()
            if current == DESKTOP_ID and previous and previous != DESKTOP_ID:
                subprocess.run(['xdg-mime', 'default', previous, mime], check=True)
            else:
                # xdg-mime has no unset command. Remove only our default token from
                # the user-owned mimeapps files it may have written.
                candidates = list(paths.config.parent.glob('*mimeapps.list'))
                candidates += list((paths.data.parent/'applications').glob('*mimeapps.list'))
                for file in candidates:
                    parser = configparser.ConfigParser(interpolation=None, strict=False)
                    parser.optionxform = str
                    parser.read(file)
                    section = 'Default Applications'
                    if parser.has_option(section, mime):
                        remaining = [x for x in parser.get(section, mime).split(';') if x and x != DESKTOP_ID]
                        if remaining:
                            parser.set(section, mime, ';'.join(remaining)+';')
                        else:
                            parser.remove_option(section, mime)
                        with file.open('w') as out:
                            parser.write(out)
    data = paths.data.parent
    for file in (data/'applications'/DESKTOP_ID, data/'mime/packages/powerbi-linux.xml',
                 data/'icons/hicolor/scalable/apps/powerbi-linux.svg',
                 data/'icons/hicolor/512x512/apps/powerbi-linux.png',
                 paths.cache/'desktop-icon.json'):
        file.unlink(missing_ok=True)
    # The RPM's system entry remains installed. Mask it for this user rather
    # than exposing it again after deleting the per-user entry. Repair copies
    # the normal entry over this mask; system files never need user writes.
    system_dirs=os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')
    if any((Path(base)/'applications'/DESKTOP_ID).is_file()
           for base in system_dirs if base and Path(base).is_absolute() and Path(base)!=data):
        target=data/'applications'/DESKTOP_ID
        target.parent.mkdir(parents=True,exist_ok=True)
        parser=configparser.ConfigParser(interpolation=None)
        parser.optionxform=str
        parser.read(resource_root()/'packaging'/DESKTOP_ID)
        parser.set('Desktop Entry','Hidden','true')
        with target.open('w') as out:
            parser.write(out)
    for command, target in [('update-desktop-database', data/'applications'), ('update-mime-database', data/'mime')]:
        if shutil.which(command) and target.exists():
            subprocess.run([command, str(target)], capture_output=True)
