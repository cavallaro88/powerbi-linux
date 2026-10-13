#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import os
from pathlib import Path
import subprocess
import tarfile
ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser()
p.add_argument('--engine',choices=['docker','podman'],default='docker')
p.add_argument('--local',action='store_true')
args=p.parse_args()
work=ROOT/'build/rpm'
for name in ('SOURCES','SPECS','BUILD','BUILDROOT','RPMS','SRPMS'):
    (work/name).mkdir(parents=True,exist_ok=True)
with tarfile.open(work/'SOURCES/powerbi-linux-0.1.0.tar.gz','w:gz') as tar:
    for name in ('src','runtime','packaging','docs','LICENSE','LICENSES','README.md','CONTRIBUTING.md','SECURITY.md','CODE_OF_CONDUCT.md','CHANGELOG.md'):
        tar.add(ROOT/name,arcname='powerbi-linux-0.1.0/'+name,
                filter=lambda info: None if '__pycache__' in info.name or info.name.endswith('.pyc') else info)
command=['rpmbuild','-ba','--define','_topdir '+str(work),str(ROOT/'packaging/powerbi-linux.spec')]
if args.local:
    subprocess.run(command,check=True)
else:
    subprocess.run([args.engine,'run','--rm','--user',str(os.getuid())+':'+str(os.getgid()),
                    '-e','HOME=/tmp/pbi-rpm-home','-v',str(ROOT)+':/work:z','pbi-linux-builder:0.1.0',
                    'rpmbuild','-ba','--define','_topdir /work/build/rpm','/work/packaging/powerbi-linux.spec'],check=True)
print(work/'RPMS')
