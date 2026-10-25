# Developer E2E tests

Use a separate Fedora user or isolated XDG directories with a disposable installation. Never use a production dataset or the investigation's private RDS credentials. The probes are source-only and must be compiled against the selected runtime/prefix; they are not part of the normal production manager.

`python3 tools/test-legacy-html.py` runs `legacy-html-probe.cs` in its own offline
window, checking HTML loading, JavaScript and a native callback. It does not
submit credentials or change Desktop. Full credential dialog validation must
also check first-show sizing, visible inputs and native Cancel with a disposable
source. See `docs/reference/legacy-html.md` for the registration and JavaScript recipe.

`refresh-probe.cs` and `adomd-probe.cs` retain the corrected timeout, XMLA error propagation, DAX and partition-commit checks from the investigation. External TMSL processing remains a diagnostic test, not supported Desktop integration. `mysql-probe.cs` is optional and takes credentials through environment, not a committed `.env`.

`generate-fixture.py OUTPUT --tables 158` creates a synthetic PBIP/TMDL model with the sales table and generated fact tables. `--rows 10000` controls fact rows. Add `--relationships` to reserve one of the 158 tables for a shared dimension and create active relationships to all 156 fact tables. The harness also verifies that a dimension filter reaches a fact-table sum. It requires no database or credentials. The included table visual originated from the investigation's synthetic Cafe/Cha/Suco report, not from enterprise reports. Do not interpret equal table count as equal memory pressure to a real model: stress certification must also match cardinality, relationships and visual complexity.

The generator creates metadata and queries, without `.pbi/cache.abf`. Desktop opens these definitions without imported data; a blank DAX sum before refresh is expected. For a cache comparison, save a populated synthetic model as PBIP using Desktop, copy the entire project to two disposable directories, and remove only the second copy's `.pbi/cache.abf`. Open each copy in a fresh session and record loaded rows, visible values and refresh completion separately. Do not use a customer cache in public fixtures. Desktop's diskless Analysis Services instance rejects a regular AMO `Database.Backup` request; that is not a valid cache-generation method.

The generated `expected.json` declares `data_loaded: false`. After `session.py --ui-refresh --save` verifies the loaded model and observes Desktop Save, it changes this fixture metadata to `true` for a separate reopen. When removing the cache from a disposable comparison copy, set that copy's expectation back to `false`.

Compile probes using the prefix's .NET compiler, or Mono in the builder. Use `session.py` for bounded document opening, DAX checks, memory sampling and explicit UI-refresh testing with diagnostic CDP. For the synthetic fixture it checks every fact table's row count, not just the sales sum. The diagnostic harness additionally needs `websocket-client` and Pillow in its developer environment; neither is a production CLI dependency. Test mode is opt-in and must use a freshly started session; it never changes a running normal session.

Compile the native UI probe with the Unicode entry point so filenames and window titles with accents are preserved:

```bash
x86_64-w64-mingw32-gcc -O2 -Wall -municode tests/e2e/ui-probe.c -o /path/to/compiled-probes/ui-probe.exe -luser32
```

`session.py --save` exercises Desktop Save for a disposable project and requires an updated PBIX or model cache. Reopen that saved project in a separate session. For the CSV harness's `sales` table, pass `--sales-table sales`; the generated PBIP fixture defaults to `Table`.

Large-report certification needs visible values after UI refresh, successful save/reopen and a two-hour soak. If CDP loses its page after renderer restart, rediscover `DevToolsActivePort`; record the event and do not treat missing evidence as a pass. `session.py` produces an evidence summary, not an automatic claim of full visual/save certification.

For prolonged use, `session.py --seconds 7260 --exercise-ui` checks the synthetic table visual and changes its sort every five minutes. It records process PSS, GPU process replacement, cgroup RAM/swap/OOM and the report page's V8 heap. Native Wayland capture must also be inspected; a browser screenshot alone does not prove delivery to the desktop window. Do not use cross-process GDI readback to capture another process's window surface.

The native hook samples buffers at most every 500 ms. It does not record every submitted frame. The harness captures the current document's native sample before taking a browser screenshot and records its HWND and timestamp/age. Retain discrepant samples and inspect them separately; successful DAX/browser output cannot turn a blank native sample into a visual pass.

`desktop-session.py` exercises `gio open` with the production desktop entry and MIME defaults, checks a new Analysis Services workspace, verifies total 300 and waits for responsive native windows. `--additional` opens another synthetic document while preserving the earlier document process. `--make-default` explicitly sets associations for the disposable test user. No diagnostic mode is enabled by this harness.

For an actual **Blank report → Get Data menu → Text/CSV → Load** flow, run `csv-session.py tests/fixtures/sales.csv --probes /path/to/compiled-probes --output /path/to/new-evidence`. It uses the direct source entry and independently checks sum 300 through DAX. Add `--save-report '/path/to/new/CSV São Paulo.pbix'` to create a table visual, check its rendered values and save through Desktop. Inspect the screenshot and separately reopen the saved report; the harness does not automatically certify those manual reviews.

This direct entry passed in the clean prefix with the current runtime. In the earlier clean-prefix test, the general source chooser was blocked by the OneLake email popup leaving Get Data disabled; use `--entry all-sources` to reproduce that limitation. No credentials are supplied by either route.

Optional provider checks are available through `python3 tools/test-mysql-provider.py`.
It compiles `mysql-provider-probe.cs`, loads the original registered factory and
all 12 dependency assemblies, and normally makes no network request. Its optional
loopback mode uses only the fixed synthetic fixture in `docs/user/connectors.md`.
Desktop UI refresh/source enumeration and production-mode save/reopen are separate
checks. The recorded MySQL scenario used a disposable local MariaDB server, not
customer connection settings or credentials. The source list regression must
compare native entry count, HTML row count and cached viewport/page size after
modal show; an initial transient 2x2 frame is insufficient to diagnose a steady
layout failure. The general OneLake chooser has not been revalidated after the
later Microsoft browser sign-in correction.

The repeatable check runner and reusable 22-tab Options audit are described in
[proactive QA](../../docs/development/automated-qa.md). Native suites require a distinct QA
installation; missing environments are blocked rather than passed.
