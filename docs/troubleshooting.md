# Troubleshooting

Run `pbi-linux doctor --json`. It reports prerequisites, runtime/patch integrity and PE cache state. Logs are under `$XDG_STATE_HOME/powerbi-linux`; service status is available with `journalctl --user -u pbi-linux-session.service`.

- **No Wayland socket:** start from your Fedora Wayland desktop session. X11 is outside this release.
- **Missing ntlm_auth:** install `samba-winbind-clients` with DNF. This helper is needed for local Analysis Services authentication, independently of Microsoft account sign-in.
- **Unknown Power BI binaries:** use the installer pinned by the lock. Do not transfer binary patch offsets to a new release.
- **WebView2 version differs:** use `repair` to restore the fixed-version CAB matching the active runtime manifest. Launch never adopts an Evergreen update.
- **Stale PE backing:** close all windows and run `pbi-linux repair`. Open falls back safely but may consume more memory.
- **Maintenance blocked:** close all managed Power BI windows and let the Wine processes finish. Do not kill a Wine server belonging to another application.
- **General Get Data chooser blocked by OneLake sign-in:** for a local CSV, open a blank report, expand the **Get Data** menu on the Home ribbon and choose **Text/CSV** directly. This path imported the synthetic CSV without sign-in in the clean-prefix test. The general source chooser and Microsoft sign-in remain limited.
- **Large-report OOM or empty visuals after external refresh:** record the scenario and versions; these are release blockers. External TMSL refresh is a diagnostic tool, not a replacement for Desktop UI refresh.

Before attaching any log to a public issue, remove usernames, document paths, dataset names, SQL text, endpoints, tokens and credentials. Prefer a synthetic reproducer. Never attach a full prefix.
