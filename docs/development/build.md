# Build from a clean source tree

The current recipe defaults to runtime **0.1.5** (`--runtime-version 0.1.5`), with
the Power BI 2.159.883.0 installer pin and the existing reviewed Wine/DXVK patches.
A complete local build and successful-build receipt were produced on October 20.
The 2.159 port passed offline and preliminary native checks; exact-archive release
acceptance is tracked separately. See [the current assessment](../reference/powerbi-2.159.md).

The historical **0.1.4** source recipe includes the modal/popup, signed-Int64 HTML, cursor and normal Wayland resize corrections.
The latest full 0.1.4 recipe has not yet been built; the private PaperWM candidate
is a single-driver incremental test. See [scope and evidence](../reference/paperwm.md).
Preserve older archives/checksums. The incremental 0.1.2 artifact replaces only
two JScript DLLs; its exact provenance and narrower validation scope are in
[Options](../reference/options-dialog.md). A full rebuild is not claimed byte-identical to an
incremental DLL replacement.

Runtime 0.1.3 additionally resolves foreign shared system cursor resources; its
incremental artifact replaces only Unix win32u. See [cursor scope](../reference/cursor.md).
The 0.1.2 JScript and 0.1.1 Wayland corrections remain included.

Install Docker or Podman and ensure your account can invoke the selected engine. No existing Wine/Bottles installation or prefix is needed. Source preparation uses Python 3.12+, Git and `patch`; compilation tools are installed inside the builder container.

```bash
python3 runtime/build.py
# Use four compiler jobs explicitly:
python3 runtime/build.py --jobs 4
# Or:
python3 runtime/build.py --engine podman
```

The script downloads the Wine archive and dnlib NuGet package using `sources.lock.json`, verifies SHA-256, checks out the pinned DXVK commit and submodules, and applies the versioned patch series with zero fuzz. It builds a complete Wine runtime including WoW64, DXVK and production C# helpers. No proprietary binaries are build inputs.

Outputs are `dist/runtime/`, the runtime archive and its checksum. `runtime.json` records provenance and hashes of every runtime file. Sources live in ignored `sources/`; build artifacts and downloads live in ignored `build/`, `dist/` and `.cache/`.

For offline source preparation:

```bash
python3 runtime/build.py --prepare-only \
  --wine-source /path/to/wine-11.18.tar.xz \
  --dxvk-source /path/to/dxvk-checkout \
  --dnlib-source /path/to/dnlib.4.5.0.nupkg
```

An offline DXVK checkout must include the pinned submodules. The preparation script clones these into its own workspace and does not patch the supplied source directories. To intentionally reprepare changed patches, remove only the generated `sources/` and corresponding `build/` directories before rebuilding.

The container base is pinned by digest. Package repository versions are recorded by the builder's package inventory; this recipe does not claim byte-for-byte reproducibility across repository updates. Release builders must retain the image digest and inventory alongside artifacts. C# stub signing keys are generated locally during provisioning, not published as release secrets.

## RPM

```bash
python3 tools/build-rpm.py
# Also compile/sign helpers against dnlib in prepared sources/
# (runs tools/validate-helpers.sh):
python3 tools/build-rpm.py --check-helpers
# With a native rpmbuild installation:
python3 tools/build-rpm.py --local
```

RPMs and source RPMs are under `build/rpm/`. The package contains CLI/source resources and desktop integration; it does not contain a prefix, Microsoft installers or the Wine runtime archive. No package script runs Wine, downloads dependencies or accesses user credentials.

Candidate release 9 includes tests/tools in the source RPM and runs the Python
unit suite during `%check`. Native Fedora builds declare the Python build
dependency; the pinned Ubuntu cross-builder obtains it through apt and verifies
the interpreter version directly. Native dialog GUI tests run separately with
`python3 tools/test-save-dialog.py` in an installed user's graphical session.

The native browser-settings check is `python3 tools/test-signin-settings.py`; it
uses synthetic storage and the prepared Desktop assemblies, without modifying
account data. The regular unit suite does not replace this native check.

Optional connector packages are pinned separately in `connectors/mysql.lock.json`;
they are downloaded at user request, not compiled into the runtime. The source
RPM and standalone export include this recipe. `python3 tools/test-mysql-provider.py`
loads the installed original provider and all dependency types without network
access. See [connector validation](../user/connectors.md) for its loopback-only query test.

RPM 12 also compiles/signs the frame helper from project sources during setup or
repair. `python3 tools/test-window-frame.py` exercises the actual Desktop base
with disposable forms and owned/fixed controls, without opening a report. See
[frame evidence and remaining compositor coverage](../reference/window-frame.md).

