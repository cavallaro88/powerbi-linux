# Changelog

## 0.1.0 — development

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

This is a validated development preview for the documented synthetic workloads. The two-hour session passed with 24 visual checks and no OOM/GPU replacement. Native refresh/Save/reopen, final normal-profile desktop dispatch and legacy-handler migration were checked. One discrepant idle native capture is retained, with cause not established. The general OneLake source chooser and Microsoft sign-in remain limited.
