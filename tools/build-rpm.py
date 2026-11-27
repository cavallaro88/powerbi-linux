#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tarfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_tree import archive_filter, refuse_symlinks
ROOT=Path(__file__).resolve().parent.parent
SOURCES=('src','runtime','connectors','packaging','docs','tests','tools','.github','.gitignore','LICENSE','LICENSES','README.md','CONTRIBUTING.md','SECURITY.md','SECURITY-RULES.md','CODE_OF_CONDUCT.md','CHANGELOG.md')
TOP='powerbi-linux-0.1.0'
# The spec copies packaging/ whole, so makepkg output and local files stop here.
member=archive_filter(TOP)
p=argparse.ArgumentParser()
p.add_argument('--engine',choices=['docker','podman'],default='docker')
p.add_argument('--local',action='store_true')
p.add_argument('--check-helpers',action='store_true',help='Compile/sign helpers in the prepared container builder before packaging')
args=p.parse_args()
work=ROOT/'build/rpm'
for name in ('SOURCES','SPECS','BUILD','BUILDROOT','RPMS','SRPMS'):
    (work/name).mkdir(parents=True,exist_ok=True)
refuse_symlinks(SOURCES)
with tarfile.open(work/'SOURCES'/(TOP+'.tar.gz'),'w:gz') as tar:
    for name in SOURCES:
        tar.add(ROOT/name,arcname=TOP+'/'+name,filter=member)
command=['rpmbuild','-ba','--define','_topdir '+str(work),str(ROOT/'packaging/powerbi-linux.spec')]
if args.local:
    if args.check_helpers:
        raise SystemExit('--check-helpers uses the prepared container builder')
    subprocess.run(command,check=True)
else:
    container=[args.engine,'run','--rm','--user',str(os.getuid())+':'+str(os.getgid())]
    if args.engine == 'podman':
        # Rootless Podman maps --user to a subordinate ID without this guard.
        container.append('--userns=keep-id')
    container += ['-e','HOME=/tmp/pbi-rpm-home','-v',str(ROOT)+':/work:z','pbi-linux-builder:0.1.0']
    if args.check_helpers:
        subprocess.run([*container,'bash','/work/tools/validate-helpers.sh'],check=True)
    subprocess.run([*container,'rpmbuild','-ba','--define',
                    '_topdir /work/build/rpm','/work/packaging/powerbi-linux.spec'],check=True)
print(work/'RPMS')
