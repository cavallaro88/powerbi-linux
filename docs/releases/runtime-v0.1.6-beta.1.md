# Runtime 0.1.6-beta.1 — sparse Wine protection metadata (beta)

Published from the exact merged product commit `bfc294572bd177c421c481f84ed20f0c9a56a219`.
This is a **beta prerelease**, not a stable runtime certification.

## What changed

- Includes `wine-11.18-vprot-sparse-zero.patch`, integrated through the reviewed
  patch registry and full runtime build.
- Linux x64 zero protection metadata for large NOACCESS reservations stays sparse
  while addresses, protections, edges, nonzero writes, fallback and 32-bit path are
  preserved.
- Pins Power BI Desktop 2.159.883.0 and WebView2 154.0.4258.62.

## Evidence scope

Isolated tests passed: the exact helper differential harness (6,360 cases), Win64
behavior probe (651 checks, 800 threaded cycles, three runs per variant), and Wine
`ntdll:virtual` (2,548) plus `kernel32:virtual` (30,964) on separately built
reference/candidate with unchanged known TODOs. A sequential blank-report A/B
measured 7.099 GiB reference versus 4.621 GiB candidate mean PSS, and a disposable
real-project copy completed user-accepted refresh/save/reopen. Direct attribution
showed renderer protection metadata falling from roughly 2,355 MiB to 3 MiB.

**This exact archive has not passed the full exact-archive release gates.** Clean
install, PBIX/PBIP/PBIR, CSV, large refresh, save/reopen, maintenance lifecycle and
the two-hour soak are not certified for this archive. `release-evidence-beta.json`
records those gaps explicitly; it is not a passing certificate. Package compatibility
and ODBC behavior are separate; the ODBC bridge remains unpublished.

## Assets

- `powerbi-linux-runtime-0.1.6-beta.1-x86_64.tar.xz` and SHA-256
- complete corresponding source `powerbi-linux-source-runtime-0.1.6-beta.1.tar.gz`
- `release-evidence-beta.json`, `SOURCE-PROVENANCE.json`, `SHA256SUMS`

## Use

Beta users should prefer `--runtime` with a local, verified archive until the
matching package pin is published, or install RPM/DEB 0.1.0-19 after its pin is
ready. This release does not replace an installed runtime automatically.

## Digests

- runtime `7a24a7dcf950457c65b8eac90e6b2b7640a6d460279d29fce7f3867a6064d421`
- source `928fc9e6175d2269f0edc3ecfba0cf820202df3100f014daafb7f82ed475583f`
- evidence `06c422a3562e8c07f20f21b82ee68cf8233127cb49c40b43e77b1ef46a3e685d`

Built with Wine 11.18 and the reviewed patch registry from `bfc294572bd177c421c481f84ed20f0c9a56a219`.
The loader prints `wine-11.18` without creating a prefix; the built Unix ntdll contains the sparse helper.
