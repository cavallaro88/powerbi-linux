# Hyprland and multiple monitors

## Diagnosis and corrections: 2026-11-17

Host: Omarchy 4.5.0 (Arch based, kernel 7.2.15), Hyprland 0.56.2, Wayland 1.26.0,
NVIDIA RTX 3060 Laptop (driver 615.78.08) with Intel Iris Xe (Mesa 26.2.5),
Python 3.14.8. Two outputs at scale 1: 2560x1080 at (0,180) and 2560x1440 at
(2560,0). Power BI Desktop 2.159.1231.0, WebView2 154.0.4258.62.

With the published runtime 0.1.6-beta.1, setup and `doctor` passed and Desktop
started, but its window was blank. Four separate Wine defects were found. Each
has a reviewed patch in `runtime/patches/`; none changes Desktop or the recipe.

### 1. Blank window on a desktop with more than one output

Every WebView page loaded and rendered: a diagnostic browser screenshot showed
the home screen. The GPU process published frames, but the owner process never
delivered one. Its receiver paints a host only when `WindowFromPoint` finds that
host, and every sample returned no window.

Wine reported both monitors at the origin, `(0,0)-(2560,1080)` and
`(0,0)-(2560,1440)`, with the second work area clipped to an empty strip. The
main window was assigned to that monitor and placed at `(2556,-4)`, outside the
desktop window, so hit testing could not reach it.

Wayland outputs expose one host mode. `add_modes()` in `win32u/sysparams.c`
takes the physical mode of a single-mode source from the host mode list, which
carries no position, and the first current mode from that physical mode. The
driver's position is lost before it is ever stored. Wine 11.22 and the
development branch contain the same code. The display keys are volatile, so no
registry setting works around it.

`wine-11.18-single-mode-position.patch` carries the driver's position into the
physical mode, as the multi-mode path already does, and follows the host
placement while no emulated mode is active.

### 2. Clipboard owner aborted by a primary selection event

`explorer.exe`, which owns the clipboard, aborted in libwayland:
`listener function for opcode 3 of zwlr_data_control_device_v1 is NULL`.

The Wayland driver binds `zwlr_data_control_manager_v1` version 1 and registers
three device events, but its protocol XML describes version 2, whose fourth
event is `primary_selection`. Hyprland 0.56.2 sends that event to version 1
devices as well. libwayland then finds no handler and aborts the process.

`wine-11.18-wayland-data-control-primary.patch` adds a handler that destroys the
offered primary selection, which the driver does not use. Afterwards text copied
on the host was read by a Wine process, and text set by a Wine process was
offered to the host as `text/plain;charset=utf-8`.

### 3. Half of the window blank after a tiled resize

Once a second window briefly shared the workspace, Hyprland halved the main
window and restored it within a second. In one of the first eleven launches the receiver
then stayed clipped to the half-width client area `(0,0)-(613,1021)` although
the host was `1253x1021` again: the right half showed the form background.
Another process read the full visible region for the same host at that moment.

`update_visible_region()` in `win32u/dce.c` fetches the region from the server
and then calls `set_visible_region()`, which also clears the DC's dirty flag. If
the window's thread resizes it between those steps, `invalidate_dce()` flags the
DC in use and the stale region clears the flag again. The cached DC keeps the old
region until some unrelated invalidation. Ordinary applications draw a window
from its own thread; the frame receiver draws the WebView host from another
thread every 16 ms, which exposes the race.

`wine-11.18-visible-region-race.patch` stops `set_visible_region()` from
clearing the flag. Both callers clear it before they fetch, so the next drawing
call refetches.

### 4. A console window at every start

That second window was `SQLDUMPER.EXE`. At every start Desktop alters an
Analysis Services trace with `StopTime` set to the maximum date. The engine
passes it through `VariantTimeToSystemTime` and `SystemTimeToVariantTime`. Wine
rounded 9999-12-31 23:59:59.9999999 up to 1 Jan 10000, then rejected that date.
The engine reported `An error occurred while parsing the 'StopTime' element`,
raised an access violation while unwinding, and launched the dump tool, whose
console is an ordinary window to a tiling compositor. Nothing in this path
depends on Hyprland or on 2.159.1231.0 (`msmdsrv.exe` is the same file as in
2.159.883.0), but it was observed on this host only. A floating window manager
would show the console as a brief flash.

