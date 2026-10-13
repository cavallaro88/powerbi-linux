# Licensing, provenance and limitations

Independent CLI, packaging, helpers and tests: GPL-3.0-or-later, see `LICENSE`. Modified Wine modules and Wine/Neutron patches retain LGPL-2.1-or-later and their original copyright notices. Upstream DXVK retains its zlib/libpng terms; the Neutron-derived presentation modifications retain LGPL-2.1-or-later. Submodule licenses remain applicable. dnlib is MIT; Selawik is SIL Open Font License 1.1, see `LICENSES/Selawik.txt` and the [upstream notice](https://github.com/microsoft/Selawik/blob/master/LICENSE.txt).

| Component | Origin / pinned version | Distribution policy |
|---|---|---|
| Wine | WineHQ 11.18 | Source and built runtime with upstream notices and corresponding source |
| Neutron-derived composition/cursor changes | neutron-wine commit in lock | Attribution and LGPL notices retained |
| DXVK | 3.1 commit in lock | Source/runtime with upstream and submodule notices |
| dnlib | NuGet 4.5.0 | Tool dependency with MIT notice |
| Optional MySQL Connector/NET and dependencies | Versions, upstream license metadata and hashes in connectors/mysql.lock.json | Downloaded separately on request, excluded from project binary/source artifacts; retain upstream notices locally |
| Selawik | Microsoft release 1.01 | Obtained during setup; preserve upstream font license |
| Power BI Desktop, .NET, WebView2 | Microsoft | Obtained by the user/setup from authorized sources; no populated prefix or modified Microsoft binary in project releases |

The project modifies local Power BI assemblies for WinRT references and installed-path discovery, and modifies a locally installed `msmdsrv.exe` to use `ImpersonateSelf(SecurityImpersonation)` in a specific call site. This does not implement Windows anonymous impersonation semantics. Local workarounds do not establish permission to modify or redistribute software under every applicable agreement. Installer terms and the user's rights remain controlling; redistribution eligibility must be verified before adding any third-party binary to releases.

This project is independent of Microsoft, Wine and Neutron. No official Power BI support on Linux is implied. Power BI cloud accounts and paid capabilities retain their normal requirements. There is no warranty of suitability, correctness or data recovery; known limitations are tracked by scenario rather than described as universal compatibility.

No credential forwarding to maintainers or project telemetry is implemented. Microsoft application/network behavior is governed by the application's own settings and terms. Wine prefixes are not security sandboxes.

Optional connector recipes do not change third-party licensing. The pinned Oracle
MySql.Data 8.0.33 package declares GPL-2.0-only; dependencies have their own terms.
The installation command requires explicit license acknowledgement and retains
package provenance plus any embedded notices. Project artifacts contain the
recipe and independent tools, not these downloaded assemblies. See
[connector installation](connectors.md) and the linked upstream packages.

The original Power BI PNG icon is extracted unchanged from the user's installed
application for local desktop integration. Neither that Microsoft artwork nor
populated model caches are included in project RPM/source/QA releases. Existing
Power BI Newtonsoft.Json is referenced locally by the cache helper; the project
does not redistribute it. See [icon behavior](app-icon.md) and [cache scope](model-cache.md).
