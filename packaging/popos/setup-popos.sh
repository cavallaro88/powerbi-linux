#!/bin/sh
set -eu
setup_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime_file="$setup_dir/powerbi-linux-runtime-0.1.5-x86_64.tar.xz"
if ! command -v pbi-linux >/dev/null 2>&1; then
    echo 'Instale primeiro o .deb desta pasta com sudo apt install ./powerbi-linux_0.1.0-16pop1_amd64.deb' >&2
    exit 1
fi
if [ ! -f "$runtime_file" ]; then
    echo 'O pacote de teste está incompleto: mantenha o script e o arquivo powerbi-linux-runtime-0.1.5-x86_64.tar.xz na mesma pasta.' >&2
    exit 1
fi
exec pbi-linux setup \
    --runtime "$runtime_file" \
    --runtime-sha256 291bb52fca8c27f2446ec4a05aaf982bb43d8c13e6b3787f32a1328ad890f05a \
    "$@"
