# Architecture

Desktop update notifications use the original Microsoft policy and are disabled
by setup/repair. Versions remain pinned to the compatibility recipe; a native
validated-release notifier is future work. See [update policy](../user/updates.md).

One repository contains the CLI, runtime patches, packaging and test tools. Keeping these together permits atomic compatibility changes. No GUI-specific API is required yet; a future GUI can drive the CLI. `doctor --json` is the initial structured interface, schema version 1.

The package launcher calls a Python standard-library CLI. Setup verifies inputs, installs a runtime into a content-addressed directory, provisions a private profile, applies local compatibility changes and generates readonly PE section backing. Only a completed initial setup becomes active. Later repair/update modifies that same prefix in place, without a full-prefix copy, snapshot retention or rollback. A small state marker blocks launch after failed/incomplete maintenance until repair/update succeeds; metadata activation alone cannot restore partially changed files. Existing legacy profile directories are not automatically deleted.

The onboarding front end resolves omitted inputs from the packaged release
manifest, checks local files before downloads and collects terminal license
acceptance. Download URLs and hashes are pinned; the manifest remains pending
until verified runtime binaries, corresponding sources and evidence are publicly
accessible. Provisioning retains the same resumable transaction after resolution.
The installed application's recipe is recorded separately from its runtime so
repair and runtime changes preserve the supported Desktop version.

Opening a document sends its absolute Unix path through a private Unix socket to one systemd user service. The broker starts all Wine processes in the same cgroup, with optional resource ceilings selected through the CLI, converts paths with the runtime's `winepath` and launches additional Desktop windows without killing earlier documents. Desktop also starts Desktop itself (File > Open with a report open, a recent file, a restart); the broker never sees those start, so it ends the session only when no `PBIDesktop.exe` of its prefix is left, not when its own children have exited. Launch and maintenance share a lock; maintenance also checks managed Wine processes outside the broker. The broker holds a session lock until it has stopped its Wine server, and maintenance and the next launch wait for it (up to 20 seconds), so a session that is still closing cannot kill their Wine processes. A client that disconnects or sends a malformed request gets no answer, but the session and its reports carry on. `pbi-linux stop` force-quits a stuck session: it stops the unit, then ends any Wine process left in the managed profiles; it waits for a session start that holds the maintenance lock (up to 85 seconds) and refuses while a repair or update holds it. A second lock orders concurrent launches, so a report opened while another is still starting the session waits for it (up to 40 seconds) instead of being refused as maintenance.

Independent XDG installations derive distinct service, socket and lock names
from their data directory. The default user's service name remains unchanged;
native QA retains the actual desktop runtime directory for systemd and Wayland.

The service uses `OOMPolicy=continue`, so the kernel ending one renderer or container for memory does not stop the whole session. It uses `KillMode=mixed`: a stop first reaches the broker, which closes its own prefix's wineserver. Remaining cgroup processes have a bounded final cleanup. This avoids sending SIGTERM to Wine's service processes before the server can coordinate shutdown; it does not affect servers for other prefixes.

Links that Desktop opens (browser sign-in, Help, a published report) go through Wine's `winebrowser` to `src/pbi_linux/open-url`, which starts the browser in a systemd scope of its own without the session's Wine and WebView2 variables; a browser started inside the session would share its memory limit and be killed when the last report closes. Wine's automatic menu builder is disabled during provisioning, maintenance and launch. The project owns its desktop entry and MIME definitions; it removes older Wine-generated launchers only when their `WINEPREFIX` points into the managed profile tree. Entries for other prefixes and shared MIME definitions are preserved. This prevents a discarded snapshot from remaining registered as a file handler. The entry's `StartupWMClass` matches Wine Wayland's `pbidesktop.exe` identity; [GNOME's window tracker](https://github.com/GNOME/gnome-shell/blob/main/src/shell-window-tracker.c) uses that metadata when matching a window to its application.

The runtime handles Wayland parenting, cursor/HKL fixes, native composition delivery, OLE DB conversions, PE backing and memory reporting. The production AppDomain manager enables culture/composition fixes without a diagnostic script interpreter. `PBIDesktop.exe.config` names it, so every Desktop start loads it, including a Desktop that Desktop starts itself; the CLR clears the `APPDOMAIN_MANAGER_*` variables after reading them, so the environment reached only the first one. Desktop's other .NET children (Mashup containers) run without it, as before. CDP, JS evaluation, credentials automation and screenshot capture remain developer-only tools.

The derived PE cache is tied to source content and device/inode/ctime/size/range. Stale cache is never used. When only the source's identity changed and its content hash still matches (btrfs numbers subvolumes at mount time, so the device number can change after a reboot), opening renames the verified cache files to the new identity instead of falling back; files of earlier identities are removed. A cache whose content no longer matches makes opening fall back to the Wine loader; explicit repair rebuilds the cache.

This loader cache is separate from a project's `.pbi/cache.abf`. The latter is an Analysis Services backup containing the model and locally loaded data. PBIP projects without it open their definitions without data and require a refresh. The launcher preserves project files, including an existing `cache.abf`; it neither generates nor removes that file. Synthetic project tests must distinguish an unprocessed model from a rendering failure.

Test probes can query the embedded Analysis Services model through AMO/ADOMD/XMLA. Processing a Desktop model externally is an unsupported diagnostic use, even though those protocols are public. The product does not silently substitute external TMSL refresh for the user's Refresh action.

The current recipe uses a pinned Microsoft fixed-version WebView2 CAB. It is extracted into each managed profile; the runtime manifest defines its version and binary hashes. A prefix policy and session environment select that folder, so a separate Evergreen update does not change the application browser. No Microsoft package is included in project artifacts.

Optional database providers are managed separately from the runtime and application
patches. `connector install` shares the maintenance lock, requires an idle managed
session, verifies pinned upstream archives in the user cache, and stages only the
provider directory/registration. A per-prefix manifest records its files. Existing
external registrations, including .NET machine.config registrations used by vendor
MSI packages, are reported without being overwritten. In-place maintenance
retains connector files; no complete snapshot is created to add a new provider.
No replacement database protocol or plugin runtime is introduced.
