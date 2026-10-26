# Installation and lifecycle

The tested target is Fedora 44 x86_64 on native Wayland; [Ubuntu/Debian DEBs](../user/debian-ubuntu.md) are experimental. Install the RPM with DNF or the DEB with APT so dependencies are resolved. `samba-winbind-clients` on Fedora and `winbind` on Debian/Ubuntu supply the local SSPI/NTLM helper; a Winbind daemon is not needed. Install the appropriate Vulkan driver for your GPU separately.

The runtime is built against glibc 2.39 in an Ubuntu build container to provide a conservative ABI baseline. This build choice alone does not certify Ubuntu compatibility.

## Required inputs

- Project runtime archive and its SHA-256, produced together by `runtime/build.py`.
- Microsoft Power BI Desktop x64 installer matching a registered exact recipe.
  The source-tree default is 2.159.883.0 in `runtime/sources.lock.json`;
  2.158.1177.0 remains accepted for local inputs and existing profiles. RPM 18
  accepts both exact installers. See the [current installation status](../user/install.md).
- Microsoft fixed WebView2 x64 **154.0.4258.62 CAB**, automatically downloaded using the official URL and checksum in the lock. Use `--webview-runtime` to supply the same CAB offline. No Evergreen installer is needed as a project setup input.
- .NET 4.0 prerequisite and .NET 4.8 installers, optionally passed with `--dotnet40-installer` and `--dotnet-installer`; otherwise downloaded from the official link and checked against the lock.

Download Microsoft installers from Microsoft. Consult their terms before using `--accept-license`, which acknowledges local installation and compatibility modifications. These tools do not bypass account, service or subscription requirements.

## Manual setup

Published releases before RPM 18 required an exact local runtime archive and its
matching checksum; RPM 18 resolves the published runtime automatically. The
manual route remains available and accepts both guarded installers. Installer identities are:

| Power BI | EXE SHA-256 |
|---|---|
| 2.158.1177.0 | `4924187834d34605c3046f01b876fba6a2cf36f864c36d16fd52c3f17a21009c` |
| 2.159.883.0 | `5412131d1f5d535e42358cb6d496703c3c0cdf9267779ac9220171f58ce20cdd` |

Microsoft's [official download page](https://www.microsoft.com/pt-br/download/details.aspx?id=58494)
may no longer offer the older validated installer. If you do not already have its
exact official EXE, use the automatic route or supply the current validated
installer. Do not substitute untrusted mirrors or bypass the recipe guards.

```bash
pbi-linux setup \
  --runtime '/path/to/powerbi-linux-runtime-VERSION-x86_64.tar.xz' \
  --runtime-sha256 'SHA256_FROM_THE_MATCHING_BUILD' \
  --installer '/path/to/PBIDesktopSetup_x64.exe' \
  --accept-license
```

Replace the paths and checksum with the actual built/published files. Read the
[licensing notes](legal.md) and Microsoft terms before using `--accept-license`.
Local prerequisite flags do not create a fully offline mode: other pinned
components still need network access or a complete verified download cache.

## State

| Location | Contents |
|---|---|
| `$XDG_DATA_HOME/powerbi-linux` | Versioned runtimes, managed profile and active metadata; legacy directories may remain |
| `$XDG_CONFIG_HOME/powerbi-linux` | Settings and previous desktop associations |
| `$XDG_CACHE_HOME/powerbi-linux` | Verified downloads and derived PE backing |
| `$XDG_STATE_HOME/powerbi-linux` | Setup, maintenance and session logs; incomplete-maintenance marker |
| `$XDG_RUNTIME_DIR/powerbi-linux` | Session socket and maintenance lock |

Defaults follow the standard `~/.local/share`, `~/.config`, `~/.cache` and `~/.local/state` locations. State directories and socket are private to the user. Power BI is not a sandbox: Wine can access files available to the user.

The default installation retains `powerbi-linux-session.service` and the session
directory above. Separate XDG data directories use an installation-derived suffix
for their service, socket and locks. Native QA keeps the actual desktop
`XDG_RUNTIME_DIR` so Wayland and systemd IPC remain reachable.

The validated profile occupies approximately 9 GiB, before the runtime, verified downloads, derived cache and your reports. Repair/update does not copy the complete prefix or retain a previous generation. Downloads, new versioned runtimes and ordinary extraction/cache still need free space. Check the filesystem containing your XDG directories before maintenance. A small package download does not represent the size of the installed Microsoft application.

## Maintenance

