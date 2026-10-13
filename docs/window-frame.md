# Window frame correction — 2026-10-18

After confirming that the PaperWM correction works, the user reported white
strips along the left and right sides, absent in their Windows installation.
A read-only native probe measured the active empty Desktop window on Fedora 44,
GNOME/PaperWM, with the local 0.1.4 PaperWM candidate. No styles, registry,
application settings, report content or active runtime were changed for this
investigation. The symptom was also visible before the resize correction.

## Measurements before correction

Coordinates below are native screen/window coordinates obtained by a
per-monitor-aware Win32 probe, rather than positions inferred from a crop:

| Measurement | Result |
|---|---|
| Window rectangle | `(100,50)–(1421,1080)`, 1321×1030 |
| Client origin on screen | `(104,50)` |
| Client size | 1313×1026 |
| Non-client insets: left, top, right, bottom | **4, 0, 4, 4** |
| Style / extended style | `0x16cf0000` / `0x00050100` |
| GetDpiForWindow | 96 |
| Window border / size-frame metrics | 4×4 |
| DWM composition enabled | true |
| DWMWA_EXTENDED_FRAME_BOUNDS | Same rectangle as GetWindowRect |

Visible main child/Chromium host rectangles fill `(104,50)–(1417,1076)`, exactly
the available client region. The side strips belong to the **non-client frame**,
not a margin in the report, a WebView CSS padding or a PaperWM column gap.
The top inset is already zero because Desktop draws its own title area.
This establishes the location of the artifact; it does not by itself identify
which application call should change.

## Why Windows can look different

