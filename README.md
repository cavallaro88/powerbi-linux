# Power BI Desktop on Fedora

Community compatibility tools for Power BI Desktop using patched Wine, DXVK and native Wayland. **Validated development preview 0.1.0: compatibility is scoped to the documented synthetic workloads.**

An installation created from official installers opened PBIX/PBIP/PBIR through the Fedora desktop, imported a local CSV, displayed the expected values and preserved them after save/reopen. A synthetic 158-table model with 156 relationships also passed UI refresh and independent data checks. A two-hour session passed with periodic visual interaction and no OOM or GPU-process replacement. One discrepant idle native-frame sample is retained in the validation notes; its cause is not established. Microsoft sign-in, cloud publishing and the general OneLake source chooser remain limited; use the direct **Get Data → Text/CSV** menu for local CSVs. See [compatibility](docs/compatibility.md).

Implementation checks and the distinction between a project's data cache and renderer failures are recorded in [validation](docs/validation.md).

## Target

Fedora 44, x86_64, a systemd user session, native Wayland and a Vulkan-capable GPU/driver. Other Fedora releases are experimental. X11, other distributions, Flatpak, AppImage and a setup GUI are outside this version.

## Install

Build or obtain the RPM, then install it:

```bash
sudo dnf install ./powerbi-linux-0.1.0-1.noarch.rpm
pbi-linux doctor
```

The RPM provides the CLI, menu entry and file associations. It does **not** include Power BI, Microsoft runtimes, credentials or a populated prefix. Provision your per-user installation using verified inputs:

```bash
pbi-linux setup \
  --runtime powerbi-linux-runtime-0.1.0-x86_64.tar.xz \
  --runtime-sha256 '<runtime checksum>' \
  --installer PBIDesktopSetup_x64.exe \
  --accept-license
pbi-linux open
pbi-linux open '/path/to/report.pbix'
```

Read [installation](docs/install.md) and [legal notes](docs/legal.md) first. Power BI **2.158.1177.0** and fixed WebView2 **154.0.4258.62** are the current version targets. Setup obtains the pinned WebView2 CAB, .NET prerequisites and fonts from their official sources and verifies their checksums. For an offline WebView2 input, pass `--webview-runtime /path/to/Microsoft.WebView2.FixedVersionRuntime.154.0.4258.62.x64.cab`; it must match the release lock. The Microsoft payload is installed privately and is absent from project release archives.

Add `--make-default` to opt into default file associations. Otherwise use **Open With → Power BI Desktop (Wine)**. Installation uses XDG directories; preferences and credentials persist across launches. Opening a file does not rebuild Wine or reapply patches.

For larger models on a host with sufficient memory, use `pbi-linux profile large`, then close and reopen Power BI. It selects the 10 GiB RAM / 4 GiB swap limits used for the synthetic refresh test on a 16 GiB host. `pbi-linux profile normal` restores the defaults.

## Develop

```bash
python3 -m unittest discover -s tests/unit -v
python3 runtime/build.py
python3 tools/build-rpm.py
```

Builds use Docker by default (`--engine podman` is also supported). Read [build instructions](docs/build.md) for dependencies, checksums and source preparation. Source preparation can run without containers. The CLI uses Python's standard library; the RPM adds host dependencies.

| Directory | Purpose |
|---|---|
| `src/` | CLI and production helpers |
| `runtime/` | Pinned sources, patches and container build |
| `tests/` | Unit tests, backend probes and synthetic fixtures |
| `packaging/` | RPM, desktop entry and MIME definitions |
| `docs/` | Architecture, compatibility, installation and troubleshooting |

## Community and licensing

File bugs using the repository issue templates with `pbi-linux doctor --json`, the runtime version and a synthetic reproducer. Never attach credentials, customer datasets or an entire prefix. See [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), [licenses](docs/legal.md) and [PT-BR installation](docs/install.pt-BR.md).

Independent project code is **GPL-3.0-or-later**. Wine/Neutron derivatives retain **LGPL-2.1-or-later** and DXVK derivatives retain their upstream terms. Full notices are in `LICENSES/`. This is an independent project, not affiliated with or supported by Microsoft. Power BI remains proprietary and subject to its own license. Source availability of these tools is not permission to redistribute Microsoft software.

## Credits

Built on [Wine](https://www.winehq.org/) and [DXVK](https://github.com/doitsujin/dxvk). The composition/cursor work draws on [Neutron](https://github.com/Nico-LaFoucate/Neutron) and its [Wine patches](https://github.com/Nico-LaFoucate/neutron-wine). [Collider](https://github.com/Nico-LaFoucate/Collider) informed the separation between engine and frontend. [Selawik](https://github.com/microsoft/Selawik) supplies the compatible UI font. See [patch provenance](docs/patches.md) for the exact adaptation and licenses.