Close all managed windows before maintenance. Setup can resume an interrupted stage using the same inputs. Repair and runtime update modify the active prefix **in place**, without temporary full-prefix copies, retained snapshots or automatic rollback. A warning is printed before mutation. Back up important files yourself: failure or interruption may leave the installation partially modified and require repair, reinstallation or restoration of your own backup.

Before mutation, a private `maintenance.json` marker is written under the state
directory. It remains after a failure or abrupt process exit; launch is blocked
and doctor reports incomplete maintenance. Repeat the verified update or run
repair. Successful maintenance or a completed fresh reinstall clears the marker. Activation metadata is
updated after the work completes, but an unchanged pointer is **not** evidence
that the in-place files are unchanged. Checksums, recipe guards, locks and idle
checks remain enforced.

To upgrade the CLI, run `sudo dnf upgrade ./powerbi-linux-0.1.0-18.noarch.rpm`
and `pbi-linux doctor`. If the HTML/email dialog checks report outdated patches,
close Desktop and run `pbi-linux repair`, then check again. Repair applies the
new recipe to the existing profile without making a snapshot.
Already-patched profiles passing doctor do not need another repair. Options requires runtime 0.1.2 as well as the RPM 9 UI recipe; see
[Options update instructions](options-dialog.md). Older runtime archives retain
their own documented scope. See [sign-in status](../user/sign-in.md)
for the distinction between fixing Continue and completing account authentication.

```bash
pbi-linux repair
pbi-linux update --runtime runtime.tar.xz --runtime-sha256 '<checksum>'

pbi-linux uninstall
```

`update` updates the **project runtime** and provisions the fixed WebView2 recipe recorded by that runtime. It does not upgrade Power BI Desktop or .NET; those require a separately validated installation recipe. Wine Gecko x86/x64 is also downloaded from WineHQ with hashes pinned from the Wine source. The project never schedules automatic updates. The fixed WebView2 package is selected by a per-prefix `BrowserExecutableFolder` policy and checked against the activated runtime manifest. An Evergreen copy or Microsoft updater created by another installer does not select a different browser for this application.

The legacy `rollback` command returns an explanatory error and changes nothing.
New activation/maintenance no longer records `previous.json`. Legacy metadata is
discarded when maintaining/activating an installation, but existing snapshot
directories are not deleted automatically: they can contain user files or be the
active installation despite their name. Old runtime directories and downloads
are not automatically purged by this change either.

`uninstall` removes per-user integration and preserves state. When the RPM's system desktop entry exists, a per-user `Hidden=true` entry masks it so it does not reappear in the menu or Open With. A later `repair` restores the menu and Open With entries without changing explicit default applications. `uninstall --purge` explicitly deletes managed profiles, runtime, cache and settings. It does not uninstall the RPM; use DNF for that. Project files saved outside managed directories are never deleted. Files saved inside a managed prefix are part of the purge.

RPM 0.1.0-2 defaults to no project RAM/swap limits or CPU quota, automatic WebView2 heap and standard browser settings. `pbi-linux profile` shows the policy; `pbi-linux profile unlimited` resets it. Optional flags include `--memory-max`, `--swap-max`, `--cpu-quota`, `--webview-heap`, `--renderer-process-limit` and `--browser-mode`. The older `normal` (6G/2G) and `large` (10G/4G) profiles remain explicit economy presets. Changes apply to the next session after closing all windows. Read [resource settings](../user/resources.md) for examples and migration.

Setup/repair with RPM 6 enables **Use my default web browser** for authentication.
For an existing profile, enable it under **File → Options and settings → Options
→ Global → Security → Authentication Browser**, then restart Desktop. A repair
is unnecessary merely to change this preference. The email patch check
in doctor does not certify browser selection or a signed-in account. See
[sign-in](../user/sign-in.md) for the tested scope.

Database providers are optional and separate from Microsoft account sign-in.
For MySQL, close Desktop and use `pbi-linux connector install mysql --accept-license`
after reading the [connector instructions and licenses](../user/connectors.md). Status and
doctor verify the managed files. RPM 7 includes this CLI and the source-list
layout correction. An existing external provider is detected and not overwritten.

RPM 7 setup/repair also disables Desktop's update notifications using Microsoft's
documented option. An RPM-only upgrade does not change that existing profile
setting. See [update policy](../user/updates.md); the current runtime update command does
not update Desktop, and a Fedora notifier for validated releases remains planned.

RPM 11 adds the [cached-model recipe](model-cache.md) and [original local app
icon](app-icon.md). Its `cache-restore` doctor check distinguishes an older profile
from an updated one. An RPM upgrade updates CLI/source recipes, not existing
Windows assemblies. Profiles already updated by validated local maintenance do
not need another repair; the original icon refreshes on the next managed launch.
