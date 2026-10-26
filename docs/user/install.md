# Install Power BI Desktop on Fedora

For the experimental Ubuntu/Debian package, use the [DEB guide](debian-ubuntu.md).

> [!WARNING]
> **Beta software.** Read [known issues](known-issues.md), keep complete project backups and try copies of your reports first. Microsoft does not support this community installation.

## Before you start

You need **Fedora 44 x86_64**, a **Wayland** desktop session, a working systemd user session and a **Vulkan-capable graphics driver**. Install your GPU's appropriate Vulkan driver before continuing.

Allow approximately **9 GiB for Power BI**, plus its compatibility components, downloads and your reports. Maintenance needs room for downloads, extraction and derived cache, but does not clone the complete installation. Wine can access files available to your user; it is not a sandbox.

## Release availability

**RPM 18 is the current published preview** and enables automatic downloads. `pbi-linux setup` resolves the published Runtime 0.1.5 with its complete corresponding source and exact-archive evidence, plus the pinned Power BI installer from Microsoft. The runtime's two-hour soak remains pending; see [known issues](known-issues.md).

Earlier published previews (RPM 12–13) need explicit local inputs, and their runtime releases contain source recipes, not compiled packages. Installing such an RPM alone does not install Power BI Desktop.

The manual route remains available: see the [developer installation contract](../reference/installation-lifecycle.md#manual-setup) and [build instructions](../development/build.md). A source-recipe archive cannot be used as a runtime package.

## 1. Install the project tools

Download the binary `.noarch.rpm` from [Releases](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-18). The `.src.rpm` is for developers. Open a terminal in the download folder and run, replacing the filename with the package you downloaded:

```bash
sudo dnf install ./powerbi-linux-0.1.0-18.noarch.rpm
```

DNF installs the Linux dependencies. The project tools install Power BI separately for your user.

## 2. Run setup

The CLI provides this guided command:

```bash
pbi-linux setup
```

It shows the selected versions, asks you to accept the terms, then downloads and verifies the published runtime, Microsoft's Power BI installer, WebView2 and .NET, and installs everything. For unattended use after reviewing the terms, use `pbi-linux setup --accept-license`.

**You do not need to choose a runtime, WebView2 or .NET.** The runtime lets the Windows application run on Linux; WebView2 is Microsoft's embedded browser used by Desktop. Setup selects the tested versions and installs them privately.

### Already downloaded Power BI?

Microsoft's [official Power BI Desktop download page](https://www.microsoft.com/pt-br/download/details.aspx?id=58494) provides **`PBIDesktopSetup_x64.exe`**. To reuse that file with the guided release, run:

```bash
pbi-linux setup --installer '/path/to/PBIDesktopSetup_x64.exe'
```

**The EXE must match the project's validated version.** Microsoft may offer a newer version before this project supports it. The page offered 2.159.883.0 when checked on October 19, 2026; RPM 18 defaults to that version and also accepts **2.158.1177.0**. Setup checks the file and explains a mismatch; do not skip checksum checks or use untrusted mirrors. Version hashes and advanced local-file options are in the [input contract](../reference/installation-lifecycle.md#required-inputs).

## 3. Open your reports

After setup succeeds, open **Power BI Desktop (Wine)** from the application menu. For a report, use the file manager's **Open With** menu, or:

```bash
pbi-linux open
pbi-linux open '/path/to/report.pbix'
pbi-linux doctor
```

PBIX, PBIP and PBIR are supported file types. Default file associations are optional: add `--make-default` during setup if you want to change them. Preferences and credentials persist between launches.

## Recovery and removal

Close all Power BI windows before maintenance. Repeating an interrupted setup with the same inputs resumes completed stages. `pbi-linux repair` and `pbi-linux update` modify the existing prefix in place: no temporary full-prefix copy, retained snapshot or automatic rollback is provided. Back up important files yourself. Failure can leave a partially modified installation requiring repair or reinstallation. Updating the RPM alone does not upgrade Power BI Desktop.

`pbi-linux update` activates the published runtime. To use a local archive instead, pass `--runtime` together with `--runtime-sha256`.

`pbi-linux uninstall` removes desktop integration and preserves managed data. `pbi-linux uninstall --purge` deletes managed installations, caches and settings, including reports saved inside those directories. Remove the RPM separately through DNF.

Start with [troubleshooting](troubleshooting.md) when something fails. See [update policy](updates.md) or the [installation lifecycle](../reference/installation-lifecycle.md) for more detail.
