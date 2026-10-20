// SPDX-License-Identifier: GPL-3.0-or-later
// Let the browser close only an open Quill picker before Desktop consumes Esc.
if (CSS.supports('appearance', 'base-select')) {
    window.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape' || event.isComposing || !(event.target instanceof Element)) return;
        const picker = event.target.closest('div.ql-toolbar select.ql-picker:is(.ql-font, .ql-size)');
        if (picker && picker.matches(':open')) event.stopPropagation();
    }, true);
}