Microsoft distinguishes the complete window rectangle, which can include
invisible resize borders, from DWM's visible frame bounds. It documents custom
frames through WM_NCCALCSIZE while retaining window hit testing. See
[GetWindowRect](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect)
and [custom frames](https://learn.microsoft.com/en-us/windows/win32/dwm/customframe).

In the prepared Wine 11.18 source, `DwmExtendFrameIntoClientArea` and
`DwmSetWindowAttribute` are successful stubs; extended frame bounds return the
complete window rectangle. Wine's ordinary frame calculation reserves the
measured size-frame inset. This is consistent with incomplete custom-frame/DWM
integration exposing a border that Windows handles differently. The precise
Desktop frame call sequence and the Windows baseline have **not** been traced;
no single stub is yet proven to be the complete cause.

## Implemented local candidate

`PatchWindowFrame.cs` changes two methods on the pinned Desktop's
`ResizableFormWithCustomCaption`: the normal non-client calculation and its
load callback. Exact canonical method-body hashes, signatures and branch layout
are checked before writing; unsupported and already-patched inputs fail.
Only a normal, resizable, unowned top-level window extends its client to the
complete window rectangle. Owned, fixed and native-maximized calculations keep
the original path. Window styles and application size constraints are retained.

The signed local `PowerBIWindowFrame.dll` creates three transparent native input
children along the sides and bottom. They deliberately draw/erase nothing;
WebView content reaches the visible edge. Hit tests and non-client mouse
messages reach the original form, including corners. Size/handle/disposal events
update and release these children. Existing caption/top-resize controls remain
under Desktop's control. No global hook, diagnostic server or keyboard shortcut
change is installed. This is separate from the [Wine resize correction](paperwm.md).

The local activation changed only Desktop's Windows assembly, this new helper
and their entries in the active patch manifest. The original DLL/metadata and a
guarded idle-only rollback script are retained privately. Runtime and resource
settings remain unchanged; no profile clone or report write was needed.

## Observed validation

- A disposable Win32 custom-frame fixture filled its complete client area and
  resized through compositor-delivered edge dragging.
- A baseline and candidate using the **actual Desktop base class** checked normal
  geometry, WS_THICKFRAME, left/right/bottom hit targets, an owned control and a
  fixed control. A hidden HWND with controlled native maximize flags compared
  the original maximized calculation and the normal calculation after clearing
  the flag. This is a component check, not a compositor maximize/restore test.
- The managed candidate also passed a real compositor edge drag, increasing its
  logical width from 726 to 774. The blue child content filled the complete frame.
- Normal-launch Desktop changed from a 1321×1030 window / 1313×1026 client to
  **1321×1030 for both**, with **0,0,0,0** insets. Native point queries selected
  the input children and returned HTLEFT, HTRIGHT and HTBOTTOM.
- The user confirmed the strips disappeared and mouse/shortcuts continued to work.
  No user report was opened or saved by the agent. An additional automated live
  drag was aborted before clicking when its pointer-position guard failed; it
  is not counted as passing evidence.
- Installed RPM 11 doctor passed 16 checks after local activation; the source
  recipe adds a seventeenth `window-frame` integrity check. Resource defaults
  remain unlimited/automatic.

Local candidate hashes:

| File | SHA-256 |
|---|---|
| Patched Desktop Windows assembly | `afbda058541d3f920dc4b3b230ea45256365bff5f18cc8f3bd91987493c10aa5` |
| Signed local frame helper | `cca0f0d909544ccbc846d5d573f84f4c42da45a6107443335ecc242f1e33190b` |

The signing key is generated locally during setup/repair; a fresh installation's
helper and patched assembly need not have these same hashes. Modified Microsoft
assemblies and the populated test prefix are not redistributed.

The final quick suite passed 75 Python tests plus syntax, desktop integration,
upstream consistency and source export checks. Baseline/candidate native probes
passed 14 checks each. A same-length modified method body was rejected by the
canonical guard; repeated/unsupported inputs were also rejected. The RPM 12
source/binary packages built successfully with helper compilation and strong-name
verification. These checks do not certify the full runtime release.

## Repeatable checks and remaining coverage

```bash
python3 tools/test-window-frame.py
# Compare a private unpatched assembly directory:
python3 tools/test-window-frame.py --baseline --assembly-dir /private/baseline
# Keep only the disposable candidate probe open for compositor input tests:
python3 tools/test-window-frame.py --hold
```

The fixture constructs a disposable base form, not a report, database connection
or cloud service. Evidence stays under ignored `.local/window-frame-tests/`.
The current assertions cover native 96-DPI metrics on the 125% Wayland host;
they do not substitute for the separate display-scale matrix. Native checks in
`check-product.py --suite components` require a dedicated QA installation.

An attempted **actual compositor maximize/restore** test was unstable. Without
the correction, native `IsZoomed` became false while WinForms still reported
Maximized, with rectangle `(-4,-4)–(1924,1084)`. The initial immediate/private
cycle passed once; subsequent baseline and candidate checks did not establish
stable compositor state. This existing divergence is retained as a separate
coverage gap, not treated as a passing maximize gate or hidden with repeated
state-setting. The controlled HWND calculation check above remains distinct.

The frame correction is included in RPM 12's **source recipe** and applied on
setup/repair with Desktop closed. Updating the RPM alone does not patch a running
profile. This machine already has the local candidate: no DNF or repair is
needed merely to test it. Full public release certification remains pending.

Removing the resizable style globally would undermine the PaperWM behavior just
validated. A compositor crop can conceal pixels while leaving incorrect client
geometry/input offsets; a background-color change still leaves the inset.
Neither establishes a proper frame implementation.

Before broader release, complete the display-scale and interaction matrix:

- Side/bottom content reaches the intended visible frame at 100%, 125% and 150%.
- Native rectangles, painted client pixels and pointer targets agree.
- PaperWM increase/decrease, mouse edge/corner resizing, maximize/restore and
  minimum-size constraints still work.
- Caption buttons, title dragging, fixed-size and owned dialogs retain behavior.
- Empty Desktop and synthetic Options/permissions windows pass a real compositor
  check, without changing or saving the user's report.

Private screenshots/probe output remain outside the public repository.
