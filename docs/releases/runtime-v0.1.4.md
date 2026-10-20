**Source recipe only — development candidate. No runtime binary is published in this release.**

Original version date: **2026-10-18**. This GitHub entry was migrated from the existing
project changelog; it does not claim an original GitHub publication on that date.

## Changelog

- Accept normal Wayland compositor size hints for resizable windows after initial configure. PaperWM resizes without maximized/resizing/tiled flags were previously discarded.
- Native baseline/candidate tests confirm actual client resizing and preserve the fixed-size control. Empty Desktop on the normal launcher follows column height, increase-width actions and compositor Super+minus. The user subsequently confirmed PaperWM resizing works perfectly; automated Super+plus injection remains separate coverage. See [scope and pending checks](https://github.com/cavallaro88/powerbi-linux/blob/main/docs/reference/paperwm.md).
- Activate a private incremental single-driver candidate locally, retaining runtime 0.1.3 and the existing profile/settings. Add the reviewed patch to the 0.1.4 source recipe; full rebuild and broader release gates remain pending.
- Record the separate acceptance plan for the three still-inactive Neutron candidates in [runtime testing](https://github.com/cavallaro88/powerbi-linux/blob/main/docs/development/runtime-testing.md).
- Diagnose the visible white frame as 4-pixel non-client left/right/bottom insets, with content filling the client area. Record the remaining cosmetic compatibility work without changing window styles or deploying an untested frame correction.

The subsequent RPM 12 frame correction handles the visible side/bottom gutters independently.

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

Source tag: [`runtime-v0.1.4`](https://github.com/cavallaro88/powerbi-linux/tree/runtime-v0.1.4). See `SOURCE-PROVENANCE.json` for the
original artifact identity and the reconstructed source commit. Historical RPM
snapshots were recovered from their original source RPMs; private investigation
Git history was not imported. RPM 12 uses the reviewed published product commit.

The source recipe is provided for inspection and controlled testing. No compiled
runtime is attached. Checksums establish integrity, not publisher identity.
This is an independent community project, without official Microsoft support.
Preserve private backups of reports and model caches. License notices and
component-specific terms are in the source tree.
