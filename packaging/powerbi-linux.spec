Name:           powerbi-linux
Version:        0.1.0
Release:        19%{?dist}
Summary:        Community Power BI Desktop compatibility tools for Fedora
License:        GPL-3.0-or-later AND LGPL-2.1-or-later AND Zlib
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
# The pinned Ubuntu cross-builder installs Python through apt; %check verifies it.
%if 0%{?fedora}
BuildRequires:  python3 >= 3.12
%endif
Requires:       python3 >= 3.12
Requires:       systemd >= 250
Requires:       samba-winbind-clients
Requires:       desktop-file-utils
Requires:       shared-mime-info
Requires:       xdg-utils
Requires:       zenity
Requires:       cabextract
Requires:       fontconfig
Requires:       freetype
Requires:       vulkan-loader
Requires:       libxkbcommon
Requires:       gnutls
Requires:       libunwind
Requires:       mesa-libEGL
Requires:       libodbc.so.2()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       pulseaudio-libs

%description
CLI installer, launcher and diagnostic tools for a community maintained Wine
runtime. Supports Fedora x86_64 with a native Wayland session. Microsoft Power
BI Desktop, .NET and WebView2 are obtained and installed separately per user.
This package does not contain Microsoft software or a populated Wine prefix.
Repair and runtime updates modify the existing profile in place without full
profile snapshots or rollback. Back up important files before maintenance.

%prep
%setup -q

%build

%check
python3 -c 'import sys; assert sys.version_info >= (3, 12)'
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v

%install
mkdir -p %{buildroot}%{_datadir}/powerbi-linux %{buildroot}%{_bindir}
cp -a src runtime connectors packaging docs LICENSE LICENSES README.md %{buildroot}%{_datadir}/powerbi-linux/
install -m 0755 packaging/pbi-linux %{buildroot}%{_bindir}/pbi-linux
mkdir -p %{buildroot}%{_datadir}/applications %{buildroot}%{_datadir}/mime/packages %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
install -m 0644 packaging/powerbi-linux.desktop %{buildroot}%{_datadir}/applications/
install -m 0644 packaging/powerbi-linux.xml %{buildroot}%{_datadir}/mime/packages/
install -m 0644 packaging/powerbi-linux.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/
find %{buildroot} -type d -name __pycache__ -prune -exec rm -rf {} +

%files
%license LICENSE LICENSES/
%doc README.md docs/
%{_bindir}/pbi-linux
%{_datadir}/powerbi-linux/
%{_datadir}/applications/powerbi-linux.desktop
%{_datadir}/mime/packages/powerbi-linux.xml
%{_datadir}/icons/hicolor/scalable/apps/powerbi-linux.svg

%changelog
* Mon Oct 26 2026 Project maintainers - 0.1.0-19
- Maintain the existing prefix in place without snapshot copies or rollback.
- Record incomplete maintenance and block launch until recovery succeeds.
- Preserve legacy profile directories and user-controlled resource defaults.
* Sun Oct 25 2026 Project maintainers - 0.1.0-18
- Enable automatic setup and update downloads from the published runtime release.
* Fri Oct 23 2026 Power BI Linux contributors <maintainers@localhost> - 0.1.0-17
- Follow GNOME light/dark preference for Desktop's System theme selection
- Keep explicit Light/Dark choices and reuse the installed Wine runtime

* Fri Oct 23 2026 Power BI Linux contributors <maintainers@localhost> - 0.1.0-16
- Render browser HTML and SVG title tooltips inside the report viewport
- Preserve original rich visual tooltip handlers and editable controls

* Wed Oct 21 2026 Project maintainers - 0.1.0-15
- Restore native resizing and adapt Options navigation/content to the viewport.
- Prevent label selection while preserving editable fields and original callbacks.
- Guard both 2.158 and 2.159 resource/native method recipes.
* Tue Oct 20 2026 Project maintainers - 0.1.0-14
- Organize user, development and reference guides; add a beta known-issues guide.
- Add guided setup and a gated pinned download contract with local input support.
- Show verified-download progress and record installed Power BI recipe metadata.
- Add exact guarded 2.159/2.158 recipes and isolate independent XDG sessions.
* Sun Oct 18 2026 Project maintainers - 0.1.0-13
- Keep Quill font and size pickers in WebView's top layer with original select events.
- Preserve Escape dismissal before Desktop consumes the key; guard local HTML inputs.
* Sun Oct 18 2026 Project maintainers - 0.1.0-12
- Extend normal Desktop client frames with transparent native resize zones.
- Retain fixed, owned and maximized frame paths; guard exact method contents.
* Sun Oct 18 2026 Project maintainers - 0.1.0-11
- Normalize linguistic JSON before the original cached-model metadata update.
- Extract the original Power BI icon locally after application provisioning.
* Sun Oct 18 2026 Project maintainers - 0.1.0-10
- Disable the local Windows Store rating prompt after publishing.
* Fri Oct 16 2026 Project maintainers - 0.1.0-9
- Bound the Options scroll pane after asynchronous loading and on resize.
- Add the HTML Int64 interoperability runtime patch and an isolated regression probe.
* Fri Oct 16 2026 Project maintainers - 0.1.0-8
- Serialize the Edit Permissions wire fields without traversing native host objects.
- Update the Wayland recipe for modal ownership, popup anchoring and client surface stacking.
- Document synthetic pointer validation and remaining nested confirmation limitations.
* Thu Oct 15 2026 Project maintainers - 0.1.0-7
- Add optional verified MySQL Connector/NET installation scoped to the managed profile.
- Recalculate data source list geometry after showing a legacy dialog.
* Thu Oct 15 2026 Project maintainers - 0.1.0-6
- Use Desktop's system authentication browser during offline setup/repair.
- Keep native MSAL authentication and document the confirmed Windows broker failure.
* Thu Oct 15 2026 Project maintainers - 0.1.0-5
- Serialize only the email dialog wire fields before invoking native validation.
- Preserve the original sign-in handlers and check the serializer patch in doctor.
* Wed Oct 14 2026 Project maintainers - 0.1.0-4
- Restore Wine MSHTML protocol and MIME registrations after installation.
- Fix legacy credential dialog initialization and deferred layout.
- Check legacy HTML registrations in doctor without starting Wine.
* Wed Oct 14 2026 Project maintainers - 0.1.0-3
- Add a locally signed native close confirmation with original localized labels.
- Preserve Desktop save/close handling and default to Cancel.
* Wed Oct 14 2026 Project maintainers - 0.1.0-2
- Default to unrestricted RAM/swap, automatic browser heap and standard browser settings.
- Add optional CLI resource settings and migrate legacy bundled limits.
* Tue Oct 13 2026 Project maintainers - 0.1.0-1
- Initial Fedora packaging; public release remains gated on compatibility tests.
