# Connector compatibility policy

Compatibility is a scenario, not a database logo. Track the complete combination
of Desktop/runtime, driver and architecture, authentication, Import/DirectQuery,
and operation. A loaded library is not a successful login; a login is not a
validated refresh, cancellation, Save/reopen or Service refresh.

## Product direction

Keep the original Power Query connectors and database protocols. Prefer a driver
already supplied by the pinned Desktop. Offer a pinned, optional installation
recipe only when an external dependency is required, as with Connector/NET.
Do not build a replacement plugin for each database or install every driver by
default. Keep the connector code, recipes and tests in this repository.

Distinguish these three routes:

| Route | Dependency discovery | Configuration |
|---|---|---|
| Native Power Query connector with a bundled driver | Desktop's private provider/driver directory and connector implementation | Keep the original M function and native credential flow |
| Native connector requiring an external provider | Vendor package, architecture, dependency set and registration in the managed prefix | Optional verified recipe; detect external installations and avoid overwriting them |
| Generic ODBC (`Odbc.DataSource` / `Odbc.Query`) | Actual Windows/Wine driver manager, driver registration and DSN/DSN-less route | Diagnose the exact driver name, process architecture and DSN scope; host unixODBC alone does not prove the Windows path |

The current `connector install/status` CLI implements **MySQL only**. General
inventory, an ODBC/DSN interface and Redshift CLI commands are planned interfaces,
not existing commands. Do not document them as available until implemented.

## Evidence matrix

Record the following axes for each scenario:

- Pinned Desktop version, runtime checksum and Fedora/display environment.
- Connector M entrypoint, implementation option, exact driver version/hash,
  64-bit architecture, bundled/managed/external origin and registration route.
- Authentication: database password, Windows identity, IAM, browser OAuth/SSO,
  device code or service identity, as applicable. Validate each independently.
- Import or DirectQuery, encrypted transport and certificate validation.
- Library loading, handle allocation, network/TLS preflight, authentication,
  metadata navigation, typed reads/query folding, refresh/cancel and Save/reopen.
- Evidence date, reproducible synthetic fixture, passed/failed/blocked/not-tested
  result for **each** operation, and the exact limitation when blocked.

Use four user-facing classifications: **validated for the recorded scenario**,
**experimental**, **not tested**, and **known limitation**. Missing evidence means
not tested, not unsupported. An operation is never promoted from a lower-level
probe to a passing Desktop test. New runtime/driver checksums require revalidation.

Initial evidence:

| Scenario | Established evidence | Remaining scope |
|---|---|---|
| MySQL Connector/NET 8.0.33, database password, Import | Factory/dependency loading; loopback MariaDB read; synthetic Desktop refresh, counts/sums, Save and normal reopen | Real-server TLS, other server versions, DirectQuery and workload cancellation |
| MySQL explicit Windows credentials | Reproduced Wine impersonation/token failure | Proper Windows identity support; do not fabricate successful authentication |
| Bundled Simba Redshift 1.5.14.1017 + experimental shared ODBC forwarder, database password, Import | Offline Engine ENV regression; real Desktop authentication/schema metadata; one derived constant row independently verified; Save and normal reopen; user subsequently reported success with another real dataset and refresh cancellation | Independently audited business-table values/types, folding, server-side cancellation/post-cancel state, DirectQuery, Windows-driver TLS policy and managed installation |
| Bundled Amazon Redshift 2.2.0 | Same offline component checks | Explicit connector implementation 2.0 and its complete Desktop scenario |
| External AWS Redshift 1.6.3.1008 MSI, `Odbc.DataSource`, database password | Silent MSI in managed prefix and user-completed full wizard in fresh Wine-only prefix; identical vendor payload, automatic driver/default DSN, actual manager/ENV/DBC checks; real metadata Import, independent DAX and Save/normal reopen; maintenance UI canceled without file changes | Configured DSN GUI/connection; typed values/cancel, installer repair/uninstall, TLS negative controls and generic installer integration; credential-dialog session workaround recorded separately |
| Redshift IAM/SSO, generic ODBC DSNs and other sources | No new compatibility claim | Separate discovery, authentication and operation tests |

The [Redshift observations](redshift.md) are from October 19, 2026 on Desktop
2.158.1177.0 and the existing local 0.1.4 runtime candidate. The bridge affects the
shared ODBC manager and remains **experimental**, outside the published RPM/CLI.
Controlled schema navigation passed without selecting business tables; the user
subsequently confirmed a successful real-dataset test, without independent counts
or detailed operation coverage. The initial native-query approval
route remains blocked by a legacy 2×2 dialog. OS-level verified TLS preflight is
separate from the Windows driver's certificate policy. Private details stay outside
Git. Update each operation's result independently.

