# Changelog

## 0.1.0 — development

### RPM release 12 — window frame development candidate, 2026-10-18

- Extend the normal resizable/unowned Desktop client to its complete frame. Replace the visible 4-pixel side/bottom gutters with transparent native resize input zones, preserving styles and fixed/owned/native-maximized calculations.
- Guard the two patched methods by exact contents and sign the helper locally. Setup/repair records its checksum; doctor checks the frame patch. Modified Microsoft binaries stay local.
- Native and actual-base-class fixtures passed frame, hit-target and owned/fixed controls. A managed compositor drag passed; normal Desktop measured zero insets, and the user confirmed the visual fix with working mouse/shortcuts. Actual compositor maximize-state divergence also reproduces on baseline and remains separate coverage, as do other display scales and broader modal workloads. See [evidence](docs/window-frame.md).
- Apply the candidate locally without cloning the profile or changing the runtime/resource policy; retain the old DLL/manifest for rollback.

### Runtime 0.1.4 — PaperWM development candidate, 2026-10-18

- Accept normal Wayland compositor size hints for resizable windows after initial configure. PaperWM resizes without maximized/resizing/tiled flags were previously discarded.
- Native baseline/candidate tests confirm actual client resizing and preserve the fixed-size control. Empty Desktop on the normal launcher follows column height, increase-width actions and compositor Super+minus. The user subsequently confirmed PaperWM resizing works perfectly; automated Super+plus injection remains separate coverage. See [scope and pending checks](docs/paperwm.md).
- Activate a private incremental single-driver candidate locally, retaining runtime 0.1.3 and the existing profile/settings. Add the reviewed patch to the 0.1.4 source recipe; full rebuild and broader release gates remain pending.
- Record the separate acceptance plan for the three still-inactive Neutron candidates in [runtime testing](docs/runtime-testing.md).
- Diagnose the visible white frame as 4-pixel non-client left/right/bottom insets, with content filling the client area. Record the remaining cosmetic compatibility work without changing window styles or deploying an untested frame correction.

### Unreleased — product repository and upstream review

- Promote the standalone product to the repository root, with normal GitHub discovery, a shorter README, documentation index and explicit roadmap. Preserve private investigation/history outside the public product history.
- Guard runtime packaging against unreviewed patch files, failed/stale builds, changed sources/payload and accidental artifact overwrite. Record the successful build and exact builder/input identity; retain unchanged runtime 0.1.3 artifacts.
- Review the 87 neutron-wine commits through `8ecb7fd`, with decisions for all 59 changed patch files and separate external-library scope. Add a repeatable consistency audit to quick QA. No new runtime patch is enabled.
- Stage mouse capture tracking, rendering-mode glyph caching and signed DPI arithmetic separately. The actual Wine DPI helper fails six of fourteen arithmetic controls before the port and passes all after; server/compositor validation remains pending.


### RPM release 11 — cached models and original app icon, 2026-10-18

- Compact valid linguistic JSON in memory before the existing model-copy/update path. The original ABF restores successfully; reapplying extensive multiline linguistic metadata caused a separate Analysis Services failure. Preserve all JSON values, escapes and number tokens; apply genuine source metadata changes normally. No report file or cache is automatically deleted or rewritten by the correction.
- A private 158-table copy passed Desktop Save, graceful close and fresh normal reopen without refresh. All table row counts/states matched, including one existing query-error state. A new source-defined measure returned 73 before and after reopening. This is scoped evidence, not certification for every model or data value.
- Extract the original PNG icon from the installed Power BI executable during user integration and refresh it on launch after upgrades. Retain the packaged fallback before provisioning; no Microsoft artwork is redistributed.
- Setup/repair compiles and signs the guarded cache helper locally; runtime 0.1.3 and unlimited resource defaults remain unchanged. See [cache validation](docs/model-cache.md).

### RPM release 10 — post-publish Store rating, 2026-10-18

- Disable only the Windows Store rating entrypoint on Fedora, returning a completed Task. Its WinRT awaiter caused a missing `System.Runtime.WindowsRuntime` error after a successful publication, even before its UWP gate ran.
- A real publication was confirmed by the user in the homologation Service workspace. Offline baseline reproduced the exception; the candidate and public regression completed with null dependencies and no publication request. One method among 29,697 changed, with embedded resources preserved. A new cloud publication using the correction remains separate.
- Setup/repair compiles the guarded patcher from project sources; runtime 0.1.3 and resource defaults are unchanged. See [publishing](docs/publishing.md).

