# Security

Do not report credentials, private datasets or exploitable issues in a public issue. Report security issues privately through this repository's security advisory channel.

Use verified release checksums and authorized Microsoft installers. A checksum supplied by the user checks integrity, not publisher authenticity. Wine runs with the user's filesystem permissions and is not a sandbox. Production launch disables the project's diagnostic interpreter and remote-debugging flags. `pbi-linux open --diagnostics` turns remote debugging on: while that session runs, any program on the computer can control Desktop's embedded browser, so use it only with disposable test reports.

Desktop's embedded browser (WebView2) is the fixed version pinned in the release recipe, and Desktop's own update notices are turned off. It receives Chromium security fixes only when a project release updates that pin, and under Wine its renderer sandbox does not isolate it. Custom visuals in a report are web code from the report's author: open reports from sources you trust.

Supported security fixes initially target the current project runtime on Fedora 44 x86_64. Experimental builds have no compatibility guarantee. Dependency notices, source provenance and integrity checks accompany releases.

The rules every change to this project must keep, each tied to a test, are in [SECURITY-RULES.md](SECURITY-RULES.md).
