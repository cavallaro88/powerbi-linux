# Patch inventory

The initial patch set targets Wine 11.18 and DXVK 3.1. Wine composition incorporates four Neutron bridge/cross-process/resize/reaper patches and the cursor correction from `neutron-wine` commit `5afd8d479ca83f57b56a2350274927647519da90`, adapted to Power BI owner-process delivery. Reproduction ports are retained under `runtime/ports/`; the normal build applies the reviewed emitted patches rather than regenerating tracked files.

| Patch or helper | Reason | Status / license |
|---|---|---|
| Wine composition aggregate | dcomp bridge, owner transport, cursor/HKL, optional capture and PE backing | Required; Wine/Neutron LGPL-2.1-or-later |
| Wine OLE DB VARIANT conversions | Numeric/boolean values otherwise appeared as zero | Required; LGPL-2.1-or-later |
| Wine Wayland parent | Owned dialogs otherwise remained behind the main window | Required; LGPL-2.1-or-later |
| Wine cgroup reporting | Report cgroup limits to CLR/Chromium/AS | Required; LGPL-2.1-or-later; initializes the path buffer in the product port |
| Wine secur32 status | Return NTSTATUS rather than BOOL from LsaFreeReturnBuffer | Required; source fix replaces the old machine-code patch; LGPL-2.1-or-later |
| DXVK presentation | Scoped GDI delivery for WebView HWND swapchains | Required; DXVK upstream terms, preserving Neutron-derived provenance |
| Culture helper | Select installed non-RTL UI cultures | Required; independent GPL-3.0-or-later |
| Shared/WinRT local assembly changes | Installed-path discovery and missing WinRT contracts | Required for pinned app; independent GPL patch tools; patched Microsoft binaries remain local |
| AS self-token change | Replace a specific anonymous-impersonation call with real self impersonation | Experimental semantics, required by current recipe; original hash and byte checks enforced |
| WebView2 per-app Windows version | The investigated profile used `win7` for `msedgewebview2.exe`; reproducing it prevents fixed-runtime GPU crashes, while Desktop remains on `win10` | Required by the tested recipe |
| Modern Power Query switch | Select the tested WebView2 editor | Required, internal app interface that may change |
| Legacy HTML registration and UI resources | Restore Wine protocol/MIME handlers; work around an unsupported CSS setter and stale credential-sidebar height | Required for the pinned app; exact input/output hashes and resource sizes checked; modified Microsoft assembly stays local |
| Email dialog serializer | Serialize the three wire fields without traversing native host/button objects when Continue reads the view model | Guarded local resource change; native validation/authentication unchanged; interactive account validation pending |

`WinRTStubs` reports APIs unavailable and contains incomplete methods; it does not implement Windows storage/launch contracts. No broader WinRT support is claimed. The self-token workaround is not equivalent to anonymous Windows identity.

Discarded experiments, forced-success patches and legacy profiles stay in the private investigation archive, not in the product's active recipe. The optional Wayland capture hook is compiled from the aggregate patch but inactive without diagnostic flags; production environment removes them.

WinRT stub keys use an RSA signature key. Native `csc /keyfile` fails on Wine with CS1548/8013141e, so setup compiles an unsigned `WinRTStubs` assembly and signs it with dnlib using the locally generated key. The helper tests verify the resulting strong-name signature and reject an unrelated assembly.

Setup enables the modern Power Query switch through the application's local feature-storage implementation. It does not invoke `PackageStorageManager`, which depends on Unity services initialized by a running Desktop process. Existing user settings and other switches are preserved by the application's own storage API.
