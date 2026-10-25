# Changelog

## 0.1.0 — development

### Unreleased — product repository and upstream review

- Test the original AWS Redshift 1.6.3.1008 Windows x64 MSI in the managed prefix:
  silent installation and automatic driver/default-DSN registration passed without
  manual driver registration. Add a generic offline Windows driver/DSN loading
  probe. Native generic ODBC authentication, metadata Import, independent one-row
  DAX and Save/normal reopen passed. A subsequent full interactive
  wizard completed in a fresh Wine-only prefix installed the same 19 vendor files and passed
  driver/DSN/handle checks; managed maintenance cancellation preserved the real
  installation. The temporary QA prefix was removed, reclaiming 565.6 MiB.
  The separate credential modal required a session-only workaround; no permanent
  patch is planned for this test. DSN connection and shared-dependency repair/uninstall remain pending. No generic
  installer command or new RPM is released; see [vendor installer evidence](docs/reference/vendor-installers.md).
- Document source/driver/authentication/operation compatibility and the shared
  inventory/ODBC roadmap. Isolate the app-private ODBC manager ENV failure and
  record a local experimental forwarding correction. Real Redshift password login,
  schema metadata, one derived Import row, independent DAX and Save/normal reopen
  passed. Add reproducible forwarding sources and a no-network Engine regression
  probe. Another real-dataset test and refresh cancellation
  subsequently passed; data, server-side cancellation and post-cancel state were not
  independently audited. Document the proposed generic vendor-MSI installation
  flow; it is not implemented. Managed installation, typed data checks, TLS policy and other
  authentication routes remain pending; RPM 13 is unchanged.
- Publish version-specific GitHub development prereleases with original RPM/source assets, checksums and provenance. Reconstruct historical tags from sanitized original sources; keep runtime releases source-only until binary distribution gates pass. Index all versions in [the release guide](docs/releases.md).

- Promote the standalone product to the repository root, with normal GitHub discovery, a shorter README, documentation index and explicit roadmap. Keep working investigation material outside the product history.
- Guard runtime packaging against unreviewed patch files, failed/stale builds, changed sources/payload and accidental artifact overwrite. Record the successful build and exact builder/input identity; retain unchanged runtime 0.1.3 artifacts.
- Review the 87 neutron-wine commits through `8ecb7fd`, with decisions for all 59 changed patch files and separate external-library scope. Add a repeatable consistency audit to quick QA. No new runtime patch is enabled.
- Stage mouse capture tracking, rendering-mode glyph caching and signed DPI arithmetic separately. The actual Wine DPI helper fails six of fourteen arithmetic controls before the port and passes all after; server/compositor validation remains pending.

### RPM release 18 — automatic setup and update, 2026-10-25

- Resolve the published runtime 0.1.5, its complete corresponding source and
  exact-archive evidence for `pbi-linux setup` and `pbi-linux update`; every
  download is verified against the pinned SHA-256.
- Keep explicit `--runtime`/`--runtime-sha256` overrides and reject partial or
  non-release inputs.
- Publish runtime 0.1.5 with its binary archive, corresponding source and
  evidence; the exact-archive two-hour soak remains pending.
- Remove the experimental Pop!_OS/DEB packaging path; the Fedora RPM is the only
  supported package format and other distributions are outside the support target.

### RPM release 17 — local GNOME theme integration, 2026-10-23

- Follow GNOME's color preference at startup and every two seconds while Desktop is open.
- Preserve explicit Light/Dark selections; update only the prefix's Windows preference.
- Reuse the existing runtime and profile without repair; restart Desktop after updating the RPM.
- Cover the bridge with unit tests and 13 native assertions using synthetic settings.

### RPM release 16 — local tooltip correction, 2026-10-23

- Show browser HTML/SVG title tooltips inside WebView instead of detached native windows.
- Preserve original rich data tooltip handlers, dynamic title updates and keyboard dismissal.
- Add guarded setup/repair recipe and tooltip integrity check; no runtime replacement.

### RPM release 15 — Options interaction, 2026-10-21

