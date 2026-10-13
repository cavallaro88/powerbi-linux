# Build from a clean source tree

Install Docker or Podman and ensure your account can invoke the selected engine. No existing Wine/Bottles installation or prefix is needed. Source preparation uses Python 3.12+, Git and `patch`; compilation tools are installed inside the builder container.

```bash
python3 runtime/build.py
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
# With a native rpmbuild installation:
python3 tools/build-rpm.py --local
```

RPMs and source RPMs are under `build/rpm/`. The package contains CLI/source resources and desktop integration; it does not contain a prefix, Microsoft installers or the Wine runtime archive. No package script runs Wine, downloads dependencies or accesses user credentials.

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
