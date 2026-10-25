# Updates and Wine tray notifications

The compatibility recipe pins Desktop, WebView2, Wine and the patches to tested
versions. Setup and repair disable Desktop's update notifications using Microsoft's
documented `DisableUpdateNotification` DWORD set to `1` under
`HKLM\Software\Microsoft\Microsoft Power BI Desktop`. Fresh installation also
passes `DISABLE_UPDATE_NOTIFICATION=1` to Microsoft's installer.

On the Fedora host the reported `explorer.exe` window corresponded to Wine's
standalone tray: a `Shell_TrayWnd` containing a `__wine_tray_icon`. Desktop includes
an update-notification icon; its original settings getter reads this registry
policy. The value was absent in the affected profile. This setting only suppresses
Desktop update notices. It does not disable all Wine tray icons or notifications.

Upgrading the RPM changes the recipe, not an existing profile. The affected host
received only this registry value locally, without another profile snapshot or
report changes. An already displayed icon can remain until Desktop exits. Check
the next normal launch for recurrence; registry/application-setting verification
alone does not certify that a current icon has disappeared.

The RPM updates the community launcher and recipes. `pbi-linux update` activates the published runtime; `--runtime` with `--runtime-sha256` activates a local archive instead. It is not a general Desktop updater. A newly released Microsoft installer must be validated with matching patches before the project can offer that Desktop version. There is currently no automatic validated-release notification or automatic Desktop upgrade channel.

The intended product flow is a Fedora notification when a tested project release
is available, followed by an explicit upgrade with a recoverable previous profile.
This notification service remains backlog. Hiding upstream notices does not make
an older Desktop version current or extend Microsoft's support policy.

To restore upstream update notices in a managed profile, set the same DWORD to
`0` using that profile's Wine `reg.exe` and restart Desktop. Setup/repair restores
the project's default of `1`. Do not run a Windows updater in another Wine prefix
or replace the pinned Desktop binaries in place.

Reference: [Microsoft installation parameters and notification policy](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop#disable-notifications).
