#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
cd /work
mkdir -p build/wine build/dxvk dist/runtime/helpers
python3 - <<'TOOLCHAIN'
from pathlib import Path
import json
import subprocess
stamp=Path('build/toolchain.json')
current={name:subprocess.check_output([name,'--version'],text=True).splitlines()[0]
         for name in ('clang','x86_64-w64-mingw32-gcc','gcc')}
current['wine_target']='i386,x86_64; win16 disabled; native Wayland'
if stamp.exists() and json.loads(stamp.read_text()) != current:
    raise SystemExit('Compiler changed. Remove generated build/ before rebuilding to avoid mixed ABIs.')
stamp.write_text(json.dumps(current,indent=2)+'\n')
TOOLCHAIN
dpkg-query -W -f='${Package}\t${Version}\n' > build/builder-packages.tsv
clang --version > build/compiler.txt
if [ "${1:-}" != "--support-only" ]; then
cd build/wine
python3 - <<'CONFIGURE'
from pathlib import Path
import hashlib
import json
import subprocess
args=['../../sources/wine/configure','--prefix=/opt/powerbi-linux','--enable-archs=i386,x86_64',
      '--disable-win16','--disable-tests','--without-x','--with-wayland']
desired={'args':args,'sources':hashlib.sha256(Path('../../sources/wine/.prepared').read_bytes()).hexdigest()}
stamp=Path('.configure.json')
if not Path('Makefile').exists() or not stamp.exists() or json.loads(stamp.read_text())!=desired:
    subprocess.run(args,check=True)
    stamp.write_text(json.dumps(desired,indent=2)+'\n')
CONFIGURE
make -j"${PBI_BUILD_JOBS:-2}"
make -j"${PBI_BUILD_JOBS:-2}" dlls/ntdll/ntdll.so
rm -rf /work/build/stage
make install DESTDIR=/work/build/stage
cd /work
# The full-build entry point starts with an empty runtime tree. Move the install
# staging directory on the same filesystem instead of retaining two complete
# unstripped Wine trees before the stripping pass.
rmdir dist/runtime/helpers dist/runtime
mv build/stage/opt/powerbi-linux dist/runtime
python3 - <<'STRIP'
from pathlib import Path
import subprocess
for file in Path('dist/runtime').rglob('*'):
    if file.is_file() and not file.is_symlink():
        with file.open('rb') as stream:
            magic = stream.read(4)
        if magic == b'\x7fELF':
            subprocess.run(['strip', '--strip-debug', str(file)], check=True)
        elif magic[:2] == b'MZ':
            import struct
            with file.open('rb') as stream:
                stream.seek(0x3c)
                offset=stream.read(4)
                if len(offset)!=4:
                    continue
                stream.seek(struct.unpack('<I',offset)[0])
                if stream.read(4)!=b'PE\0\0':
                    continue
            subprocess.run(['x86_64-w64-mingw32-strip', '--strip-debug', str(file)], check=True)
STRIP
else
    test -x dist/runtime/bin/wine
    dist/runtime/bin/wine --version
fi
MESON_ARGS=()
if [ -f build/dxvk/build.ninja ]; then MESON_ARGS+=(--reconfigure); fi
meson setup "${MESON_ARGS[@]}" build/dxvk sources/dxvk --cross-file sources/dxvk/build-win64.txt --buildtype release \
    -Denable_d3d8=false -Denable_d3d9=false -Denable_d3d10=false -Denable_d3d11=true
ninja -C build/dxvk -j"${PBI_BUILD_JOBS:-2}"
mkdir -p dist/runtime/dxvk dist/runtime/helpers
cp build/dxvk/src/dxgi/dxgi.dll build/dxvk/src/d3d11/d3d11.dll dist/runtime/dxvk/
cp sources/dnlib/lib/net45/dnlib.dll dist/runtime/helpers/
cp /work/src/helpers/WinRTStubs.cs dist/runtime/helpers/
for tool in PatchShared PatchWinRT MakeKey SignStubs EnableModernEditor; do
    mcs -r:dist/runtime/helpers/dnlib.dll -out:dist/runtime/helpers/"$tool".exe src/helpers/"$tool".cs
 done
mcs -target:library -out:dist/runtime/helpers/PowerBIDiagnostics.dll src/helpers/PowerBIDiagnostics.cs
mcs -target:library -r:dist/runtime/helpers/PowerBIDiagnostics.dll \
    -out:dist/runtime/helpers/PowerBICompositionManager.dll src/helpers/PowerBICompositionManager.cs
# winepath/wineboot may be Windows PE programs rather than Unix wrappers.
for tool in winepath wineboot; do
    if [ ! -x dist/runtime/bin/"$tool" ]; then
        printf '#!/bin/sh\nexec "$(dirname "$0")/wine" %s.exe "$@"\n' "$tool" > dist/runtime/bin/"$tool"
        chmod +x dist/runtime/bin/"$tool"
    fi
 done
