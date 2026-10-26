# Database connectors

The support unit is a source/driver/authentication/operation combination. See
the [connector compatibility policy](../reference/connector-support.md) for bundled drivers,
generic ODBC, the evidence matrix and the planned product interfaces.

Database drivers remain the original Windows/.NET providers used by Power BI.
They are installed inside the same managed Wine profile as Desktop. Installing a
Fedora MySQL client, or running an installer in the default `~/.wine` prefix,
does not register a provider in the managed Desktop profile.

The CLI offers optional installation recipes, not replacement database plugins.
Recipes pin upstream downloads, dependencies and checksums, install the original
assemblies, register the provider using Desktop's ADO.NET provider directory,
and record the installed files for diagnosis. No connector is installed by
default. Original vendor installers may also work in the same prefix, depending
on their Windows requirements; this must be validated per installer. External
providers are reported as external and are never silently overwritten.

## MySQL

The current compatibility recipe uses Oracle Connector/NET **8.0.33**, with its
full .NET Framework dependency set in `connectors/mysql.lock.json`. This is a
pinned compatibility version, not a claim of support for every MySQL/MariaDB
release or an automatic upgrade channel for database drivers.

Read the upstream package licenses linked in the lock file, then close Desktop:

```bash
pbi-linux connector status mysql
pbi-linux connector install mysql --accept-license
pbi-linux doctor
```

The operation is scoped to the active profile. It verifies all packages before
publishing the provider directory and registration, rejects a running managed
session and rolls back its new files if activation fails. It does not make a
second complete prefix snapshot. Repeating a verified installation is a no-op.
In-place repair/update retains the selected connector in the existing profile.

The driver and dependencies are downloaded separately; they are not included in
the RPM, runtime archive or public project source export. Oracle's 8.0.33 NuGet
package declares GPL-2.0-only; dependencies retain their respective upstream
licenses. The local installation retains package provenance and embedded license
notices. No change to application accounts, stored database credentials, report
queries or TLS policy is made by installation.

`doctor` reports an absent optional connector without failing a local-only
installation. A managed installation is checked against its recorded file
hashes. External installations require separate native validation. File integrity
and factory loading do not establish server connectivity or a successful refresh.

## Data source settings

The legacy source list can be empty even when native entries exist: on Wine its
virtualized list may initialize with zero viewport/page size before the modal
appears. The compatibility patch requests the widget's own resize once after
showing the dialog, only if its cached page size is zero. It does not change
source discovery, permissions or queries. The MySQL provider dependency is a
separate requirement.

Real-report sources appeared, but a missing
cursor and unresponsive clicks were initially observed before interaction recovered after a
delay estimated at 10–60 seconds. The cause was not identified. The list fix does not certify input
latency; see [troubleshooting](troubleshooting.md).

Validation results and remaining server/TLS limitations are recorded in
[compatibility](../reference/compatibility.md). Report bugs with the connector status and
redacted error text; exclude passwords, connection strings, tokens and reports.

