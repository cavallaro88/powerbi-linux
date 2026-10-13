Name:           powerbi-linux
Version:        0.1.0
Release:        5%{?dist}
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

%prep
%setup -q

%build

%check
python3 -c 'import sys; assert sys.version_info >= (3, 12)'
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v

%install
mkdir -p %{buildroot}%{_datadir}/powerbi-linux %{buildroot}%{_bindir}
cp -a src runtime packaging docs LICENSE LICENSES README.md %{buildroot}%{_datadir}/powerbi-linux/
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
* Sun Oct 11 2026 Project maintainers - 0.1.0-1
- Initial Fedora packaging; public release remains gated on compatibility tests.
