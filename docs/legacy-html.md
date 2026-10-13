# Legacy HTML dialogs

Some Desktop dialogs still use Wine MSHTML/Gecko, including database
credentials. A refresh can wait for one of these dialogs while its progress
animation and Cancel button appear frozen. A responsive main thread or CPU
activity alone does not establish that data loading is advancing.

The Fedora reproduction on October 14 had a 2 × 2 credential window disabling
both the report and the refresh dialog. A read-only managed stack identified
`CredentialsChallengeResolver.ShowResolveDialog`. Cancelling that request
revealed the original refresh errors asking for MySQL credentials.

## Corrections

Setup/repair registers Wine's own `mshtml.dll` in both architectures after the
installers. The affected prefix had HTML COM class entries but lacked the
`about:` and `res:` protocol handlers and the `text/html` MIME handler. Installing
Gecko alone did not restore these entries. Doctor now checks the persisted
registrations and the activated UI patch version without starting Wine or
opening a browser. Upgrading only the RPM leaves this check pending until
`pbi-linux repair` applies the recipe to the existing installation.

The supported local `Microsoft.Mashup.Client.UI.dll` receives two small changes
to embedded JavaScript resources:

- In `ts/jquery.extensions.js`, an `E_NOTIMPL` from the DOM `textOverflow`
  setter enables a jQuery hook using `style.setProperty`. Other errors propagate.
  The credential title's SmartTip otherwise interrupts dialog initialization.
- In `ts/floatingdialog/floatingdialog.js`, a deferred pass clears the credential
  sidebar's stale inline height and repeats the existing layout calculation
  after `showDialog` assigns the final width. Error display can calculate that
  height before the final width is assigned, leaving the credential fields above
  the visible area even after HTML initializes. The pass runs only for a
  credential challenge; other legacy dialogs keep their existing sizing.

The recipe checks the exact original assembly and final output hashes, preserves
PE/resource sizes and IL, and retains the original backup. It does not replace
the credential backend, select an authentication method, supply a password,
change source permissions or approve native queries. The existing localized
HTML controls, credential scope choices and cancellation callbacks remain in use.

Updating an RPM changes the CLI recipe; it does not rewrite an existing profile
or reload assemblies in a running Desktop. Close Desktop before setup/repair.
An older CLI repair recipe does not include these corrections. Save pending work
before restarting a session that already loaded the old assembly.

## Component test

```bash
python3 tools/test-legacy-html.py
```

This opens only its own offline test window and checks rendered HTML,
JavaScript evaluation and a callback to .NET. It does not patch the installation
or interact with Desktop. It is a component test, not certification of every
Desktop HTML dialog or database connector.

See [native close confirmation](native-dialogs.md) and
[refresh cancellation](refresh-cancellation.md) for the separate close/save and
engine cancellation paths. A cancelled credential request does not establish
that cancelling an already-running database query succeeds for every connector.

## Credential dialog validation

On Fedora 44 Wayland, a fresh Desktop process opened a disposable two-table
PBIP whose MySQL source used the closed loopback address `127.0.0.1:65534`.
The first credential window measured 702 × 381, with 700 × 379 HTML content;
fields and Cancel were inside the viewport without a diagnostic sizing script.
Native mouse messages switched to the Database tab and then clicked Cancel.
The credential window disappeared within the first observation at 0.129 seconds.
After dismissing the refresh result, the main native window was enabled again.
No credential values were entered or submitted.

The diagnostic Desktop copy used a private inspection helper and test-only
cgroup limits of 10 GiB RAM / 2 GiB swap. The RAM ceiling was reached, with zero
OOM events or kills. Product defaults were unchanged, and the test process and
its browser policy were removed afterward. These checks cover first-show
layout, tab interaction and credential cancellation; they do not certify MySQL
authentication, network refresh completion or every connector.
