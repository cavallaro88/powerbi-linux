# Neutron review — 2026-10-18

Reviewed [neutron-wine](https://github.com/Nico-LaFoucate/neutron-wine) from
`5afd8d479ca83f57b56a2350274927647519da90` through `8ecb7fd1789dde9db03811cdaa4980eb8c6c2a91`:
**87 commits, 59 changed patch files**, plus build/external-library changes.
The separate [Neutron CLI](https://github.com/Nico-LaFoucate/Neutron) reference was
read at `3dd137579e0f2d4a0fa82ef1d414986745122128`. The 87-commit delta belongs to the
Wine repository rather than that CLI.

The complete commit/patch decisions, upstream hashes, target files, external
scope and staged-candidate hashes are in the [review ledger](../../runtime/upstream/neutron-2026-10-18.json).
Production remains pinned to the original Neutron base with the existing Power BI
ports. Runtime 0.1.3, active profiles, resource defaults and previous artifacts
were preserved; fetching an upstream revision does not enable its patches.

## Adopted build protection

Upstream [480d6a4](https://github.com/Nico-LaFoucate/neutron-wine/commit/480d6a4)
refuses packaging builds that used untracked patches. We independently adapted
that behavior and strengthened it with a reviewed filename/hash registry and a
successful full-build receipt matching version, builder, source contents and
compiled payload. Failed builds invalidate previous success, extra payload files
fail, install staging is cleared, and existing artifacts cannot be overwritten.
Eight isolated failure-boundary regressions passed. The real packaging entry
also refused missing success evidence without creating an artifact or altering
runtime 0.1.3. Actual prepared source inputs were fingerprinted successfully.
A new full Wine build remains separate; see [build details](../development/build.md).

## Runtime candidates

| Candidate | Evidence | Before enabling |
|---|---|---|
| Signed server DPI arithmetic | Wine 11.18 uses unsigned products for negative coordinates. The actual source helper failed 6 of 14 arithmetic controls; its ratio-aware port passed all 14. | Compile a full consistent server/runtime; test negative origins, fractional/mixed DPI and compositor geometry. |
| Capture-aware mouse tracking | Upstream change can avoid premature WM_MOUSELEAVE while dragging outside a captured control; applies and reverses with zero fuzz. | Native captured-drag/release and no-capture controls, compositor input and actual Desktop regression. |
| Rendering-mode glyph bitmap cache | Source inspection finds a cache key without rendering mode and a size-unbounded copy. Port preserves Wine's transformed-glyph cache bypass; applies and reverses with zero fuzz. | Compile DirectWrite, reproduce mixed aliased/antialiased heap behavior and compare rendering. |

These patches are isolated under [runtime/candidates](../../runtime/candidates/README.md).
**None is part of the production series.** Patch application and isolated source
arithmetic are not runtime/UI certification. The DPI test compiles the actual
extracted function, not a rewritten Python model, but does not run Wine server.

Other worthwhile candidates include Direct2D command-buffer pointer lifetime and
large glyph-run bounds, surface copy before resize flush, monitor origin/rotation,
NOACTIVATE clicks, menu deactivation and DPI/window lookup performance. Their
specific dependencies and acceptance work are recorded individually. DXGI
background-color storage is a separate potential DXVK candidate; there is no
Power BI caller failure yet, and finite/NaN input checks need review.

## Changes withheld

- A forced dark fill hides fresh-surface flashes for Adobe's dark UI; it does not
  repair missing paint and changes Power BI's light interface globally.
- Transacted-registry calls mapped to immediate ordinary writes lose rollback
  semantics; no demonstrated Power BI failure requires that compromise.
- AMD video encoding, CUDA/D3D12 sharing, OpenCL and audio/media additions do not
  match the demonstrated Power BI workload. D3D11 WinRT media wrappers do not
  implement the missing CLR System.Runtime.WindowsRuntime bridge.
- Several restacking, WIC pooling, role-less flush and window-shared-memory
  changes require Neutron-specific infrastructure. Wine 11.18 already has parts
  of the TIB/fiber work, so replaying its older whole patch would be incorrect.
- Diagnostic stack suspension and rectangle logging remain opt-in investigation
  candidates rather than production behavior.

Only **21 of 59** upstream patch files apply fully to the currently prepared
Wine source with zero fuzz. The others need a port or are tied to upstream's
stack; an unsuccessful dry run alone does not prove a fix is already present.
Even a clean application does not prove relevance or correctness for Power BI.

## Repeat the checks

```bash
# No network or upstream checkout required; included in quick QA:
python3 tools/audit-neutron.py
# Verify exact upstream commit/patch contents against an existing checkout:
python3 tools/audit-neutron.py --checkout /path/to/neutron-wine
# Isolated actual-source arithmetic comparison; requires cc and patch:
python3 tools/test-dpi-arithmetic.py --wine-source /path/to/prepared/wine
```

The audit does not fetch or mutate repositories. Refresh a private upstream
checkout explicitly before reviewing the next range; an unreviewed checkout HEAD
is rejected rather than certified from stale decisions. Advancing production's
base or changing candidate bytes requires updating the ledger. A runtime port
must retain its upstream license/provenance, pass native regressions and complete
the documented compatibility gates before release.
