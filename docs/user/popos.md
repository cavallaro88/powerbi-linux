# Pop!_OS 24.04 — experimental package

The local `amd64` DEB targets **Pop!_OS 24.04 with native Wayland**. Ubuntu 24.04
is accepted as the corresponding base for dependency/install checks. Fedora 44
remains the graphically tested target. Pop!_OS ships the new COSMIC desktop;
see [System76's desktop guide](https://support.system76.com/support/desktop-environment).
The Fedora UI results do not certify COSMIC behavior.

Extract the local test bundle, open a terminal in its directory and run:

```bash
sudo apt install ./powerbi-linux_0.1.0-16pop1_amd64.deb
./setup-popos.sh
```

For an existing installation, close Desktop, install the new DEB and run
`pbi-linux repair` instead of setup. Revision `0.1.0-16pop1` supplies the Options
resize, scrolling and label-selection correction. This update uses the existing
runtime; allow space for another complete profile while repair creates its
transactional snapshot.

Run the setup script as your regular user. It passes the bundled runtime and
its exact checksum to the CLI. Setup requests license acceptance, obtains the
pinned official Power BI installer and prepares WebView2/.NET automatically.
An existing exact installer can be supplied with `--installer '/path/to/EXE'`.
There is no need to install the distribution's Wine package.

The DEB installs only project tools and integration files; its root maintainer
scripts update desktop/MIME/icon caches. They never run Wine or download
Microsoft components. `sudo apt remove powerbi-linux` preserves managed user
profiles; use the normal [user removal commands](install.md#recovery-and-removal)
for those. Keep backups and review [known issues](known-issues.md).

This is a local experiment, built without a CI run or a public release. Native
COSMIC testing remains outstanding. Use `pbi-linux doctor --json` for sanitized
diagnostics when reporting results. The original default automatic-runtime
download gate remains in place; the test bundle supplies a verified local runtime.
