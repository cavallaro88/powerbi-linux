# Original Windows ODBC installer experiment

The intended external-driver workflow is to download the vendor's Windows x64
installer, execute it in the managed Desktop prefix, configure its connection and
use the original Power Query connector or generic ODBC route. The generic
installation UI/CLI is still a proposal; no `driver install` command exists yet.

## AWS Redshift MSI — October 19, 2026

The [AWS Windows installation page](https://docs.aws.amazon.com/pt_br/redshift/latest/mgmt/odbc-driver-windows-how-to-install.html)
links to [AmazonRedshiftODBC64-1.6.3.1008.msi](https://s3.amazonaws.com/redshift-downloads/drivers/odbc/1.6.3.1008/AmazonRedshiftODBC64-1.6.3.1008.msi).
This is the exact package tested, not a recommendation to automatically choose
the 1.x branch for new installations or a test of the separate 2.x MSI.

| Input | Recorded value |
|---|---|
| MSI product/version | Amazon Redshift ODBC Driver 64-bit, 1.6.3.1008 |
| Summary architecture | `x64;1033` |
| Product code | `{7DD810B2-3864-4C61-8E4A-11679FBCBA3F}` |
| Download size | 17,879,040 bytes |
| Locally recorded SHA-256 | `e446b000eeae2c0587195e0afe424b27706cb052d9ef21ea018f9341b712824c` |
| Driver registration | `Amazon Redshift (x64)` |
| Installer's default system DSN | `Amazon Redshift ODBC DSN` |

The SHA-256 identifies the downloaded input; it was not compared with a separately
published vendor checksum or an independently verified Authenticode signature.
The package and vendor license files are retained privately, not redistributed
in this repository, source export or RPM.

The managed prefix was idle. After checking for existing vendor keys/DSN/path and
backing up affected existing CRT files and activation metadata, the unmodified
MSI ran through `msiexec /i /qn /norestart /L*v`. It returned **0** in 5.74 seconds.
This first check tested the MSI execute sequence in silent mode. The subsequent
full interactive check is recorded below.

The installer populated the driver/DSN registrations automatically. No driver DLL
was manually copied and no ODBC registration was manually added for this package.
The actual Wine ODBC manager enumerated both the new driver and its default DSN;
the installed 1.6.3.1008 DLL loaded and allocated/released ODBC 3 ENV/DBC handles.
These offline checks sent no credentials or SQL.

The vendor directory occupies approximately 54 MiB. The MSI also installed/updated
six CRT files in the prefix's `system32`; this is broader than adding a driver
registration. Existing app patches, bundled driver files, active/previous manifests
and resource settings were verified unchanged. No full profile was cloned and no
original customer report was opened. Backup/uninstall and shared-CRT behavior must
be addressed before promising a transactional generic installation facility.

The test uses the exact runtime checksum recorded in the
[Redshift evidence](redshift.md#evidence--october-19-2026). The existing shared
ODBC-manager correction remains active. Installing this MSI does not remove the
need for that correction, replace Desktop's private bundled drivers, or select
this external driver for existing `AmazonRedshift.Database` queries.

## Interactive installer follow-up

The same unmodified MSI subsequently ran with its **default full UI** in a fresh
Wine-only QA prefix using the same runtime checksum. No quiet/passive flag or
license-acceptance property was supplied. The user completed the original wizard
manually and confirmed completion; the installer exited **0**. Its 115.3-second
elapsed time includes manual interaction and is not an installation benchmark.

All **19 vendor files** in the default installation directory matched the real
silent installation byte for byte. The actual ODBC manager enumerated the driver
and its default DSN; a native x64 probe loaded the registered driver and allocated
and released ODBC 3 ENV/DBC handles. That check performed no authentication, SQL
or network operation. This establishes a working interactive MSI installation on
the tested runtime, in addition to the separate real Desktop connection test.

The fresh prefix contained neither Power BI nor .NET and was not copied from the
user's profile. Its disk use grew from approximately 494.5 to **565.6 MiB**. After
verification its processes were stopped and the prefix was deleted, reclaiming
that space; private logs and probe sources remain available. The driver's live
Desktop authentication/Import evidence comes from the managed prefix, not this
Wine-only environment.

Reopening the MSI in the existing managed prefix presented the expected
**Change, repair, or remove** screen. Change was disabled because this package has
no independently selectable features. The original cancel flow completed with
`UserExit` in the MSI log; the Unix process status was 66, consistent with the low
byte of Windows `ERROR_INSTALL_USEREXIT` (1602). App/bundled/vendor/CRT file hashes
and activation/settings metadata were unchanged. The registered driver/DSN and
offline loading/handle checks passed again afterward. Repair and removal were
not executed. A future installer launcher must capture and interpret Windows MSI
exit status correctly rather than treat a truncated Unix status as a full MSI code.

The interactive installer required no session resize or permanent UI patch.
The credential-modal observation below concerns the separate Power BI login UI.

## Native Desktop connection test

A new disposable PBIP uses `Odbc.DataSource` with the exact installed driver name,
`HierarchicalNavigation=true` and `SSLMode=verify-full`. Its M expression navigates
metadata and derives one constant row; it selects no business table and requests
no native SQL approval. Its endpoints and model remain private.
An endpoint-free [M fixture](../../tests/fixtures/redshift-odbc-metadata.m) records
the same test route for reproduction with a disposable local report.

Desktop opened the native ODBC Database credential dialog. The worker loaded the
new DLL from the vendor installation directory. The initial attempt reached the
Redshift server but returned SQLSTATE 28000 / password authentication failed.
After the user edited the native fields and retried, authentication and metadata
Import **passed**. Independent local Analysis Services DAX returned one row, sum
1 and label `Redshift MSI probe`; the report displayed that row and total, and
the sole partition was ready with an empty error. Credentials were entered
directly in Desktop, not collected by the agent. No TLS setting was weakened.

The credential dialog exposed a separate UI issue: the user could not interact
and footer controls were clipped. A compositor click activated the enabled modal,
and a session-only resize exposed the complete form/buttons. The username field
was focused without changing its value. The user then confirmed editing and
connection worked. No permanent UI patch is planned as part of this installer
test; retain the observation for investigation if it recurs. The workaround does
not certify the ordinary first-attempt credential layout.

The one-row model was saved and gracefully closed. Fresh normal-launcher reopen
passed without refresh; independent DAX again returned one row, sum 1 and the
expected label. The default DSN contains vendor example placeholders.
Enumeration is not proof of a configured working DSN: the live test uses a
DSN-less connection. Editing the driver's DSN setup GUI and a successful DSN-based
connection remain separate checks. [Microsoft documents both ODBC connection
routes](https://learn.microsoft.com/en-us/power-query/connectors/odbc).

`SSLMode=verify-full` was explicitly configured, matching the
[AWS TLS documentation](https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-ssl-support.html).
No untrusted-certificate or wrong-hostname negative control was performed, so
this is not complete certificate-policy certification.

## Reproduce offline discovery and loading

After installing a Windows driver in the managed prefix, close Desktop and run:

```bash
python3 tools/test-odbc-driver.py \
  --driver 'Amazon Redshift (x64)' \
  --dsn 'Amazon Redshift ODBC DSN'
```

`--dsn` is optional. The tool requires an idle managed installation, compiles the
project's own [native probe](../../tests/e2e/odbc-driver.cs), checks x64 process and
driver registration, enumerates the manager, loads the actual registered DLL and
checks ODBC 3 ENV/DBC allocation/release. It creates private logs and `result.json`
under ignored `.local/odbc-driver`. It never installs, connects, reads credential
values or opens a report. A busy-session refusal was also checked without creating
the requested evidence directory.

Remaining gates include DSN GUI/connection, installer repair/uninstall, shared
dependencies, full typed data/cancel coverage,
2.x and other vendor installers. A passing MSI does not certify arbitrary custom
actions, Windows integrated authentication, IAM or browser callbacks under Wine.
