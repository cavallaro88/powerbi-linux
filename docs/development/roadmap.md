# Product roadmap

The development preview is scoped to Fedora 44 x86_64 and native Wayland.

- Complete the [guided setup release contract](setup-release.md): the terminal
  flow and pinned download selection are implemented, but published runtime
  binaries with exact-artifact evidence remain pending. Review and adapt the new
  Power BI recipe using the [2.159 assessment](../reference/powerbi-2.159.md) before
  enabling its download; preserve maintenance of existing 2.158 installations.

- Provision a dedicated graphical QA installation and orchestrate unattended
  compositor input, modal/dropdown checks, real Desktop Save and independent
  saved-data verification. Existing individually run probes are building blocks.
- Broaden the local [window frame correction](../reference/window-frame.md) across display scales,
  multiple monitors and actual modal workloads. Isolate the baseline Wine/PaperWM
  maximize-state divergence before certifying compositor maximize/restore.
- Validate the remaining nested permission confirmations, source-list input delay,
  general OneLake chooser after sign-in and another corrected cloud publish cycle.
- Reproduce and isolate real-server refresh timeouts/TLS separately from local
  cached-model restoration. Connector cancellation remains workload-dependent.
- Productize the experimental shared ODBC-manager correction: native Redshift
  database-password authentication/metadata and one-row Save/reopen passed; the
  user confirmed another real-dataset test and refresh cancellation. Independent
  typed table checks, folding, server-side cancellation/post-cancel state,
  transactional activation/rollback and other
  ODBC regressions remain. Add shared driver inventory and ODBC/DSN diagnostics. Track support
  per driver/authentication/mode/operation instead of claiming entire databases;
  see the [connector policy and test layers](../reference/connector-support.md).
- Validate a generic original Windows x64 vendor-MSI installation path inside the
  managed prefix. AWS Redshift 1.6.3.1008 passed silent MSI execution, a user-completed
  full wizard in a fresh Wine-only prefix, automatic registration/loading and
  generic ODBC metadata Import/Save/reopen. Maintenance UI cancellation preserved
  the real installation. Exercise DSN setup, shared dependencies and repair/uninstall;
  retain the separate credential-modal workaround as an observation rather than
  scheduling a permanent patch for this test. Test ClickHouse separately, without
  assuming every vendor installer works on Wine; retain optional pinned recipes.
- Compile/test the three inactive [Neutron candidates](../reference/upstream-neutron.md) using
  the [recorded acceptance plan](runtime-testing.md):
  signed server DPI, capture-aware tracking and rendering-mode glyph cache.
  Port related high-priority rendering/monitor fixes only with native evidence.
- Revalidate the full compatibility matrix for each new runtime checksum,
  including large-model complexity, multiple documents and prolonged sessions.
- Versioned [RPM prereleases and source-only runtime history](../releases.md) are indexed
  on GitHub. Establish public distribution, a private security reporting channel,
  signing policy, certified runtime binaries and validated Fedora notifications.
- Expand cache regression coverage to additional synthetic populated models and
  partition/schema changes. Automatic versioned backup/rotation is not implemented.

A GUI, other distributions, X11, Flatpak and AppImage are outside this release.
Keep CLI, runtime recipes and tests together until separate versioning solves a
concrete maintenance problem. The CLI remains the interface for any future GUI.
