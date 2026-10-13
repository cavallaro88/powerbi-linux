# Installation and lifecycle

The only supported target is Fedora 44 x86_64 on native Wayland. Install the RPM with DNF so dependencies are resolved. `samba-winbind-clients` supplies the local SSPI/NTLM helper; a Winbind daemon is not needed. Install the appropriate Vulkan driver for your GPU separately.

The runtime is built against glibc 2.39 in an Ubuntu build container to provide a conservative ABI baseline. This is a build environment choice, not a supported Ubuntu installation target.

## Required inputs

- Project runtime archive and its SHA-256, produced together by `runtime/build.py`.
- Microsoft Power BI Desktop 2.158.1177.0 x64 installer matching `runtime/sources.lock.json`.
- Microsoft fixed WebView2 x64 **154.0.4258.62 CAB**, automatically downloaded using the official URL and checksum in the lock. Use `--webview-runtime` to supply the same CAB offline. No Evergreen installer is needed as a project setup input.
- .NET 4.0 prerequisite and .NET 4.8 installers, optionally passed with `--dotnet40-installer` and `--dotnet-installer`; otherwise downloaded from the official link and checked against the lock.

Download Microsoft installers from Microsoft. Consult their terms before using `--accept-license`, which acknowledges local installation and compatibility modifications. These tools do not bypass account, service or subscription requirements.

## State

| Location | Contents |
|---|---|
| `$XDG_DATA_HOME/powerbi-linux` | Runtime generations, profile generations and active/previous pointers |
| `$XDG_CONFIG_HOME/powerbi-linux` | Settings and previous desktop associations |
| `$XDG_CACHE_HOME/powerbi-linux` | Verified downloads and derived PE backing |
| `$XDG_STATE_HOME/powerbi-linux` | Setup, maintenance and session logs |
| `$XDG_RUNTIME_DIR/powerbi-linux` | Session socket and maintenance lock |

Defaults follow the standard `~/.local/share`, `~/.config`, `~/.cache` and `~/.local/state` locations. State directories and socket are private to the user. Power BI is not a sandbox: Wine can access files available to the user.

The validated profile occupies approximately 9 GiB, before the runtime, verified downloads, derived cache and your reports. On a filesystem without reflinks, repair/update needs space for another complete profile and its cache; the original is retained for rollback. Check the filesystem containing your XDG directories before maintenance. A small RPM download does not represent the size of the installed Microsoft application.

## Maintenance

Close all managed windows before maintenance. Setup can resume an interrupted stage using the same inputs. Repair and runtime update create a separate profile generation before activating it; failure leaves the current pointer untouched.

```bash
pbi-linux repair
pbi-linux update --runtime runtime.tar.xz --runtime-sha256 '<checksum>'
pbi-linux rollback
pbi-linux uninstall
```

`update` updates the **project runtime** and provisions the fixed WebView2 recipe recorded by that runtime. It does not upgrade Power BI Desktop or .NET; those require a separately validated installation recipe. Wine Gecko x86/x64 is also downloaded from WineHQ with hashes pinned from the Wine source. The project never schedules automatic updates. The fixed WebView2 package is selected by a per-prefix `BrowserExecutableFolder` policy and checked against the activated runtime manifest. An Evergreen copy or Microsoft updater created by another installer does not select a different browser for this application. Rollback retains the prior runtime's WebView2 contract; it does not silently adopt the current CLI's browser version. Previous profiles are retained for rollback and can consume substantial disk space when reflinks are unavailable.

`uninstall` removes per-user integration and preserves state. When the RPM's system desktop entry exists, a per-user `Hidden=true` entry masks it so it does not reappear in the menu or Open With. A later `repair` restores the menu and Open With entries without changing explicit default applications. `uninstall --purge` explicitly deletes managed profiles, runtime, cache and settings. It does not uninstall the RPM; use DNF for that. Project files saved outside managed directories are never deleted. Files saved inside a managed prefix are part of the purge.

The normal profile uses a 6 GiB RAM + 2 GiB swap limit and a 512 MiB V8 heap. For larger models on a host with sufficient memory, run `pbi-linux profile large`, then close and reopen Power BI. It selects the tested 10 GiB RAM / 4 GiB swap limits and keeps the 512 MiB heap. `pbi-linux profile normal` restores the defaults. These are cgroup limits, not reserved memory. The large synthetic refresh was tested on a 16 GiB host; larger limits do not guarantee successful refresh of every model. Developer overrides remain available in `settings.json`; follow the compatibility matrix.
