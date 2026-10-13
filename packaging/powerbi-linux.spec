Name:           powerbi-linux
Version:        0.1.0
Release:        1%{?dist}
Summary:        Community Power BI Desktop compatibility tools for Fedora
License:        GPL-3.0-or-later AND LGPL-2.1-or-later AND Zlib
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
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
* Sun Oct 11 2026 Project maintainers - 0.1.0-1
- Initial Fedora packaging; public release remains gated on compatibility tests.
