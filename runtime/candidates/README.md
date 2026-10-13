# Reviewed, inactive runtime candidates

These are follow-up candidates from the [87-commit Neutron review](../../docs/upstream-neutron.md).
They are **not applied by runtime/build.py**, are absent from the production
patch registry and are not enabled in runtime 0.1.3. Keep them separate until
their native/runtime acceptance checks pass.

| File | Origin / port | Validation so far |
|---|---|---|
| `neutron-server-signed-dpi.patch` | Signed-coordinate portion of Neutron `1bdc3e5`, adapted to Wine 11.18 `struct ratio`; no WM_PAINT changes | Actual extracted helper: baseline 6/14 failures, candidate 0/14. Full server/compositor pending. |
| `neutron-win32u-capture-tracking.patch` | Exact upstream patch from `95f58b9` | Zero-fuzz application and reverse dry run. Compilation and captured-drag native regression pending. |
| `neutron-dwrite-rendering-mode.patch` | `cef5dcf`, retaining Wine 11.18 transformed-cache bypass and size accounting | Zero-fuzz application and reverse dry run. Compilation, bitmap/heap and render regression pending. |

Hashes and frozen upstream revision are in
[the review ledger](../upstream/neutron-2026-10-18.json). Upstream descriptions
and author attribution are preserved. These Wine/Neutron-derived patches retain
LGPL-2.1-or-later terms; see [license](../../LICENSES/LGPL-2.1.txt).
No claim is made that these are the cause of an observed Power BI failure.
