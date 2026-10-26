# Compatibility and release gates

**Historical evidence below is version-specific.** The current runtime 0.1.5 /
Power BI 2.159 candidate has separate [port and validation status](powerbi-2.159.md).
The older passes in this table do not certify that candidate.

Snapshot/rollback results below describe historical CLI behavior. Current CLI
maintenance is [in place without snapshots](installation-lifecycle.md#maintenance);
the new release gate requires separate in-place maintenance failure/retry evidence.

The current runtime was built from source and exercised on Fedora 44 x86_64 Wayland in a disposable prefix created from official installers. The table below distinguishes current product checks from older investigation results. Required synthetic scenarios passed, including a two-hour session. This remains a development preview: one discrepant idle native-frame sample is retained, and its cause is not established. See [validation](validation.md) for the exact checksum and scope of each result.

| Scenario | Investigation evidence | New product certification |
|---|---|---|
| Wine Wayland composition and owned dialogs | Passed | Native submitted frame and browser capture agree after clean-prefix reopen; cursor confirmation remains investigation evidence |
| CSV Load | Passed | Direct Text/CSV entry, visual creation and PBIX save/reopen passed; general source chooser blocked by OneLake sign-in |
| Numeric table visual: 120, 100, 80, total 300 | Passed | Passed in clean prefix, including newly imported CSV; independent DAX agrees |
| PBIX save and reopen | Passed | Passed in clean prefix with spaces and accents |
| Options settings dialog | Clipped 600 × 400 modal reproduced in a synthetic PBIP | Runtime 0.1.2 / RPM 9: seven numeric cases, 22-tab navigation/footer/scroll audit, compositor scroll and original Cancel callback passed. No settings submitted; broad input/resize coverage pending. See [Options](options-dialog.md) |
| Data source settings list | Native entries existed while HTML rows were absent | Reproduced with CSV: cached viewport/page size 0. Fresh guarded patch displayed CSV and MySQL sources with page size 10; user confirmed real-report sources. Initially unresponsive clicks/missing cursor recovered after an estimated 10–60 seconds; cause and input latency remain unresolved. No source/permission changes |
| Close with unsaved changes | Legacy modal failed to initialize in a reported session | Native Save/Don't save/Cancel passed in actual Desktop with a disposable PBIP; save/cache/reopen and normal-mode startup checked; see [native dialogs](native-dialogs.md) |
| Cached PBIP model | Original ABF loaded; extensive multiline linguistic JSON failed during metadata update | RPM 11: in-memory compaction, actual source measure applied, Desktop Save and fresh normal reopen; 158 table counts/states matched, including one existing query-error state. Original preserved. See [scope](model-cache.md) |
| Cancel an in-progress data refresh | User reports Cancel does not interrupt loads | Synthetic native clicks passed during evaluation (~0.8 s) and data loading (19.879 s), retaining committed data; original freeze not reproduced; see [scope](refresh-cancellation.md) |
| Desktop PBIX/PBIP/PBIR opening | — | GIO dispatch, relative project links and responsive native windows passed without diagnostic mode |
| Additional document while another remains open | — | Two PBIX documents passed; native windows retained and both DAX totals confirmed |
| MySQL Connector/NET 8.0.33, MariaDB 10.11.19 | Earlier backend refresh passed; TLS failed in investigation | Optional managed recipe, native factory/dependencies, synthetic loopback UI refresh with Database credentials, 3 rows / total 300, two committed partitions and source list passed. Explicit Windows username/password impersonation fails on Wine's placeholder LogonUser token; reproduced separately. Unencrypted local fixture only; real-server TLS unverified. See [connectors](../user/connectors.md) |
| Redshift database password, experimental shared ODBC forwarder | Original app-private manager failed ENV allocation; Wine manager passed | Controlled real authentication/schema metadata, one derived Import row, independent DAX and Save/normal reopen passed. User subsequently confirmed another real-dataset test and refresh cancellation; counts/types, server-side cancellation and post-cancel state were not independently audited. Managed installation, other auth and TLS policy remain pending. See [Redshift](redshift.md) |
| Refresh 158 tables using external TMSL | Commit/DAX passed, ~4.2 min, ~9.66 GiB peak | Diagnostic result only |
| Original external AWS Redshift MSI, generic ODBC | — | MSI 1.6.3.1008 passed silent installation in the managed prefix and user-completed full UI in a fresh Wine-only prefix, with identical vendor files and actual driver/DSN/ENV/DBC checks. Managed maintenance UI canceled without file changes. Native ODBC password authentication, one derived metadata row, independent DAX and Save/normal reopen passed. Credential modal needed a session-only workaround; configured DSN connection, typed data/cancel and repair/uninstall remain separate. See [vendor installer evidence](vendor-installers.md) |
| Original enterprise thin-report UI refresh | Renderer OOM | Not certified; synthetic evidence does not reproduce every property of that report |
| Synthetic 158-table UI refresh with 156 relationships | — | All 156 fact tables × 10,000 rows, dimension propagation, total 300 and save/reopen passed in clean prefix; native frames before/after Save and a separate reopen passed; 7,264.90-second soak passed with 24 visual checks and no OOM/GPU replacement |
| Thin-report visuals after external refresh | Data committed; visuals not notified | External processing remains an unsupported diagnostic flow |
| Microsoft sign-in / cloud publishing | Browser authentication/persistence passed; real homologation publication confirmed by user | Post-success Windows Store rating failed locally; RPM 10 disables that entrypoint with offline regression evidence. New corrected cloud cycle and broader scenarios remain separate; see [publishing](../user/publishing.md) and [sign-in](../user/sign-in.md). |
| Fresh prefix from official installers | — | Passed; committed wineboot interruption/resume also passed |
| Repair, update, rollback and preserving uninstall | — | Passed natively; update candidate differs in version metadata with identical executable files |
| RPM dependency installation | — | DNF dependency installation and packaged CLI/integration checks in a Fedora 44 container; native GUI tested separately from the checkout |

## Required certification

The newer [Options correction](options-dialog.md) has scoped evidence for runtime
0.1.2 / RPM 9; it does not inherit full certification from older archive hashes.

The later [Edit Permissions correction](permissions-wayland.md) has separate
synthetic compositor-input OK/Cancel/reopen evidence for runtime 0.1.1 and the
RPM 8 HTML recipe. Historical passes above are tied to their original checksum.
The new checksum needs broader release gates; the nested None/Delete Permissions
confirmation and real-server refresh/TLS remain pending.

Install from an empty user profile on Fedora 44. Verify PBIX/PBIP/PBIR through the file manager, project-relative references, spaces/accents and additional opens while a document is already active. Import the synthetic sales CSV, verify exact visual values and save/reopen the result.

Use a synthetic 158-table model and report for a UI refresh, verify both model commit and displayed numbers, save/reopen and run a two-hour session. Monitor renderer heap/PSS, cgroup RAM/swap, OOM events and GPU process restarts. A successful TMSL response or screenshot showing a populated Data pane is insufficient. Passing this workload does not certify every enterprise model or untested connector.

Also test interrupted setup, checksum failures, in-place runtime update/repair, failure marking and successful retry, default-association restoration and uninstall. Retain sanitized evidence with exact runtime/Power BI/WebView2 versions and environment. The release checker requires passing evidence for every listed scenario and the exact runtime checksum. These gates describe synthetic coverage; the preview retains known limitations and the discrepant capture documented in validation.
