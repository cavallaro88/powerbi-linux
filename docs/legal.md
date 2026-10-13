# Licensing, provenance and limitations

Independent CLI, packaging, helpers and tests: GPL-3.0-or-later, see `LICENSE`. Modified Wine modules and Wine/Neutron patches retain LGPL-2.1-or-later and their original copyright notices. Upstream DXVK retains its zlib/libpng terms; the Neutron-derived presentation modifications retain LGPL-2.1-or-later. Submodule licenses remain applicable. dnlib is MIT; Selawik is SIL Open Font License 1.1, see `LICENSES/Selawik.txt` and the [upstream notice](https://github.com/microsoft/Selawik/blob/master/LICENSE.txt).

| Component | Origin / pinned version | Distribution policy |
|---|---|---|
| Wine | WineHQ 11.18 | Source and built runtime with upstream notices and corresponding source |
| Neutron-derived composition/cursor changes | neutron-wine commit in lock | Attribution and LGPL notices retained |
| DXVK | 3.1 commit in lock | Source/runtime with upstream and submodule notices |
| dnlib | NuGet 4.5.0 | Tool dependency with MIT notice |
| Selawik | Microsoft release 1.01 | Obtained during setup; preserve upstream font license |
| Power BI Desktop, .NET, WebView2 | Microsoft | Obtained by the user/setup from authorized sources; no populated prefix or modified Microsoft binary in project releases |

The project modifies local Power BI assemblies for WinRT references and installed-path discovery, and modifies a locally installed `msmdsrv.exe` to use `ImpersonateSelf(SecurityImpersonation)` in a specific call site. This does not implement Windows anonymous impersonation semantics. Local workarounds do not establish permission to modify or redistribute software under every applicable agreement. Installer terms and the user's rights remain controlling; redistribution eligibility must be verified before adding any third-party binary to releases.

This project is independent of Microsoft, Wine and Neutron. No official Power BI support on Linux is implied. Power BI cloud accounts and paid capabilities retain their normal requirements. There is no warranty of suitability, correctness or data recovery; known limitations are tracked by scenario rather than described as universal compatibility.

No credential forwarding to maintainers or project telemetry is implemented. Microsoft application/network behavior is governed by the application's own settings and terms. Wine prefixes are not security sandboxes.