## Test layers

1. Run ordinary CI without cloud credentials: recipe/manifest/path/architecture
   guards and failures, supported original inputs, and rollback behavior.
2. In a dedicated Fedora QA session, enumerate the actual manager, load the
   selected driver and allocate/release its handles without contacting a server.
   Keep bundled/private driver discovery separate from global ODBC registration.
3. Use disposable local databases for supported password/TLS and typed-value
   regressions. PostgreSQL compatibility does not certify Redshift-specific
   SQL, authentication, catalogs or query folding.
4. Use an explicitly configured cloud test environment for IAM/SSO and actual
   vendor behavior. Begin with a read-only literal query and synthetic data.
   Enter interactive credentials in the native flow. Never copy production
   passwords/tokens into fixtures, CLI history, logs or CI secrets by accident.
5. Complete Desktop navigation, actual pointer/keyboard input, refresh/cancel,
   independent values and Save/reopen. Verify Service/gateway refresh separately;
   successful Desktop refresh does not certify a gateway installation.

Use the [QA isolation policy](../development/automated-qa.md): a test session must not take over
an unattended user's graphical session. Budget disk before creating profiles;
reuse a dedicated QA installation rather than cloning a production prefix for
each driver. Never rewrite a user's queries, authentication mode or TLS policy
as an implicit compatibility repair.

## Diagnostics and implementation order

The planned shared inventory should report bundled/managed/external/absent
drivers, bitness, versions, registration route, connector implementation and
the matching evidence scope. `doctor` should fail broken managed integrity and
report optional/untested capabilities separately. Offline status should not
launch a browser, connect to a database or read credential values.

After the current Redshift password/Import proof, implement this inventory and
its machine-readable matrix, then generic ODBC registration/DSN diagnostics.
Separate discovery, installation, credential handling and test execution. Keep
installation under the existing maintenance lock and idle-prefix rules, with
input checksums, original license notices, transactional activation and rollback.
Add a new driver recipe only for a demonstrated missing dependency.

### Proposed generic vendor-installer flow

Validate running the original Windows x64 vendor MSI in the managed Desktop
prefix as the normal external-driver installation route. A generic launcher would
select the active prefix/runtime, require an idle session, run the original wizard,
retain a local installation log, and inspect driver registration/loading afterward.
Allow the vendor's normal DSN configuration where needed. Registration success
does not establish server connectivity or the installer's arbitrary custom-action
compatibility with Wine. This interface is proposed, not implemented.

This avoids requiring a database-specific project plugin or recipe for every ODBC
driver. Optional pinned recipes remain useful for tested dependencies and convenient
downloads. Keep the shared ODBC-manager compatibility correction separate from
vendor driver installation and preserve it across maintenance. An externally
installed global driver need not be the driver selected by a bundled native connector.

Use the [ClickHouse Windows MSI/Power BI workflow](https://clickhouse.com/docs/integrations/connectors/data-visualization/powerbi-and-clickhouse)
as an external-installer acceptance case. The [driver's tagged documentation](https://github.com/ClickHouse/clickhouse-odbc/blob/v1.5.5.20260810/README.md)
describes architecture, registry registration and DSN defaults. The [AWS Windows
installation guide](https://docs.aws.amazon.com/pt_br/redshift/latest/mgmt/odbc-driver-windows-how-to-install.html)
also uses the vendor MSI. The separate [AWS MSI experiment](vendor-installers.md)
passed silent installation, a user-completed full interactive installation,
automatic registration and a real generic ODBC metadata Import on this runtime.
ClickHouse, arbitrary vendor installers and the AWS DSN setup GUI remain untested. These Windows
instructions alone are not evidence of Wine compatibility.

Bug reports should carry redacted error codes, component versions and the
failing stage. Exporting complete traces, connection strings, DSNs, user names,
SQL or tokens is not a suitable default support bundle. Use the application's
credential flow and document its actual Wine/storage limitations; do not promise
native Linux keyring integration that has not been implemented.

References: [Microsoft Redshift connector and implementations](https://learn.microsoft.com/en-us/power-query/connectors/amazon-redshift),
[AWS ODBC architecture and setup](https://docs.aws.amazon.com/redshift/latest/mgmt/odbc20-install.html),
[existing provider evidence](../user/connectors.md).
