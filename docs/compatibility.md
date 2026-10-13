# Compatibility and release gates

The current runtime was built from source and exercised on Fedora 44 x86_64 Wayland in a disposable prefix created from official installers. The table below distinguishes current product checks from older investigation results. Required synthetic scenarios passed, including a two-hour session. This remains a development preview: one discrepant idle native-frame sample is retained, and its cause is not established. See [validation](validation.md) for the exact checksum and scope of each result.

| Scenario | Investigation evidence | New product certification |
|---|---|---|
| Wine Wayland composition and owned dialogs | Passed | Native submitted frame and browser capture agree after clean-prefix reopen; cursor confirmation remains investigation evidence |
| CSV Load | Passed | Direct Text/CSV entry, visual creation and PBIX save/reopen passed; general source chooser blocked by OneLake sign-in |
| Numeric table visual: 120, 100, 80, total 300 | Passed | Passed in clean prefix, including newly imported CSV; independent DAX agrees |
| PBIX save and reopen | Passed | Passed in clean prefix with spaces and accents |
| Close with unsaved changes | Legacy modal failed to initialize in a reported session | Native Save/Don't save/Cancel passed in actual Desktop with a disposable PBIP; save/cache/reopen and normal-mode startup checked; see [native dialogs](native-dialogs.md) |
| Cancel an in-progress data refresh | User reports Cancel does not interrupt loads | Synthetic native clicks passed during evaluation (~0.8 s) and data loading (19.879 s), retaining committed data; original freeze not reproduced; see [scope](refresh-cancellation.md) |
| Desktop PBIX/PBIP/PBIR opening | — | GIO dispatch, relative project links and responsive native windows passed without diagnostic mode |
| Additional document while another remains open | — | Two PBIX documents passed; native windows retained and both DAX totals confirmed |
| MySQL Connector/NET 8.0.33, MariaDB 10.11 | Backend refresh passed; TLS failed | Optional connector recipe pending |
| Refresh 158 tables using external TMSL | Commit/DAX passed, ~4.2 min, ~9.66 GiB peak | Diagnostic result only |
| Original enterprise thin-report UI refresh | Renderer OOM | Not certified; synthetic evidence does not reproduce every property of that report |
| Synthetic 158-table UI refresh with 156 relationships | — | All 156 fact tables × 10,000 rows, dimension propagation, total 300 and save/reopen passed in clean prefix; native frames before/after Save and a separate reopen passed; 7,264.90-second soak passed with 24 visual checks and no OOM/GPU replacement |
| Thin-report visuals after external refresh | Data committed; visuals not notified | External processing remains an unsupported diagnostic flow |
| Microsoft sign-in / cloud publishing | Email prompt fixed; account authentication pending | See [sign-in status](sign-in.md); not v1 gate |
| Fresh prefix from official installers | — | Passed; committed wineboot interruption/resume also passed |
| Repair, update, rollback and preserving uninstall | — | Passed natively; update candidate differs in version metadata with identical executable files |
| RPM dependency installation | — | DNF dependency installation and packaged CLI/integration checks in a Fedora 44 container; native GUI tested separately from the checkout |

## Required certification

Install from an empty user profile on Fedora 44. Verify PBIX/PBIP/PBIR through the file manager, project-relative references, spaces/accents and additional opens while a document is already active. Import the synthetic sales CSV, verify exact visual values and save/reopen the result.

Use a synthetic 158-table model and report for a UI refresh, verify both model commit and displayed numbers, save/reopen and run a two-hour session. Monitor renderer heap/PSS, cgroup RAM/swap, OOM events and GPU process restarts. A successful TMSL response or screenshot showing a populated Data pane is insufficient. Passing this workload does not certify every enterprise model or untested connector.

Also test interrupted setup, checksum failures, runtime update, repair, rollback, default-association restoration and uninstall. Retain sanitized evidence with exact runtime/Power BI/WebView2 versions and environment. The release checker requires passing evidence for every listed scenario and the exact runtime checksum. These gates describe synthetic coverage; the preview retains known limitations and the discrepant capture documented in validation.
