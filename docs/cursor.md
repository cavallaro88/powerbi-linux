# Cursor stuck on a resize shape — runtime 0.1.3

The user reported the horizontal/vertical resize cursor remaining over ordinary
Power BI controls. The live session repeatedly logged `Failed to get icon info`
for its current cursor handle, with no active mouse capture or move/size loop.
The existing Neutron-derived fallback keeps the last successfully resolved image
when the new handle cannot be resolved. A retained resize cursor can therefore
remain visible after an embedded browser selects a foreign-process arrow.

## Correction

The new Wine patch resolves **shared standard user32 cursor resources** in their
owning process, then loads a local shared instance for GetIconInfo. The receiving
Wayland driver can use the intended shape through its existing path. It does not
force every cursor to an arrow or change mouse input routing.

The owner lookup validates the USER handle's type/generation. Internal Wine
messages transfer only a whitelisted resource integer, with a 50 ms deadline;
foreign GDI pointers/bitmaps are not dereferenced. A bounded cache retains resource
identities for successful lookups. Private/custom, animated and unsupported
foreign cursors keep the existing failure/fallback behavior. Local cursors,
null/hide handling and existing Wayland fallback code are unchanged.

Only `lib/wine/x86_64-unix/win32u.so` is replaced in the incremental runtime,
based on verified 0.1.2. Its internal message appends to the existing codes without
changing the server protocol or driver ABI. Source locks, JScript, Wayland driver,
DXVK and production helpers retain their prior contents. The full source build
recipe includes the new patch and defaults to 0.1.3; byte identity between a full
build and the incremental archive is not claimed.

## Evidence

The x64 two-process native component used a fresh, disposable Wine prefix and
message-only windows. It touched no report or Microsoft installation:

- Baseline 0.1.2: four checks passed, eight failed.
- Candidate 0.1.3: all **12 checks passed**: seven standard resources, local custom
  cursor, destroyed handle, preserved unsupported foreign custom case, repeated
  cached resolution and bounded failure for an unresponsive owner (50 ms).
- The public wrapper compiled and ran the same probe successfully and removed
  its own generated prefix after shutdown.

A separate own visible two-process window exercised actual GNOME compositor
pointer motion, without clicks. The left region selected a local NS resize cursor;
the right selected an arrow created by the helper process. On 0.1.2 the Wayland
shape requests stayed `[27,27,27,27]` (NS resize); on 0.1.3 they correctly alternated
`[27,1,27,1]` (resize/arrow). Pointer readback confirmed the own test window.
This establishes the reproducer's protocol behavior, not every Power BI cursor
or every submitted visual frame. The test services were stopped.

After the user closed Power BI, runtime 0.1.3 was activated and the real project
was reopened through the installed RPM 9 launcher, without diagnostic injection.
On October 18, compositor pointer motion between the sidebar divider and canvas
produced `[32644,32512,32644,32512]` in native cursor resource readback:
horizontal resize/arrow/horizontal resize/arrow. Each sample verified the main
window under the pointer and the compositor-to-native coordinate mapping.
This checks live resource selection and resolution; it does not certify every
rendered compositor frame or the original data-grid scenario. An earlier popup
hover run used the wrong window-coordinate assumption and is excluded from this
acceptance evidence. Only its informational notice was dismissed; no refresh,
settings submission, report edit or save was performed. All 452 monitored project
files matched their fresh pre-activation hashes. The installed doctor passed all
15 checks and RPM integrity verification was clean.

Custom browser cursors, diagonal resizing, drag-and-drop, physical display scaling
changes, x86/WoW64 execution and broader workloads need separate coverage.
The previous 158-table/soak evidence does not certify 0.1.3.

## Regressions and installation

From the source tree:

```bash
python3 tools/test-cursor-resource.py --runtime /path/to/runtime-0.1.3
```

This uses a host MinGW compiler, or the prepared Docker/Podman builder, and a fresh
Wine prefix. It closes its own processes and removes only that generated prefix;
logs/results remain private under `.local/cursor-resource/`. No .NET, Microsoft
installer, report, database or real pointer interaction is needed for this
component. `tests/e2e/cursor-shape-probe.c` supplies the separate visible fixture;
its compositor motion/protocol assertions are not yet integrated into a public
unattended runner.

RPM 9 is compatible with this runtime: no additional DNF upgrade is required.
Standard `pbi-linux update --runtime ... --runtime-sha256 ...` also snapshots the
profile and needs the documented disk space. This notebook uses a bounded local
runtime-only maintenance after Wine is idle, with active metadata backup and the
old runtime retained. Never replace the active pointer while a managed session
is running. The runtime archive's adjacent SHA-256 file identifies the exact
archive. Corresponding sources and sanitized QA evidence are prepared alongside
it in `dist/powerbi-linux-source-runtime-0.1.3.tar.gz` and
`dist/powerbi-linux-qa-runtime-0.1.3.tar.gz`, with adjacent SHA-256 files.
These are local development artifacts, not a published release; broader release
gates remain pending.
