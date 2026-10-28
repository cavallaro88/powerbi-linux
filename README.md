<p align="center">
  <img src="packaging/powerbi-linux.svg" alt="Power BI Linux project icon" width="112">
</p>

# Power BI Linux

[![Product checks](https://github.com/cavallaro88/powerbi-linux/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/cavallaro88/powerbi-linux/actions/workflows/checks.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)
[![Platform: Fedora 44](https://img.shields.io/badge/platform-Fedora%2044-51a2da)](docs/user/install.md)
![Architecture: x86_64](https://img.shields.io/badge/arch-x86__64-informational)
![Display: Wayland](https://img.shields.io/badge/display-Wayland-yellow)
[![Status: beta](https://img.shields.io/badge/status-beta-orange)](docs/user/known-issues.md)

Run Microsoft Power BI Desktop on Fedora, with Linux desktop integration and a managed installation. Experimental DEB packaging is available for [Ubuntu and Debian](docs/user/debian-ubuntu.md).

> [!WARNING]
> **Beta software.** Features can fail, and compatibility depends on the exact Power BI and runtime versions. Keep a private backup of your complete project and work on copies first. Read [known issues and unsupported features](docs/user/known-issues.md) before installing.
>
> This is an independent community project, with no Microsoft affiliation, endorsement or official support.

## What is Power BI Linux?

Power BI Linux prepares and runs the Windows edition of Power BI Desktop on Linux. It manages a dedicated per-user installation, a patched Wine/DXVK compatibility runtime, and the Microsoft components Desktop needs. Your reports remain Power BI reports, and Microsoft account and service requirements still apply.

The project combines installation and recovery tools with targeted compatibility fixes for Desktop's windows, dialogs, embedded browser and model handling. The runtime builds on **Wine**, **DXVK** and reviewed components from [Neutron's Wine runtime](https://github.com/Nico-LaFoucate/neutron-wine). See the [technical patch inventory](docs/reference/patches.md) for attribution and scope.

## What you can do

- **Open reports from your desktop:** launch PBIX, PBIP and PBIR files through the file manager or application menu.
- **Import and edit data:** CSV import, report visuals, save/reopen and a synthetic 158-table refresh have passed recorded tests.
- **Use repaired dialogs and controls:** compatibility work covers save confirmation, Options, credentials, permissions, and font/size selectors.
- **Maintain the existing installation:** interrupted setup can resume; repair and runtime updates work in place without snapshots or automatic rollback. Back up important files yourself before maintenance.
- **Sign in through your browser:** authentication and persistence have passed on the test host; a real publication was confirmed in a test workspace.
- **Add optional providers:** MySQL has a managed installation recipe. Other connector scenarios have separate experimental status.

These results apply to their recorded versions and test cases. They do not certify every report, connector or newer release. The [short compatibility guide](docs/user/known-issues.md) explains the practical limits.

## Install

**Ubuntu / Debian (experimental):** use the [DEB installation guide](docs/user/debian-ubuntu.md).
This does not expand Fedora's validation claims to other distributions or apply
any resource preset. The instructions below are for the published Fedora RPM.

Download the recommended **binary RPM** from [Releases](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-19), then install it using DNF. The `.src.rpm` is for developers.

```bash
sudo dnf install ./powerbi-linux-0.1.0-19.fc44.noarch.rpm
```

> [!IMPORTANT]
> **`pbi-linux setup` installs the rest.** It downloads and verifies the published runtime (with its matching source and evidence), WebView2 and .NET, and the pinned Power BI installer from Microsoft. You accept the terms and wait; installing the RPM alone does not install Power BI Desktop.

Microsoft's [official Power BI Desktop download](https://www.microsoft.com/pt-br/download/details.aspx?id=58494) provides `PBIDesktopSetup_x64.exe`. **Its current version can differ from the release's validated version.** RPM 18 defaults to **2.159.883.0** and also accepts **2.158.1177.0**; other installer hashes are rejected. [Native validation and release readiness](docs/reference/powerbi-2.159.md) are tracked separately. WebView2 and .NET are prepared by setup; you do not need to choose or install those components yourself.

### How long does setup take?

Allow **several minutes, plus download time**. One complete local setup of Power BI
2.159.883.0 with runtime 0.1.5 took about **6 minutes 16 seconds** (375.97 seconds
recorded) with prerequisite
downloads already cached. This is a reference measurement, not a time limit;
slower hardware, storage or network connections can take longer.

**The .NET and Power BI installers run silently and can spend several minutes
without printing anything in the terminal.** Silence alone does not mean setup
has frozen. The CLI warns before these stages; wait for completion or an explicit
error rather than closing the terminal just because no new lines appear.

## Everyday use

After completing setup, open **Power BI Desktop (Wine)** from the application menu, or use **Open With** in your file manager.

```bash
pbi-linux open
pbi-linux open '/path/to/report.pbix'
pbi-linux doctor
```

Preferences and credentials persist between launches. Default file associations are optional. Resource limits are also optional; see [resource settings](docs/user/resources.md).

For failures, start with [troubleshooting](docs/user/troubleshooting.md). Report reproducible problems through [Issues](https://github.com/cavallaro88/powerbi-linux/issues/new/choose), with sanitized `pbi-linux doctor --json` output and a synthetic example. Keep customer reports, credentials and populated installations private.

## Documentation and contributing

- [User guides](docs/user/README.md): installation, known issues, troubleshooting and optional settings.
- [Development](docs/development/README.md): builds, architecture, testing and roadmap.
- [Technical reference](docs/reference/README.md): investigations, compatibility evidence and patch details.
- [Release history](docs/releases.md) and [changelog](CHANGELOG.md).

Contributions follow [CONTRIBUTING](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md) and [security policy](SECURITY.md). The CI badge covers automated product checks; graphical compatibility requires separate native validation.

## License and credits

Independent project tools are **GPL-3.0-or-later**. Wine/Neutron-derived components retain **LGPL-2.1-or-later**; DXVK and other dependencies retain their own licenses. See [LICENSE](LICENSE), [third-party notices](LICENSES/) and [licensing details](docs/reference/legal.md).

Power BI and Microsoft product names and artwork belong to Microsoft. Microsoft software is downloaded separately from its official sources. The original application icon is extracted only for your local installation; the repository uses the project's own fallback icon.
