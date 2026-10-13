# Troubleshooting

Run `pbi-linux doctor --json`. It reports prerequisites, runtime/patch integrity and PE cache state. Logs are under `$XDG_STATE_HOME/powerbi-linux`; service status is available with `journalctl --user -u pbi-linux-session.service`.

- **No Wayland socket:** start from your Fedora Wayland desktop session. X11 is outside this release.
- **Missing ntlm_auth:** install `samba-winbind-clients` with DNF. This helper is needed for local Analysis Services authentication, independently of Microsoft account sign-in.
- **Unknown Power BI binaries:** use the installer pinned by the lock. Do not transfer binary patch offsets to a new release.
- **WebView2 version differs:** use `repair` to restore the fixed-version CAB matching the active runtime manifest. Launch never adopts an Evergreen update.
- **Stale PE backing:** close all windows and run `pbi-linux repair`. Open falls back safely but may consume more memory.
- **Maintenance blocked:** close all managed Power BI windows and let the Wine processes finish. Do not kill a Wine server belonging to another application.
- **An explorer.exe window advertises a Power BI update:** Wine can display a standalone Windows tray window. Setup/repair disables Desktop's upstream update notices with Microsoft's own policy; an already displayed icon may persist until exit. See [update policy](updates.md) for existing profiles and the separate validated-release backlog.
- **General Get Data chooser blocked by OneLake sign-in:** for a local CSV, open a blank report, expand the **Get Data** menu on the Home ribbon and choose **Text/CSV** directly. This path imported the synthetic CSV without sign-in in the clean-prefix test. Microsoft browser sign-in and account persistence after restart passed; the general source chooser has not been revalidated after that fix.
- **Large-report OOM or empty visuals after external refresh:** record the scenario and versions; these are release blockers. External TMSL refresh is a diagnostic tool, not a replacement for Desktop UI refresh.

Before attaching any log to a public issue, remove usernames, document paths, dataset names, SQL text, endpoints, tokens and credentials. Prefer a synthetic reproducer. Never attach a full prefix.

- **Cannot find provider `MySql.Data.MySqlClient`:** close Desktop and install the
  optional driver with `pbi-linux connector install mysql --accept-license` after
  reading its upstream licenses. Check `pbi-linux connector status mysql` and
  `pbi-linux doctor`. A Fedora MySQL package or another Wine prefix does not supply
  this .NET provider to Desktop. Installation does not change passwords or TLS.
- **Data source settings list is blank:** older HTML recipes initialized its
  virtualized list before the dialog had a usable height. Upgrade to RPM 7 and
  inspect doctor. An outdated profile requires repair with Desktop closed; a
  locally patched profile already passing doctor does not need another snapshot.
  This visual issue is separate from provider installation. Do not clear all
  permissions or remove `.pbi/cache.abf` to repair the list.
- **Sources appear but clicks initially do nothing or the cursor disappears:**
  a user observed interaction recover after an estimated 10–60 seconds; the delay
  was not instrumentally measured and its cause is unknown. Cursor-image errors were present in the session log, without
  establishing the cause of the click delay. This is separate from the blank-list
  correction. Record time from opening to first successful interaction, whether
  it repeats on a second opening, and whether keyboard focus responds. Avoid
  repeatedly submitting permission changes while response is delayed.
- **Privacy Level or OK does not react in Edit Permissions:** a separate Wayland
  correction requires runtime 0.1.1; the independent serializer correction requires
  the RPM 8 HTML recipe applied to the profile. Synthetic compositor-input
  OK/Cancel/reopen passed. A focus-only workaround did not fix the user's case.
  Do not repeatedly submit settings, clear permissions or remove caches. The
  nested None/Delete Permissions path remains unresolved.
  See [validation and installation](permissions-wayland.md).
- **Provider loads but a database connection fails:** distinguish server address,
  port, credentials, authorization, version compatibility and TLS. The loopback
  fixture passed with explicitly unencrypted local transport; this does not
  validate production TLS or justify disabling encryption on a real source.
- **MySQL refresh reports `Invalid handle`:** a confirmed case failed in
  `WindowsIdentity.Impersonate` because Wine's explicit Windows logon returned a
  placeholder token. For MySQL-native credentials, edit only the affected source
  and choose **Database**, entering the database username/password there. Check
  the exception stack and the affected source's current credential type before
  applying this diagnosis. A later screenshot already showed Database; the trace
  alone does not identify which source or prior state used impersonation. See
  [credential mode and scope](connectors.md#windows-credential-override-invalid-handle).

- **Options opens clipped, without its navigation or footer:** runtime 0.1.2 fixes
  a signed Int64 conversion that interrupts HTML initialization; the RPM 9 recipe
  also bounds its scroll pane. Both per-user runtime and UI recipe must be applied.
  See [Options installation and evidence](options-dialog.md). Changing the report
  cache or RAM limits does not address this initialization failure.

- **Resize cursor stays over ordinary controls:** runtime 0.1.3 has a scoped
  correction for shared system cursor resources owned by another process. The
  earlier fallback could retain the last valid resize image. A component and
  GNOME compositor-motion reproducer passed; actual Power BI restart validation
  is separate. See [cursor evidence](cursor.md).

- **A PBIP fails with an Analysis Services unexpected exception when ABF exists:**
  retain the cache and project definitions. Image loading may succeed while the
  later metadata update fails. RPM 11 handles the reproduced extensive multiline
  linguistic JSON case without deleting data or bypassing model synchronization.
  Check `cache-restore` in doctor; see [diagnosis and recovery](model-cache.md).
  Other causes require their own evidence.
- **The launcher still shows a generic icon:** the original PNG is extracted
  after Desktop provisioning, on integration and managed launch with RPM 11.
  Check the per-user desktop entry and application availability; see
  [original app icon](app-icon.md). The generic packaged icon is the pre-setup fallback.
