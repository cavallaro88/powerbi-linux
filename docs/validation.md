# Validation — 2026-10-13

This is a **validated development preview**, scoped to the synthetic scenarios below. It is not a guarantee for arbitrary enterprise models, other desktops/distributions, untested connectors or Microsoft cloud services. Historical experiments are preserved in [investigation notes](investigation-history.md).

The exact source-built runtime archive is `powerbi-linux-runtime-0.1.0-x86_64.tar.xz`, SHA-256:

```text
a7db45d0c14213a14b5f2ce1bc6c7bd5d1e1b982199f8c0020503e9c57421eed
```

Tests used Fedora 44 x86_64, GNOME 50.5 on native Wayland, kernel 7.2.9-200.fc44, Mesa 26.2.4 and a host with approximately 16 GiB RAM. Power BI Desktop is 2.158.1177.0 and fixed WebView2 is 154.0.4258.62. The installation was created from an empty prefix using verified official installers; imported investigation profiles do not supply this evidence.

| Scenario | Result and scope |
|---|---|
| Clean setup / interrupted setup | Passed; a real wineboot completed, an injected interruption followed that committed boundary, and normal setup resumed. This does not cover every possible mid-installer interruption. |
| CSV import / visual / save and reopen | Direct Blank report → Get Data menu → Text/CSV passed without sign-in. DAX and visible Cafe 120, Suco 100, Cha 80, Total 300 agreed; an accented PBIX filename reopened correctly. Peak RAM reached the 6 GiB limit, with approximately 991 MiB swap and no OOM. |
| Production desktop PBIX | GIO MIME/default dispatch, Unicode/spaces and two simultaneous documents passed with diagnostics disabled. The final normal-profile run used 6 GiB RAM and approximately 1.80 GiB swap, with no OOM; both native windows responded and both DAX totals were 300. |
| Production desktop PBIP / PBIR | Relative project/report/model references passed through GIO with the final desktop entry, diagnostics disabled and the normal memory profile. |
| Synthetic large UI refresh | 158 tables: sales + 156 facts + one dimension, 156 active relationships and 10,000 rows per fact. Actual Schema and data refresh passed, including every fact count, dimension filter propagation and total 300. |
| Native refresh / Save / reopen | A new fixture had no model cache. Native frames before and after Save showed the numeric visual. Separate reopen preserved all counts, relationship behavior and the visible native values. Final refresh peak sampled RAM was approximately 9.36 GiB under the large profile, without OOM. |
| Two-hour use | 7,264.90 seconds, 3,601 memory samples and 24 periodic visual-sorting checks. All counts/filter/total were rechecked at the end. No cgroup OOM or GPU-process replacement; peak sampled RAM 5.36 GiB, no swap, sampled V8 used heap 285.02–449.60 MiB. The final native frame showed the correct values. |
| Native maintenance | Bad checksum rejected without pointer changes; damaged derived-cache metadata repaired; repaired and updated profiles opened; rollback restored the original. The update candidate changes version metadata only, with identical executable files, so it does not certify future Wine versions. |
| Uninstall / integration migration | Preserving uninstall retained profiles and cleared own default tokens. Repair restored integration without forcing defaults. Final migration removed 22 obsolete managed Wine/MIME entries and preserved defaults/other files. Unit and RPM checks cover masking/restoring the global RPM entry without modifying system files. |
| Source / packaging checks | 23 unit tests passed from an independently exported project tree; desktop validation, syntax and CLI loading passed. RPM dependency installation and packaged integration checks run in a Fedora 44 container, separately from native UI testing. |

Initial native GUI tests ran from the checkout with isolated XDG directories, a portable NTLM helper and no host unixODBC installation. At that initial stage, the RPM was not installed on the native host. Its DNF dependency checks are a separate container validation; they do not claim a containerized GUI or a native-host RPM installation.

## Capture discrepancy retained

One idle reopen returned correct model counts and browser output while its sampled native image was blank. That run remains visually uncertified and is retained as `idle-capture-discrepancy` in the QA bundle. A separate manual idle reopen and the final repeat showed the correct native values without visual interaction. The repeat records HWND 0x10064 and a sampled frame age of 0.267 seconds. The harness now records native-window/timestamp metadata and captures the native sample before browser screenshot instrumentation.

The diagnostic hook samples at most every 500 ms; it is not a recording of every submitted buffer. The cause of the discrepant sample is **not established**. Do not count it as a visual pass or infer a universal rendering fix from the later successful run. Production launch disables this instrumentation.

## Model cache versus loader cache

A project's `.pbi/cache.abf` stores the locally loaded model/data; opening a PBIP without it loads definitions without imported rows. This matches [Microsoft's project documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset) and the earlier controlled cache comparison. The fixture generator now declares `data_loaded: false`; a verified UI refresh and Desktop Save change that disposable fixture expectation to `true` for reopen. The launcher preserves project caches.

This file is separate from the project's derived PE loader backing. That backing is tied to the browser's content/inode/ctime/size/ranges; invalid backing falls back to the regular loader, and explicit repair rebuilds it.

## Evidence and remaining scope

The companion `powerbi-linux-qa-20261013.tar.gz` contains selected synthetic JSON, query logs, reviewed screenshots, runtime/build inventory, environment information and a per-file SHA-256 manifest. Personal workspace/user paths are replaced in text; images were reviewed separately. It contains no populated prefixes, PBIX/ABF payloads, installers, signing keys or unrelated investigation logs. `release-evidence.json` records the exact archive and scenario scope; the release checker validates those recorded gates, not publisher authenticity or universal compatibility.

Microsoft sign-in, cloud publishing and the general OneLake source chooser remain limited. Local CSV uses the direct menu route. The original enterprise thin-report refresh and optional enterprise connectors remain uncertified; external TMSL processing is a diagnostic flow, not a replacement for the user's Refresh action. See [compatibility](compatibility.md).

## Installed RPM follow-up

The user subsequently installed this exact RPM on the native Fedora host. Setup, all doctor checks, native PBIX visual review and production GIO PBIX/PBIP/PBIR checks passed with system NTLM and unixODBC. See [host validation](validation-host.md) for the exact RPM checksum, evidence and scope.
