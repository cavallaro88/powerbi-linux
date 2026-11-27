# Legacy HTML dialogs

Some Desktop dialogs still use Wine MSHTML/Gecko, including database
credentials. A refresh can wait for one of these dialogs while its progress
animation and Cancel button appear frozen. A responsive main thread or CPU
activity alone does not establish that data loading is advancing.

The Fedora reproduction on October 14 had a 2 × 2 credential window disabling
both the report and the refresh dialog. A read-only managed stack identified
`CredentialsChallengeResolver.ShowResolveDialog`. Cancelling that request
revealed the original refresh errors asking for MySQL credentials.

## Corrections

Setup/repair registers Wine's own `mshtml.dll` in both architectures after the
installers. The affected prefix had HTML COM class entries but lacked the
`about:` and `res:` protocol handlers and the `text/html` MIME handler. Installing
Gecko alone did not restore these entries. Doctor now checks the persisted
registrations and the activated UI patch version without starting Wine or
opening a browser. Upgrading only the RPM leaves this check pending until
`pbi-linux repair` applies the recipe to the existing installation.

The original credential correction in `Microsoft.Mashup.Client.UI.dll` makes two changes
to embedded JavaScript resources:

- In `ts/jquery.extensions.js`, an `E_NOTIMPL` from the DOM `textOverflow`
  setter enables a jQuery hook using `style.setProperty`. Other errors propagate.
  The credential title's SmartTip otherwise interrupts dialog initialization.
- In `ts/floatingdialog/floatingdialog.js`, a deferred pass clears the credential
  sidebar's stale inline height and repeats the existing layout calculation
  after `showDialog` assigns the final width. Error display can calculate that
  height before the final width is assigned, leaving the credential fields above
  the visible area even after HTML initializes. The pass runs only for a
  credential challenge; other legacy dialogs keep their existing sizing.

The recipe checks the exact original assembly and final output hashes, preserves
PE/resource sizes and IL, and retains the original backup. It does not replace
the credential backend, select an authentication method, supply a password,
change source permissions or approve native queries. The existing localized
HTML controls, credential scope choices and cancellation callbacks remain in use.

Updating an RPM changes the CLI recipe; it does not rewrite an existing profile
or reload assemblies in a running Desktop. Close Desktop before setup/repair.
An older CLI repair recipe does not include these corrections. Save pending work
before restarting a session that already loaded the old assembly.

## Component test

```bash
python3 tools/test-legacy-html.py
```

This opens only its own offline test window and checks rendered HTML,
JavaScript evaluation and a callback to .NET. It does not patch the installation
or interact with Desktop. It is a component test, not certification of every
Desktop HTML dialog or database connector.

See [native close confirmation](native-dialogs.md) and
[refresh cancellation](refresh-cancellation.md) for the separate close/save and
engine cancellation paths. A cancelled credential request does not establish
that cancelling an already-running database query succeeds for every connector.

## Credential dialog validation

On Fedora 44 Wayland, a fresh Desktop process opened a disposable two-table
PBIP whose MySQL source used the closed loopback address `127.0.0.1:65534`.
The first credential window measured 702 × 381, with 700 × 379 HTML content;
fields and Cancel were inside the viewport without a diagnostic sizing script.
Native mouse messages switched to the Database tab and then clicked Cancel.
The credential window disappeared within the first observation at 0.129 seconds.
After dismissing the refresh result, the main native window was enabled again.
No credential values were entered or submitted.

The diagnostic Desktop copy used a private inspection helper and test-only
cgroup limits of 10 GiB RAM / 2 GiB swap. The RAM ceiling was reached, with zero
OOM events or kills. Product defaults were unchanged, and the test process and
its browser policy were removed afterward. These checks cover first-show
layout, tab interaction and credential cancellation; they do not certify MySQL
authentication, network refresh completion or every connector.

## Data source list — RPM 7

