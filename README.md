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

Run Microsoft Power BI Desktop on Fedora, with Linux desktop integration and a managed installation.

> [!WARNING]
> **Beta software.** Features can fail, and compatibility depends on the exact Power BI and runtime versions. Keep a private backup of your complete project and work on copies first. Read [known issues and unsupported features](docs/user/known-issues.md) before installing.
>
> Tested target: **Fedora 44, x86_64, native Wayland**, a systemd user session and a Vulkan-capable GPU/driver. This is an independent community project, with no Microsoft affiliation, endorsement or official support.

## What is Power BI Linux?

Power BI Linux prepares and runs the Windows edition of Power BI Desktop on Linux. It manages a dedicated per-user installation, a patched Wine/DXVK compatibility runtime, and the Microsoft components Desktop needs. Your reports remain Power BI reports, and Microsoft account and service requirements still apply.

Our work combines installation and recovery tools with targeted compatibility fixes for Desktop's windows, dialogs, embedded browser and model handling. The runtime builds on **Wine**, **DXVK** and reviewed components from [Neutron's Wine runtime](https://github.com/Nico-LaFoucate/neutron-wine). See the [technical patch inventory](docs/reference/patches.md) for attribution and scope.

## What you can do

- **Open reports from your desktop:** launch PBIX, PBIP and PBIR files through the file manager or application menu.
- **Import and edit data:** CSV import, report visuals, save/reopen and a synthetic 158-table refresh have passed recorded tests.
- **Use repaired dialogs and controls:** compatibility work covers save confirmation, Options, credentials, permissions, and font/size selectors.
- **Keep your installation recoverable:** interrupted setup can resume; repair and runtime updates use separate profile generations with rollback.
- **Sign in through your browser:** authentication and persistence have passed on the test host; a real publication was confirmed in a test workspace.
- **Add optional providers:** MySQL has a managed installation recipe. Other connector scenarios have separate experimental status.

These results apply to their recorded versions and test cases. They do not certify every report, connector or newer release. The [short compatibility guide](docs/user/known-issues.md) explains the practical limits.

## Install

Download the recommended **binary RPM** from [Releases](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-13), then install it using DNF. The `.src.rpm` is for developers.

```bash
sudo dnf install ./powerbi-linux-0.1.0-13.noarch.rpm
```

> [!IMPORTANT]
> **The published RPM 13 still requires manual setup inputs.** Published runtime releases contain source recipes, not ready-to-use runtime binaries. Installing the RPM alone does not install Power BI Desktop.
>
> The setup improvements in this source tree prepare a guided installation with verified automatic downloads. It remains gated on a validated, published runtime and matching Power BI recipe. See the [installation guide](docs/user/install.md) for the currently usable manual route and release readiness.

Microsoft's [official Power BI Desktop download](https://www.microsoft.com/pt-br/download/details.aspx?id=58494) provides `PBIDesktopSetup_x64.exe`. **Its current version can differ from the release's validated version.** Published RPM 13 accepts **2.158.1177.0**. The local RPM 14 candidate adds a guarded **2.159.883.0** recipe; its [native validation and release readiness](docs/reference/powerbi-2.159.md) are tracked separately. WebView2 and .NET are prepared by setup; you do not need to choose or install those components yourself.

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
