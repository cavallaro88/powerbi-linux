# Development releases

Local candidates are prepared in the source tree and have not been published as
new GitHub releases:

- [RPM 17 — local GNOME theme integration](releases/v0.1.0-17.md)
- [RPM 16 / DEB 0.1.0-16pop1 — local tooltip correction](releases/v0.1.0-16.md)
- [RPM 15 / DEB 15pop1 — local Options interaction fixes](releases/v0.1.0-15.md)
- [RPM 14 — local guided setup and documentation candidate](releases/v0.1.0-14.md)
- [Runtime 0.1.5 — complete local build candidate](releases/runtime-v0.1.5.md)

The current RPM preview is [0.1.0-13](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-13).
All entries are **prereleases**, with dated, version-specific changelogs.
Access follows the GitHub repository visibility. No stable release is certified.

[RPM 14](releases/v0.1.0-14.md) adds the guided setup and documentation work, not a
published replacement. Automatic installation remains gated on a validated,
published runtime binary and matching Power BI recipe.
[Runtime 0.1.5](releases/runtime-v0.1.5.md) has a complete local build; its exact-archive
acceptance and publication are tracked separately.

[RPM 15 / DEB 15pop1](releases/v0.1.0-15.md) are local Options interaction fixes.
Existing installations apply them with `pbi-linux repair`; no new runtime or CI
run is required. [RPM 16 / DEB 0.1.0-16pop1](releases/v0.1.0-16.md) are local
tooltip fixes applied the same way, with Desktop closed. [RPM 17](releases/v0.1.0-17.md)
is a local GNOME theme integration: update the RPM and restart Desktop, without
a repair.

## CLI and Fedora RPM

Each revision has the original binary RPM, its source RPM, `SHA256SUMS` and
`SOURCE-PROVENANCE.json`. No Microsoft installers, populated prefixes or reports
are attached. Old revisions are retained for reproduction; use RPM 13 for current testing.

| Revision | Version notes | GitHub release |
|---|---|---|
| 0.1.0-13 | [Changelog](releases/v0.1.0-13.md) | [Downloads](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-13) |
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
[the build guide](development/build.md); full release validation and corresponding-source
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
RPM 13 was built from its tagged product commit; its source and binary payloads
were compared against that commit and matching source RPM before publication.

The published history is a clean reconstruction: one commit per release snapshot,
plus the current development state. Each release tag reproduces its released
source byte-for-byte. Commit identifiers quoted inside released snapshots and in
the published `SOURCE-PROVENANCE.json` assets belong to the earlier development
history and cannot be resolved here; the [release catalogue](../packaging/releases.json)
records this repository's tag commits.

The machine-readable [release catalogue](../packaging/releases.json) records
tag/source commits and asset SHA-256 values for the published releases, RPM 1–13
and runtime 0.1.0–0.1.4. Later local candidates are not published and are not in
the catalogue. The original RPM payloads were
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
corresponding source and all exact-artifact [release gates](development/build.md#release-validation).

Do not upload report data, caches, populated profiles or private evidence.
Do not promote an incremental component test to full runtime certification.