The source-settings dialog uses a separate virtualized list. A CSV-only fixture
proved that native discovery returned one source while the HTML had zero rows:
its cached viewport and page size were both zero even after the visible container
reached 300 pixels in height. Calling the widget's original resize changed page
size to 10 and rendered the source. A fresh process with the guarded resource
patch did the same without manually invoking a resize. MySQL source rows also
appeared after the successful synthetic database refresh.

The recipe now includes a third resource, `komanagedatasourcesdialog.js`: after
showing the dialog it requests the widget's own resize if its cached page size
is zero. PE/resource sizes and IL remain unchanged. Doctor verifies the complete
updated UI assembly. No source is synthesized, and discovery, queries and
permissions remain under Desktop's original handlers. See [connectors](../user/connectors.md)
for the independent MySQL dependency and full validation scope.

Visible sources were also confirmed in the real report. A missing
cursor and unresponsive clicks initially recovered after an estimated 10–60 seconds. This observation
does not establish a cause or certify physical input latency; the resize patch
only corrects list geometry.

## Edit Permissions — RPM 8

The original getViewModel fallback traversed native host/button objects while
serializing the form, causing TargetParameterCountException after OK. The new
size-preserving resource patch supplies getJSON for its 13 original wire fields.
It preserves privacy, credential type and encryption; original handlers perform
persistence and cancellation. This is separate from runtime 0.1.1's Wayland
modal/popup correction. The synthetic compositor-input cycle passed with both.
The nested None/Delete Permissions confirmation is still limited;
see [scope](permissions-wayland.md).

## Options initialization and scrolling — runtime 0.1.2 / RPM 9

The Options dialog exposed a separate .NET Int64-to-JavaScript conversion failure
in Wine, followed by a pane-height error. The runtime and guarded local UI recipe
fix these two stages; seven numeric cases and the 22-tab synthetic navigation/
geometry audit passed. See [Options](options-dialog.md) for evidence, installation
and remaining limits. This does not certify other untested nested HTML dialogs.

## Dialogs two pixels wide on Hyprland: 2026-11-18

Observed on the two-monitor Hyprland host described in [Hyprland](hyprland.md),
with Desktop 2.159.1231.0. The unexpected error report ("Something went wrong")
and Data source settings opened as a 2 x 2 pixel window with no visible content
while the main window stayed disabled. To the user this is a frozen Desktop
with nothing to dismiss. Posting `WM_CLOSE` to the dialog restored Desktop.

### Diagnosis

These dialogs share one host (`Ux.FloatingDialog.FloatingDialog`): a borderless
owned WinForms form that starts at 2 x 2 pixels. The page measures its content
and calls the host (`ModalDialog._resizeHost` to `Js_OnResize`), which sets the
form size.

- Trace probes in the dialog script showed the page healthy: 4434 characters of
  content, measured at 460 x 242, and the host call made and returned.
- No `SetWindowPos` followed. A relay trace showed the host reading the monitor
  DPI and nothing else.
- The form carried `WS_MAXIMIZE`. Hyprland sets the maximized state on every
  toplevel when it is mapped, so that clients draw no decorations, and the
  Wayland driver mirrors that state into the window style. WinForms only
  records a new size while a form is maximized.

An earlier working diagnosis in this file blamed Internet Explorer's element
resize events, which Wine's HTML engine does not raise. Polling the size in the
dialog script instead changed nothing, which disproved it.

### Correction

`wine-11.18-wayland-fixed-dialog-maximized.patch` ignores the compositor's
maximized state for an owned window without a sizing frame, unless the window
is maximized itself. Such a window is announced with equal minimum and maximum
sizes and cannot have been maximized by the compositor. No Desktop file and no
dialog script changes.

### Evidence

`tests/e2e/dialog-size.py` opens a dialog in a diagnostics session and checks
its window. Local builds of this source tree, not published:

