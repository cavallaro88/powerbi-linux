# Patch inventory

The initial patch set targets Wine 11.18 and DXVK 3.1. Wine composition incorporates four Neutron bridge/cross-process/resize/reaper patches and the cursor correction from `neutron-wine` commit `5afd8d479ca83f57b56a2350274927647519da90`, adapted to Power BI owner-process delivery. Reproduction ports are retained under `runtime/ports/`; the normal build applies the reviewed emitted patches rather than regenerating tracked files.

**Updated 2026-10-16:** runtime 0.1.2 / RPM 9 adds the HTML signed-Int64
conversion and the Options scroll-pane correction. It retains the 0.1.1 modal
parenting and RPM 8 permissions serializer. Exact-checksum synthetic evidence
is scoped separately from historical release gates; see [Options](options-dialog.md)
and [Edit Permissions](permissions-wayland.md).

| Patch or helper | Reason | Status / license |
|---|---|---|
| Wine composition aggregate | dcomp bridge, owner transport, cursor/HKL, optional capture and PE backing. Since 0.1.7-local.10 the owner transport also delivers frames while the main window is disabled by a modal dialog; see [Options](options-dialog.md#november-22-the-report-went-blank-behind-a-modal-dialog) | Required; Wine/Neutron LGPL-2.1-or-later |
| Wine composition frame transport | Frames wider than 4096 or taller than 2304 pixels were rejected in silence, so Desktop stayed blank on an ultrawide or 5K output; a publisher gave a frame up as soon as the receiver held its lock, and the browser does not present it again | Part of the composition aggregate; LGPL-2.1-or-later; local build only. Any frame shape up to 7680 x 4320 pixels in area (the mapping is sparse), a larger one logged once as `err:dcomp`; publishers wait up to 50 ms in all plus 1 ms per MB of frame (one shared deadline, as the caller holds the graphics lock), the receiver holds the lock for the copy alone and waits 8 ms plus the same per MB; the shared objects are named `__pbi_dcomp_v3_*` since the mapping grew. 5120 x 1440 headless output blank before, rendered after; 11 and 18 dropped frames while a report opened before, 0 and 0 after |
| Wine shared system cursor resources | Resolve foreign standard cursor identities with bounded IPC and load local images | LGPL-2.1-or-later; scoped 0.1.3 component/compositor candidate, see [cursor](cursor.md) |
| Wine HTML signed Int64 | Initialize legacy HTML Options when .NET exposes Int64 cache properties; HTML ES5+ only | Required; LGPL-2.1-or-later; seven numeric cases, x64 component |
| Wine OLE DB VARIANT conversions | Numeric/boolean values otherwise appeared as zero | Required; LGPL-2.1-or-later |
| Wine named pipe directory listing | Listing `\\.\pipe\` failed with `STATUS_BAD_DEVICE_TYPE`, so tools that find a program by its pipe name saw none; the pbir CLI reported no running Desktop | LGPL-2.1-or-later; not in a published runtime yet, see [named pipes](named-pipes.md) |
| Wine normal Wayland resize | Accept normal compositor size hints after initial configure for resizable windows; private 0.1.4 component/Desktop candidate, see [PaperWM](paperwm.md) | LGPL-2.1-or-later |
| Wine Wayland parent | Owned dialogs otherwise remained behind the main window | Required; LGPL-2.1-or-later |
| Wine single-mode monitor placement | Wayland outputs lost their position, so every monitor sat at the origin and a window on a second monitor was never painted | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md) |
| Wine Wayland data-control primary selection | A compositor that sends `primary_selection` to a version 1 device aborted the clipboard owner | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md) |
| Wine visible-region race | A resize by the window's thread could leave the frame receiver's cached DC clipped to the old client area | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md) |
| Wine OLE Automation maximum date | Rounding the last half second of year 9999 produced an invalid date; Analysis Services then launched SQLDUMPER at every start | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md) |
| Wine queue masks after internal messages | A cursor lookup that waited for another process left the UI thread waiting on a queue no message could signal; Desktop appeared frozen until the pointer shape changed | LGPL-2.1-or-later; local build only, see [cursors](cursor.md#desktop-frozen-after-a-cursor-change-2026-11-18) |
| Wine fixed-size dialog maximized state | Hyprland reports every mapped toplevel as maximized; Desktop's borderless legacy dialogs then ignored their own resize and stayed 2 x 2 pixels | LGPL-2.1-or-later; local build only, see [legacy HTML](legacy-html.md#dialogs-two-pixels-wide-on-hyprland-2026-11-18) |
| Wine toplevel state kept across configures | Hyprland sends a configure without a toplevel event when a window becomes hidden or visible; it was read as a request to leave the maximized state, and the window took its restored size inside an unchanged tile | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md#window-back-at-its-restored-size-after-a-workspace-switch) |
| Wine restored size after leaving the maximized state | A window that starts maximized and is answered without a size kept its maximized rectangle, was announced with a fixed size and was mapped floating | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md#desktop-mapped-as-a-floating-window) |
| Wine keyboard layout before a keymap | On a seat with no keyboard, or before the keymap arrived, text input focus announced a layout of language 0; WinForms threw CultureNotFoundException and Desktop never loaded the report (seen under headless GNOME) | LGPL-2.1-or-later; local build only, see [Hyprland](hyprland.md#fedora-44-gnome-container-check-2026-11-27) |
| Wine cgroup reporting | Report cgroup limits to CLR/Chromium/AS | Required; LGPL-2.1-or-later; initializes the path buffer in the product port |
| Wine secur32 status | Return NTSTATUS rather than BOOL from LsaFreeReturnBuffer | Required; source fix replaces the old machine-code patch; LGPL-2.1-or-later |
| DXVK presentation | Scoped GDI delivery for WebView HWND swapchains | Required; DXVK upstream terms, preserving Neutron-derived provenance |
| Culture helper | Select installed non-RTL UI cultures | Required; independent GPL-3.0-or-later |
| Desktop configuration names the AppDomain manager | The CLR clears the manager's environment variables once it has read them, so a Desktop started by Desktop (another report, a recent file, a restart) ran without the culture helper and crashed in `AppModule.Run`; `PBIDesktop.exe.config` now names it for every Desktop start | Required; applied only to 2.159.1231.0 and 2.160.1151.0, whose original file checksums are recorded (`CONFIG_ORIGINALS`) and checked before the change; two elements inserted at the start of `<runtime>`, refused if the file already names a manager or has no single `<runtime>` section; original kept with the other backups. 2.158.1177.0 and 2.159.883.0 keep their configuration (repair puts back one an earlier repair changed), and launch names the manager through environment variables, as before |
| Shared/WinRT local assembly changes | Installed-path discovery and missing WinRT contracts | Required for pinned app; independent GPL patch tools; patched Microsoft binaries remain local |
| AS self-token change | Replace a specific anonymous-impersonation call with real self impersonation | Experimental semantics, required by current recipe; original hash and byte checks enforced |
| WebView2 per-app Windows version | The investigated profile used `win7` for `msedgewebview2.exe`; reproducing it prevents fixed-runtime GPU crashes, while Desktop remains on `win10` | Required by the tested recipe |
| Modern Power Query switch | Select the tested WebView2 editor | Required, internal app interface that may change |
| Legacy HTML registration and UI resources | Restore Wine protocol/MIME handlers; work around an unsupported CSS setter, stale credential-sidebar height and zero-page virtualized source list | Required for the pinned app; exact input/output hashes and resource sizes checked; modified Microsoft assembly stays local |
| Normal Desktop window frame | Guarded two-method change plus a signed local helper; full client with transparent native edge input, unchanged fixed/owned/native-maximized paths | GPL-3.0-or-later tools; Microsoft binaries remain local; see [frame evidence](window-frame.md) |
| Options sizing and selection | Bound sidebar/content to the viewport, retain editable text, advertise native resizing for `SettingsDialog` only | Guarded 2.158/2.159 resource and IL changes; original callbacks retained; [scope](options-dialog.md#october-21-options-resizing-and-selection) |
| Quill font/size pickers | Use WebView's in-page select picker; preserve browser Escape before Desktop consumes it | Guarded local report-view HTML change; original controls/events retained; [scoped validation](text-pickers.md) |
| Browser title tooltips | Render HTML/SVG title tips inside WebView instead of detached native windows; preserve rich data tooltip handlers | Guarded local report-view HTML change; same-origin visual frames included; [scope](intermittent-popup.md) |
| Email dialog serializer | Serialize the three wire fields without traversing native host/button objects when Continue reads the view model | Guarded local resource change; native validation/authentication unchanged; browser sign-in and account persistence after normal restart confirmed on Fedora |
| Edit Permissions serializer | Serialize the 13 original wire fields without native host/button objects when OK pulls the view model | Guarded local resource change; privacy/encryption callbacks retained; synthetic compositor OK/Cancel/reopen passed |
| Options dialog shown | Let the Options page tell the host it is ready, which the Options recipe had stopped; the dialog otherwise stayed fully transparent where the compositor honours window opacity (Hyprland) | Guarded local resource change, 2.159.1231.0 and 2.160.1151.0; see [Options](options-dialog.md#november-21-options-was-an-empty-frame-on-hyprland) |
| Legacy dialog serializers | Serialize a dialog's view model without walking into the native host object when OK reads it; OK otherwise did nothing in Options, Export template, View as, connector warnings and about 15 more | Guarded local resource change to the two shared scripts, 2.159.1231.0 and 2.160.1151.0; a dialog's own `getJSON` still wins; see [legacy HTML](legacy-html.md#ok-did-nothing-in-most-legacy-dialogs-2026-11-21) |
| Auto recovery dialog serializer | Serialize the description and radio group state without traversing the native host object when OK reads the view model, so Desktop can close with unopened recovered files | Guarded local resource change, 2.159.1231.0 and 2.160.1151.0; original keep/delete handlers retained; keep, delete and no-file closes passed on one Hyprland host with 2.159.1231.0, OK with the default choice with 2.160.1151.0; see [legacy HTML](legacy-html.md#desktop-would-not-close-auto-recovery-dialog-2026-11-21) |
| Data source settings body | Stop the dialog body from scrolling; Wine laid it out five pixels short, which added two scroll bars over the sort button | Guarded step after the Options recipe, 2.159.1231.0 and 2.160.1151.0; see [legacy HTML](legacy-html.md#scroll-bars-inside-data-source-settings-2026-11-18) |

`WinRTStubs` reports APIs unavailable and contains incomplete methods; it does not implement Windows storage/launch contracts. No broader WinRT support is claimed. The self-token workaround is not equivalent to anonymous Windows identity.

RPM 10's `PatchStoreRating.cs` removes only the Windows Store rating entrypoint
from the local Desktop assembly. This avoids JIT loading a missing WinRT bridge
after a successful publish; upload/result handling remains unchanged. See
[publishing evidence](../user/publishing.md).

Discarded experiments, forced-success patches and legacy profiles stay in the private investigation archive, not in the product's active recipe. The optional Wayland capture hook is compiled from the aggregate patch but inactive without diagnostic flags; production environment removes them.

WinRT stub keys use an RSA signature key. Native `csc /keyfile` fails on Wine with CS1548/8013141e, so setup compiles an unsigned `WinRTStubs` assembly and signs it with dnlib using the locally generated key. The helper tests verify the resulting strong-name signature and reject an unrelated assembly.

Setup enables the modern Power Query switch through the application's local feature-storage implementation. It does not invoke `PackageStorageManager`, which depends on Unity services initialized by a running Desktop process. Existing user settings and other switches are preserved by the application's own storage API.

Optional Connector/NET installation is a provider recipe, not a Microsoft assembly
patch or a replacement connector. Downloads and the complete .NET dependency set
are pinned in `connectors/mysql.lock.json`, installed only on request and checked
through a per-profile manifest. The source-list patch resizes the existing widget
one tick after show only when its cached page size is zero; native enumeration,
selection and permission callbacks remain unchanged.

RPM 11's signed `PowerBICacheCompatibility` helper compacts valid linguistic JSON
in memory before the **complete original** TmslApplier model-copy/update path.
It preserves metadata changes rather than skipping application of project
schema. Guarded setup rejects unsupported/already patched assemblies. Existing
Newtonsoft.Json is used from the local application. See [failure isolation,
Save/reopen and limits](model-cache.md). The original application icon is
extracted locally by the CLI; it is not an assembly patch.

The [October 18 upstream review](upstream-neutron.md) covers 87 new commits and
all 59 changed patch files. The Neutron review itself did not change the production source pin/series.
The later, independently diagnosed PaperWM correction adds a patch for 0.1.4;
see [its separate evidence and limits](paperwm.md).
Three inactive candidates live outside `patches/`; build protection was adopted
independently. `runtime/patches.lock.json` prevents unreviewed production inputs.
