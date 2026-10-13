# Architecture

Desktop update notifications use the original Microsoft policy and are disabled
by setup/repair. Versions remain pinned to the compatibility recipe; a native
validated-release notifier is future work. See [update policy](updates.md).

One repository contains the CLI, runtime patches, packaging and test tools. Keeping these together permits atomic compatibility changes. No GUI-specific API is required yet; a future GUI can drive the CLI. `doctor --json` is the initial structured interface, schema version 1.

The package launcher calls a Python standard-library CLI. Setup verifies inputs, installs a runtime into a content-addressed directory, provisions a private profile, applies local compatibility changes and generates readonly PE section backing. Only a completed installation becomes active. Snapshots remain at stable absolute paths; activation swaps metadata pointers rather than moving a populated prefix.

Opening a document sends its absolute Unix path through a private Unix socket to one systemd user service. The broker starts all Wine processes in the same cgroup, with optional resource ceilings selected through the CLI, converts paths with the runtime's `winepath` and launches additional Desktop windows without killing earlier documents. Launch and maintenance share a lock; maintenance also checks managed Wine processes outside the broker.

The service uses `KillMode=mixed`: a stop first reaches the broker, which closes its own prefix's wineserver. Remaining cgroup processes have a bounded final cleanup. This avoids sending SIGTERM to Wine's service processes before the server can coordinate shutdown; it does not affect servers for other prefixes.

Wine's automatic menu builder is disabled during provisioning, maintenance and launch. The project owns its desktop entry and MIME definitions; it removes older Wine-generated launchers only when their `WINEPREFIX` points into the managed profile tree. Entries for other prefixes and shared MIME definitions are preserved. This prevents a discarded snapshot from remaining registered as a file handler. The entry's `StartupWMClass` matches Wine Wayland's `pbidesktop.exe` identity; [GNOME's window tracker](https://github.com/GNOME/gnome-shell/blob/main/src/shell-window-tracker.c) uses that metadata when matching a window to its application.

The runtime handles Wayland parenting, cursor/HKL fixes, native composition delivery, OLE DB conversions, PE backing and memory reporting. The production AppDomain manager enables culture/composition fixes without a diagnostic script interpreter. CDP, JS evaluation, credentials automation and screenshot capture remain developer-only tools.

The derived PE cache is tied to source content and inode/ctime/size/range. Stale cache is never used. Opening falls back to the Wine loader; explicit repair rebuilds the cache.

This loader cache is separate from a project's `.pbi/cache.abf`. The latter is an Analysis Services backup containing the model and locally loaded data. PBIP projects without it open their definitions without data and require a refresh. The launcher preserves project files, including an existing `cache.abf`; it neither generates nor removes that file. Synthetic project tests must distinguish an unprocessed model from a rendering failure.

Test probes can query the embedded Analysis Services model through AMO/ADOMD/XMLA. Processing a Desktop model externally is an unsupported diagnostic use, even though those protocols are public. The product does not silently substitute external TMSL refresh for the user's Refresh action.

The current recipe uses a pinned Microsoft fixed-version WebView2 CAB. It is extracted into each managed profile; the runtime manifest defines its version and binary hashes. A prefix policy and session environment select that folder, so a separate Evergreen update does not change the application browser. No Microsoft package is included in project artifacts.

Optional database providers are managed separately from the runtime and application
patches. `connector install` shares the maintenance lock, requires an idle managed
session, verifies pinned upstream archives in the user cache, and stages only the
provider directory/registration. A per-prefix manifest records its files. Existing
external registrations, including .NET machine.config registrations used by vendor
MSI packages, are reported without being overwritten. Profile snapshots naturally
retain connector files; no complete snapshot is needed just to add a new provider.
No replacement database protocol or plugin runtime is introduced.