- Add guarded native resizing for the Options dialog in both supported Desktop recipes.
- Fit sidebar/content to the viewport and preserve the footer and sidebar scroll access.
- Disable selection of UI labels while preserving editable fields and original callbacks.
- Apply the correction through normal per-user repair, using the existing runtime.

### RPM release 14 — guided setup and documentation candidate, 2026-10-20

- Explain the product, own features and upstream credits; reuse the project icon
  and add CI, license, platform and beta badges.
- Separate user guides, development and technical reference. Preserve technical
  investigations, remove the duplicate Portuguese guide and add a concise
  [known-issues guide](docs/user/known-issues.md).
- Add interactive terms acceptance and pinned automatic-download selection while
  retaining local setup arguments. Keep automatic setup gated until the runtime
  binary, corresponding source and exact-artifact evidence are published.
- Show download progress and actionable connection/version errors; record the
  installed Power BI version and recipe and guard maintenance compatibility.
- Port the current 2.159.883.0 EXE using exact original hashes, unchanged embedded
  resource contents and guarded native methods. Preserve its new DPI-layout
  handling and keep the 2.158 recipe available for existing installations. Local
  installers select their exact registered recipe; runtime updates preserve the
  installed Desktop version. Native validation remains separate from offline
  patch checks. See the [assessment](docs/reference/powerbi-2.159.md).
- Give isolated XDG installations separate session services, preserving the
  standard user's service name. Require matching Power BI/WebView2 versions in
  runtime release evidence, in addition to the existing exact-archive gates.

### Runtime 0.1.5 — complete local build candidate, 2026-10-20

- Build the full reviewed Wine/DXVK recipe with a successful-build receipt,
  toolchain provenance and Power BI 2.159 pin; avoid duplicate unstripped staging.
- Pass clean setup with interruption/resume, native components, 158-table refresh,
  CSV/visual/Save, normal document reopening, runtime migration and recovery.
- Keep the exact-archive two-hour gate pending. Runtime-binary
  publication remains pending; automatic setup remains disabled.
  See [local runtime notes](docs/releases/runtime-v0.1.5.md).

### RPM release 13 — text picker development candidate, 2026-10-18

- Render only Quill font/size selectors in WebView2's in-page top layer using `appearance: base-select`. The detached Chromium popup reproduced as an empty white window despite populated options.
- Keep the original select controls, options and change handlers. Let the browser dismiss an open picker with Escape before Desktop consumes that key; unrelated shortcuts retain their handlers.
- Apply only a hash-guarded local report-view HTML change during setup/repair, with original backup and a `text-pickers` doctor check. No Wine rebuild, diagnostic interpreter or report-content patch is introduced.
- Fresh Desktop diagnostics passed eight keyboard assertions, compositor pointer selection and actual formatted-text verification. Doctor passed 18 checks. Other selectors, display scales and a full compatibility matrix remain separate. See [text picker evidence](docs/reference/text-pickers.md).

### RPM release 12 — window frame development candidate, 2026-10-18

- Extend the normal resizable/unowned Desktop client to its complete frame. Replace the visible 4-pixel side/bottom gutters with transparent native resize input zones, preserving styles and fixed/owned/native-maximized calculations.
- Guard the two patched methods by exact contents and sign the helper locally. Setup/repair records its checksum; doctor checks the frame patch. Modified Microsoft binaries stay local.
- Native and actual-base-class fixtures passed frame, hit-target and owned/fixed controls. A managed compositor drag passed; normal Desktop measured zero insets, and the user confirmed the visual fix with working mouse/shortcuts. Actual compositor maximize-state divergence also reproduces on baseline and remains separate coverage, as do other display scales and broader modal workloads. See [evidence](docs/reference/window-frame.md).
- Apply the candidate locally without cloning the profile or changing the runtime/resource policy; retain the old DLL/manifest for rollback.

### Runtime 0.1.4 — PaperWM development candidate, 2026-10-18

