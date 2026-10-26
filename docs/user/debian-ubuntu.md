# Experimental DEB: Debian and Ubuntu

> [!WARNING]
> **Experimental, not certified support.** The DEB enables Ubuntu 24.04/26.04 and
> Debian 13 on x86_64 with native Wayland, a systemd user session and an appropriate
> Vulkan driver. Fedora 44 remains the tested baseline. Other versions and derived
> distributions are not automatically accepted. Back up projects and start with
> copies. Microsoft does not support this community installation.

## Install

Use an experimental DEB supplied with its SHA-256 and corresponding project
sources, or [reproduce a post-merge build](../development/build.md#experimental-deb).
The candidate filename is `powerbi-linux_0.1.0-18~experimental2_amd64.deb`;
this guide does not imply that it has already been published on GitHub.

From the directory containing the package and checksum:

```bash
sha256sum -c powerbi-linux_0.1.0-18~experimental2_amd64.deb.sha256
sudo apt update
sudo apt install ./powerbi-linux_0.1.0-18~experimental2_amd64.deb
pbi-linux setup
```

APT resolves Linux dependencies; setup separately downloads and verifies the
pinned runtime, Power BI, .NET and WebView2 after terms acceptance. Installing the
DEB does not run Wine or download/install Microsoft software. Do not install a
system Wine package as a substitute for the project's managed runtime.

Allow approximately 9 GiB for Desktop plus components, downloads and working
files. Setup may take several minutes without new terminal output. The existing
[installation guide](install.md) describes setup, exact-version checks and recovery.

After setup, open **Power BI Desktop (Wine)** from the application menu, or:

```bash
pbi-linux open
pbi-linux open '/path/to/report.pbix'
pbi-linux doctor
```

The ordinary packaged launcher handles the installation: no QA wrapper or source
checkout is required. The doctor labels the distribution experimental; a passing
diagnostic does not certify every report, connector or desktop environment.
Default file associations remain opt-in (`pbi-linux setup --make-default`).

## User-controlled resource policy

The DEB does not choose a resource preset or change RAM, swap, CPU, browser heap
or renderer settings. The project's existing defaults are unchanged, and package
installation, upgrade and removal do not edit per-user settings. Users can choose
optional settings later through the existing [resource commands](resources.md).
No setting from the development VM is copied into the package.

## Update and remove

Repair and runtime update work **in place**, without copying the complete prefix
or retaining a rollback snapshot. Back up important files yourself: interruption
or failure can require repair or reinstallation. Old profile directories are
not automatically deleted. See the [maintenance policy](updates.md).

Install a newer DEB with `sudo apt install ./new-package.deb`. Updating the Linux
package does not reinstall or upgrade Desktop automatically; see [updates](updates.md).

```bash
sudo apt remove powerbi-linux
# Or remove the package and its system package configuration:
sudo apt purge powerbi-linux
```

Neither command deletes per-user prefixes, settings, credentials, caches or
reports. User-created menu entries from setup may remain; before removing the
package, `pbi-linux uninstall` removes that user integration while preserving
managed data. The separate `pbi-linux uninstall --purge` is destructive and is
not run by package hooks.

## Evidence and limits

Container tests cover package dependency resolution, CLI/menu/MIME metadata,
installation, reinstall, package upgrade, removal and purge. They do not cover a
Wayland session or Power BI UI. The Ubuntu 26.04 GNOME VM completed setup with
runtime 0.1.5 / Power BI 2.159.883.0; the user reported XLSX import into
`teste.pbix`, save and reopen. That report was not independently audited, used a
manually prepared QA installation, and does not certify the final DEB or Debian UI.
No real user report or account is included in package tests.
