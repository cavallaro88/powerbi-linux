# Guided setup release contract

The CLI resolves omitted setup inputs using `packaging/setup.json`, shipped inside
the RPM. It never follows a `latest` URL or trusts a checksum downloaded alongside
an arbitrary runtime. Explicit local inputs retain the original provisioning path.

## Metadata

The schema is `1`. `status` is `pending` until a matching binary release is ready;
`reason` explains missing release requirements. `powerbi` contains `version`,
`sha256`, `url` and the human-facing `download_page`. Its version and checksum must
match `runtime/sources.lock.json`. `runtime` is null until ready, then contains
`version`, `url`, `sha256`, `source_url` and `evidence_url` for the published binary,
complete corresponding source and sanitized exact-artifact certification evidence.
The source/evidence links must identify release assets, not a source-only recipe.

With an explicit local `--runtime` and matching `--runtime-sha256`, setup can
download the pinned official Power BI installer after license acceptance even
while the public runtime manifest is pending. This supports fully local,
offline-prepared installs. It does not select an automatic project runtime, mark the manifest
ready or certify the provided archive. Incorrect local runtime checksums are
rejected before any Microsoft download.

All downloads use fixed HTTPS URLs and SHA-256 checks. Power BI's installer must
come from `download.microsoft.com`. WebView2, .NET, Gecko and fonts continue using
the existing pinned prerequisite recipes. The 0.1.0-19 beta manifest points at
Runtime 0.1.6-beta.1 with fixed binary, source and evidence URLs plus SHA-256 values.
Do not substitute a placeholder checksum or an incremental investigation build. RPM 18
keeps the published runtime 0.1.5 pin.

## Preparing a release

1. Validate the exact Power BI installer and adapt the guarded local patches. Keep
   the previous supported recipe usable for existing profiles. Do not just replace
   old assembly hashes with new ones. The [2.159 assessment](../reference/powerbi-2.159.md)
   describes the current blocker.
2. Complete a full runtime build using the reviewed sources and build receipt.
   Package under a new immutable runtime version. Retain sources, notices and
   toolchain provenance; see [build](build.md).
3. Run every existing runtime release gate against that archive and a dedicated QA
   installation. Add the actual Power BI/WebView2 versions to the evidence. Use
   `python3 tools/release-check.py RUNTIME_ARCHIVE EVIDENCE_JSON`. Quick CI checks
   are not substitute evidence.
4. Prepare the runtime binary, checksums, full corresponding sources, evidence and
   release notes as release assets. Verify the published downloads and their
   hashes. Until the assets are available, keep `status: pending`.
5. Set the verified fixed URLs and checksums, then set `status: ready`. Build the
   matching RPM and source RPM. Validate the RPM from an empty Fedora 44 Wayland
   user installation using only `pbi-linux setup`; also test explicit local inputs,
   interrupted setup, in-place maintenance failure and successful retry. Publish the paired beta and update the
   recommended release links only after those checks pass.

Runtime 0.1.5 was published with the two-hour soak still pending to enable
automatic setup; that gap is tracked in its release notes and in
[known issues](../user/known-issues.md).

An installed RPM pins one download selection. Future Desktop versions require a
new reviewed recipe and package; `update` activates the published runtime or an
explicitly supplied archive.
Installed metadata records `powerbi_version` and `recipe_id`; older installations
are identified from their runtime's Power BI source record. The CLI retains exact
2.158 and 2.159 recipes. Local installers select by their complete SHA-256; repair
and runtime changes preserve the installed application version. Unregistered or
inconsistent recipe identities are rejected before modifying the maintenance profile.

Native QA installations isolate XDG data/config/cache/state and derive distinct
session sockets, locks and systemd service names from the data directory. Keep
the real desktop `XDG_RUNTIME_DIR` so Wayland and systemd's private IPC socket
remain reachable. The normal default installation retains
`pbi-linux-session.service`; test cleanup targets only its own service. A
copy-on-write upgrade test does not count as the clean-install release gate.

## Terminal behavior

Without local inputs, `setup` uses the validated manifest. It shows components and
versions, then asks for license acceptance on a terminal. Refusal, EOF or an
unavailable release exits before provisioning. Non-interactive use requires
`--accept-license`. Explicit `--runtime` requires `--runtime-sha256`; supplied
installers and prerequisites must match the pinned checksums. Existing profiles
are directed to open/repair/update before any downloads.

Downloads show progress, verify cached content, reject insecure redirects and
remove partial files after failure. Repeating setup retries incomplete downloads
and resumes the existing completed provisioning stages; it does not resume
partially downloaded HTTP byte ranges. Prerequisite file options alone are not a
fully offline mode: other pinned downloads still need a populated cache or network.