`wine-11.18-oleaut32-max-date.patch` keeps 23:59:59 for the last half second of
year 9999. The Windows result for that exact value was not measured; that the
round trip works in Analysis Services on Windows shows it yields a valid date.

## Observed evidence

Runtime 0.1.6-beta.1 is the published archive. The local build is a
`runtime/build.py` output of this source tree, SHA-256
`73fb3dae562434c923ef04c47b6bbc14aade87be6f8b1374044c82e7f95deab4`; it is not
published and a rebuild is not claimed byte-identical. The descriptions of two
patches and one source comment were reworded after that build; no code changed.

| Check | 0.1.6-beta.1 | Local build with the four patches |
|---|---|---|
| Monitor rectangles (`monitor-layout-probe`) | Both at the origin | `(0,0)-(2560,1080)` and `(2560,-180)-(5120,1260)` |
| Frames delivered to the main window | None | Delivered |
| `opcode 3` abort of `explorer.exe` | Observed in each session run | None |
| Clipboard, host to Wine and Wine to host | Not tested | Passed for text |
| Maximum date round trip (`variant-date-probe`) | Fails with year 10000 | 9999-12-31 23:59:59, converts back |
| `StopTime` errors and SQLDUMPER per start | 2 errors, console shown | None in two starts |
| Halve and restore beside a short-lived window | Not reached (blank) | Clip matched the host in ten rounds; stale once with only the first two patches |
| Tiled, maximized and fullscreen on each monitor | Not reached (blank) | Frames delivered and clip matched the host in every state |

The repeatable probes are `tests/e2e/monitor-layout-probe.cs` and
`tests/e2e/variant-date-probe.cs`. Compile them with the prefix's .NET compiler
and run them with the runtime under test, in a disposable prefix:

```bash
wine 'C:\windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo monitor-layout-probe.cs
wine monitor-layout-probe.exe
```

### Synthetic session

`tests/e2e/session.py --ui-refresh --save` ran against a fresh copy of a
three-table synthetic PBIP with the local build above. An earlier build with
only the first two patches gave the same results.

- Refresh was requested through Desktop's UI 14.33 seconds after launch.
- Independent ADOMD queries confirmed total 300, the fact row count and the
  relationship filter.
- Save wrote `Synthetic.SemanticModel/.pbi/cache.abf`.
- The native frames before and after Save were reviewed and showed Cafe 120,
  Suco 100, Cha 80 and total 300. No GPU restart or cgroup OOM was recorded.

## Scope and limits

- One host and one package snapshot. Arch is a rolling release; this does not
  certify other snapshots, GPUs, compositors or display scales.
- Fractional scaling, mixed scales and monitor hotplug were not tested. The
  desktop window still covers only the primary monitor while the virtual screen
  spans both; no failure followed from that in the states tested.
- The visible-region race was observed once and not reproduced under tracing;
  the correction follows from the code path rather than from a failing test.
  The stress rounds show no regression, not the absence of the race.
- Hyprland 0.56.2 offers no `xdg_toplevel_icon_manager_v1`, so windows have no
  per-window icon.
- `tools/test-window-frame.py` fails its "owned frame preserved" case here and
  passes under GNOME (mutter 50.6, checked 2026-11-27). Hyprland sends the
  owned test form a configure with the maximized state, even as a floating
  window, so Desktop's base class gives it the maximized insets (4,4,4,5) as on
  Windows. The probe expects the normal frame; the custom frame and resize
  zones pass. Runtimes from before and after the 2026-11-27 changes give the
  same result.
- No published runtime contains these patches. Until one does, build a runtime
  from the source tree; see [building](../development/build.md).

## Fedora 44 headless date check: November 24, 2026

The PR integration was built on Fedora 44 with the pinned builder image. A
[native C equivalent](../../tests/e2e/variant-date-probe.c) of the C# date probe
checks the same seven inputs and rejection of year 10000 without requiring .NET
in the disposable Wine prefix. Compile it with MinGW-w64 (also available in the
builder image):

