#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
cd /work
mkdir -p .local/helper-check/unsigned
trap 'rm -f .local/helper-check/stubs.snk' EXIT
cp sources/dnlib/lib/net45/dnlib.dll .local/helper-check/
for tool in PatchShared PatchWinRT PatchSavePrompt PatchStoreRating PatchCacheCompatibility MakeKey SignStubs EnableModernEditor ConfigureSignIn; do
    mcs -r:.local/helper-check/dnlib.dll -out:.local/helper-check/"$tool".exe src/helpers/"$tool".cs
 done
mcs -target:library -out:.local/helper-check/PowerBIDiagnostics.dll src/helpers/PowerBIDiagnostics.cs
mcs -target:library -r:.local/helper-check/PowerBIDiagnostics.dll \
    -out:.local/helper-check/PowerBICompositionManager.dll src/helpers/PowerBICompositionManager.cs
mono .local/helper-check/MakeKey.exe .local/helper-check/stubs.snk
mcs -target:library -out:.local/helper-check/unsigned/WinRTStubs.dll src/helpers/WinRTStubs.cs
mono .local/helper-check/SignStubs.exe .local/helper-check/unsigned/WinRTStubs.dll \
    .local/helper-check/WinRTStubs.dll .local/helper-check/stubs.snk
sn -vf .local/helper-check/WinRTStubs.dll
mcs -target:library -r:System.Windows.Forms -r:System.Drawing \
    -out:.local/helper-check/unsigned/PowerBISaveDialog.dll src/helpers/PowerBISaveDialog.cs
mono .local/helper-check/PatchSavePrompt.exe --sign-dialog \
    .local/helper-check/unsigned/PowerBISaveDialog.dll .local/helper-check/PowerBISaveDialog.dll \
    .local/helper-check/stubs.snk
sn -vf .local/helper-check/PowerBISaveDialog.dll
mcs -target:library -out:.local/helper-check/Microsoft.Mashup.Client.UI.dll tests/fixtures/save-dialog-ui.cs
mcs -optimize+ -target:library -r:System.Windows.Forms -r:System.Drawing \
    -r:.local/helper-check/Microsoft.Mashup.Client.UI.dll \
    -out:.local/helper-check/unsigned/Microsoft.PowerBI.Client.Windows.dll tests/fixtures/save-dialog-desktop.cs
mono .local/helper-check/PatchSavePrompt.exe .local/helper-check/unsigned/Microsoft.PowerBI.Client.Windows.dll \
    .local/helper-check/Microsoft.PowerBI.Client.Windows.dll .local/helper-check/Microsoft.Mashup.Client.UI.dll \
    .local/helper-check/PowerBISaveDialog.dll
# These negative cases must fail and must not emit an output assembly.
if mono .local/helper-check/PatchShared.exe; then exit 1; fi
if mono .local/helper-check/PatchWinRT.exe; then exit 1; fi
if mono .local/helper-check/SignStubs.exe; then exit 1; fi
if mono .local/helper-check/PatchSavePrompt.exe; then exit 1; fi
if mono .local/helper-check/PatchSavePrompt.exe --sign-dialog .local/helper-check/PowerBIDiagnostics.dll \
    .local/helper-check/unexpected.dll .local/helper-check/stubs.snk; then exit 1; fi
if mono .local/helper-check/PatchSavePrompt.exe .local/helper-check/Microsoft.PowerBI.Client.Windows.dll \
    .local/helper-check/unexpected.dll .local/helper-check/Microsoft.Mashup.Client.UI.dll \
    .local/helper-check/PowerBISaveDialog.dll; then exit 1; fi
if mono .local/helper-check/SignStubs.exe .local/helper-check/PowerBIDiagnostics.dll \
    .local/helper-check/unexpected.dll .local/helper-check/stubs.snk; then exit 1; fi
if mono .local/helper-check/PatchShared.exe .local/helper-check/WinRTStubs.dll .local/helper-check/unexpected.dll; then exit 1; fi
if [ -e .local/helper-check/unexpected.dll ]; then exit 1; fi
printf 'Mono-compatible helpers/patchers compiled; malformed inputs rejected. Cache helper library is compiled/tested with the installed application dependency by its native regression.\n'