References: [Microsoft's MySQL prerequisite](https://learn.microsoft.com/en-us/power-query/connectors/mysql-database),
[Oracle's NuGet package](https://www.nuget.org/packages/MySql.Data/8.0.33).

## Redshift and ODBC

The pinned Desktop already contains Amazon and Simba Windows x64 Redshift
drivers. Both passed offline loading and handle-allocation checks. With a local
experimental ODBC-manager forwarder, native password authentication, schema
metadata, a derived one-row Import, Save and normal reopen passed. Another real
dataset and refresh cancellation also passed in manual testing. Independent
business-data/type checks, server-side cancellation and other authentication
routes still require validation.
See [Redshift evidence and limits](../reference/redshift.md). There is no managed Redshift
installation command yet. Generic ODBC/DSN discovery is separate from the
built-in `AmazonRedshift.Database` connector and its private driver INIs.

The original AWS x64 MSI also passed automatic driver/DSN registration, offline
loading and native generic-ODBC authentication/metadata Import in the managed
prefix, with no manual registration. See the [vendor-installer experiment](../reference/vendor-installers.md)
for exact version, independent one-row verification and the credential-dialog
focus/size workaround. A successful configured DSN is separate from this DSN-less
connection test.

## Validation and reproduction

On Fedora 44 native Wayland with Desktop 2.158.1177.0, the installed provider
factory, connection object and all 12 assemblies resolved in .NET Framework 4.8.
Power BI then refreshed a disposable two-table PBIP against local MariaDB
10.11.19: the sales query returned 3 rows; visible values were 120, 100 and 80,
with total 300; independent DAX confirmed the same count/sum. Both partitions
were committed (state 1) with empty errors. Data source settings displayed the
native MySQL entry. Save and a normal production-mode reopen retained 3 rows
and total 300 without the diagnostic manager or browser debugger.

The database was disposable and bound only to loopback. The test explicitly
selected unencrypted transport for this local fixture and requested removal of
only its own source permissions afterward; removal was not independently checked
in a fresh process. No real database was queried and no customer
report, credentials or TLS policy was changed. The native SQL confirmation used
its original DOM callback; physical clicking and mature geometry of that
particular confirmation were not separately certified. This is not certification
of TLS, every MariaDB/MySQL version, or every query in a production model.

From a checkout and prepared managed profile:

```bash
# No connection: factory, connection class and all dependency types.
python3 tools/test-mysql-provider.py
```

The optional `--loopback-port PORT` mode is exclusively for a disposable fixture
containing database `pbi_linux_fixture`, user `pbi_fixture`, password
`synthetic-local-test-only`, and table `sales(Produto VARCHAR(20), Vendas BIGINT)`
with rows `('Cafe',120), ('Cha',80), ('Suco',100)`. Create it in a temporary
MariaDB container, bind its port to **127.0.0.1**, and wait until an authenticated
`SELECT 1` succeeds before creating/querying the fixture. A successful
`mariadb-admin ping` alone can occur before initialization completes.

```bash
python3 tools/test-mysql-provider.py --loopback-port PORT
```

This tool only connects to 127.0.0.1 with those fixed synthetic identifiers and
executes a read-only count/sum. It deliberately does not accept production
credentials or a remote host. Power BI UI refresh must be validated separately
using a disposable report; a successful standalone provider query is insufficient.

Dynamic or hand-authored M queries can also produce Power BI's normal warning
that some sources may not be listed. A source is not the same as a query/table:
several blocked queries can share one connection. The layout correction does not
change native source discovery or synthesize additional entries.

## Windows credential override: `Invalid handle`

A real-report refresh on the installed RPM 7 failed with
`System.Security.SecurityException: Invalid handle` in
`WindowsIdentity.CreateFromToken` / `WindowsIdentity.Impersonate`, reached through
the engine's Windows credential override with an explicit username/password.
The provider was installed and all 15 doctor checks passed.

The pinned Wine `LogonUserW` implementation returns success with the placeholder
handle `0xdeadbeef`. A standalone test with fixed dummy credentials reproduced
the same exception and stack without contacting a database. This identifies the
Windows impersonation failure; it does not establish the outcome of a subsequent
database connection or certify production TLS.

A later user screenshot shows **Type: Database** for the source currently being edited. The trace does not establish that this source is still configured as Windows, nor exclude another source or an earlier credential state. Do not change a source already using Database solely on the basis of that trace.

For MySQL-native usernames/passwords, choose **Database** in the credential dialog.
For an existing source, use **Data source settings → select the affected source
→ Edit Permissions → Credentials → Edit**, then choose Database and enter the
database credentials. Keep the intended source scope. Do not change the query or
clear unrelated permissions. Microsoft lists both Windows and Database modes;
the limitation here is Wine's explicit Windows credential override, not a claim
that Power BI itself lacks Windows authentication.

Changing connector versions, deleting model caches or retrying the same Windows
credentials does not repair that placeholder token. Do not substitute the current
user's token and report a successful Windows logon: that would misrepresent the
requested identity. See [Microsoft's Database authentication steps](https://learn.microsoft.com/en-us/power-query/connectors/mysql-database#connect-from-power-query-desktop).
