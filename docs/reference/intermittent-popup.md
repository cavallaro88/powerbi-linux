# Intermittent white auxiliary window

Reported on Fedora on October 23, 2026: a small, empty white rectangle appears
beside the upper-right corner of Desktop. It can appear and disappear repeatedly
over a few seconds, then disappear completely. It was subsequently confirmed to
appear when hovering text. The installed project package is RPM 15.

The screenshot establishes the visual symptom; it does not identify the native
window class, process or owner. It does not establish a connection to the
Options resizing correction. Hover-triggered tooltips are the working diagnosis;
the precise rendering or placement failure is not established.

A 90-second native inventory collected 193 samples. It recorded several owned,
untitled `Chrome_WidgetWin_1` windows, each 24 native pixels high, appearing for
approximately 0.5–1.9 seconds. The white artifact appeared
during this observation period. This links the symptom to hover interaction and
provides evidence of transient WebView2 windows, but does not prove which
individual HWND produced the screenshot or explain the white content.

An earlier [font-picker popup issue](text-pickers.md) had a similar appearance,
but its correction applies only to the font and size selectors. It is not
evidence that this new report has the same cause.

## Local correction in RPM 16

The guarded `tooltips.py` recipe adds authored JavaScript to the locally installed
report-view HTML, after the existing font-picker recipe. Both the complete input
document and output document, plus the authored fragment, are checked by SHA-256.
The original document is retained for repair. No modified Microsoft document or
populated prefix is distributed. A new Wine/WebView2 runtime is not required.

On hover or keyboard focus, the helper temporarily empties browser `title`
attributes and SVG title text and renders the same plain text in a manual in-page
popover. It restores values on exit without overwriting changes made by the
application. SVG title node identity and existing accessible references remain.
The tip is constrained to its document viewport and uses text content rather
than HTML parsing. Escape, click, scroll and resize dismiss it without consuming
application commands. Desktop disables PointerEvent, so the implementation uses
its supported mouse-event path.

An existing visible ARIA tooltip takes precedence over a second plain title tip.
The implementation does not replace Power BI's rich data-tooltip renderers,
report-page tooltip contents, value formatting or visual event handlers. SVG
titles and same-origin visual frames use the same correction as interface text.
Cross-origin visual frames cannot be instrumented by this document script;
arbitrary custom visuals and report-page tooltips still require separate native
validation. This is not a general fix for every Wine popup.

Setup/repair applies the recipe with Desktop closed; installing the project
package alone does not update the profile. `pbi-linux doctor` adds a `tooltips`
integrity check. Repair creates a managed snapshot and may require approximately
9 GiB additional space for another complete installation.

## Validation scope

The browser regression [tooltips-audit.js](../../tests/automation/tooltips-audit.js)
exercises HTML/inherited/empty titles, dynamic changes/removal, literal text,
SVG titles, accessibility references, existing rich tooltip coexistence,
keyboard/click/Escape behavior, viewport edges, removed targets and same-origin
frames. It runs in a disposable diagnostic document in the pinned WebView2.
Python tests cover input/recipe/output guards, idempotence and rejection before
any application-file replacement.

The first diagnostic copies failed to load a synthetic report because their
Analysis Services process exited. Their compositor attempt did not establish
native hover delivery and is not counted as passing evidence.

After repair, a separate **normal managed launch** loaded and refreshed the
synthetic report. Real Mutter pointer input established a positive control: one
QA button using the original browser title path created a native popup. The
corrected button displayed its text in the in-page popover with no native popup.
The QA bypass existed only in that disposable report document.

The synthetic table was converted to a clustered-column chart using Desktop's
original controls. Real pointer hover over its three bars displayed Cafe **120**,
Suco **100** and Cha **80** in the original rich tooltip renderer. Each tooltip
stayed inside the viewport, with no native popup and no second plain tooltip.
This is scoped evidence for that built-in chart; arbitrary custom visuals,
cross-origin frames and report-page tooltips still need separate validation.
The browser DOM suite passed 20 checks; 144 Python unit tests passed. The repaired
Fedora installation passed all 19 doctor checks, including the new recipe's exact
document hash. No user report was opened or saved during these tests.

Do not suppress arbitrary unnamed or small native windows: legitimate controls
can use them.

Private window inventories and screenshots stay outside the source export.