### Runtime 0.1.3 — cursor development candidate, 2026-10-16

- Resolve foreign shared standard user32 cursor resources through bounded internal Wine IPC and load them locally. This lets the existing Wayland path update a stale resize cursor when an embedded browser selects an arrow.
- Preserve unsupported/custom foreign behavior and local cursor handling. Incremental payload replaces only Unix win32u from runtime 0.1.2; RPM 9 remains compatible.
- Twelve x64 component checks and a compositor-motion resize/arrow reproducer passed. After activation, live Power BI sidebar/canvas hover alternated horizontal resize/arrow resources twice with verified pointer targets (2026-10-18). Doctor passed 15 checks; 452 monitored project files were unchanged. Original data-grid, custom cursor and broader workload coverage remain separate. Add public component and visible-fixture sources; see [cursor evidence](docs/cursor.md).

### RPM release 9 / runtime 0.1.2 — development candidate, 2026-10-16

- Convert signed Automation Int64 values to JavaScript numbers in Wine's HTML ES5+ engine. This prevents the Options cache-description binding from interrupting initialization; legacy standalone variant handling stays behind its original path.
- Bound the existing Options scroll pane after asynchronous loading and on resize, preserving original controls and callbacks.
- Seven isolated numeric cases and all 22 synthetic Options tabs passed; a compositor click scrolled the pane, and the original Cancel callback closed it. No settings were submitted. Broader resize/input and historical large-model gates remain separate.
- Add a public offline numeric regression tool. Incremental runtime payload changes are limited to x64/x86 JScript DLLs; RPM upgrades still require separate per-user runtime/recipe maintenance. See [Options evidence](docs/options-dialog.md).

### RPM release 8 / runtime 0.1.1 — development candidate, 2026-10-16

- Keep owned borderless modals as transient Wayland toplevels while dropdowns are active. Anchor tool popups whose WinForms owner is invisible to the visible window beneath them.
- Track the actual client-surface parent and restrict subsurface stacking to valid siblings. The runtime is an incremental rebuild of the Unix Wayland driver; other payload files retain the verified 0.1.0 contents.
- Serialize the 13 original Edit Permissions view-model fields without traversing native host/button objects. Preserve original privacy/encryption callbacks and PE/resource sizes; no credential values are supplied by the patch.
- The complete synthetic CSV compositor-input cycle passed: privacy selection, OK closes, reopen preserves the choice, Cancel closes and retains the previously saved choice. A separate serializer check preserves Database and encryption=true while native host/button getters throw if accessed.
- The earlier v1 and v3 candidates were rejected. The None/no-credential path opens a separate nested Delete Permissions dialog that stayed at 2×2/loading during cleanup; that case remains unresolved. Real-server refresh/TLS and broader workload certification remain separate.

### RPM release 7 — development preview, 2026-10-15

- Disable Desktop update notices with Microsoft's documented installer/registry option during setup/repair. A Fedora notification for validated releases remains future work; runtime update is separate from Desktop update.
- Add optional `connector status/install mysql`: original Oracle Connector/NET, full pinned .NET dependency set, verified downloads, staging/rollback, manifest and external-provider detection. No report, credential or TLS changes.
- Fix blank Data source settings by recalculating an existing list whose cached page size is zero after its modal appears. Fresh CSV and MySQL fixtures rendered the discovered source.
- Real-report sources were confirmed by the user. Initial cursor/click trouble recovered after an estimated 10–60 seconds; its cause and input latency remain unresolved.
- Native provider/dependency load and a Power BI UI refresh against disposable MariaDB 10.11.19 passed: 3 rows, total 300 and committed/error-free partitions. Explicitly unencrypted loopback test; production TLS is not certified.
- Add public provider validation tools and regression coverage for corrupt inputs, unsafe paths, external registrations, busy sessions, tampering and failed activation cleanup.

### RPM release 6 — development preview, 2026-10-15

