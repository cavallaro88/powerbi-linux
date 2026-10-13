# Proactive QA

User testing remains useful for real workflows, but routine compatibility
failures should be found before a new RPM is offered. The current work adds a
repeatable entry point, evidence reports and a reusable Options audit. It does
not yet supply a fully unattended native Desktop lab.

## What runs now

From the source tree:

```bash
python3 tools/check-product.py
```

This runs the Python tests, syntax compilation, desktop-entry validation and a
fresh source export. Each check has its own log and deadline. `result.json` and
`junit.xml` distinguish passed, failed and blocked checks. Timeouts, missing
executables and incomplete evidence cannot become successful checks. The report
explicitly lists GUI obligations outside that run's scope.

The public-project workflow runs the same command on push, pull requests,
manual dispatch and a daily UTC schedule. It retains reports/logs for 14 days.
The workflow is prepared source, not a service activated on this notebook. It
starts operating remotely only when the public project/workflow is published
and enabled. GitHub's [schedule rules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
and [artifact action](https://github.com/actions/upload-artifact) describe that
execution and retention; this change did not publish or trigger any workflow.

The local quick run on October 16 passed all four checks, including **59 unit
tests**. This is later development-source validation; the installed RPM 9 and
its existing artifact hashes remain unchanged.

## Native components

```bash
python3 tools/check-product.py --suite components --qa-root /path/to/dedicated-qa
```

This adds QA doctor, offline HTML/native callback, seven numeric interop cases,
synthetic sign-in settings and synthetic save-dialog components. It requires an
already provisioned, distinct QA installation under:

```text
QA_ROOT/data/powerbi-linux/active.json
QA_ROOT/data/powerbi-linux/profiles/...
QA_ROOT/data/powerbi-linux/runtimes/...
QA_ROOT/config/powerbi-linux/...
QA_ROOT/cache/powerbi-linux/...
```

Provision it with the normal setup recipe and QA XDG directories, using accepted
official installers. The runner never creates a profile copy automatically and
never uses a production prefix as fallback. It refuses missing QA installations,
prefix paths escaping QA, and an already busy QA prefix. The Wayland socket is
retained as an absolute address when the test's XDG runtime directory changes.

Native checks require the QA graphical session. Dedicated test users/VMs must
provide their own Wayland desktop. Do not schedule GUI checks in a working user's
session: test windows and compositor input can take focus. Disk estimates and a
retention budget are required before provisioning a full extra installation;
the current host has a history of disk pressure. No extra approximately 9 GiB
profile has been created by this work.

The native suite was not run in this change: a separate QA installation has not
been provisioned. Its missing-environment path is recorded as **blocked**, with
exit code 2 and a JUnit skipped entry, not as a successful native run. The new
isolation and report guards have unit tests. Component success still does not
prove the corresponding Desktop button receives physical input.

## Reusable Options audit

`tests/automation/options-audit.py` ports the previous private 22-tab audit into
public project code. It requires the diagnostic copy's private IPC directory:

```bash
python3 tests/automation/options-audit.py \
  --bridge /path/to/private-bridge --output /path/to/new-evidence
```

`OptionsAuditManager.cs` is its source-only diagnostic companion, compiled
against the QA installation's `PowerBICompositionManager.dll` with references to
`System.Windows.Forms.dll` and `System.Drawing.dll`. It is loaded only by a
renamed `PBIOptionsAudit.exe` diagnostic copy, with:

```text
APPDOMAIN_MANAGER_ASM=OptionsAuditManager
APPDOMAIN_MANAGER_TYPE=OptionsAuditManager
PBI_OPTIONS_AUDIT_DIR=<Windows path to private bridge>
```

The directory must exist and be private. Prepare only the generated
`Synthetic.pbip` fixture, then open File → Options and settings → Options in that
QA copy. The manager requires the exact synthetic main window and evaluates
requests only in its Options WebBrowser. It is absent from production helper
installation. It does not enumerate other processes or load a user's report.
This preparation/opening is still a developer operation: automatic QA Desktop
launch/menu navigation and teardown have not yet been integrated.

The audit serializes requests, correlates every response with a fresh nonce,
requires the synthetic scope marker and fails on deadlines or a changed/empty
tab inventory. It checks all expected tabs for visible content, both footer
buttons, usable scroll geometry and JavaScript errors. It restores the original
navigation/error-handler state and never submits OK or changes setting inputs.

The earlier private audit passed all 22 tabs on runtime 0.1.2. The public port's
negative cases passed unit tests and the new C# companion was compilation
checked. It has not yet completed a live end-to-end run with that new companion.
Do not transfer the old live result to the new harness. Physical pointer, focus,
window resize and localized-label coverage remain separate assertions.

## Work required for an unattended native lab

1. Provision a reusable Fedora 44 GNOME Wayland test user/VM with synthetic
   fixtures, no account secrets, a disk budget and a recoverable clean baseline.
2. Integrate diagnostic Desktop launch, menu navigation, the public Options audit
   and deterministic teardown. Add Sources, Privacy Level/OK/Cancel, nested
   dialogs, save confirmation and resizing. Record initialization/response time.
3. Add compositor pointer tests. DOM callbacks and backend success must not
   satisfy mouse/focus assertions. Keep native frames and browser evidence
   separate so one cannot hide a failure in the other.
4. Run small UI refresh, cancel, saved-data and desktop-association scenarios on
   each candidate. Run the existing large fixture and prolonged session nightly
   or before release, tied to the exact runtime checksum.
5. Publish retained failure reports and gate a candidate on required results.
   Existing `tools/release-check.py` remains the release evidence gate; the quick
   runner does not bypass it. No native runner or autonomous repair service has
   been installed or enabled yet.

A failed test should produce a reproducible case for development; it should not
automatically patch production or update a user's installation. Authentication
with MFA and enterprise-specific data sources still need representative user
validation. Broad scripted coverage reduces that burden without claiming zero
remaining bugs.

## Cursor resource regression added later on October 16

`python3 tools/test-cursor-resource.py --runtime /path/to/runtime` independently
creates a small Wine-only test prefix and checks cross-process standard cursor
resources. Twelve checks passed on 0.1.3; see [cursor scope](cursor.md). The own
prefix was removed after the test. This does not provision the separate Desktop
QA installation or complete the pending public compositor/GUI orchestration.

## Post-publish Store rating regression, October 18

`python3 tools/test-store-rating.py` invokes only the local rating entrypoint
with null services, no window or report. The original reproduced the WinRT
assembly error; the corrected entrypoint returned a completed Task. This check
is included in the components suite. The October 18 quick run passed all four
checks, including 60 Python tests; cloud publishing is separate from this offline
regression. See [publishing](publishing.md).

## October 18 cache and icon coverage

The RPM 11 quick suite contains 65 unit tests. Native cache normalization adds
ten own-input checks, and the components runner includes that tool alongside
the Store-rating regression. Native checks were run individually on the host;
the dedicated QA installation remains a separate obligation. A private populated
158-table copy additionally passed a genuine TMDL measure change, Desktop Save,
graceful close and fresh normal reopen. Counts/states matched, including one
preexisting query error. That private evidence is sanitized before export; real
models and ABF files never enter the public suite. These tests do not constitute
an unattended end-to-end lab. See [cache evidence](model-cache.md) and
[local icon extraction](app-icon.md).

## Repository and upstream checks

After promoting the product to the repository root, quick QA runs 73 unit tests
and five checks: units, syntax, desktop entry, Neutron review consistency and
source export. The upstream audit validates the 87-commit/59-patch ledger and
inactive candidate hashes without network access. Supplying an upstream checkout
also verifies every recorded patch against its frozen commit and refuses a
checkout HEAD that has not been reviewed.

Eight build-provenance regressions and a real negative packaging entry check
protect against stale/unreviewed builds. The separately run DPI arithmetic tool
compiled the actual Wine helper before and after a candidate: six of fourteen
controls failed before, none after. This source-level check does not replace
server compilation or compositor regression. See [Neutron decisions](upstream-neutron.md).
