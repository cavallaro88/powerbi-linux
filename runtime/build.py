#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare pinned sources and compile in a container. Run from a clean clone."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid
import zipfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'src'))
from pbi_linux.assets import download
from pbi_linux.common import check_digest, digest
from pbi_linux import build_provenance

WINE_PATCHES = ('wine-11.18-composition.patch','wine-11.18-oledb32-variant.patch',
                'wine-11.18-wayland-parent.patch','wine-11.18-cgroup-memory.patch','wine-11.18-secur32-status.patch','wine-11.18-jscript-int64.patch','wine-11.18-cursor-resource.patch','wine-11.18-wayland-normal-resize.patch')


def preparation_matches(marker, expected):
    if not marker.exists():
        return False
    try:
        actual=json.loads(marker.read_text())
    except ValueError:
        actual=None
    if actual != expected:
        raise SystemExit('Prepared sources no longer match the recipe. Remove generated sources/ and build/ before rebuilding.')
    return True


def run(*args, cwd=ROOT):
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def prepare_dnlib(args, lock, cache, sources):
    archive = Path(args.dnlib_source).resolve() if args.dnlib_source else download(lock['dnlib']['url'],lock['dnlib']['sha256'],cache)
    check_digest(archive,lock['dnlib']['sha256'])
    (sources/'dnlib').mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in ('lib/net45/dnlib.dll','LICENSE.txt'):
            target=sources/'dnlib'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(name))


def prepare_bundled(args):
    lock=json.loads((ROOT/'runtime/sources.lock.json').read_text())
    manifest=json.loads((ROOT/'export-manifest.json').read_text())
    sources=ROOT/'sources'
    sources.mkdir(exist_ok=True)
    for name in ('wine','dxvk'):
        archive=ROOT/('patched-'+name+'-source.tar.xz')
        check_digest(archive,manifest[archive.name])
    for name in ('wine','dxvk'):
        archive=ROOT/('patched-'+name+'-source.tar.xz')
        target=sources/name
        marker=target/'.bundled-source-sha256'
        if target.exists():
            if not marker.is_file() or marker.read_text().strip()!=manifest[archive.name]:
                raise SystemExit('Preserve/move existing sources/'+name+' before unpacking a different source bundle')
            continue
        pending=sources/('.'+name+'-extract-'+uuid.uuid4().hex)
        pending.mkdir()
        try:
            with tarfile.open(archive) as tar:
                if any(not Path(m.name).parts or Path(m.name).parts[0]!=name for m in tar.getmembers()):
                    raise SystemExit('Unexpected corresponding-source archive layout')
                tar.extractall(pending,filter='data')
            (pending/name/'.bundled-source-sha256').write_text(manifest[archive.name]+'\n')
            os.replace(pending/name,target)
        finally:
            shutil.rmtree(pending)
    wine_recipe={'source_sha256':lock['wine']['sha256'],
                 'patches':{name:digest(ROOT/'runtime/patches'/name) for name in WINE_PATCHES}}
    dxvk_recipe={'commit':lock['dxvk']['commit'],
                 'patch_sha256':digest(ROOT/'runtime/patches/dxvk-3.1-composition.patch')}
    if not preparation_matches(sources/'wine/.prepared',wine_recipe) or not preparation_matches(sources/'dxvk/.prepared',dxvk_recipe):
        raise SystemExit('Corresponding-source preparation markers are missing')
    prepare_dnlib(args,lock,ROOT/'.cache/downloads',sources)
    print('Exact patched source bundles prepared without Git metadata or upstream checkouts.')


