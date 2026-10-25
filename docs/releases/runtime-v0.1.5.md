# Runtime 0.1.5 — published setup runtime

Published on **October 25, 2026** from the 0.1.5 candidate, built on
October 20, 2026. It enables automatic setup downloads and is a development
prerelease, not a stable certification.

- Produce a complete Wine 11.18 / DXVK 3.1 build with the reviewed production
  patch registry, including the normal Wayland resize correction.
- Pin Power BI Desktop 2.159.883.0 and retain WebView2 154.0.4258.62.
- Build the compatibility helpers from the current sources; RPM 14 supplies the
  guarded application recipes for both supported Power BI versions.
- Support explicit compiler parallelism with `--jobs`. Move install staging
  before stripping and recreate helper output directories to avoid redundant
  unstripped trees and incomplete packaging.
- Record the fixed builder image, toolchain/package inventory, input fingerprint
  and complete runtime payload through the full-build receipt.

Runtime archive: `powerbi-linux-runtime-0.1.5-x86_64.tar.xz`, SHA-256
`291bb52fca8c27f2446ec4a05aaf982bb43d8c13e6b3787f32a1328ad890f05a`.
Builder image: `sha256:d50ed5eb8eb25584011520b0bfb00ecd7dc0cd54fe4ede65f62728e698ca9ed5`.
Build input fingerprint: `16217551d31fb7bd962b567d827dc58bf61961e199d8ff03b343dfe16a106854`.

Clean installation, interruption/resume, nine native components, 158-table refresh
and Save, CSV visual/Save, normal document reopening, maintenance and uninstall
passed locally on the exact archive. **The exact-archive two-hour soak remains
pending**; the earlier synthetic two-hour session used a different local build.

The [2.159 assessment](../reference/powerbi-2.159.md) separates preliminary
upgrade tests from the clean-install and exact-archive acceptance work.

## Assets

The [runtime-v0.1.5 release](https://github.com/cavallaro88/powerbi-linux/releases/tag/runtime-v0.1.5)
attaches the runtime archive, the complete corresponding source (including
patched Wine/DXVK sources), exact-archive evidence, `SHA256SUMS` and
`SOURCE-PROVENANCE.json`. `pbi-linux setup` and `pbi-linux update` download this
archive when the installed package ships the ready setup manifest; every
download is verified against the pinned SHA-256.
