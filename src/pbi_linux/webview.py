# SPDX-License-Identifier: GPL-3.0-or-later
"""Install a pinned Microsoft fixed-version CAB in a transaction-owned prefix."""
import os
from pathlib import Path
import shutil
import uuid
from .common import Error, check_digest, run


def folder(prefix, config):
    version=config['runtime_version']
    if not version or any(not part.isdigit() for part in version.split('.')):
        raise Error('Invalid fixed WebView2 version')
    result=Path(prefix)/'drive_c/powerbi-linux-webview'/version
    if not result.resolve().is_relative_to(Path(prefix).resolve()):
        raise Error('Fixed WebView2 path escapes the managed prefix')
    return result


def verify(directory, config):
    check_digest(directory/'msedge.dll',config['runtime_dll_sha256'])
    check_digest(directory/'msedgewebview2.exe',config['runtime_exe_sha256'])
    return directory/'msedge.dll'


def install(prefix, archive, config, log):
    target=folder(prefix,config)
    check_digest(archive,config['sha256'])
    if target.exists():
        try:
            return verify(target,config)
        except (Error,OSError):
            pass
    if not shutil.which('cabextract'):
        raise Error('Install cabextract before provisioning WebView2')
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    pending=target.parent/('.extract-'+uuid.uuid4().hex)
    pending.mkdir(mode=0o700)
    try:
        run(['cabextract','-q','-d',pending,archive],timeout=300,log=log)
        source=pending/config['cab_root']
        if source.parent!=pending or not source.is_dir():
            raise Error('Unexpected fixed WebView2 CAB layout')
        verify(source,config)
        # Callers only use this on a pending setup generation or a snapshot.
        # Validate the replacement before removing a damaged transaction copy.
        if target.exists():
            shutil.rmtree(target)
        os.replace(source,target)
        return verify(target,config)
    finally:
        shutil.rmtree(pending)
