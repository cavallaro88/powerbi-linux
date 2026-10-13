# Development releases

The current RPM preview is [0.1.0-12](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-12).
All entries are **prereleases**, with dated, version-specific changelogs.
Access follows the GitHub repository visibility. No stable release is certified.

## CLI and Fedora RPM

Each revision has the original binary RPM, its source RPM, `SHA256SUMS` and
`SOURCE-PROVENANCE.json`. No Microsoft installers, populated prefixes or reports
are attached. Old revisions are retained for reproduction; use RPM 12 for current testing.

| Revision | Version notes | GitHub release |
|---|---|---|
| 0.1.0-12 | [Changelog](releases/v0.1.0-12.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-12) |
| 0.1.0-11 | [Changelog](releases/v0.1.0-11.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-11) |
| 0.1.0-10 | [Changelog](releases/v0.1.0-10.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-10) |
| 0.1.0-9 | [Changelog](releases/v0.1.0-9.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-9) |
| 0.1.0-8 | [Changelog](releases/v0.1.0-8.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-8) |
| 0.1.0-7 | [Changelog](releases/v0.1.0-7.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-7) |
| 0.1.0-6 | [Changelog](releases/v0.1.0-6.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-6) |
| 0.1.0-5 | [Changelog](releases/v0.1.0-5.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-5) |
| 0.1.0-4 | [Changelog](releases/v0.1.0-4.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-4) |
| 0.1.0-3 | [Changelog](releases/v0.1.0-3.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-3) |
| 0.1.0-2 | [Changelog](releases/v0.1.0-2.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-2) |
| 0.1.0-1 | [Changelog](releases/v0.1.0-1.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-1) |

## Wine/DXVK runtime

Runtime versions have separate tags and changelogs. These entries publish
**source recipes only**, not compiled runtimes. The recipe tarballs cannot be
passed to `pbi-linux setup --runtime`. Build the corresponding runtime following
[the build guide](build.md); full release validation and corresponding-source
publication remain required before distributing runtime binaries.

| Version | Version notes | Source recipe |
|---|---|---|
| 0.1.4 | [Changelog](releases/runtime-v0.1.4.md) | [Source](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.4) |
| 0.1.3 | [Changelog](releases/runtime-v0.1.3.md) | [Source](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.3) |
| 0.1.2 | [Changelog](releases/runtime-v0.1.2.md) | [Source](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.2) |
| 0.1.1 | [Changelog](releases/runtime-v0.1.1.md) | [Source](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.1) |
| 0.1.0 | [Changelog](releases/runtime-v0.1.0.md) | [Source](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.0) |

## Source history and verification

Historical RPM 1–11 tag trees were reconstructed from their original source
packages; historical runtime recipes came from their original source exports
or the reviewed 0.1.4 product commit. Original dates are documented in the notes,
rather than fabricated as original GitHub publication dates. Private investigation
branches were not imported. Historical CI metadata is omitted from runtime snapshots;
the active checks live on `main`. RPM 12 uses the published reviewed product commit.

The machine-readable [release catalogue](../packaging/releases.json) records
tag/source commits and asset SHA-256 values. The original RPM payloads were
compared to source-package content before upload. Checksums do not provide a
publisher signature; RPM signing remains planned. Historic validation describes
its recorded scope and does not certify every model, connector or display setup.

## Subsequent releases

Update the RPM revision and changelog, build and check the package, retain the
matching source RPM and reviewed source commit, and prepare version-specific
notes. Create a new immutable tag rather than moving an existing release tag.
Attach only reviewed assets and their checksums, stage a draft, verify the
uploaded asset digests, then publish with the appropriate development/stable
classification. A runtime binary additionally requires the complete matching
corresponding source and all exact-artifact [release gates](build.md#release-validation).

Do not upload report data, caches, populated profiles or private evidence.
Do not promote an incremental component test to full runtime certification.
