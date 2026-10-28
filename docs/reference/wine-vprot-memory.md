# Sparse Wine protection metadata

The Wine 11.18 patch `wine-11.18-vprot-sparse-zero.patch` keeps zero-valued
protection metadata sparse on Linux x64. It does not change application RAM/swap,
CPU, V8 heap or renderer policies, and does not disable memory protections.

## Mechanism

Wine maintains one protection byte per guest page. Reserving a large NOACCESS
range can therefore touch hundreds of MiB of metadata despite not committing
application data. `set_page_vprot` previously used `memset` over this zero range.
The helper now uses `MADV_DONTNEED` only for complete host pages wholly inside
zero segments of private anonymous table blocks. The virtual mutex and table
addresses remain unchanged. Unaligned edges, nonzero values, errors and non-Linux
systems retain `memset`; the 32-bit path is unchanged.

Do not extend this to bit updates: clearing COMMITTED does not necessarily yield
zero. Decommit still materializes tables in the synthetic test; release recovers
the zero interior. Discarding adjacent metadata or freeing a published table
would violate protection semantics. A preexisting boundary expression can form
a next-block pointer for a zero-length final segment; this patch does not change
that expression or claim to fix it.

## Validation scope (October 2026)

Tests used Fedora 44 x86_64, Wine 11.18, Desktop 2.158.1177.0 and WebView2
154.0.4258.62, separate copied prefix/runtimes and validated inode-keyed PE cache.
Copying a prefix invalidates cache identity; regenerate separate backing for the
copy and verify mapped backing before comparing builds. No CDP or resource caps
were used in the graphical A/B.

- A native differential harness executes the exact helper extracted from the
  shipped patch: 6,360 cases including boundaries, nonzero values, immediate
  failure and partial-discard failure. Larger host-page masks are arithmetic
  simulations on a 4 KiB host, not kernel portability certification.
- Synthetic Win64 reservations of 64/256/1024 GiB reduced metadata from roughly
  16/64/256 MiB to 32 KiB. Reserved address space is not committed physical data.
- The behavior probe passed three runs per variant: 651 checks, guard fault,
  write-watch, neighboring metadata, query/protect, reuse and 800 threaded cycles.
- Wine `ntdll:virtual` (2,548 tests) and `kernel32:virtual` (30,964 tests) passed
  on rebuilt reference and candidate, with the same 112/140 known TODO cases.
- A sequential blank-report A/B, 61 samples per condition, averaged
  7.099 GiB reference versus 4.621 GiB candidate PSS in the final five minutes.
  Six renderers remained. Their attributed metadata fell from approximately
  2,355 MiB to 3 MiB. This is one observed pair, not a universal savings estimate.
- A private real-data project was manually refreshed, saved, closed and reopened;
  the user accepted visuals and values. The same ODBC correction was needed in
  both variants and is separate from this patch. Approximately three minutes
  after refresh, PSS+SwapPss was 9.884 GiB candidate versus 13.146 GiB reference.
  This logical footprint is not physical RAM (host swap used zram). Source/cache
  snapshots and exact reference refresh start were not fixed; no speedup claim.

No customer project, cache, credential, screenshot or modified vendor binary is
shipped here. Windows measurements used different Desktop/WebView versions and
metrics; they do not establish a direct cross-OS overhead percentage.

## Reproduction and remaining gates

Run `PYTHONPATH=src python -m unittest discover -s tests/unit -p test_vprot_sparse.py`.
This compiles only a small native harness when gcc is present; it never builds a
package, starts Wine or accesses a report. CI therefore verifies source-level
helper behavior and hash/preparation registration, not native application QA.

With MinGW in an isolated builder:

```sh
x86_64-w64-mingw32-gcc -O2 -Wall -Wextra -Werror -static tests/e2e/vprot-behavior.c -o /private/test/vprot-behavior.exe
x86_64-w64-mingw32-gcc -O2 -Wall -Wextra -Werror -static tests/e2e/vprot-micro.c -o /private/test/vprot-micro.exe
```

Run behavior under each runtime in an explicit disposable prefix. The micro
probe accepts reservation size in GiB (64/256/1024) and waits on stdin at each
printed stage: baseline, reserved, sparse commit, decommit, release, reserve and
release again. Measure PSS/SwapPss externally before sending a newline. Bound
memory, tasks and runtime with a cgroup. It touches one 4 KiB page per 4 GiB;
it never commits the entire huge range. Record binary hashes, cache state and
actual runtime loaded. Do not use a live customer prefix or infer heap use from
RSS/virtual size. The behavioral probe performs no database/network operation.

Long-duration soak, latency under reserve/release churn, additional applications,
and non-4-KiB host kernels remain unverified. Independent static review found no
new blocking correctness issue but noted syscall/lock contention as a performance
risk. This is not full compatibility certification. Integrating source does not
replace installed runtime archives or waive their integrity/build-provenance
checks; compile and verify a separately versioned runtime before distribution.