| Check | Without the patch | With the patch (SHA-256 `85894f9f8dc06c6153899df058edbf75b1be40e46a84cad073a701b78b6fe8d6`) |
|---|---|---|
| Unexpected error report | 2 x 2, maximized | 462 x 244, not maximized, in two runs |
| Data source settings | 2 x 2, maximized | 802 x 609, not maximized |
| Content and buttons | Nothing visible | Message and buttons drawn; Cancel and Close dismissed the dialogs and re-enabled the main window |
| Main window | Maximized style, tiled | Unchanged |
| `session.py --ui-refresh --save` | Passed on 2026-11-17 | Passed: total 300, fact rows, relationship filter, save |

Limits:

- One host. Other compositors do not report a floating dialog as maximized, so
  the patch should not act there; that was not tested.
- Only these two dialogs were opened. The navigator, credential prompts and the
  Power Query dialogs use the same host and were not exercised.
- A first version read the window style while holding the driver's window data
  lock and deadlocked Desktop during startup. The style is now read first.
- Data source settings showed scroll bars inside the dialog; see the next
  section.
- The error report was triggered by sending the report page's error message to
  the host with one argument missing. Desktop's own handling of that error is
  what the dialog reports.
- The error report does not always settle at 462 x 244. Counting the first
  three openings of four fresh sessions, it settled at 640 x 224 in 4 of 12
  with this patch alone and in 5 of 12 with the later driver patches: the same
  content on fewer lines. 640 is the width of the page laid out in a wide
  window (the message has a maximum width of 600 pixels), 462 its width laid
  out in the initial 2 x 2 window. What gives the page a wide window in those
  openings was not established.

## Scroll bars inside Data source settings: 2026-11-18

Same host and Desktop build. Once the dialog had its size, its body showed a
vertical and a horizontal scroll bar although the content is laid out for the
dialog's width, and the vertical bar covered part of the sort button.

### Diagnosis

Probes in the shared dialog script reported the layout three seconds after the
dialog was shown:

- The body is `#dialogContent` (`.o-group-body`), a flex item of the column
  `.modal-main`. The style sheet gives it `overflow-y: auto` and a maximum
  height of 590 pixels in a dialog that cannot be resized.
- The body was 800 x 453 with a client area of 783 x 436 and a scrollable
  extent of 800 x 441. The engine gave the flex item a content height of 436,
  five pixels less than the extent of its last row of buttons.
- Those five pixels call for the vertical bar. The bar narrows the client area
  to 783, two children have a fixed width of 800
  (`.o-group-dataSourceView`, `.o-group-bottomRowContainer`), and that calls
  for the horizontal bar.
- It is not stale state: hiding the body and showing it again, which rebuilds
  its box, changed nothing. Hiding only the horizontal axis left the vertical
  bar and a body of 436.

Whether Internet Explorer's engine computes the same five pixels differently
was not measured; no Windows installation was compared.

### Correction

The source list scrolls by itself (`.o-group-dataSourceEntries`, 300 pixels
high) and the dialog is sized to its content, so the body never needs to
scroll. One more guarded step in the UI recipe sets `overflow: hidden` on the
body before the dialog is shown. It takes 55 of the 110 bytes of padding the
source list step left in `komanagedatasourcesdialog.js`; PE and resource sizes
and IL stay unchanged.

The step is applied to **2.159.1231.0 and 2.160.1151.0**. The recipe verifies
the hash of the complete assembly, and 2.158.1177.0 and 2.159.883.0 were not
available to compute one; they keep the output of the Options step. In
2.160.1151.0 the source list resource is byte-identical, 704 bytes earlier, like
the other shifted resources. `pbi-linux doctor` reports the installed assembly
as outdated until `pbi-linux repair` has run.

### Evidence

| Check | Before | With the step |
|---|---|---|
| Body client area | 783 x 436, both bars | No bars |
| Dialog window | 802 x 587 | 802 x 592 |
| Sort button | Partly covered | Whole |
| Recipe output, 2.159.1231.0 | `3b0639cf...` | `426f5e88...`, same length, only the source list resource differs |
| Recipe output, 2.160.1151.0 | Options step output | `c7d7c812...`, same length, only the source list resource differs |
| Dialog window, 2.160.1151.0, Hyprland headless output | Not measured | 802 x 592, not maximized |