```bash
x86_64-w64-mingw32-gcc -O2 -Wall tests/e2e/variant-date-probe.c -o /path/to/VariantDateProbe.exe -loleaut32
WINEPREFIX=/path/to/disposable-prefix WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree,mshtml=d' /path/to/runtime/bin/wine /path/to/VariantDateProbe.exe
```

Use a fresh, private prefix, then stop its own wineserver and remove it. The
recorded checks used a private runtime directory without a compositor socket;
no Desktop session or user installation was opened or changed.

| Runtime | Checks passed | Checks failed |
|---|---|---|
| Published 0.1.6-beta.1 | 6 | 2 |
| Local 0.1.7-pr-integration.1 | 8 | 0 |

Both failing inputs in the published runtime produced year 10000, which could
not be converted back. The candidate kept those inputs in year 9999. The normal
2026-to-2027 rollover still rounded up, and year 10000 as an input stayed
rejected. Both disposable prefixes stopped and were removed.

This validates the date conversion only. Monitor placement, clipboard exchange,
the visible-region race and Desktop's trace startup were not exercised by this
headless check; Fedora/GNOME graphical acceptance remains pending.
## Later corrections: 2026-11-18

Four further Wine defects were found on the same host. None changes Desktop.

- **Legacy dialogs two pixels wide.** Hyprland reports every mapped toplevel as
  maximized, and the driver passed that on to Desktop's borderless dialogs,
  which then ignored their own resize.
  `wine-11.18-wayland-fixed-dialog-maximized.patch`; see
  [legacy HTML](legacy-html.md#dialogs-two-pixels-wide-on-hyprland-2026-11-18).
- **Desktop frozen after a cursor change.** Not specific to Hyprland.
  `wine-11.18-queue-masks-after-internal.patch`; see
  [cursors](cursor.md#desktop-frozen-after-a-cursor-change-2026-11-18).

- **Desktop mapped as a floating window**, slightly larger than the monitor.
  `wine-11.18-wayland-unmaximize-restore-size.patch`; see below.
- **Window back at its restored size after a workspace switch.**
  `wine-11.18-wayland-keep-toplevel-state.patch`; see below.

### Desktop mapped as a floating window

Desktop sometimes came up as a floating window of 2564 x 1084 (2564 x 1444 on
the larger output) instead of a tile. It was first put down to the output the
window started on; the output plays no part.

- Desktop starts maximized. For a new window Hyprland predicts the size of its
  tile from the window it would split. If that window is floating there is no
  prediction, and the first configure carries no size and no maximized state.
  A floating dialog holding the focus is enough (observed); so is a floating
  window that is the first of its workspace while the focus is elsewhere (read
  from `DwindleAlgorithm.cpp`, not exercised).
- The driver cleared `WS_MAXIMIZE` and left the window at its maximized
  rectangle. That rectangle covers the monitor, so win32u reports the window as
  fullscreen and not resizable, the driver announces equal minimum and maximum
  sizes, and Hyprland maps a window with a fixed size floating.

The patch gives the window the size of its restored placement when a configure
ends the maximized state without a size. It is then an ordinary resizable
window; Hyprland tiles it and sends the size of the tile.

### Window back at its restored size after a workspace switch

Found while testing the previous correction on a workspace that was shown.

- Hyprland changes a window's suspended state when it becomes hidden or
  visible. That state exists from `xdg_wm_base` version 6; for an older client
  Hyprland only sends the surface configure, without a toplevel event
  (`XDGShell.cpp`, `setSuspeneded`). The driver binds version 2.
- The driver cleared its pending toplevel state after every sequence, so it
  read that configure as "no size, no states" and cleared `WS_MAXIMIZE`. A
  WinForms window answers by taking its restored size.
- The tile kept its size. The next toplevel configure, usually sent when the
  window gets the focus back, corrected the window. A window shown again
  without the focus stayed at its restored size inside the tile.

The patch notes whether a toplevel event arrived in the sequence. Without one
only the serial is new: it is handed to a configure that is still to be
acknowledged, or acknowledged at once, and nothing is applied to the window.
The last size is deliberately not applied again; a window that has resized
itself since would be put back. Without this patch the previous one would act
on every such configure.

### Evidence for both

`tests/e2e/window-state.py` shows its own windows and needs no Desktop session.

Local builds of this source tree, not published:

| Check | Runtime 0.1.7-local.4, without the patches | With both (SHA-256 `d7008184bd6ce496e2a431629a823383042b2feade28c93ba82d1e8bea8e571c`) |
|---|---|---|
| Maximized start beside a focused floating window (`window-state.py`) | Floating, 2568 x 1448 | Tiled |
| Tiled window while its workspace is hidden, and when it is shown again | Not maximized, 900 x 600 inside a tile of 2536 x 1390, both times | Maximized, 2536 x 1390 throughout |
| Desktop started while a floating dialog held the focus | Floating at 2564 x 1444 in 2 of 2 starts | Tiled in 3 of 3 starts |
| Legacy dialogs (`dialog-size.py`) | Passed | Passed: error report and Data source settings |
| `session.py --ui-refresh --save` | Passed | Passed: refresh from the interface, model total and fact rows verified, save observed |

The cursor wake test was not repeated on this build. It needs the desktop
pointer over the Desktop window, and these tests ran on a headless output so
that no test window covered the monitor in use.

Limits:

- One host. Other compositors answer a maximized start with a size, and send no
  configure without a toplevel event to a version 2 client as far as is known;
  neither was tested.
- The second case of a missing tile prediction (the first window of a
  workspace while the focus is elsewhere) was exercised on 2026-11-27: a
  maximized probe mapped on a workspace without the focus. With runtime
  0.1.7-local.14, which skipped the restore for an initial configure sent
  before the compositor saw the maximize request, it floated at 2568 x 1088
  in 6 of 20 starts; with 0.1.7-local.15 (archive SHA-256
  `609d4cc8a2b3e1f94f303a4286f7cefefa3327f8040e8617dcc2599cacd7dc18`), which
  restores on every initial configure, it was tiled and maximized in 24 of 24
  (12 with that driver built alone, 12 with the archive).

## Fedora 44 GNOME container check: 2026-11-27

Not Hyprland, but recorded here beside the other compositor evidence. A
Fedora 44 container with systemd, a lingering user and `mutter 50.6 --headless
--wayland --no-x11 --virtual-monitor 1920x1080` (software rendering, no input
device), on the same host.

- The RPM built by `tools/build-rpm.py` installed and passed `rpm -V`.
- `pbi-linux setup --runtime` with a local runtime and the cached installers
  completed; `doctor` passed all 25 checks.
- `tools/test-window-frame.py` passed, including the owned frame case that
  fails on Hyprland.
- With runtime 0.1.7-local.12, Desktop showed two .NET "Culture is not
  supported" errors at start and never loaded the report. The seat had no
  keyboard, so no keymap ever arrived, and the driver announced a keyboard
  layout of language 0 when a window gained text input focus. From runtime
  0.1.7-local.13 (`wine-11.18-wayland-no-layout-hkl.patch`) Desktop loads it
  with no dialog.
- The container had only Cantarell and Noto Sans, so ▲ and ▼ had no fallback
  font. Fedora Workstation installs Noto Sans Symbols 2 through
  `default-fonts-core-math`; the packages now depend on it
  (`font(notosanssymbols2)`, Debian `fonts-noto-core`, Arch `noto-fonts`).
- A fresh setup on 0.1.7-local.14, then `pbi-linux update` to
  0.1.7-local.15: `doctor` passed. On local.15 a copy of a report with tinted
  pill badges rendered `$258K`,
  `LY $231K` and ▲ ▼ in Noto Sans Symbols 2, as on Hyprland and Windows.
  `dialog-size.py` (error report and Data source settings),
  `test-number-format.py`, `test-window-frame.py`, `test-legacy-html.py`,
  `test-html-int64.py`, `test-store-rating.py`, `test-cache-compatibility.py`
  and `test-signin-settings.py` passed.
- Not run there: anything that needs input (no input device), the cursor
  wake test, and `tools/check-product.py`'s builder-compiled native probes.
