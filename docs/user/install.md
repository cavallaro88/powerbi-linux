# Install Power BI Desktop on Fedora

> [!WARNING]
> **Beta software.** Read [known issues](known-issues.md), keep complete project backups and try copies of your reports first. Microsoft does not support this community installation.

## Before you start

You need **Fedora 44 x86_64**, a **Wayland** desktop session, a working systemd user session and a **Vulkan-capable graphics driver**. Install your GPU's appropriate Vulkan driver before continuing.

Allow approximately **9 GiB for Power BI**, plus its compatibility components, downloads and your reports. Repairs may need space for another complete installation. Wine can access files available to your user; it is not a sandbox.

## Release availability

**The guided installer is being prepared locally.** The repository remains private until its owner chooses to make it public. Automatic setup stays disabled until a matching, validated runtime and its sources are available as public release downloads.

The currently published preview is **RPM 13**, which requires manual inputs and Power BI **2.158.1177.0**. Its runtime releases contain source recipes, not compiled packages. Installing that RPM alone does not install Power BI Desktop. The local RPM 14 candidate adds **2.159.883.0** support; see the [candidate status](../reference/powerbi-2.159.md).

If you are testing the existing manual route, use the [developer installation contract](../reference/installation-lifecycle.md#manual-setup) and [build instructions](../development/build.md). A source-recipe archive cannot be used as a runtime package.

## 1. Install the project tools

Download the binary `.noarch.rpm` from [Releases](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-13). The `.src.rpm` is for developers. Open a terminal in the download folder and run, replacing the filename with the package you downloaded:

```bash
sudo dnf install ./powerbi-linux-0.1.0-13.noarch.rpm
```

DNF installs the Linux dependencies. The project tools install Power BI separately for your user.

## 2. Run setup

The new CLI provides this guided command:

```bash
pbi-linux setup
```

**Until its release downloads are ready, it explains what is unavailable and exits before installation.** Once enabled, it shows the selected versions, asks you to accept the terms, and downloads and prepares the required components automatically. For unattended use after reviewing the terms, use `pbi-linux setup --accept-license`.

**You do not need to choose a runtime, WebView2 or .NET.** The runtime lets the Windows application run on Linux; WebView2 is Microsoft's embedded browser used by Desktop. Setup selects the tested versions and installs them privately.

### Already downloaded Power BI?

Microsoft's [official Power BI Desktop download page](https://www.microsoft.com/pt-br/download/details.aspx?id=58494) provides **`PBIDesktopSetup_x64.exe`**. To reuse that file with the guided release, run:

```bash
pbi-linux setup --installer '/path/to/PBIDesktopSetup_x64.exe'
```

**The EXE must match the project's validated version.** Microsoft may offer a newer version before this project supports it. The page offered 2.159.883.0 when checked on October 19, 2026; RPM 13 accepts only 2.158.1177.0. The local RPM 14 candidate recognizes both exact installers. Setup checks the file and explains a mismatch; do not skip checksum checks or use untrusted mirrors. Version hashes and advanced local-file options are in the [input contract](../reference/installation-lifecycle.md#required-inputs).

## 3. Open your reports

After setup succeeds, open **Power BI Desktop (Wine)** from the application menu. For a report, use the file manager's **Open With** menu, or:

```bash
pbi-linux open
pbi-linux open '/path/to/report.pbix'
pbi-linux doctor
```

PBIX, PBIP and PBIR are supported file types. Default file associations are optional: add `--make-default` during setup if you want to change them. Preferences and credentials persist between launches.

## Recovery and removal

Close all Power BI windows before maintenance. Repeating an interrupted setup with the same inputs resumes completed stages. `pbi-linux repair` repairs a separate copy; `pbi-linux rollback` restores the previous installation. Updating the RPM alone does not upgrade Power BI Desktop.

`pbi-linux uninstall` removes desktop integration and preserves managed data. `pbi-linux uninstall --purge` deletes managed installations, caches and settings, including reports saved inside those directories. Remove the RPM separately through DNF.

Start with [troubleshooting](troubleshooting.md) when something fails. See [update policy](updates.md) or the [installation lifecycle](../reference/installation-lifecycle.md) for more detail.
