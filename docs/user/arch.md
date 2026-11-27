# Experimental package: Arch Linux and Omarchy

> [!WARNING]
> **Experimental, not certified support.** The recipe accepts Arch Linux and
> Omarchy on x86_64 with native Wayland, a systemd user session and an appropriate
> Vulkan driver. Arch is a rolling release: a result recorded for one package
> snapshot does not carry over to the next. Fedora 44 remains the tested baseline.
> Other Arch derivatives are not automatically accepted. Back up projects and
> start with copies. Microsoft does not support this community installation.

## What was tested

One host, on 2026-11-17: Omarchy 4.5.0 (kernel 7.2.15), Hyprland 0.56.2, two
monitors at scale 1 side by side, NVIDIA RTX 3060 (driver 615.78.08) with Intel
Iris Xe (Mesa 26.2.5), Python 3.14.8. Power BI Desktop 2.159.1231.0 installed,
opened a synthetic PBIP, refreshed through the UI, rendered the expected values
and saved. The [Hyprland reference](../reference/hyprland.md) records the scope,
the four Wine corrections this needed and what remains untested.

## Runtime requirement

The published runtime 0.1.6-beta.1 does **not** contain those corrections. With
it, Desktop starts but its window stays blank on a desktop with more than one
monitor. Until a runtime that includes them is published, build one from this
source tree and pass it to setup:

```bash
python3 runtime/build.py --runtime-version 0.1.7-local.1
```

The build needs Docker or Podman and takes roughly half an hour on a 20-thread
laptop; see [building](../development/build.md). It writes the archive and its
`.sha256` to `dist/`.

## Install

There is no published Arch package and no AUR entry. Build the package from a
checkout of this repository:

```bash
cd packaging/arch
makepkg -sif
```

The package version does not change with the checkout, so `-f` is needed: without
it, makepkg installs a package it built earlier instead of building the current
sources.

`makepkg` runs the unit tests, and pacman resolves the Linux dependencies
(`samba` supplies `ntlm_auth`; no Winbind daemon is needed). Installing the
package does not run Wine or download Microsoft software. Do not install a system
Wine package as a substitute for the project's managed runtime.

Then install Desktop for your user, with the runtime you built:

```bash
pbi-linux setup \
  --runtime '/path/to/dist/powerbi-linux-runtime-0.1.7-local.1-x86_64.tar.xz' \
  --runtime-sha256 'SHA256_FROM_THE_MATCHING_SHA256_FILE'
```

Setup shows the selected versions, asks you to accept the terms, then downloads
and verifies Power BI, .NET and WebView2. Allow approximately 9 GiB and several
minutes; the test host took 5 minutes 38 seconds with downloads included. The
[installation guide](install.md) describes setup, exact-version checks and
recovery.

After setup, open **Power BI Desktop (Wine)** from the application menu, or:

```bash
pbi-linux open
pbi-linux open '/path/to/report.pbix'
pbi-linux doctor
```

The doctor labels the distribution experimental; a passing diagnostic does not
certify every report, connector or desktop environment. Default file
associations remain opt-in (`pbi-linux setup --make-default`).

## Notes for this platform

- **Tiling.** Desktop opens as an ordinary tiled window. Tiled, floating,
  maximized and fullscreen states delivered frames on both monitors. How
  Hyprland places Desktop's own dialogs was not tested.
- **Theme.** On Hyprland, Desktop follows `org.gnome.desktop.interface
  color-scheme` (Omarchy sets it with every theme) once you select
  **System default** in Desktop's theme menu. See [theme scope](../reference/gnome-theme.md).
- **Window icon.** Hyprland 0.56.2 does not offer `xdg_toplevel_icon_manager_v1`,
  so Wine cannot set a per-window icon. The launcher icon is unaffected.
- **Log noise.** Arch's `samba` package ships no `/etc/samba/smb.conf`, so
  `ntlm_auth` prints `Can't load /etc/samba/smb.conf` into the session log. Local
  NTLM authentication still works.
- **Packet capture.** The runtime's `wpcap.so` imports `libpcap.so.0.8`; Arch
  ships `libpcap.so.1`. Desktop does not capture packets, so the package does not
  depend on libpcap.

## Update and remove

Repair and runtime update work **in place**, without copying the complete prefix
or retaining a rollback snapshot. Back up important files yourself. See the
[maintenance policy](updates.md).

After pulling new sources, rebuild and reinstall with `makepkg -sif` again, then
close Desktop and run `pbi-linux repair`. Updating the Linux package does not
reinstall or upgrade Desktop automatically. With a runtime you built yourself,
use `pbi-linux update --runtime <archive> --runtime-sha256 <sha>` for a new
build; a plain `pbi-linux update` refuses to replace it with the published
runtime unless you pass `--published`.

```bash
sudo pacman -R powerbi-linux
```

This does not delete per-user prefixes, settings, credentials, caches or
reports. Before removing the package, `pbi-linux uninstall` removes the user's
menu integration while preserving managed data. The separate
`pbi-linux uninstall --purge` is destructive and is not run by the package.
