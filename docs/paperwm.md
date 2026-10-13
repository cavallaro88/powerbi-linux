# PaperWM and normal Wayland window resizing

## Diagnosis and correction — 2026-10-18

On Fedora 44 / GNOME 50 / PaperWM 50.0.1, at 125% display scaling, Desktop
was a normal resizable Wayland window in the tiling space. PaperWM shortcuts
were registered, with no application-specific floating rule. Both a direct
MetaWindow resize and PaperWM's resize action reached a window whose native
style included WS_THICKFRAME, but its actual frame remained 880×673 logical
pixels while PaperWM requested a height of 824.

Wine 11.18's `wayland_configure_window` ignored width/height hints unless a
configure carried maximized, resizing or tiled state. PaperWM can issue normal
programmatic resizes without those states. The driver discarded their sizes;
changing the report, clearing its cache or disabling keyboard grabs does not
address that path.

`wine-11.18-wayland-normal-resize.patch` accepts these hints for resizable
windows after the initial configure has completed. Initial placement and
fixed-size behavior retain their existing path. Ordinary application size
constraints remain in effect. The change is confined to the Unix Wayland driver.
It is independent of the three inactive [Neutron candidates](runtime-testing.md).

## Observed evidence

A disposable native Win32 probe was tested against the unchanged 0.1.3 driver
and the candidate, in its own prefix without Desktop, credentials or reports:

| Check | Baseline | Candidate |
|---|---|---|
| Direct normal-window size request | Remains 720×480 | Applied, with PaperWM column height restored |
| PaperWM increase-width action | Ignored | Width increases to 1208 |
| Super+minus through compositor | Ignored | Width decreases to 1057 |
| Fixed-size control (`allows_resize=false`) | Existing path | Remains 720×480 |

Native WM_SIZE/client rectangles were recorded as well as compositor frames;
this checks actual application resizing rather than enlargement of a stale
buffer. A single-window PaperWM column fills the available height again after
a height action; that layout policy is distinct from Wine ignoring a request.

The normal managed Desktop launcher then opened an **empty** Home window with
the candidate. Its height matched PaperWM's 824 logical pixels. Two increase
**actions** and two compositor Super+minus inputs alternated widths 1208 and
1359, preserving height. The Home UI reflowed visibly. Direct synthetic injection
of Super+plus did not reliably invoke the shortcut in this session; the action
itself passed. The user subsequently confirmed that the PaperWM resizing
worked perfectly after activation (2026-10-18), resolving the manual acceptance
check. This user observation is separate from automated key-injection coverage.
No original report was opened or saved during these tests. Doctor passed all
16 checks and installed RPM 11 verification passed.

The standalone probe source is [tiling-probe.c](../tests/e2e/tiling-probe.c).
Build it using the project builder's MinGW compiler:

```bash
x86_64-w64-mingw32-gcc -municode -O2 -o tiling-probe.exe \
  tests/e2e/tiling-probe.c -luser32 -lgdi32
# Run only in a disposable native-Wayland test prefix:
WINEPREFIX=/absolute/path/to/disposable-prefix /path/to/runtime/bin/wine ./tiling-probe.exe
# Repeat with --fixed and the baseline runtime, closing the test Wine server
# before changing runtimes. The probe closes automatically after ten minutes.
```

Apply the same compositor requests to each runtime and record frame/buffer,
WM_SIZE and client/native rectangles. Missing graphical evidence is not a pass.
No debug shell extension or diagnostic D-Bus interface is installed by the product.

The visible white side strips were investigated separately after that confirmation;
see [window frame measurements](window-frame.md).

## Artifact and installation scope

The private incremental candidate is `0.1.4-paperwm-candidate`:

- Archive SHA-256: `5c1b78221ca28234e2e6dacf63c20c6d7ec7940a09470371b8378714b05a4bb0`.
- Base 0.1.3 archive: `4c630a409c92e3b84cb8848164ddd3f47dcce3968443c2ec0576a520fbc10c83`.
- Only changed executable payload: `lib/wine/x86_64-unix/winewayland.so`.
- Driver compiled from the retained patched Wine 11.18 tree in the existing
  project builder; the candidate manifest identifies this incremental origin.

The local profile was idle during activation. Only its runtime pointer changed;
the profile, application patches, settings and previous pointer were preserved,
with an activation backup and guarded rollback script in private evidence.
The old runtime remains installed. This local activation requires no DNF upgrade
or profile clone. RPM upgrades alone do not replace a per-user runtime.

The production **source recipe** now targets 0.1.4 and includes this patch in its
reviewed registry. No full Wine/WoW64 rebuild, public 0.1.4 runtime, full modal
regression, multi-monitor/mixed-DPI validation or exact-archive prolonged release
run is claimed. Those remain required before wider distribution. Do not label
the private incremental candidate a certified release or overwrite older archives.
