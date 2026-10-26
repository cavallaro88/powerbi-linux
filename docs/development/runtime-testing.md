# Runtime candidate acceptance plan

Keep the three reviewed Neutron candidates inactive until their own tests pass.
Test one patch at a time against runtime 0.1.3, with identical application/input
versions. Record exact source/patch/runtime hashes; never combine candidates
before an individual result can be reproduced. Missing evidence is blocked, not
passed. The current PaperWM investigation is a separate Wine driver correction.

## Component order

1. **Signed server DPI**: the actual helper already passes 14 arithmetic cases
   after its port (six baseline failures). Next compile a consistent server and
   exercise real window geometry at 100%, 125% and 150%, including negative
   coordinates, displays to the left/above, maximize/restore and pointer alignment.
2. **Capture-aware mouse tracking**: log capture ownership, mouse-move/leave,
   button-up and cancellation. Drag outside the control, release outside, change
   focus, and compare ordinary no-capture hover. Confirm the API contract and,
   where ambiguous, run the same probe on Windows rather than treating Wine or
   upstream screenshots as the behavioral oracle.
3. **Rendering-mode glyph cache**: repeatedly mix aliased/antialiased rendering,
   font sizes and cached entries. Compare each mode against its own fresh render;
   compare heap integrity as well as pixels. Run transformed-glyph controls and
   do not remove Wine 11.18's existing transformed-cache bypass.

Use minimal disposable Win32 probes/prefixes for these components. A real
compositor test must send input through the compositor; posting messages to a
window does not establish keyboard/pointer delivery. Record WM_SIZE/native
rectangles as well as MetaWindow frames so scaling a stale buffer cannot pass.

## Desktop and combined acceptance

Only candidates passing components proceed to a separately provisioned QA
Desktop with synthetic data. Cover Options, permissions, scroll/resize,
refresh/cancel and Desktop Save followed by graceful close and fresh reopen,
with independent counts/totals. Keep production reports and credentials out.
Then test approved patches together and run the exact-archive prolonged session
and release compatibility matrix. A component or a clean RPM build does not
satisfy those obligations.

Defaults remain unlimited RAM/swap/CPU and automatic browser resources. Measure
consumption rather than silently adding caps. Reserve disk before creating a
full QA profile (about 9 GiB plus builds, downloads and reports); avoid a full
profile clone merely to test a native window. Keep one baseline/candidate pair
and in-place failure/retry evidence; clean up owned test processes and prefixes.

Most of this work is scriptable. Physical monitor arrangements or
ambiguous Windows behavior may require a separate lab or targeted manual evidence.
Sources, observations, gates and exact gaps belong in [the upstream review](../reference/upstream-neutron.md)
and [automated QA](automated-qa.md), rather than an implicit compatibility claim.