def prepare(args):
    lock = json.loads((ROOT/'runtime/sources.lock.json').read_text())
    cache = ROOT/'.cache/downloads'
    sources = ROOT/'sources'
    sources.mkdir(exist_ok=True)
    wine = Path(args.wine_source).resolve() if args.wine_source else download(lock['wine']['url'], lock['wine']['sha256'], cache)
    check_digest(wine, lock['wine']['sha256'])
    wine_recipe={'source_sha256':lock['wine']['sha256'],
                 'patches':{name:digest(ROOT/'runtime/patches'/name) for name in WINE_PATCHES}}
    if not preparation_matches(sources/'wine/.prepared',wine_recipe):
        pending = sources/'wine-extract'
        if pending.exists():
            shutil.rmtree(pending)
        pending.mkdir()
        with tarfile.open(wine) as tar:
            tar.extractall(pending, filter='data')
        target = sources/'wine'
        if target.exists():
            shutil.rmtree(target)
        os.replace(pending/'wine-11.18', target)
        pending.rmdir()
        for patch in WINE_PATCHES:
            run('patch', '--batch', '--fuzz=0', '-p1', '-i', ROOT/'runtime/patches'/patch, cwd=target)
        (target/'.prepared').write_text(json.dumps(wine_recipe,indent=2)+'\n')
    dxvk = sources/'dxvk'
    if not dxvk.exists():
        if args.dxvk_source:
            run('git', 'clone', '--no-hardlinks', str(Path(args.dxvk_source).resolve()), dxvk)
        else:
            run('git', 'clone', lock['dxvk']['url'], dxvk)
    run('git', 'checkout', '--detach', lock['dxvk']['commit'], cwd=dxvk)
    if args.dxvk_source:
        original_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(args.dxvk_source).resolve(),text=True).strip()
        if original_commit != lock['dxvk']['commit']:
            raise SystemExit('Offline DXVK checkout must match the pinned commit in sources.lock.json')
        entries = subprocess.check_output(['git','submodule','status','--recursive'], cwd=Path(args.dxvk_source).resolve(), text=True).splitlines()
        for entry in entries:
            name = entry.split()[1]
            if entry[0] in '-+U':
                raise SystemExit('Offline DXVK source has an uninitialized or mismatched submodule: '+name)
            if not (dxvk/name/'.git').exists():
                source = Path(args.dxvk_source).resolve()/name
                target = dxvk/name
                if target.exists():
                    shutil.rmtree(target)
                run('git','clone','--no-hardlinks',source,target)
                run('git','checkout','--detach',entry.split()[0].lstrip('-+'),cwd=target)
    else:
        run('git','submodule','update','--init','--recursive',cwd=dxvk)
    dxvk_recipe={'commit':lock['dxvk']['commit'],
                 'patch_sha256':digest(ROOT/'runtime/patches/dxvk-3.1-composition.patch')}
    if not preparation_matches(dxvk/'.prepared',dxvk_recipe):
        run('patch','--batch','--fuzz=0','-p1','-i',ROOT/'runtime/patches/dxvk-3.1-composition.patch',cwd=dxvk)
        (dxvk/'.prepared').write_text(json.dumps(dxvk_recipe,indent=2)+'\n')
    prepare_dnlib(args,lock,cache,sources)
    recipe = {'lock_sha256':digest(ROOT/'runtime/sources.lock.json'),
              'patches':{file.name:digest(file) for file in sorted((ROOT/'runtime/patches').glob('*.patch'))}}
    (sources/'build-inputs.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print('Pinned sources and patches prepared.')


def package(engine='docker', version='0.1.2'):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise SystemExit('Invalid runtime version')
    archive=ROOT/('dist/powerbi-linux-runtime-'+version+'-x86_64.tar.xz')
    if archive.exists() or archive.with_suffix(archive.suffix+'.sha256').exists():
        raise SystemExit('Runtime artifact already exists; select a new version instead of overwriting it')
    runtime=ROOT/'dist/runtime'
    builder=json.loads(subprocess.check_output([engine,'image','inspect','pbi-linux-builder:0.1.0'],text=True))[0]
    build_provenance.verify(ROOT, version, builder['Id'])
    lock=json.loads((ROOT/'runtime/sources.lock.json').read_text())
    if not preparation_matches(ROOT/'sources/wine/.prepared',{'source_sha256':lock['wine']['sha256'],
        'patches':{name:digest(ROOT/'runtime/patches'/name) for name in WINE_PATCHES}}):
        raise SystemExit('Prepare Wine sources before packaging')
    if not preparation_matches(ROOT/'sources/dxvk/.prepared',{'commit':lock['dxvk']['commit'],
        'patch_sha256':digest(ROOT/'runtime/patches/dxvk-3.1-composition.patch')}):
        raise SystemExit('Prepare DXVK sources before packaging')
    required=('bin/wine','bin/wineserver','bin/winepath','lib/wine/i386-windows/ntdll.dll',
              'lib/wine/x86_64-windows/ntdll.dll','dxvk/d3d11.dll','dxvk/dxgi.dll',
              'helpers/PatchShared.exe','helpers/PatchWinRT.exe','helpers/MakeKey.exe','helpers/SignStubs.exe',
              'helpers/EnableModernEditor.exe','helpers/PowerBIDiagnostics.dll',
              'helpers/PowerBICompositionManager.dll','helpers/dnlib.dll','helpers/WinRTStubs.cs')
    for name in required:
        if not (runtime/name).is_file():
            raise SystemExit('Incomplete build: '+name)
    for directory in ('helpers','licenses'):
        (runtime/directory).mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'sources/dnlib/LICENSE.txt',runtime/'licenses/dnlib.txt')
    for file in (ROOT/'LICENSES').iterdir():
        shutil.copyfile(file,runtime/'licenses'/file.name)
    shutil.copyfile(ROOT/'LICENSE',runtime/'licenses/project-GPL-3.0.txt')
    shutil.copyfile(ROOT/'sources/wine/AUTHORS',runtime/'licenses/Wine-AUTHORS.txt')
    for file in (ROOT/'sources/wine/libs').rglob('*'):
        if file.is_file() and file.name.upper().startswith(('LICENSE','COPYING')):
            target=runtime/'licenses/wine-libraries'/file.relative_to(ROOT/'sources/wine/libs')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,target)
    for name in ('builder-packages.tsv', 'compiler.txt', 'toolchain.json'):
        source = ROOT/'build'/name
        if not source.exists():
            raise SystemExit('Missing builder provenance: '+name)
        shutil.copyfile(source, runtime/name)
    for base in ('sources/dxvk/include','sources/dxvk/subprojects'):
        for file in (ROOT/base).rglob('*'):
            if file.is_file() and (file.name.upper().startswith(('LICENSE','COPYING'))):
                target=runtime/'licenses/dxvk-submodules'/file.relative_to(ROOT/'sources/dxvk')
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(file,target)
    lock=json.loads((ROOT/'runtime/sources.lock.json').read_text())
    manifest={'schema':1,'arch':'x86_64','version':version,'sources':lock,
              'builder_image_id':builder['Id'],
              'build_input_sha256':json.loads((ROOT/'build/runtime-build-success.json').read_text())['input_sha256'],
              'dockerfile_sha256':digest(ROOT/'runtime/Dockerfile'),
              'patches':{f.name:digest(f) for f in sorted((ROOT/'runtime/patches').glob('*.patch'))},
              'files':{str(p.relative_to(runtime)):digest(p) for p in sorted(runtime.rglob('*')) if p.is_file() and p.name!='runtime.json'}}
    (runtime/'runtime.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with tarfile.open(archive,'w:xz',dereference=False) as tar:
        # Emit symlinks without following them; archive paths remain relative.
        for file in sorted(runtime.iterdir()):
            tar.add(file,arcname=file.name)
    (archive.with_suffix(archive.suffix+'.sha256')).write_text(digest(archive)+'  '+archive.name+'\n')
    print(archive)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--package-only',action='store_true',help='Package an already completed runtime build')
    p.add_argument('--runtime-version', default='0.1.5', help='Version recorded in the manifest and archive filename')
    p.add_argument('--bundled-sources',action='store_true',help='Build from the corresponding patched source archives in an exported project')
    p.add_argument('--wine-source')
    p.add_argument('--dxvk-source')
    p.add_argument('--dnlib-source')
    p.add_argument('--engine',choices=['docker','podman'],default='docker')
    p.add_argument('--jobs',type=int,default=2,help='Parallel compiler jobs (default: 2)')
    args=p.parse_args()
    if args.jobs < 1:
        p.error('--jobs must be at least 1')
    if args.package_only:
        package(args.engine, args.runtime_version)
        return
    (ROOT/'build/runtime-build-success.json').unlink(missing_ok=True)
    build_provenance.reviewed_patches(ROOT)
    if args.bundled_sources:
        prepare_bundled(args)
    else:
        prepare(args)
    if args.prepare_only:
        return
    run(args.engine,'build','-t','pbi-linux-builder:0.1.0',ROOT/'runtime')
    builder=json.loads(subprocess.check_output([args.engine,'image','inspect','pbi-linux-builder:0.1.0'],text=True))[0]
    started=build_provenance.begin(ROOT, args.runtime_version, builder['Id'])
    # An old install tree must not contribute files removed by the new recipe.
    if (ROOT/'dist/runtime').exists():
        shutil.rmtree(ROOT/'dist/runtime')
    run(args.engine,'run','--rm','--user',str(os.getuid())+':'+str(os.getgid()),'-e','HOME=/tmp/pbi-build-home',
        '-e','PBI_BUILD_JOBS='+str(args.jobs),
        '-v',str(ROOT)+':/work:z','-w','/work',builder['Id'],'bash','runtime/build-inside.sh')
    build_provenance.record_success(ROOT, started)
    package(args.engine, args.runtime_version)

if __name__=='__main__':
    main()
