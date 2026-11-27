# SPDX-License-Identifier: GPL-3.0-or-later
"""Let OK work in every legacy HTML floating dialog, not one dialog at a time.

On OK, a dialog's host asks the page for its view model. Without a getJSON
of its own, `KoFloatingDialog.getViewModel` (and `DropForm.getViewModel` for
drop-down forms) serializes it with `ko.toJSON`. Knockout walks every
enumerable property, inherited ones included: the `_typedHost` getter of
`KoFloatingDialogViewModel` and the `_host` of each button view model return
the .NET host object. Wine's JScript enumerates that object's members and
reads each one; a method that takes arguments raises DISP_E_BADPARAMCOUNT
(0x8002000e), which ends the OK handler, so the dialog stays open. This made
the Auto recovery dialog unclosable, and it affects every dialog of the family
whose view model has no getJSON: Options, Export template, View as, the
connector warnings, the storage mode and DirectQuery choices, and more.

Both shared scripts are MSHTML-only resources of Microsoft.Mashup.Client.UI.dll.
Each gets a walker equivalent to `ko.toJS` that returns nothing for an object
that is not a JScript object (`instanceof Object` is false for a COM object in
Wine, and testing it calls nothing on the object). The JSON is the same as
before minus the host objects, which the host never reads. A view model's own
getJSON still wins. Knockout itself is untouched: WebView2 pages load it too.
"""
import hashlib
import re
import struct
from .common import Error

# The complete Microsoft.Mashup.Client.UI.dll of each build after
# legacy_html.patch_ui and this module.
UI_PATCHED_SHA256 = {
    '2.159.1231.0': '1ecad1e587dad994d2a48e024c3fb3ba71d1be655cdacc448608a306e6dd0c62',
    '2.160.1151.0': 'e6fb874fd98437dedf2a1cf5187d3532754241adf520354087cabc7b1773677f',
}

_WALKER = (
    b'function toJS(v,k,o){var i,p,r;'
    b'if(v&&typeof v=="object"&&!(v instanceof Object))return;'
    b'for(i=0;ko.isObservable(v)&&i<10;i++)v=v();'
    b'if(typeof v!="object"||v===null||v instanceof Date||v instanceof String||v instanceof Number||v instanceof Boolean)return v;'
    b'if(!(v instanceof Object))return;'
    b'for(i=0;i<k.length;i++)if(k[i]===v)return o[i];'
    b'r=v instanceof Array?[]:{};k.push(v);o.push(r);'
    b'if(v instanceof Array)for(i=0;i<v.length;i++)r[i]=toJS(v[i],k,o);'
    b'else for(p in v)r[p]=toJS(v[p],k,o);'
    b'return r;}'
)


class _Resource:
    def __init__(self, name, marker, marker_offset, size, original, patched, call, walker_before, walker_after,
                 removed=()):
        self.name, self.marker, self.marker_offset, self.size = name, marker, marker_offset, size
        self.original, self.patched, self.call = original, patched, call
        self.walker_before, self.walker_after, self.removed = walker_before, walker_after, removed

    def locate(self, source):
        # Found by a unique marker and checked against the .NET resource length
        # prefix, never by a fixed offset: dnlib may move resources in other builds.
        if source.count(self.marker) != 1:
            raise Error('Unsupported ' + self.name + ' resource; no patch produced')
        start = source.index(self.marker) - self.marker_offset
        if start < 4 or struct.unpack_from('<I', source, start - 4)[0] != self.size:
            raise Error('Invalid ' + self.name + ' resource offset')
        return start

    def hash(self, source):
        start = self.locate(source)
        return hashlib.sha256(source[start:start + self.size]).hexdigest()

    def patch(self, source):
        start = self.locate(source)
        resource = source[start:start + self.size]
        sha = hashlib.sha256(resource).hexdigest()
        if sha == self.patched:
            return source
        if sha != self.original:
            raise Error('Unsupported ' + self.name + ' contents; no patch produced')
        old, new = self.call
        anchor = self.walker_before or self.walker_after
        if resource.count(old) != 1 or resource.count(anchor) != 1:
            raise Error('Unexpected ' + self.name + ' script; no patch produced')
        updated = resource.replace(old, new)
        if self.walker_before:
            updated = updated.replace(anchor, _WALKER + b'\r\n' + anchor)
        else:
            updated = updated.replace(anchor, anchor + _WALKER + b'\r\n')
        for text in self.removed:
            if updated.count(text) != 1:
                raise Error('Unexpected ' + self.name + ' script; no patch produced')
            updated = updated.replace(text, b'')
        # Room for the walker: leading indentation (and, for the drop-down form,
        # three comments and the source map comment). Line breaks stay.
        updated = re.sub(rb'(?m)^ +', b'', updated)
        if len(updated) > self.size:
            raise Error(self.name + ' serializer exceeds its resource')
        updated = updated.ljust(self.size, b' ')
        if hashlib.sha256(updated).hexdigest() != self.patched:
            raise Error('Unexpected ' + self.name + ' patch output')
        return source[:start] + updated + source[start + self.size:]


RESOURCES = (
    _Resource(
        'floating dialog serializer',
        marker=b'var KoFloatingDialog = /** @class */ (function () {\r\n', marker_offset=62, size=8049,
        original='cfdc334b76a797764975b155eea327b75e11fb589578ae10df56331b0ae7726e',
        patched='3bd9956fb4fbf7e2722a14d78cac877f839033f89ed2f6b5c479a4351373f502',
        call=(b'            return ko.toJSON(KoFloatingDialog._viewModel);\r\n',
              b'            return JSON.stringify(toJS(KoFloatingDialog._viewModel,[],[]));\r\n'),
        walker_before=b'    KoFloatingDialog.updateViewModel = function (jsonViewModel) {\r\n', walker_after=None),
    _Resource(
        'drop-down form serializer',
        marker=b'var DropForm;\r\n(function (DropForm) {\r\n', marker_offset=186, size=2652,
        original='ccf0dba88e781080a5cdb1cb8a32de23ee8529f84177c88ff807ef965f7e4853',
        patched='d023deaf4c2dde1dc3f8333204ad1881aea2afa9e14a266b7ba3f9c5ac298fde',
        call=(b'        return ko.toJSON(_viewModel);\r\n',
              b'        return JSON.stringify(toJS(_viewModel,[],[]));\r\n'),
        walker_before=None, walker_after=b'    DropForm.getViewModel = getViewModel;\r\n',
        removed=(b'// remove a test only dependence on editor.js\r\n',
                 b'// The editor is not busy and has finished all queued blocking and non-blocking tasks\r\n',
                 b'// The editor is busy executing a task that requires the editor to be blocked\r\n',
                 b'//# sourceMappingURL=C:/__w/1/s/private/Product/MashupClient/UI.Windows/ts/DropForm/DropForm.js.map')),
)


def patch_ui(source):
    """Patch both shared serializers in place; sizes and other bytes are unchanged."""
    for resource in RESOURCES:
        source = resource.patch(source)
    return source


def patched(source):
    """True when both shared serializers carry the walker."""
    return all(resource.hash(source) == resource.patched for resource in RESOURCES)
