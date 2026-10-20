#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export an allowlisted standalone project tree without investigation state."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
p.add_argument('--with-runtime-sources',action='store_true')
args=p.parse_args()
output=args.output.resolve()
allowed=('src','runtime','connectors','tests','packaging','tools','docs','.github','LICENSE','LICENSES',
         'README.md','CONTRIBUTING.md','SECURITY.md','CODE_OF_CONDUCT.md','CHANGELOG.md','.gitignore')
if output.exists():
    raise SystemExit('Output must be a new directory')
if (ROOT.resolve().is_relative_to(output) or output.is_relative_to(ROOT/'sources')
        or any(output.is_relative_to((ROOT/name).resolve()) for name in allowed)):
    raise SystemExit('Invalid export destination')
output.mkdir(parents=True)
def ignored(directory, names):
    return [n for n in names if n in ('__pycache__','results','.git','.pbi','.env')
            or n.startswith('.env.')
            or n.lower().endswith(('.pyc','.log','.dmp','.abf','.pbix','.exe','.dll','.so','.snk','.pfx','.pem'))]
for name in allowed:
    source=ROOT/name
    if source.is_dir():
        shutil.copytree(source,output/name,ignore=ignored)
    else:
        shutil.copy2(source,output/name)
if args.with_runtime_sources:
    for name in ('wine','dxvk'):
        if not (ROOT/'sources'/name).exists():
            raise SystemExit('Prepare runtime sources before requesting a corresponding-source bundle')
        with tarfile.open(output/('patched-'+name+'-source.tar.xz'),'w:xz') as tar:
            # Keep .gitmodules and upstream .gitignore files; only repository
            # metadata (including submodule .git pointers) is private state.
            tar.add(ROOT/'sources'/name,arcname=name,
                    filter=lambda i: None if '.git' in Path(i.name).parts else i)
manifest={str(file.relative_to(output)):hashlib.sha256(file.read_bytes()).hexdigest()
          for file in sorted(output.rglob('*')) if file.is_file()}
(output/'export-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(output)
