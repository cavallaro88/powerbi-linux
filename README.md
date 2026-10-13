# Power BI Desktop on Fedora

Community tools to install and run Power BI Desktop on Fedora using a patched
Wine/DXVK runtime and native Wayland. Open PBIX, PBIP and PBIR files from the
Linux desktop, with a managed per-user installation and the original Power BI
icon extracted locally from the installed application.

**Development preview 0.1.0: Fedora 44, x86_64, native Wayland.** Other Fedora
versions are experimental. A systemd user session and a Vulkan-capable GPU/driver
are required. The project is independent of Microsoft and has no official
Microsoft support. See [compatibility and limits](docs/compatibility.md).

## Install

Install the CLI and desktop integration through DNF:

```bash
sudo dnf install ./powerbi-linux-0.1.0-12.noarch.rpm
# Upgrade an existing installation:
sudo dnf upgrade ./powerbi-linux-0.1.0-12.noarch.rpm
pbi-linux doctor
```

The RPM contains the project's tools and recipes. Power BI, Microsoft runtimes,
credentials and populated Wine prefixes are obtained or created separately for
each user. Provision using a project runtime archive and the official Power BI
installer:

```bash
pbi-linux setup \
  --runtime powerbi-linux-runtime-0.1.3-x86_64.tar.xz \
  --runtime-sha256 '<runtime checksum>' \
  --installer PBIDesktopSetup_x64.exe \
  --accept-license
pbi-linux open
pbi-linux open '/path/to/report.pbix'
```

The current recipe targets Power BI **2.158.1177.0** and fixed WebView2
**154.0.4258.62**. Setup obtains checksum-verified prerequisites from their official
sources. Review the [installation guide](docs/install.md),
[guia em português](docs/install.pt-BR.md) and [licensing notes](docs/legal.md).
Versioned RPM prereleases and their changelogs are in [GitHub Releases](https://github.com/cavallaro88/powerbi-linux/releases).
The current preview is [RPM 12](https://github.com/cavallaro88/powerbi-linux/releases/tag/v0.1.0-12).
Runtime entries currently provide source recipes only; see the [release index](docs/releases.md)
and [build guide](docs/build.md) before provisioning.

Add `--make-default` during setup to associate files by default; otherwise use
**Open With → Power BI Desktop (Wine)**. Preferences and credentials persist
across launches. Opening a file does not rebuild or re-patch the application.

## Everyday use

Resource limits are optional. Defaults impose no project RAM/swap cap or CPU
quota; WebView2 heap and renderer counts remain automatic.

```bash
pbi-linux profile
pbi-linux profile unlimited
pbi-linux doctor --json
```

Read [resource settings](docs/resources.md) for optional limits. Close all Desktop
windows and reopen to apply a resource change. For optional MySQL Connector/NET,
read the [connector guide and licenses](docs/connectors.md), then install with
`pbi-linux connector install mysql --accept-license` while Desktop is closed.

RPM upgrades update CLI and recipes. Existing profiles receive assembly/runtime
changes through the documented maintenance procedure, rather than during an
active session. See [lifecycle](docs/install.md) and [update policy](docs/updates.md).
A populated profile occupies about 9 GiB; repairs may need another full copy.

## Compatibility status

Validated scenarios include official-installer provisioning, desktop file
opening, CSV import/save/reopen, a synthetic 158-table relational refresh and a
two-hour session. Browser sign-in and persistence passed on the Fedora host;
a real publication was confirmed by the user in a homologation Service workspace.
RPM 11 additionally passed cached-model Save and fresh normal reopen in a private
158-table copy, preserving counts/states and a genuine metadata change. One
preexisting query-error state persisted; every cell and source refresh were not
revalidated. This is scoped evidence rather than universal enterprise support.

Current workarounds and regression evidence cover [legacy dialogs](docs/legacy-html.md),
[permissions](docs/permissions-wayland.md), [Options](docs/options-dialog.md),
[cursors](docs/cursor.md), [PaperWM resizing](docs/paperwm.md), [post-publish Store prompts](docs/publishing.md) and
[model caches](docs/model-cache.md). Keep a private backup of the complete project,
including `.pbi/cache.abf`; a normal Git checkout excludes imported cached data.
See the [documentation index](docs/README.md), [roadmap](docs/roadmap.md) and
[87-commit Neutron review](docs/upstream-neutron.md).

## Develop and contribute

```bash
python3 tools/check-product.py
python3 runtime/build.py
python3 tools/build-rpm.py
```

Builds use Docker by default, with Podman also supported. See [build instructions](docs/build.md)
and [automated QA](docs/automated-qa.md). The regular suite uses synthetic inputs;
native UI tests require a dedicated graphical QA installation.

| Directory | Contents |
|---|---|
| `src/` | CLI and locally compiled compatibility helpers |
| `runtime/` | Pinned dependencies, patches, provenance and build recipe |
| `connectors/` | Optional provider recipes and verified package metadata |
| `tests/` | Unit checks, native probes, fixtures and UI automation |
| `packaging/` | RPM, desktop entry, fallback icon and MIME definitions |
| `tools/` | Build, export, release validation and component checks |
| `docs/` | Installation, compatibility, recovery and developer guides |

Build outputs, downloaded sources, private evidence and model caches are ignored.
They are not part of the source repository or public export. Full corresponding
Wine/DXVK sources must accompany distributed runtime binaries.

Report reproducible bugs with sanitized doctor output and a synthetic example;
follow [CONTRIBUTING](CONTRIBUTING.md) and [SECURITY](SECURITY.md). Do not attach
customer reports, credentials or populated prefixes.

Independent tools are **GPL-3.0-or-later**. Wine/Neutron-derived components retain
**LGPL-2.1-or-later** and their notices; DXVK and other dependencies retain their
own terms. See [LICENSE](LICENSE), [LICENSES](LICENSES/) and [provenance](docs/legal.md).
Microsoft artwork is extracted only for local use and is not bundled in the RPM.
