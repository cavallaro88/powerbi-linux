# Follow the GNOME color preference

With the updated project tools installed, select **System default** (Portuguese:
**Padrão do sistema**) in Desktop's theme menu. Desktop follows GNOME's light/dark
preference at startup and while open, with a polling interval of two seconds.
Explicit **Light** and **Dark** selections remain under Desktop's control.
Close every Desktop window and reopen after updating the tools so the broker
loads the new code. No profile repair or Wine runtime rebuild is required.
The integration is included in the local Fedora RPM **0.1.0-17**. See the
[local release notes](../releases/v0.1.0-17.md) for the update command.

## Implementation

The broker forwards `XDG_CURRENT_DESKTOP` into its systemd user service. On GNOME
sessions it reads `org.gnome.desktop.interface color-scheme` through `gsettings`:
`prefer-dark` maps to dark; `prefer-light` and `default` map to light. The bridge
does not write GNOME settings and skips other desktops to avoid reading stale
GNOME preferences. Missing schemas, unavailable session buses and unknown values
leave the last Windows preference intact.

The packaged `PowerBIThemeSync.cs` helper is compiled using the managed profile's
existing .NET compiler into a temporary private session directory. Before the
first report opens, it sets only the prefix-local DWORD `AppsUseLightTheme` under
`HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`, then sends
`WM_SETTINGCHANGE` with `ImmersiveColorSet` to the prefix's windows. Subsequent
changes run from a bounded worker; successful unchanged values are not written
again. Read and write operations have timeouts, failed updates are retried, and
the worker stops before the broker shuts down Wine. Initialization failure is
logged and does not block opening Desktop.

Desktop's original `ResizableFormWithCustomCaption.WndProc` recognizes this
notification. `ThemeService.OnWindowsThemeChanged` checks that the user's saved
selection is exactly `System` before reading `AppsUseLightTheme` and applying the
new theme. The bridge does not alter Desktop's saved selection, inject browser
styles, patch Microsoft assemblies or change report themes.

The optional integration needs `gsettings` (Fedora's `glib2`, present in GNOME),
a working user session bus and the already provisioned .NET compiler. Details
and failures appear as `GNOME theme:` lines in the managed `session.log`.

## Validation

Unit tests cover preference mapping, unavailable settings, desktop selection,
deduplication, retries, compiler failure, worker cleanup and forwarding the
desktop identity into systemd. Run:

```bash
python3 -m unittest discover -s tests/unit
```

The native test requires an explicit disposable copy of a populated profile under
the repository's `.local/` directory. Never point it at a working user profile:
it deliberately changes the copy's Windows theme preference.

```bash
python3 tools/test-theme-sync.py \
  --prefix .local/theme-sync/prefix \
  --runtime '/absolute/path/to/validated/runtime'
```

It exercises the Python startup/compiler path and sends real native messages to
a synthetic WinForms receiver that invokes the original Desktop `ThemeService`
with in-memory user settings. Thirteen assertions cover dark/light transitions,
delivery of `ImmersiveColorSet`, preservation of explicit Light/Dark and returning
to System. It does not open a report, save user settings or change GNOME's theme.
The test writes private evidence under `.local/theme-tests/`.

Validated locally with Desktop **2.159.883.0** and runtime **0.1.5**. This verifies
the native bridge and original theme service, not the complete visible Desktop,
Power Query, accessibility/high-contrast behavior or all supported versions.
Full visual validation remains a separate gate.

Reference: [GNOME color-scheme behavior](https://discourse.gnome.org/t/how-light-dark-style-works/17085).
