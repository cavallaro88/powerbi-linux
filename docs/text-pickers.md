# Font and text-size pickers

On October 18, 2026, the font and size controls in a report text box opened a
detached white window on Fedora 44, GNOME/PaperWM and the local runtime 0.1.4
candidate. The issue reproduced in an empty, unsaved Desktop report. Its HTML
contained all 26 fonts and 24 sizes; installing fonts or changing model data
was not needed.

A native inventory found an owned `Chrome_WidgetWin_1` popup in a different
process from Desktop, with `WS_EX_NOACTIVATE` and the expected native rectangle.
The compositor displayed a separate white window elsewhere. This establishes a
popup presentation/placement failure; it does not establish that every white
popup has this cause or certify a general cross-process Wine fix.

## Compatibility change

The pinned WebView2 supports [Chromium's customizable select](https://developer.chrome.com/blog/a-customizable-select).
The browser can paint the picker in the page's top layer rather than through
the detached native popup. The project adds authored CSS scoped to Quill's
font and size selects under `div.ql-toolbar`, including bounded scrolling and
theme colors. Original controls, option values, selection, Quill change handlers
and document-formatting behavior remain in charge.

Desktop prevents the default Escape action on those HTML controls. A small
window capture listener stops propagation only for Escape originating inside
one of these **open** pickers. It does not prevent the default browser dismissal,
replace keyboard navigation, or handle Escape elsewhere. IME composition is
excluded. CSS and the listener are guarded by feature support.

`text_pickers.py` validates the complete original `reportView.html`, the authored
recipe and the resulting document by SHA-256. Setup validates this input before
replacing any application file, backs up the original, then applies the fragment
locally. Repeated maintenance uses that original backup. Doctor verifies the
recorded and actual output checksum. The only modified Microsoft file remains
local; RPMs carry the patch code and authored CSS/JavaScript.

Original document SHA-256:

```text
0a03d24a6967d3026e8e910399cddd51ef668efd8f9b700a874f55f63059c41a
```

Patched document SHA-256:

```text
1d45d1ed9faf3253e1013941dc3be9bc51ff5415f8994e77e9e873c9671ae708
```

## Validation

The corrected document was loaded in a fresh diagnostic Desktop session, without
the earlier temporary style injection. Eight CDP keyboard checks confirmed both
pickers open/close, Escape preserves formatting, Home/End/arrow selection reaches
Quill, and large font/size lists remain navigable. Resulting text had the chosen
Arial/Verdana and 96pt formatting.

Separate pointer input through GNOME's compositor selected Tahoma and 40pt,
with native HWND/position guards. Subsequent diagnostic text input had exactly
those styles in the original Quill editor. Pointer-triggered reflow changed the
toolbar position during one attempt; the initial post-insertion check of toolbar
values was unsuitable because they follow caret focus. Verification used the
actual newly formatted text instead. Physical Escape dismissal was checked
separately. Diagnostic screenshots and output remain private.

Doctor passed 18 checks after the bounded local activation. Four regression
tests cover unknown HTML, changed recipes, idempotent output and refusal before
any application-file replacement. No customer report was opened, saved or
modified. The scoped tests do not certify every dropdown, display scale, theme
or full runtime release; Power Query and legacy HTML dialogs use other controls.

## Installation and regression steps

RPM 13 supplies the setup/repair recipe. Updating the RPM alone does not replace
an existing profile's HTML. With Desktop closed, normal maintenance applies the
recipe; review [maintenance and disk requirements](install.md) first. This host
already has the bounded local candidate, its original file and guarded rollback;
no DNF or profile clone is needed just to test it. The Wine runtime and resource
settings are unchanged.

Use a new unsaved blank report and insert a text box with sample text. Select
the text, choose a font and a size, and check actual formatting. Reopen each
list, navigate and scroll to an off-screen option. Press Escape and confirm the
choice remains unchanged. Repeat with pointer input after resizing the window.
Discard this disposable report when finished. Check `text-pickers` in doctor;
do not use a customer report or remove caches for this regression.
