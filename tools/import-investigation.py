#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Developer-only bridge. Copy a prepared prefix for disposable migration tests.

Never distribute the resulting runtime/prefix: it is local investigation state.
This does NOT certify setup from official installers or a rebuilt runtime.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux.common import Paths,Error,atomic_json,digest
from pbi_linux.provision import snapshot,activate,idle,BIN
from pbi_linux import patches,pe_cache
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--runtime',type=Path,required=True)
p.add_argument('--helpers',type=Path,required=True)
a=p.parse_args()
paths=Paths()
# Prevent accidentally adopting private state into a real user's installation.
if not paths.data.resolve().is_relative_to((ROOT/'.local').resolve()):
    raise SystemExit('Set isolated XDG directories under product/.local before importing')
with paths.lock():
    idle(paths)
    if paths.active.exists():
        raise SystemExit('Disposable installation already exists')
    runtime=paths.data/'runtimes/investigation-local'
    prefix=paths.data/'profiles/investigation-local'
    snapshot(a.runtime.resolve(),runtime)
    prefix.mkdir(parents=True)
    shutil.copytree(a.prefix.resolve(),prefix,dirs_exist_ok=True,symlinks=True,
                    ignore=shutil.ignore_patterns('AnalysisServicesWorkspaces','graphics-logs','*.log','*.dmp','Cache','Code Cache','GPUCache'))
    helpers=runtime/'helpers'
    helpers.mkdir(exist_ok=True)
    for name in ('PowerBIDiagnostics.dll','PowerBICompositionManager.dll','PatchShared.exe','PatchWinRT.exe','MakeKey.exe','EnableModernEditor.exe','dnlib.dll'):
        shutil.copy2(a.helpers/name,helpers/name)
    shutil.copy2(ROOT/'src/helpers/WinRTStubs.cs',helpers/'WinRTStubs.cs')
    for name in ('PowerBIDiagnostics.dll','PowerBICompositionManager.dll'):
        shutil.copy2(helpers/name,prefix/BIN/name)
    for tool in ('winepath','wineboot'):
        file=runtime/'bin'/tool
        if not file.exists():
            file.write_text('#!/bin/sh\nexec "$(dirname "$0")/wine" '+tool+'.exe "$@"\n')
            file.chmod(0o755)
    manifest={'schema':1,'arch':'x86_64','version':'investigation-local-NOT-A-RELEASE',
              'files':{str(file.relative_to(runtime)):digest(file) for file in runtime.rglob('*') if file.is_file()}}
    atomic_json(runtime/'runtime.json',manifest)
    hashes={name:digest(prefix/BIN/name) for name in (*patches.ORIGINALS,'WinRTStubs.dll','PowerBIDiagnostics.dll','PowerBICompositionManager.dll')}
    pe_cache.prepare(pe_cache.webview(prefix),paths.cache/'pe'/prefix.name)
    activate(paths,prefix,runtime,hashes,'0'*64)
print('Disposable migration copy created. Original investigation unchanged.')
