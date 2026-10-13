# Power BI Desktop on Fedora

Community compatibility tools for Power BI Desktop using patched Wine, DXVK and native Wayland. **Validated development preview 0.1.0: compatibility is scoped to the documented synthetic workloads.**

RPM 11 adds a scoped [cache restore correction](docs/model-cache.md), preserving
the original model synchronization and data. Desktop Save and a fresh normal
reopen passed in a private 158-table copy, including a real metadata change.
Desktop integration uses the original Power BI icon extracted locally from the
installed application; Microsoft artwork is not bundled in the RPM.

The runtime 0.1.3 candidate adds a scoped [cross-process cursor correction](docs/cursor.md),
with a native component and compositor-motion reproducer. RPM 9 remains compatible.
After restart, the real Power BI sidebar/canvas alternated horizontal resize and
arrow resources correctly; data-grid, custom-cursor and broader workload coverage
remain separate.

The RPM 9 / runtime 0.1.2 candidate fixes incomplete Options initialization and
clipped scrolling. Its 22-tab synthetic audit and numeric regression have a
separate [validation scope](docs/options-dialog.md). It retains the earlier
[Edit Permissions corrections](docs/permissions-wayland.md).

An installation created from official installers opened PBIX/PBIP/PBIR through the Fedora desktop, imported a local CSV, displayed the expected values and preserved them after save/reopen. A synthetic 158-table model with 156 relationships also passed UI refresh and independent data checks. A two-hour session passed with periodic visual interaction and no OOM or GPU-process replacement. One discrepant idle native-frame sample is retained in the validation notes; its cause is not established. Microsoft browser sign-in passed with a real account on the Fedora host; a real homologation publication was confirmed by the user, while another cloud cycle after the local correction and the general OneLake source chooser remain separate; use the direct **Get Data → Text/CSV** menu for local CSVs. See [compatibility](docs/compatibility.md).

Implementation checks and the distinction between a project's data cache and renderer failures are recorded in [validation](docs/validation.md). The subsequent [installed-RPM host validation](docs/validation-host.md) passed with system NTLM/ODBC and production desktop dispatch.

RPM 10 removes the Windows Store rating prompt that could raise a local WinRT
error after a successful publication. A real homologation publication was confirmed
by the user; the correction has separate offline evidence. See [publishing](docs/publishing.md).

Setup and repair suppress Desktop update notices using Microsoft's documented
policy. A Fedora notification for validated releases remains planned; see
[update policy](docs/updates.md).

## Target

Fedora 44, x86_64, a systemd user session, native Wayland and a Vulkan-capable GPU/driver. Other Fedora releases are experimental. X11, other distributions, Flatpak, AppImage and a setup GUI are outside this version.

## Install

Build or obtain the RPM, then install it:

```bash
sudo dnf install ./powerbi-linux-0.1.0-11.noarch.rpm
pbi-linux doctor
```

The RPM provides the CLI, menu entry and file associations. It does **not** include Power BI, Microsoft runtimes, credentials or a populated prefix. Provision your per-user installation using verified inputs:

```bash
pbi-linux setup \
  --runtime powerbi-linux-runtime-0.1.3-x86_64.tar.xz \
  --runtime-sha256 '<runtime checksum>' \
  --installer PBIDesktopSetup_x64.exe \
  --accept-license
pbi-linux open
pbi-linux open '/path/to/report.pbix'
```

Read [installation](docs/install.md) and [legal notes](docs/legal.md) first. Power BI **2.158.1177.0** and fixed WebView2 **154.0.4258.62** are the current version targets. Setup obtains the pinned WebView2 CAB, .NET prerequisites and fonts from their official sources and verifies their checksums. For an offline WebView2 input, pass `--webview-runtime /path/to/Microsoft.WebView2.FixedVersionRuntime.154.0.4258.62.x64.cab`; it must match the release lock. The Microsoft payload is installed privately and is absent from project release archives.

Add `--make-default` to opt into default file associations. Otherwise use **Open With → Power BI Desktop (Wine)**. Installation uses XDG directories; preferences and credentials persist across launches. Opening a file does not rebuild Wine or reapply patches.

RPM 0.1.0-2 defaults to no project RAM/swap limits or CPU quota, automatic WebView2 heap and standard browser settings. `pbi-linux profile` shows the effective policy. Limits and economy options are opt-in; `pbi-linux profile unlimited` restores the default. Close all Power BI windows and reopen to apply changes. See [resource settings](docs/resources.md) for individual options and the optional `normal`/`large` economy presets.

RPM 0.1.0-3 adds a [native unsaved-changes confirmation](docs/native-dialogs.md).
RPM 0.1.0-4 fixes [legacy credential dialogs](docs/legacy-html.md) that could
remain invisible and block refresh. Existing profiles need `pbi-linux repair`
after upgrading the RPM, with Desktop closed, to receive the correction.
RPM 0.1.0-6 includes the Continue correction and selects Desktop's existing system
authentication browser during setup/repair. Microsoft authentication completed in
Vivaldi with a real account on the Fedora host. See [sign-in status](docs/sign-in.md)
for the exact scope, existing-profile setting and remaining cloud checks.
RPM 0.1.0-7 adds optional [original database connectors](docs/connectors.md) and
fixes the blank legacy data source list. MySQL Connector/NET installation and a
synthetic MariaDB UI refresh passed; real-server TLS remains unverified. After
reading the upstream licenses, close Desktop and run:

```bash
pbi-linux connector install mysql --accept-license
pbi-linux connector status mysql
```

The separate [refresh-cancellation checks](docs/refresh-cancellation.md) record
successful cancellation and an approximately 20-second wait during synthetic
data loading. A subsequent real refresh blockage was traced to an invisible
credential request; cancellation of running queries remains connector-dependent.

## Develop

Run `python3 tools/check-product.py` for repeatable checks and JSON/JUnit evidence.
See [proactive QA](docs/automated-qa.md) for the prepared daily CI, isolated native
components, public Options audit and the remaining unattended-GUI work.

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
