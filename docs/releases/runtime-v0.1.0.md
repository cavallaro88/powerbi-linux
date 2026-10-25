**Source recipe only — development candidate. No runtime binary is published in this release.**
> **Recipe withdrawn.** The published recipe assets were removed from GitHub Releases; the source snapshot remains at the [tag](https://github.com/cavallaro88/powerbi-linux/tree/runtime-v0.1.0) and the artifact digests remain in the [release catalogue](../../packaging/releases.json).


Original version date: **2026-10-13**. This GitHub entry was migrated from the existing
project changelog; it does not claim an original GitHub publication on that date.

## Changelog

- Initial Wine 11.18 / DXVK 3.1 recipe and reviewed source patches for native Wayland, composition delivery and local Desktop compatibility.
- Corresponds to the original runtime source export accompanying the first Fedora development preview.
- This entry archives the source recipe; it does not newly certify the original binary or every enterprise workload.

## Source and validation scope

The published recipe archive and GitHub source downloads contain project sources,
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

Source tag: [`runtime-v0.1.0`](https://github.com/cavallaro88/powerbi-linux/tree/runtime-v0.1.0). See `SOURCE-PROVENANCE.json` for the
original artifact identity and the reconstructed source commit. Historical RPM
snapshots were recovered from their original source RPMs; private investigation
Git history was not imported. RPM 12 uses the reviewed published product commit.

The source recipe is provided for inspection and controlled testing. No compiled
runtime is attached. Checksums establish integrity, not publisher identity.
This is an independent community project, without official Microsoft support.
Preserve private backups of reports and model caches. License notices and
component-specific terms are in the source tree.
