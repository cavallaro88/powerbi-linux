# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit desktop targets; distribution ancestry does not imply compatibility."""
from pathlib import Path
import shlex


def release(text=None):
    if text is None:
        text = Path('/etc/os-release').read_text()
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition('=')
        if separator and key in ('ID', 'VERSION_ID', 'PRETTY_NAME'):
            try:
                words = shlex.split(value, comments=True)
            except ValueError:
                continue
            if len(words) == 1:
                result[key] = words[0]
    return result


def status(info=None):
    info = release() if info is None else info
    name, version = info.get('ID', ''), info.get('VERSION_ID', '')
    if name == 'fedora':
        return True, 'Fedora 44 is the tested target; other Fedora releases are experimental'
    detected = info.get('PRETTY_NAME') or (name + ' ' + version).strip() or 'unknown distribution'
    return False, 'Detected ' + detected + '. Target: Fedora 44, x86_64 and Wayland'


TARGETS = 'Fedora 44, x86_64 / Wayland'


def ntlm_help():
    return 'Install samba-winbind-clients before opening Power BI'