Screenshots of both views of the dialog (Global permissions and Data sources
in current file, with four and five buttons in the bottom row) were reviewed:
no bars, the sort button and every button whole. The dialog's own Close button
closed it and re-enabled the main window. The fixture has no external source,
so the list showed its empty text in both views.

Limits:

- One host. The step does not depend on the compositor, but only this one was
  used.
- On 2.160.1151.0 the dialog's size was checked, not its pixels: screen
  captures of the headless output came back black on that run. The changed
  resource is byte-identical to the one reviewed on 2.159.1231.0.
- The warning row for unknown data sources was not shown in the test. With
  the body no longer scrolling, content taller than 590 pixels would be cut
  off instead; nothing in this dialog comes near that height.
- Other dialogs with the same body rule were not examined for the same five
  pixels.

## Desktop would not close: Auto recovery dialog, 2026-11-21

Observed on the Hyprland host with Desktop 2.159.1231.0. Closing Desktop while
AutoRecovery held a recovered file that was never opened showed "Auto
recovery" ("There are recovered files that haven't been opened..."). OK did
nothing with either choice. Cancel and the close button cancelled the close,
and the next close showed the dialog again, so Desktop could not be closed
except by stopping the session.

### Diagnosis

- The dialog is a legacy HTML floating dialog
  (`FloatingDialog.AutoRecoveryKeepOrDeleteDialog`, its script an embedded
  resource of `Microsoft.PowerBI.Client.Windows.dll`). Its main thread
  answered `WM_NULL` at once, and clicks reached the page: a posted click
  selected the other radio button.
- OK makes the host read the page's view model (`KoFloatingDialog.getViewModel`).
  This view model has no `getJSON`, so the page falls back to `ko.toJSON`.
  Knockout walks every enumerable property, including inherited ones, and the
  `_typedHost` getter of `KoFloatingDialogViewModel` returns the .NET host
  object.
- With `warn+jscript`, OK raised `0x8002000e` (`DISP_E_BADPARAMCOUNT`) with
  the stack `_typedHost`, `performance`, `mark`: Wine's JScript enumerates the
  host object's members and reads the `mark` method as a property. The
  exception ends the OK handler. This is the failure the email and Edit
  Permissions serializers already work around.
- The host deserializes the result and reads only
  `keepOrDeleteRecoveredFilesRadioGroup.state`; `delete` removes the files.

### Correction

The recipe gives this view model a `getJSON` that serializes plain values only:
the description and the radio group's name, label and state. It is a
size-preserving change to the embedded script, guarded by the original and
patched resource hashes (`a86f3f8f...`, `511d75f7...`); the indentation below
the module marker and the source map comment make room for it. It is applied to
**2.159.1231.0 and 2.160.1151.0**; the resource is byte-identical in both.
`pbi-linux doctor` reports it as `auto-recovery-dialog`; `pbi-linux repair`
applies it.

### Evidence

Production session after `pbi-linux repair`, Desktop closed with `WM_CLOSE`
and OK clicked with posted mouse messages:

| Check | Before | With the correction |
|---|---|---|
| OK, "No, remove the files" | Dialog stays open | Desktop exited 3 s later; the recovered file was removed |
| OK, "Yes, I want to view the files later" | Dialog stays open | Desktop exited 2 s later; the recovered file was kept |
| Close with no recovered file | Not tested | No dialog; Desktop exited 7 s later |
| `tools/test-powerbi-recipe.py --version 2.159.1231.0` | Not run | Passed, same length |
| 2.160.1151.0, QA installation, Hyprland headless output, OK with the default choice | Dialog still open 60 s later; the recovered file was kept | Desktop exited 3 s later; the recovered file was removed |
| `tools/test-powerbi-recipe.py --version 2.160.1151.0` | | Passed, same length |

