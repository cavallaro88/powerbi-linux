# Known issues and support limits

> [!WARNING]
> **Power BI Linux is beta software.** Keep a private backup of your complete project and work with copies first. For PBIP projects, include `.pbi/cache.abf`: a normal Git checkout excludes imported cached data. See [cache recovery](../reference/model-cache.md).

The tested platform is **Fedora 44 x86_64, native Wayland**, with a systemd user session and Vulkan graphics. A local [Pop!_OS 24.04 DEB](popos.md) also accepts Ubuntu 24.04 as an experimental base; COSMIC graphics have not been validated. Other distributions and X11 are outside the current support target. Other Fedora versions are experimental.

## What has worked in recorded tests

Opening PBIX/PBIP/PBIR from the desktop; CSV import, visuals and save/reopen; a synthetic 158-table refresh and two-hour session; browser sign-in and persistence; and a confirmed publication to a test workspace. These are version-specific results, not a guarantee for every report. The [detailed compatibility matrix](../reference/compatibility.md) records the scope and versions.

## What may affect your work

| Feature | Status | Impact and next step |
|---|---|---|
| Installing from current published releases | Partial | RPM 13 needs explicit setup inputs. Runtime downloads are source recipes only; a recipe archive cannot be used as a runtime. See [installation](install.md). |
| New Power BI Desktop versions | Not validated as a release | Published RPM 13 targets 2.158.1177.0. Local candidates from RPM 14 onward add guarded 2.159.883.0 patches; complete native release validation is still pending. Other installer hashes are rejected. Do not bypass checksum checks. |
| Embedded Windows authentication broker | Known failure | Use the default system browser for Microsoft sign-in. See [sign-in](sign-in.md). |
| MySQL with explicit Windows username/password impersonation | Known failure | Wine's placeholder Windows token fails this flow. Database-password authentication passed in a local fixture; real-server TLS remains unvalidated. See [connectors](connectors.md). |
| General Get Data / OneLake chooser | Not validated | Direct Text/CSV import passed. The general chooser was blocked by sign-in and has not been revalidated after authentication. Use the direct CSV entry for the tested CSV path. |
| Data source settings list | Partial | Sources can appear before clicks respond; a delay of roughly 10–60 seconds was observed. The cause remains unresolved. See [source-list evidence](../reference/legacy-html.md). |
| Options window size and text selection | Local correction | RPM 15 / DEB `0.1.0-15pop1` adapt navigation/content to the window, preserve editable text and advertise native resizing. Close Desktop and run `pbi-linux repair` after installing the update. See [scope and validation](../reference/options-dialog.md#october-21-options-resizing-and-selection). |
| Intermittent small white window on hover | Local correction | RPM 16 / DEB `0.1.0-16pop1` show browser HTML/SVG title tips inside WebView, including same-origin visual frames. Rich data tooltips retain their original handlers; full native visual/report-page validation remains pending. Install the package with Desktop closed, then run `pbi-linux repair`. See [scope and limits](../reference/intermittent-popup.md). |
| GNOME light/dark preference | Local correction | RPM 17 follows GNOME's color preference while Desktop's theme selection is **System default**; explicit Light/Dark selections stay under Desktop's control. Restart Desktop after updating the RPM; no repair is required. Other desktop environments are not covered. See [scope and limits](../reference/gnome-theme.md). |
| Nested permission confirmations | Not validated | Main Edit Permissions OK/Cancel has scoped tests. Nested None/Delete confirmations still need validation. See [permissions](../reference/permissions-wayland.md). |
| Redshift and external Windows ODBC installers | Partial / experimental | Controlled authentication, metadata and limited Import/Save/reopen passed. A general managed installation flow, other authentication modes and broader typed-data/TLS coverage remain pending. See [Redshift](../reference/redshift.md). |
| Refresh cancellation | Partial | Synthetic cancellation and user tests passed, but the originally reported freeze was not reproduced. Server-side cancellation and post-cancel data state are not generally certified. See [cancellation](../reference/refresh-cancellation.md). |
| Complex enterprise reports | Not validated | A reported original thin-report refresh ran out of renderer memory. The synthetic large-model pass does not cover every model's complexity. Keep originals and verify results independently. |
| Visuals after external diagnostic refresh | Known failure / unsupported flow | External processing can commit data without notifying visuals. Use Desktop's normal refresh flow; external TMSL processing is diagnostic only. |
| PaperWM maximize/restore and display variations | Partial | Normal resizing has scoped candidate evidence. Maximize/restore divergence, multiple monitors and additional display scales need broader validation. See [window frame](../reference/window-frame.md) and [PaperWM](../reference/paperwm.md). |
| Cloud publishing | Partial | A real publication was confirmed. Broader account/workspace flows and a new cloud cycle after the Store-prompt correction remain unvalidated. See [publishing](publishing.md). |

**Known failure** means a problem was reproduced or reported in the recorded scope. **Partial** means only part of the flow has evidence or a workaround exists. **Not validated** means support has not been established; it does not claim the feature always fails.

## Before reporting a problem

Run `pbi-linux doctor` and consult [troubleshooting](troubleshooting.md). Include versions, sanitized diagnostic output and a synthetic reproduction in your [bug report](https://github.com/cavallaro88/powerbi-linux/issues/new/choose). Do not upload reports, model caches, credentials or populated installations.
