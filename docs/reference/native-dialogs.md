# Native close confirmation

RPM 0.1.0-3 adds a native WinForms confirmation for unsaved changes on Fedora.
It changes only `ApplicationCloseHandler.ShowYesNoCancelSaveChangesPrompt`.
The helper uses Desktop's original localized title, question and three button
labels. Save returns the existing modal result 6, Don't save returns 7, and
Cancel returns 2. Desktop retains responsibility for saving and closing.

Enter defaults to Cancel. Escape, the question's title-bar close button, an
unexpected response or an error displaying the question also return Cancel.
No button is selected automatically by the product. Import dialogs and refresh
cancellation are unchanged.

## Why use a native confirmation

The reported close failure left the main window responsive but disabled by an
owned modal measuring 2 × 2 pixels. Its legacy HTML component did not expose an
initialized document. The composition transport also stopped painting browser
surfaces while their main window was disabled, explaining the white background.
The exact reason the legacy dialog failed to initialize remains unresolved.
A native question avoids that HTML initialization path for this simple decision.

The later refresh investigation identified missing Wine HTML registration and
embedded JavaScript failures in credential dialogs. See
[legacy HTML dialogs](legacy-html.md). The native close confirmation remains
the supported save/close question.

## Installation and validation

The helper and patcher ship as source. Setup/repair compiles them with the
installed .NET compiler, signs the helper with a locally generated key, verifies
the supported method/enum shape, and writes the patched assembly. The helper is
included in installation integrity hashes. The temporary key is removed on
success or failure. The existing Wine/DXVK runtime archive is unchanged.

The following checks passed on October 14, Fedora 44 x86_64 Wayland:

- All 31 Python unit tests, both on the host and during RPM build, including
  preservation of Desktop on native-helper compilation or patch rejection.
- Mono compilation, strong-name verification and negative patch-input checks.
- Native synthetic patched-method tests: original labels, Save/Don't save/Cancel,
  safe default mappings, question closing, modal ownership and owner recovery.
- Real Desktop with a disposable PBIP: Cancel retained the document; Save closed
  it and produced a cache; reopening preserved the visual total 300 and 200 fact
  rows; Don't save closed after an unsaved visual sort.
- The actual helper installation pipeline, including fresh local signing and
  WinRT remapping, passed with application-file backups. The resulting profile
  reopened through the installed launcher in normal mode, returned the expected
  data, responded to native probes and closed. No diagnostic browser endpoint or
  RAM/swap/CPU cap was enabled for that normal-mode check.
- The RPM installed through DNF in a Fedora 44 container; packaged CLI/resource
  checks, helper source inclusion and RPM integrity passed. Native GUI checks
  are separate from this container check.

These checks cover the synthetic scenarios above, not every report, connector,
locale or save-error flow. The three explicit confirmation choices were exercised
with diagnostic mode enabled; the final normal-mode reopen/close used a clean
saved document and did not require a question.

Upgrade the CLI package before running repair: an older CLI's repair recipe can
replace the Desktop DLL with its older patch set. Updating only an RPM does not
rewrite a running Desktop process. Apply setup/repair with Desktop closed.

## Standalone component test

```bash
python3 tools/test-save-dialog.py
```

Run this in an installed user's Fedora session. It compiles and signs a temporary
helper, patches an offline preview, and exercises only its own synthetic forms.
It does not replace installation files or choose a response in Desktop. Logs
remain under `.local/save-dialog/` and its temporary key is removed.

If the native confirmation is already installed, the test reads the verified
preserved original DLL for its preview. That preview still requires WinRT
remapping and must not be copied into an installation. The script records this
condition explicitly. Component testing does not certify real Desktop saving.

See [refresh cancellation](refresh-cancellation.md) for the separate Cancel test.
