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
- No published runtime contains these patches. Until one does, build a runtime
  from the source tree; see [building](../development/build.md).