Limits:

- One host. 2.158.1177.0 and 2.159.883.0 keep the original script.
- Other floating dialogs whose view model has no `getJSON` failed the same
  way on OK. The survey that followed and the shared correction are in the
  next section.
- The dialog opened on the focused workspace rather than with Desktop's main
  window, as other dialogs of this family do on Hyprland. That is not changed.

## OK did nothing in most legacy dialogs, 2026-11-21

A survey of every legacy HTML dialog after the Auto recovery incident, on
Desktop 2.159.1231.0.

### Diagnosis

- Every Knockout floating dialog loads one shared script,
  `ts/floatingdialog/kofloatingdialog.js`, and drop-down forms load
  `ts/dropform/dropform.js`. Both are MSHTML-only resources of
  `Microsoft.Mashup.Client.UI.dll`; WebView2 pages do not load them.
- On OK, the host calls `getViewModel`. Without a `getJSON` of its own, the
  view model is serialized with `ko.toJSON`. Knockout walks inherited
  enumerable properties too: the `_typedHost` getter of
  `KoFloatingDialogViewModel` and the `_host` of every button view model return
  the .NET host object, a COM object. Wine's JScript enumerates its members
  and reads each one; a method that takes arguments raises
  `DISP_E_BADPARAMCOUNT`, which ends the OK handler.
- About 19 dialogs reach that fallback. Among them are Options, Export
  template, View as, the third-party and preview connector warnings, the
  DirectQuery and storage mode choices, "Discard all query changes", import of
  a custom visual, Edit Permissions for several sources, the Navigator
  parameter picker and the error report's "Send details". Cancel and the close
  button do not read the view model, so those dialogs could be cancelled but
  not confirmed.

### Correction

`src/pbi_linux/dialog_serializers.py` gives both shared scripts a walker
equivalent to `ko.toJS` that returns nothing for an object that is not a
JScript object (`instanceof Object` is false for a COM object, and the test
calls nothing on it). The JSON is what Windows produces minus the host
objects, which the C# side never reads: it deserializes with
`JavaScriptSerializer`, which ignores missing members. A view model's own
`getJSON` still wins, so the Auto recovery, email and Edit Permissions
serializers stay as they are. Knockout itself is unchanged.

Each resource is found by a unique marker and its .NET length prefix, guarded
by its original and patched hashes, and changed in place: leading indentation
(and, in the drop-down form, three comments and the source map comment) make
room for the walker. The complete assembly hash is recorded per build. It is
applied to **2.159.1231.0 and 2.160.1151.0**, whose two scripts are
byte-identical; `pbi-linux doctor` reports it as `dialog-serializers`.

### Evidence

| Check | Before | With the correction |
|---|---|---|
| File > Export > Power BI template, OK (Hyprland, QA installation) | Dialog stayed open after two clicks; Cancel closed it | Dialog closed and the Save dialog opened |
| Walker against Desktop's own knockout and dialog scripts (Node, host simulated as a COM-like object that throws when read) | Original throws at `performance.mark` | Output equals `ko.toJSON` with host objects left out on 3000 random object graphs; the host is never read |
| `tools/test-powerbi-recipe.py --version 2.159.1231.0` | | Passed, same length |
| 2.160.1151.0: File > Export > Power BI template, OK (Hyprland headless output, QA installation) | Dialog stayed open | Dialog closed and the Save dialog opened |
| 2.160.1151.0: Options, OK with no changes | Dialog stayed open | Dialog closed |
| `tools/test-powerbi-recipe.py --version 2.160.1151.0` | | Passed, same length |

Limits:

- One host. Node is not Wine's JScript: the JScript
  behaviour relied on (`instanceof` and `typeof` on a COM object) comes from
  the Wine 11.18 source, and the Export template and Options runs above.
- Dialogs whose page wires its own OK (Analysis Services live connection
  properties, the Report Server dialogs) were not resolved.