- Enable Desktop's existing system authentication browser during offline setup/repair using its own settings API. Avoid the failing Windows broker path without changing MSAL or account policies.
- A real account completed Microsoft authentication in Vivaldi on the Fedora host. The account remained connected after a normal production restart; cloud operations need separate validation.
- Add a synthetic native settings test covering fresh-process persistence, repeated configuration, read-only checks and preservation of unrelated settings/package parts.

### RPM release 5 — development preview, 2026-10-15

- Fix Continue in the legacy email prompt by serializing its existing email/retry/warning fields without traversing native UI objects.
- Preserve native email validation, cancellation and authentication. The guarded resource patch preserves PE/resource sizes and IL and is applied before WinRT/save-dialog patching.
- Doctor checks the email serializer resource. Completing the email prompt is tracked separately from successful Microsoft authentication.

### RPM release 4 — development preview, 2026-10-14

- Register Wine's built-in MSHTML in both architectures after installers and during repair; doctor checks the protocol and MIME handlers without starting Wine.
- Fix the legacy credential dialog's unsupported text-overflow setter and stale sidebar height using guarded, size-preserving embedded JavaScript patches.
- Preserve the existing credential controls and callbacks. No credentials, authentication methods or source permissions are selected automatically.
- Default resource settings remain unrestricted; this change does not alter the engine cancellation implementation.

### RPM release 3 — development preview, 2026-10-14

- Native close confirmation preserves Desktop's localized Save/Don't save/Cancel labels and existing save/close handler.
- Cancel is the default response; helper errors also return Cancel.
- Own helper compiles and signs locally during setup/repair, with the existing pinned Wine/DXVK runtime.
- Native component tests and actual Desktop Save/Don't save/Cancel passed with a disposable PBIP, including save/cache/reopen and a normal-mode startup check.
- RPM builds now run the Python unit suite; native GUI validation remains separate.
- Native Cancel completed during query evaluation (~0.8 s) and data loading (19.879 s), preserving committed data. The original reported freeze was not reproduced; cancellation logic is unchanged.

### RPM release 2 — 2026-10-14

- Default RAM/swap ceilings and fixed V8 heap removed; standard browser settings replace forced economy defaults.
- CLI exposes optional RAM/swap/CPU, heap, renderer and browser-mode settings; normal/large remain explicit economy presets.
- Exact legacy bundled limits migrate to unlimited; custom settings and new explicit choices are preserved.
- Earlier native refresh/Save/soak results describe bounded profiles. Release 2 policy checks are recorded separately.

### RPM release 1 — 2026-10-13

- Fedora-only CLI, RPM packaging and PBIX/PBIP/PBIR desktop integration.
- XDG state, private session broker, input verification and transactional repair/update/rollback.
- Production composition helper separated from UI diagnostics.
- Pinned Wine/DXVK sources and source-level secur32 correction.
- Unit tests, synthetic sales fixture, licensing and release documentation.
- Wine/DXVK runtime and RPM built; synthetic 158-table UI refresh and PBIP save/reopen checked in a disposable prepared prefix.
- Fixed WebView2 recipe, native stub signing and local feature-switch setup; browser-specific Wine version override fixes the clean-prefix GPU crash.
- Clean-prefix PBIX rendering and independent DAX total 300 verified; committed wineboot interruption/resume verified.
- CSV import harness and relational 158-table fixture added; the general source chooser blocks at the OneLake sign-in popup.
- Direct Text/CSV import, numeric visual creation, Unicode save/reopen and production desktop PBIX/PBIP/PBIR dispatch verified in the clean prefix.
- Native repair/update/rollback and preserving uninstall verified; uninstall clears automatic association tokens and masks an installed system RPM entry for the user.
- Graceful broker shutdown, Unicode native probes, memory-profile CLI and periodic UI/heap/GPU monitoring added.
- Wine's automatic desktop exports disabled; legacy launchers pointing into managed snapshots cleaned without removing foreign-prefix handlers.

This is a validated development preview for the documented synthetic workloads. The two-hour session passed with 24 visual checks and no OOM/GPU replacement. Native refresh/Save/reopen, final normal-profile desktop dispatch and legacy-handler migration were checked. One discrepant idle native capture is retained, with cause not established. The general OneLake source chooser and cloud operations still require separate validation; Microsoft browser sign-in passed on the Fedora host.
