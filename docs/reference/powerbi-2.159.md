# Power BI Desktop 2.159.883.0 assessment

**October 20, 2026 — local compatibility candidate.** The guarded recipe has been
ported and offline checks passed. Native acceptance and release certification are
tracked separately below. RPM 18 targets this version; the 2.158 recipe remains
available for existing profiles. No existing
user installation was changed during the assessment or candidate preparation.

The [machine-readable assessment](powerbi-2.159-assessment.json) retains the
observed installer/file hashes and guarded-recipe results without Microsoft binaries.

Microsoft replaced this installer with 2.159.1231.0 at the same address on
November 2, 2026. That port is recorded [below](#215912310-november-2026); the
sections before it describe 2.159.883.0 and are kept as dated evidence.

The [official Microsoft download page](https://www.microsoft.com/pt-br/download/details.aspx?id=58494)
advertised 2.159.883.0, published October 15. Its EXE's embedded version also
reported 2.159.883.0. The exact installer obtained from Microsoft was:

- [PBIDesktopSetup_x64.exe](https://download.microsoft.com/download/8/8/0/880bca75-79dd-466a-927d-1abf1f5454b0/PBIDesktopSetup_x64.exe)
- Size: 703,228,680 bytes.
- SHA-256: `5412131d1f5d535e42358cb6d496703c3c0cdf9267779ac9220171f58ce20cdd`.

## Initial assessment

The EXE's attached cabinet was extracted without executing the installer. The
embedded MSI cabinet supplied these unmodified application files:

| Installed file | MSI cabinet name | New SHA-256 |
|---|---|---|
| Microsoft.PowerBI.Client.Shared.dll | PowerBI.Client.Shared.dll | `b374f445156cea1caf13eabbfc0b03ee8d2179a75039713f0dfc9cad2535c10a` |
| Microsoft.PowerBI.Client.Windows.dll | FilePowerBIClientWindows | `5c49618814888815ec3649ad2bf7dcf0209de1b3722d30372c126b3ebaf79938` |
| Microsoft.Mashup.Client.UI.dll | Microsoft.Mashup.Client.UI.dll | `15a88f90544f1a2c7f002f0de05c6aed65dcfcda1074a0ab847f3623e55ecb3d` |

All three differ from the guarded 2.158 inputs. Running the actual existing
`signin.patch_windows` and `legacy_html.patch_ui` functions on the new inputs
rejected them, respectively:

```text
Unsupported Desktop assembly for email dialog patch
Unsupported legacy HTML assembly; no patch produced
```

This establishes that the current recipe cannot safely be reused unchanged. It
does not establish that Desktop itself cannot run on Wine. Updating checksums
alone would bypass the protection without proving that the fixes still apply.

## Guarded port

- All five targeted legacy HTML resources are byte-identical to 2.158 and moved
  by exactly 256 bytes. The new recipe checks each original/patched resource hash,
  retains its length and verifies the complete final assembly hash:
  `a2c3db990ed08e371356aec9055d9d46026978413472512873385593917e6c94`.
- The email resource is byte-identical, with original SHA-256
  `7c763aa03488af892735911041a2055c7d06ab7baba2e1bda4048a600e1d75a4`.
  The existing serializer transformation passed against the exact new assembly.
- The Quill report-view HTML is byte-identical; its existing guarded recipe passed.
- The Analysis Services workaround has a newly verified call/import location.
  The imported functions and sole call site were inspected; exact input/call bytes
  and final output hash guard the new transformation.
- The window-frame methods have new exact fingerprints. The new DPI layout calls
  are retained; only the previously scoped client extension and resize helper are
  inserted. Other native patchers accepted the actual new assembly's guarded
  signatures and bodies.
- The complete offline sequence passed: installed-path, WinRT remap, Store prompt,
  cache normalization, frame and save confirmation. Local helper signatures passed.

The repeatable resource check writes only JSON evidence:

```bash
python3 tools/test-powerbi-recipe.py /path/to/unmodified/bin \
  --version 2.159.883.0 --output /path/to/new-evidence.json
```

Existing 2.158 originals and repair remain supported. Local installer selection
uses exact hashes; runtime changes do not silently change the installed app version.

## Preliminary native acceptance

A sanitized copy-on-write upgrade view passed installation, guarded patching and
`doctor`. Its read-only lower layer was the existing 2.158 profile; account and
report state were removed from the QA view. Session services and XDG data,
configuration, cache and state were isolated. The original manifest remained
unchanged. This is an upgrade test, not the clean-install release gate.

With the preliminary runtime archive SHA-256
`5c1b78221ca28234e2e6dacf63c20c6d7ec7940a09470371b8378714b05a4bb0`:

- A three-table synthetic model passed normal UI refresh. The request was sent
  26.8 seconds after launch; this is not a measurement of refresh duration.
  Independent ADOMD queries confirmed total 300, row count and relationship filters.
- The report rendered Cafe 120, Suco 100, Cha 80 and total 300. Native frame
  captures were reviewed before and after Save and agreed with the report view.
- Save produced the project's imported data cache. A fresh launch through GIO,
  from a project path containing spaces and accents, independently returned 300.
  PBIX and PBIR also passed normal GIO opening with two documents coexisting.
  The windows responded and no diagnostic mode was enabled.
- Direct CSV import independently returned 300, rendered the expected table and
  saved a PBIX through Desktop's actual Save dialog. Its normal reopening passed.
- Failed preliminary attempts exposed QA harness issues: the test must retain
  the real desktop runtime directory, preflight every probe, and resolve the
  ADOMD assembly from Desktop's application directory. Those attempts remain
  failed evidence; the subsequent complete runs are separate results.

## Exact-archive native tests

A genuinely empty managed profile completed setup using official installers and
runtime 0.1.5, SHA-256
`291bb52fca8c27f2446ec4a05aaf982bb43d8c13e6b3787f32a1328ad890f05a`.
Only verified prerequisite downloads were reused; no existing profile was copied.
Setup was deliberately interrupted during .NET after the Wine/Wayland stages.
No active installation was created on interruption. Repeating the same command
resumed and completed successfully; both attempts together took 375.97 seconds.
Doctor passed after installation.

A separate 192.24-second synthetic session confirmed 158 model tables, the
expected row count in every fact table, dimension-filter propagation and total
300. Refresh was requested through Desktop's UI 21.95 seconds after launch;
that timestamp is not the refresh duration. Save wrote the imported cache.
Native before/after-Save frames and the report capture were reviewed and showed
Cafe 120, Suco 100, Cha 80 and total 300. No GPU restart or cgroup OOM was recorded.

Direct CSV import created the expected table visual, independently returned 300
and saved a new PBIX. Normal GIO opening of PBIX, PBIP and PBIR passed, including
relative project links, spaces/accents in paths, responsive windows and two
documents coexisting. The PBIX/PBIP reopen checks independently confirmed saved
data without diagnostic mode. These tests do not certify all reports or UI input.

## Remaining release validation

The [runtime 0.1.5 notes](../releases/runtime-v0.1.5.md) record the successful full
build, fixed builder and input fingerprint. All nine native component checks passed again against the clean 0.1.5
installation. Repair and rollback passed. Runtime changes 0.1.5 → 0.1.3 → 0.1.5
preserved Power BI 2.159 and passed doctor, including both rollback directions.
Non-purge removal preserved the profile; purge removed managed data and preserved
the external synthetic PBIX. The temporary QA profiles were then removed, and
the original production installation manifest remained unchanged.

The **two-hour exact-archive session has not been run**. Earlier runtime sessions
cannot satisfy that gate. No current-version cloud cycle is claimed. The runtime
binary is published as a beta candidate (runtime 0.1.5) with its complete
corresponding source and evidence, and automatic setup uses it; the two-hour
session remains the open gate in the
[release contract](../development/setup-release.md).

## 2.159.1231.0 (November 2026)

**November 17, 2026: guarded recipe ported; one experimental host tested.** The
unversioned Microsoft address pinned for 2.159.883.0 has served a different
file since November 2, 2026. Automatic setup of a release that pins the older
build therefore stops at `Checksum verification failed`. The older installer
could not be obtained again from Microsoft, so no 2.159.883.0 baseline was run
on the new host.

- [PBIDesktopSetup_x64.exe](https://download.microsoft.com/download/8/8/0/880bca75-79dd-466a-927d-1abf1f5454b0/PBIDesktopSetup_x64.exe), the same address as before
- Embedded version: 2.159.1231.0.
- Size: 702,986,400 bytes.
- SHA-256: `55e8ee44aa908d75edaed4bdb1a34863f41c047951f3724f298486fe07049f2d`.

The [machine-readable record](powerbi-2.159.1231-assessment.json) holds the
hashes and the offline check result without Microsoft binaries.

### What changed in the application files

The cabinet was extracted without running the installer.

| Installed file | 2.159.1231.0 SHA-256 | Against 2.159.883.0 |
|---|---|---|
| Microsoft.PowerBI.Client.Shared.dll | `3c4a994c17a3a61396711c6986b2a03f898bca9eb6973b893a91207fc68a99bc` | Rebuilt |
| Microsoft.PowerBI.Client.Windows.dll | `708f3de4cffe09a0c3aed30db5f0af820c3a7219b7924f0fac062b815d8e6c32` | Rebuilt |
| Microsoft.Mashup.Client.UI.dll | `1b90774991b5a1951ec8ac712bf079388d4feef1ed49edeebaf908702400bbb9` | Rebuilt |
| msmdsrv.exe | `90dd9882dd0ef22c1a49261099021798d1edf4817afff6b336322e7651659495` | Identical |
| WebView2Resources/minerva/reportView.html | `0a03d24a6967d3026e8e910399cddd51ef668efd8f9b700a874f55f63059c41a` | Identical |

Both 2.159 recipes reject the other build's files: the existing guards did their
job, and updating checksums alone would not have been a port.

### Guarded port

- The five targeted legacy HTML resources are byte-identical to 2.158 and
  2.159.883.0 and moved by exactly **328** bytes (256 in 2.159.883.0). The recipe
  looks the shift up from the exact original hash, checks every original and
  patched resource hash, keeps each length and verifies the intermediate assembly
  hash `072a113c12b0cfb170e8ab00eb3e05a58237d2581ac9c479e9e4c858667d7749`.
- The Options native method sits at a new file offset with the same method and
  member tokens. Its 2.159.883.0 replacement body differs in exactly two bytes,
  the low bytes of two user-string (`ldstr`) tokens, because the `#US` heap
  moved. Mapping those two tokens back makes the original
  region hash to the 2.159.883.0 guard, which shows the code is otherwise the
  same. The final assembly hash is
  `3b0639cf526493de18e7d088561f0bfcbb7a528917b4c3e1424ec8637ac260c1`.
- The email resource and the Quill report-view document are byte-identical;
  their existing guarded transformations passed against the new assemblies.
- The Analysis Services workaround applies unchanged, since `msmdsrv.exe` is
  the same file.
- The name-based native patchers (window frame, save confirmation, Store prompt,
  cache normalization, WinRT remap, installed path) accepted the new assemblies
  during a real setup. No fingerprint had to be loosened.

```bash
python3 tools/test-powerbi-recipe.py /path/to/unmodified/bin \
  --version 2.159.1231.0 --output /path/to/new-evidence.json
```

That offline check passed. Exact 2.159.883.0 and 2.158.1177.0 installers remain
registered for local inputs and existing profiles; only the build Microsoft
currently serves carries a download address.

### Native result on one experimental host

Omarchy 4.5.0 (Arch based) with Hyprland 0.56.2, two monitors, NVIDIA RTX 3060
with Intel Iris Xe. This is **not** the Fedora validation host and not release
certification.

- A genuinely empty managed profile completed `pbi-linux setup` in 5 minutes 38
  seconds, downloads included, with the published runtime 0.1.6-beta.1. Doctor
  passed all 20 checks.
- With that runtime the window stayed blank on the two-monitor desktop because
  of a Wine defect unrelated to the Desktop version. The remaining checks used
  a local runtime build with corrections that are proposed separately.
- `tests/e2e/session.py --ui-refresh --save` on a three-table synthetic PBIP:
  refresh requested through the UI 14.33 seconds after launch; independent ADOMD
  queries confirmed total 300, the fact row count and the relationship filter;
  Save wrote the imported cache; the native frames before and after Save showed
  Cafe 120, Suco 100, Cha 80 and total 300. No GPU restart or cgroup OOM.

Not run for this build: the nine native component checks, CSV import, the
158-table refresh, save/reopen of a PBIX, sign-in, publishing, the two-hour
session, and anything on Fedora.