The experimental Redshift ODBC forwarder has a separate source-only builder and
no-network Engine comparison probe; neither installs it or changes the runtime.
See [Redshift reproduction and productization gates](../reference/redshift.md). It is not part
of the published RPM or the default runtime build.

`python3 tools/test-odbc-driver.py --driver 'exact Windows driver name'` checks
an existing registration, actual manager discovery, DLL loading and ODBC 3 handles
without connecting. Optional `--dsn` checks the manager's matching DSN entry. See
[the AWS vendor-MSI evidence](../reference/vendor-installers.md); the tool does not install a
driver or turn offline loading into connectivity certification.

## Experimental Pop!_OS DEB

`python3 tools/build-deb.py` builds `0.1.0-16pop1` for `amd64`, using a local
Ubuntu 24.04 container's `dpkg-deb`. `--local` uses the installed `dpkg-deb`.
It does not invoke CI, push code, run Wine or download Microsoft software.
The result is in `dist/popos-24.04/`. Debian metadata and root cache-maintenance
scripts are under `packaging/debian/`; bundle instructions and the local-runtime
setup script are in `packaging/popos/`.

Dependency/install checks in Ubuntu's base do not certify Pop!_OS's COSMIC UI.
See [experimental use](../user/popos.md). Source changes for this experiment do
not change the already built runtime 0.1.5 binary or its pending release gates.

## Corresponding source

When distributing a runtime, publish the exact corresponding patched source and build recipe, Wine/Neutron notices, DXVK/submodule licenses, dnlib notice, builder image digest and package inventory. The runtime binary alone is not a complete release. Use the source export tooling to create a sanitized project source tree; the full Wine/DXVK source bundle is generated from the prepared sources.

```bash
python3 tools/export-source.py /path/to/new-public-source --with-runtime-sources
```

This exports the standalone project, an SHA-256 file manifest and the full patched Wine/DXVK source archives. Git metadata, investigation directories, model caches, environment files, private-key files and compiled project inputs are excluded. Review source text before publishing; filename filtering does not redact secrets embedded in source code. Retain the source archives when distributing the corresponding runtime.

From a freshly unpacked source export, build directly from those exact patched bundles:

```bash
python3 runtime/build.py --bundled-sources
# For offline preparation, also supply the pinned dnlib NuGet package:
python3 runtime/build.py --bundled-sources --prepare-only \
  --dnlib-source /path/to/dnlib.4.5.0.nupkg
```

Bundle hashes and patch preparation markers are checked before compilation. This path needs neither Wine's upstream archive nor a DXVK Git checkout; submodule source is included in the bundle.

## Release validation

`python3 tools/release-check.py RUNTIME_ARCHIVE EVIDENCE_JSON` refuses certification until every required scenario has passing evidence for the exact archive checksum. Start with `docs/release-evidence.example.json`; pending cases are deliberately not accepted. Imported investigation prefixes/runtimes cannot satisfy this check.

The offline HTML numeric regression is `python3 tools/test-html-int64.py`; see
[Options evidence](../reference/options-dialog.md) for the separate 22-tab audit and limits.

## Reviewed inputs and successful-build receipts

The October 18 Neutron review added an independent packaging guard inspired by
upstream commit `480d6a4`. `runtime/patches.lock.json` records every production
patch filename and SHA-256. Unknown/modified patches fail; a Git checkout also
requires the patches and registry to be committed. An exported tree uses the
same registry without needing private Git history.

A full runtime build invalidates the previous success receipt before preparation,
uses a fixed builder image ID and clears generated install staging. Only a
successful build with unchanged input contents records
`build/runtime-build-success.json`. It fingerprints runtime recipes, helpers,
licenses, prepared Wine/DXVK/dnlib source content and compiled payload, including
modes and in-tree symlink targets. External symlink inputs are refused.

`--package-only` now requires that receipt to match version, builder, input
contents and compiled files. Forgotten extra DLLs/executables fail. Packaging may
add only its own license/provenance metadata. Existing runtime archive/checksum
names cannot be overwritten; choose a new explicit `--runtime-version` when
needed. Old development staging without a receipt needs a full rebuild. This
requirement does not invalidate existing released archives or the active runtime.

These are build-integrity checks, not compatibility certification. Eight isolated
regressions cover failed/stale builds, patch review, source/payload changes,
symlink escape and repeat metadata preparation. Runtime 0.1.5 completed a full Wine/DXVK build with this guard on October 20;
the failure gate is also exercised at the real packaging entry point. Candidate runtime patches remain outside the production
registry and are not automatically applied.
