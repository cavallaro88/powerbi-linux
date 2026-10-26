# Options dialog — runtime 0.1.2 / RPM 9

## October 21: Options resizing and selection

RPM 15 adds a guarded correction for both Desktop 2.158.1177.0
and 2.159.883.0. No runtime replacement is required. Close Desktop, install the
updated project package and run `pbi-linux repair`; upgrading the package alone
does not replace the per-user application assembly.

The reported monitor is **3440×1440 at 100%**. The native Fedora test
monitor is 1920×1080 at 125%; a 3440×1440 browser viewport is simulated separately.
That viewport test is not certification of a physical ultrawide/COSMIC session.

The native floating dialog lacked `WS_THICKFRAME`, so Wayland advertised a fixed
minimum/maximum size despite the HTML resize handles and `IsResizable` flag.
The bounded native recipe enables that style only for the culture-independent
`SettingsDialog` name when its original flag is true. Other floating dialogs
retain their original styles. The drop shadow and original native resize
callbacks remain. The eight-case enum switch is compacted to a checked `+10`
mapping, retaining its original unsupported-value exception. Its freed IL bytes
hold an aligned extended `CreateParams` getter; only that getter's MethodDef RVA
changes. Complete input/output hashes and the original method slot/RVA are
verified; PE size, resource locations and metadata table layout remain unchanged.

The Options-only JavaScript makes the original sidebar and content scroll within
the visible body, fits the footer and stops label selection. Inputs, textareas
and editable content retain text selection. It disables content-driven window
auto-sizing for this dialog to prevent its new native border from feeding back
into repeated size requests. Original tab, keyboard, save/cancel and maximize
callbacks remain. No modified Microsoft binary is distributed.

The diagnostic fixture [options-native-probe.cs](../../tests/e2e/options-native-probe.cs)
checks actual styles, fixed/unrelated controls, all eight original native resize
messages and invalid enum rejection. The [tab audit](../../tests/automation/options-audit.py)
checks all 22 pages without submitting settings. Evidence distinguishes native
method checks, viewport simulation and actual compositor input; COSMIC still
requires a test on the target installation.

The original investigation follows below.

The reported Options dialog opened as a 600 × 400 window with its left/top
content clipped and navigation/footer missing. It reproduced in a disposable
synthetic PBIP, independently of a database connection or report cache.

## Cause and correction

Initialization passed two .NET `Int64` cache-size properties to the legacy HTML
view. Wine 11.18's JScript Automation conversion handled unsigned 64-bit values,
but left signed `VT_I8` as an opaque variant. Using these properties in the
localized cache-description binding interrupted initialization before the dialog
received its intended size. Int32 and Double controls worked in the isolated
reproducer; four signed Int64 cases failed with runtime 0.1.1.

`wine-11.18-jscript-int64.patch` converts signed Int64 to a JavaScript number only
in HTML mode with the ES5-or-newer engine. Its guard preserves the previous
standalone/legacy variant path. JavaScript numbers retain their usual precision
limit; the component test includes the maximum safe integer, not arbitrary
64-bit integer precision. No cache-size preference is changed.

After this correction, Options opened at 1002 × 802, but a separate pane-height
calculation left lower content clipped outside the body. The RPM 9 guarded
resource recipe bounds the existing pane to its body's remaining height after
asynchronous loading and on resize. Original navigation, scrollbars, localized
controls and save/cancel callbacks remain in use. PE and resource sizes are
preserved; the proprietary modified assembly remains local.

## Evidence and limits

On Fedora 44 / GNOME 50 native Wayland at fractional scale 1.25:

- The isolated x64 IE11 HTML component passed all seven numeric cases with 0.1.2;
  runtime 0.1.1 passed the three controls and failed the four Int64 cases.
- All 22 Options tabs (15 Global, seven Current File) passed automated navigation,
  visible content/footer and scroll-pane geometry checks without JavaScript errors.
  This navigated tabs; it did not change settings or submit OK.
- A compositor mouse click on the original scroll arrow moved the pane by 48
  pixels. The original Cancel callback closed the synthetic Options dialog.
  Mouse delivery to Cancel is not certified by that callback test.
- The complete local UI patch chain reproduced the exact tested assembly and was
  idempotent. The 53 Python unit tests passed. Both x64 and x86 JScript modules
  were built; the HTML component itself was exercised in x64 only.

The incremental runtime replaces only the two architecture-specific JScript
DLLs from verified 0.1.1. The Wayland driver, DXVK, helper payloads and source locks
are unchanged. SHA-256 for this exact incremental archive:

```text
379e3e0a58198f858b8b478619c397651befc0d4f2e159f293e81c3692b87f3b
```

The runtime manifest identifies the base archive, patch hash, builder and all
payload hashes. A full source build contains the same patch series; it is not
claimed byte-identical to this incremental artifact. Older large-model and soak
passes do not certify this new checksum. Real-server refresh/TLS, the nested
None/Delete Permissions confirmation and broad input/resize coverage remain
separate work.

## Installation and regression

Upgrade the CLI recipe with `sudo dnf upgrade ./powerbi-linux-0.1.0-9.noarch.rpm`.
An RPM upgrade alone does not replace the per-user Wine runtime or assembly.
For an existing installation without the local maintenance already applied,
close Desktop and use:

```bash
pbi-linux update \
  --runtime ./powerbi-linux-runtime-0.1.2-x86_64.tar.xz \
  --runtime-sha256 379e3e0a58198f858b8b478619c397651befc0d4f2e159f293e81c3692b87f3b
pbi-linux doctor
```

Current CLI update modifies the existing prefix without a snapshot or rollback;
see the [maintenance policy](installation-lifecycle.md#maintenance) and back up
important files yourself. Do not repeat it on a locally maintained profile
already matching this runtime/UI recipe and passing doctor.

From the source checkout, the isolated regression is:

```bash
python3 tools/test-html-int64.py
# Test another verified runtime without activating it:
python3 tools/test-html-int64.py --runtime /path/to/runtime
```

It compiles and opens its own short-lived HTML component using installed .NET,
then writes private evidence under `.local/html-int64/`. It does not open a report
or modify Desktop settings. The full Options audit used a private in-process
inspector in a diagnostic Desktop copy, without distributing Microsoft resources;
that 22-tab audit is not yet a standalone public GUI regression tool.
