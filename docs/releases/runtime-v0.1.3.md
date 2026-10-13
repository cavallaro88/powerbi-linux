**Source recipe only — development candidate. No runtime binary is published in this release.**

Original version date: **2026-10-16**. This GitHub entry was migrated from the existing
project changelog; it does not claim an original GitHub publication on that date.

## Changelog

- Resolve foreign shared standard user32 cursor resources through bounded internal Wine IPC and load them locally. This lets the existing Wayland path update a stale resize cursor when an embedded browser selects an arrow.
- Preserve unsupported/custom foreign behavior and local cursor handling. Incremental payload replaces only Unix win32u from runtime 0.1.2; RPM 9 remains compatible.
- Twelve x64 component checks and a compositor-motion resize/arrow reproducer passed. After activation, live Power BI sidebar/canvas hover alternated horizontal resize/arrow resources twice with verified pointer targets (2026-10-18). Doctor passed 15 checks; 452 monitored project files were unchanged. Original data-grid, custom cursor and broader workload coverage remain separate. Add public component and visible-fixture sources; see [cursor evidence](https://github.com/cavallaro88/powerbi-linux/blob/main/docs/cursor.md).

## Source and validation scope

The attached recipe archive and GitHub source downloads contain project sources,
pins, patch series and build instructions. Wine/DXVK source dependencies are
obtained by the pinned recipe. No compiled runtime is attached: the full build,
matching corresponding-source publication and compatibility release gates remain
required before binary distribution. Scoped historical component evidence is
preserved in the changelog; it is not full release certification.

Historical CI metadata was omitted when reconstructing these recipe snapshots.
No runtime source/build input was changed by that omission. Use `main` for the
current CI and candidate acceptance plan. The three reviewed Neutron candidates
remain inactive.

## Provenance and limits

Source tag: [`runtime-v0.1.3`](https://github.com/cavallaro88/powerbi-linux/tree/runtime-v0.1.3). See `SOURCE-PROVENANCE.json` for the
original artifact identity and the reconstructed source commit. Historical RPM
snapshots were recovered from their original source RPMs; private investigation
Git history was not imported. RPM 12 uses the reviewed published product commit.

The source recipe is provided for inspection and controlled testing. No compiled
runtime is attached. Checksums establish integrity, not publisher identity.
This is an independent community project, without official Microsoft support.
Preserve private backups of reports and model caches. License notices and
component-specific terms are in the source tree.
