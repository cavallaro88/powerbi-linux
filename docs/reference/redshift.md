# Amazon Redshift: experimental ODBC compatibility

The pinned Desktop **2.158.1177.0** already supplies two Windows x64 drivers:

| Connector implementation | Bundled driver | Observed file version |
|---|---|---|
| Legacy implementation | Simba Amazon Redshift ODBC Driver | 1.5.14.1017 |
| Implementation 2.0 | Amazon Redshift ODBC Driver | 2.2.0 |

Use the original `AmazonRedshift.Database` connector and enter database credentials
in Desktop. Microsoft describes this [username/password flow and the separate
implementation option](https://learn.microsoft.com/en-us/power-query/connectors/amazon-redshift).
The inspected project uses Import and native navigation, with no explicit
`Implementation`, SQL statement option or `Value.NativeQuery`. It does not use
`Odbc.DataSource` or a generic DSN. Do not rewrite its queries as a presumed fix.
The missing implementation option alone does not establish feature-switch state;
confirm driver selection from the actual worker's loaded modules or version trace.

## Reproduced failure and candidate

After the native credential dialog, Desktop initially failed with:

```text
Failed to allocate ODBC handle of type 'ENV'.
```

This failure occurs before server authentication. The pinned Engine's embedded
ODBC service loads the app-private Microsoft `PRIVATE_ODBC32.dll`. Direct handle
allocation and the actual Engine `OdbcInterop` / `OdbcEnvironmentHandle`
constructors reproduce the failure, with pooling both disabled and enabled.
Wine's `odbc32.dll` and both bundled drivers allocate/release handles successfully.
The exact lower-level incompatibility inside the Microsoft manager is not yet
isolated; a missing dependency is not established by this result.

The local experimental candidate forwards 170 **named** exports from an authored,
code-free `PRIVATE_ODBC32.dll` to Wine's real ODBC manager. It covers all 38 names
requested by the pinned Engine interop. It does not fabricate successful calls,
replace the database protocol, or alter authentication or TLS settings.

Wine does not provide six original exports, which the candidate deliberately
leaves absent: `DllBidEntryPoint`, `GetODBCSharedData`, `ODBCSetTryWaitValue`,
`SQLCancelHandle`, `SQLCompleteAsync` and `g_hHeapMalloc`. This is not full private
API, ordinal or ODBC 3.8 parity. **The manager is shared by ODBC-based connectors**;
passing the Redshift probe does not certify other sources or asynchronous calls.

Two bundled Windows drivers were registered in the managed prefix under
`HKLM\Software\ODBC\ODBCINST.INI`, with matching `Installed` values in its
`ODBC Drivers` subkey:

| Driver name | Driver path relative to Desktop `bin` |
|---|---|
| Amazon Redshift ODBC Driver | `ODBC Drivers/Amazon Redshift ODBC Driver/rsodbc64.dll` |
| Simba Amazon Redshift ODBC Driver | `ODBC Drivers/Simba Amazon Redshift ODBC Driver/AmazonRedshiftODBC_sb64.dll` |

No existing driver registration was overwritten. No DSN or credential was created
by the compatibility installation. The original manager and activation metadata
were backed up, the replacement hash was recorded for launch integrity, and a
private guarded rollback retains the original manager and removes only these two
new registrations. The runtime, resource policy and original projects are unchanged.

## Evidence — October 19, 2026

Environment: Fedora 44 x86_64, native Wayland, Desktop 2.158.1177.0, existing local
0.1.4 PaperWM runtime candidate, SHA-256
`5c1b78221ca28234e2e6dacf63c20c6d7ec7940a09470371b8378714b05a4bb0`.
Active forwarding DLL SHA-256:
`501043c21a26a23235bdedb4aad54fc475250dfd0046a6fe572c49224905b3f2`.
Exact input and driver hashes are recorded in
[`experiment.json`](../../connectors/redshift/experiment.json).

| Operation | Observed result |
|---|---|
| Both vendor DLLs: x64 loading, ODBC 3 ENV/DBC allocation/release | Passed offline; no connection |
| Actual Engine ENV constructors, pooling off/on | Original manager fails; forwarder passes |
| Real database username/password authentication | Passed through native Desktop and bundled Simba driver |
| Schema metadata navigation and Import of a derived constant row | Passed; no business tables selected |
| Independent local Analysis Services DAX | 1 row, sum 1, label `Redshift ODBC probe` |
| Save, graceful close and fresh normal launcher reopen | Passed; same independent DAX result without refresh |
| Original customer project preservation | All 487 inspected definition files unchanged; originals never opened/saved |
| User's subsequent manual test with another real dataset | User reported success after the local correction; table counts, types and exact operations were not independently audited |
| User's manual refresh cancellation | User reported successful cancellation; server-side termination, exact phase and post-cancel state were not independently checked |
| Explicit implementation 2.0, independently verified business-table values/types, folding, DirectQuery | Not tested |
| IAM, browser/Entra SSO, generic ODBC DSNs and Service/gateway refresh | Not tested |

The successful fixture uses the ordinary connector navigation path, forces a schema
`Name` read, then emits one constant row. See the endpoint-free
[metadata fixture](../../tests/fixtures/redshift-metadata.m). It proves a real
connection and metadata read, not the correctness or performance of the original
project's table queries. A startup DAX check before the catalog finished loading
was retried after readiness; it was not counted as a passing restore.

After these controlled checks, the user tested another real dataset and confirmed
success on October 19, 2026. This is additional manual acceptance evidence for the
local correction. The user subsequently confirmed that refresh cancellation also
worked. Exact row counts, type coverage, folding, server-side cancellation and
real-dataset Save/reopen remain outside that reported evidence. The agent's
preservation check above predates these user-run tests.

An earlier literal `Value.NativeQuery` fixture encountered a separate legacy
native-SQL approval dialog stuck at 2×2 pixels. No approval was bypassed; that query
was not completed. Native-query approval remains a known limitation, separate from
ODBC ENV allocation. The inspected project's native-navigation queries do not use
that path.

A separate OS-level preflight verified PostgreSQL TLS/certificates at the selected
endpoints. This does **not** certify the Windows driver's certificate policy. Private
endpoints, credentials, logs, cache and screenshots remain outside Git.

## Reproduce the component check

The source contains the forwarding definition, input hashes, builder and an offline
Engine regression probe. It does **not** contain modified Microsoft DLLs or vendor
drivers. The builder requires `x86_64-w64-mingw32-gcc` (also present in the project's
[runtime builder image](../../runtime/Dockerfile)); the normal RPM does not require it.
From a source checkout with that compiler available:

```bash
python3 tools/redshift-odbc.py --output .local/odbc-build build
# Close Desktop; BASELINE is an untouched pinned private manager, not a candidate.
python3 tools/redshift-odbc.py --output .local/odbc-probe probe \
  --baseline /path/to/original/PRIVATE_ODBC32.dll \
  --candidate .local/odbc-build
```

Both commands require a new output directory. The probe checks pinned input hashes,
rejects a busy managed Wine session, and compares both pooling settings using the
actual Engine constructors. It opens no report and performs no login, SQL or network
request. A fresh source build reproduced the locally active candidate byte for byte
with the cached builder toolchain. Different toolchains must be recorded and tested.
These commands **build and test only**; they do not activate or remove the candidate.

## Productization gates

The separate [vendor MSI test](vendor-installers.md) installed AWS's original
1.6.3.1008 Windows driver and default DSN without manual registration. A fresh
generic `Odbc.DataSource` fixture authenticated and imported metadata successfully,
with independent one-row verification. This tests a different route from the
bundled native connector; it does not change existing project queries or bundled
driver selection. The native ODBC credential dialog needed a session-only
focus/size workaround before the user could retry.

The bridge is active only as a local experiment. **RPM 13 does not ship or enable
it**, and the current `connector install/status` CLI still manages MySQL only.
There is no `connector install redshift` command and no additional driver download
was needed for this test. Manual vendor installation alone would not correct the
app-private manager failure reproduced here.

Before an opt-in managed Redshift recipe is released:

1. Add transactional activation/status/removal with idle locking, input/runtime
   checks, ownership of the two new registrations, original backup and rollback.
2. Preserve and verify the chosen bridge across repair/update; current production
   maintenance does not manage this experimental DLL entry as a supported recipe.
3. Exercise typed reads, query folding, refresh/cancel, errors and Save/reopen with
   synthetic server-side tables. Regress other ODBC connectors sharing the manager.
4. Validate implementation 2.0 and each additional authentication route separately.
   Keep native-query approval and Windows-driver TLS validation as explicit gaps.

Follow the [connector support policy](connector-support.md) for the broader matrix
and isolated test lab. No per-database replacement plugin is required by this result.
