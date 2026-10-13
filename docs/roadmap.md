# Product roadmap

The development preview is scoped to Fedora 44 x86_64 and native Wayland.

- Provision a dedicated graphical QA installation and orchestrate unattended
  compositor input, modal/dropdown checks, real Desktop Save and independent
  saved-data verification. Existing individually run probes are building blocks.
- Broaden the local [window frame correction](window-frame.md) across display scales,
  multiple monitors and actual modal workloads. Isolate the baseline Wine/PaperWM
  maximize-state divergence before certifying compositor maximize/restore.
- Validate the remaining nested permission confirmations, source-list input delay,
  general OneLake chooser after sign-in and another corrected cloud publish cycle.
- Reproduce and isolate real-server refresh timeouts/TLS separately from local
  cached-model restoration. Connector cancellation remains workload-dependent.
- Compile/test the three inactive [Neutron candidates](upstream-neutron.md) using
  the [recorded acceptance plan](runtime-testing.md):
  signed server DPI, capture-aware tracking and rendering-mode glyph cache.
  Port related high-priority rendering/monitor fixes only with native evidence.
- Revalidate the full compatibility matrix for each new runtime checksum,
  including large-model complexity, multiple documents and prolonged sessions.
- Versioned [RPM prereleases and source-only runtime history](releases.md) are indexed
  on GitHub. Establish public distribution, a private security reporting channel,
  signing policy, certified runtime binaries and validated Fedora notifications.
- Expand cache regression coverage to additional synthetic populated models and
  partition/schema changes. Automatic versioned backup/rotation is not implemented.

A GUI, other distributions, X11, Flatpak and AppImage are outside this release.
Keep CLI, runtime recipes and tests together until separate versioning solves a
concrete maintenance problem. The CLI remains the interface for any future GUI.