- Accept normal Wayland compositor size hints for resizable windows after initial configure. PaperWM resizes without maximized/resizing/tiled flags were previously discarded.
- Native baseline/candidate tests confirm actual client resizing and preserve the fixed-size control. Empty Desktop on the normal launcher follows column height, increase-width actions and compositor Super+minus. PaperWM resizing was subsequently confirmed working after activation; automated Super+plus injection remains separate coverage. See [scope and pending checks](docs/reference/paperwm.md).
- Activate a private incremental single-driver candidate locally, retaining runtime 0.1.3 and the existing profile/settings. Add the reviewed patch to the 0.1.4 source recipe; full rebuild and broader release gates remain pending.
- Record the separate acceptance plan for the three still-inactive Neutron candidates in [runtime testing](docs/development/runtime-testing.md).
- Diagnose the visible white frame as 4-pixel non-client left/right/bottom insets, with content filling the client area. Record the remaining cosmetic compatibility work without changing window styles or deploying an untested frame correction.

### RPM release 11 — cached models and original app icon, 2026-10-18

- Compact valid linguistic JSON in memory before the existing model-copy/update path. The original ABF restores successfully; reapplying extensive multiline linguistic metadata caused a separate Analysis Services failure. Preserve all JSON values, escapes and number tokens; apply genuine source metadata changes normally. No report file or cache is automatically deleted or rewritten by the correction.
- A private 158-table copy passed Desktop Save, graceful close and fresh normal reopen without refresh. All table row counts/states matched, including one existing query-error state. A new source-defined measure returned 73 before and after reopening. This is scoped evidence, not certification for every model or data value.
- Extract the original PNG icon from the installed Power BI executable during user integration and refresh it on launch after upgrades. Retain the packaged fallback before provisioning; no Microsoft artwork is redistributed.
- Setup/repair compiles and signs the guarded cache helper locally; runtime 0.1.3 and unlimited resource defaults remain unchanged. See [cache validation](docs/reference/model-cache.md).

### RPM release 10 — post-publish Store rating, 2026-10-18

- Disable only the Windows Store rating entrypoint on Fedora, returning a completed Task. Its WinRT awaiter caused a missing `System.Runtime.WindowsRuntime` error after a successful publication, even before its UWP gate ran.
- A real publication was confirmed by the user in the homologation Service workspace. Offline baseline reproduced the exception; the candidate and public regression completed with null dependencies and no publication request. One method among 29,697 changed, with embedded resources preserved. A new cloud publication using the correction remains separate.
- Setup/repair compiles the guarded patcher from project sources; runtime 0.1.3 and resource defaults are unchanged. See [publishing](docs/user/publishing.md).

### Runtime 0.1.3 — cursor development candidate, 2026-10-16

- Resolve foreign shared standard user32 cursor resources through bounded internal Wine IPC and load them locally. This lets the existing Wayland path update a stale resize cursor when an embedded browser selects an arrow.
- Preserve unsupported/custom foreign behavior and local cursor handling. Incremental payload replaces only Unix win32u from runtime 0.1.2; RPM 9 remains compatible.
- Twelve x64 component checks and a compositor-motion resize/arrow reproducer passed. After activation, live Power BI sidebar/canvas hover alternated horizontal resize/arrow resources twice with verified pointer targets (2026-10-18). Doctor passed 15 checks; 452 monitored project files were unchanged. Original data-grid, custom cursor and broader workload coverage remain separate. Add public component and visible-fixture sources; see [cursor evidence](docs/reference/cursor.md).

### RPM release 9 / runtime 0.1.2 — development candidate, 2026-10-16

- Convert signed Automation Int64 values to JavaScript numbers in Wine's HTML ES5+ engine. This prevents the Options cache-description binding from interrupting initialization; legacy standalone variant handling stays behind its original path.
- Bound the existing Options scroll pane after asynchronous loading and on resize, preserving original controls and callbacks.
- Seven isolated numeric cases and all 22 synthetic Options tabs passed; a compositor click scrolled the pane, and the original Cancel callback closed it. No settings were submitted. Broader resize/input and historical large-model gates remain separate.
- Add a public offline numeric regression tool. Incremental runtime payload changes are limited to x64/x86 JScript DLLs; RPM upgrades still require separate per-user runtime/recipe maintenance. See [Options evidence](docs/reference/options-dialog.md).

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
