# SPDX-License-Identifier: GPL-3.0-or-later
"""Let the Auto recovery dialog's OK button close Desktop.

Closing Desktop while recovered files that were never opened remain in
AutoRecovery shows the legacy HTML dialog "Auto recovery". OK asks the page for
its view model. This one has no getJSON, so KoFloatingDialog falls back to
ko.toJSON, which also walks the inherited, enumerable `_typedHost` getter into
the .NET host object. Wine's JScript enumerates that object's members and reads
`performance.mark` as a property: DISP_E_BADPARAMCOUNT (0x8002000e). The
exception ends the OK handler, so the dialog stays open. Cancel cancels the
close, and the next close shows the dialog again: Desktop cannot be closed.

The fix gives the view model a getJSON that serializes plain values only: the
description and the radio group's name, label and state. The host reads only
that state ("delete" removes the files); its original handlers stay in control.
"""
import hashlib
import re
from .common import Error


RESOURCE_ORIGINAL_SHA256 = 'a86f3f8f709618708de4e227f0dd18aea3af6e5cc3737b2aa3904e035c661515'
RESOURCE_PATCHED_SHA256 = '511d75f7e93b5f34364dd84d5b55d5d97ad6c707b5f7d185f2d61104adbbb1ce'
_SIZE = 2290
_NAME = b'var AutoRecoveryKeepOrDeleteDialog;\r\n'
_NAME_OFFSET = 689
_ANCHOR = b'    AutoRecoveryKeepOrDeleteDialog.ViewModel = ViewModel;\r\n'
_HOOK = (
    b'ViewModel.prototype.getJSON=function(){var g=this.keepOrDeleteRecoveredFilesRadioGroup;'
    b'return JSON.stringify({dialogDescriptionText:this.dialogDescriptionText,'
    b'keepOrDeleteRecoveredFilesRadioGroup:{name:g.name,groupLabel:g.groupLabel,state:g.state()}});};\r\n'
)
_SOURCE_MAP = (
    b'//# sourceMappingURL=C:/__w/1/s/private/Product/PowerBI/ClientWindows/Web/ts/'
    b'FloatingDialog/AutoRecoveryKeepOrDeleteDialog.js.map'
)


def _resource(source):
    # dnlib moves resources when later setup steps rewrite the assembly. Find
    # the resource by its unique name marker and check its hash, never a fixed PE offset.
    if source.count(_NAME) != 1:
        raise Error('Unsupported Auto recovery dialog resource; no patch produced')
    start = source.index(_NAME) - _NAME_OFFSET
    if start < 0:
        raise Error('Invalid Auto recovery dialog resource offset')
    return start, source[start:start + _SIZE]


def resource_hash(source):
    return hashlib.sha256(_resource(source)[1]).hexdigest()


def patch_windows(source):
    """Patch the dialog script in place without changing PE or resource sizes.

    The caller has verified the whole Desktop assembly against its recipe; this
    also requires the exact original (or already patched) resource contents.
    """
    start, resource = _resource(source)
    sha = hashlib.sha256(resource).hexdigest()
    if sha == RESOURCE_PATCHED_SHA256:
        return source
    if sha != RESOURCE_ORIGINAL_SHA256:
        raise Error('Unsupported Auto recovery dialog contents; no patch produced')
    if resource.count(_ANCHOR) != 1 or resource.count(_SOURCE_MAP) != 1:
        raise Error('Unexpected Auto recovery dialog script; no patch produced')
    # Room for the hook: the indentation below the name marker (so the marker
    # keeps its offset) and the source map comment. The copyright notice, the
    # other comments and the line breaks stay.
    marker = _NAME_OFFSET
    body = resource[marker:].replace(_ANCHOR, _HOOK + _ANCHOR).replace(_SOURCE_MAP, b'')
    updated = resource[:marker] + re.sub(rb'(?m)^ +', b'', body)
    if len(updated) > _SIZE:
        raise Error('Auto recovery dialog serializer exceeds its resource')
    updated = updated.ljust(_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != RESOURCE_PATCHED_SHA256:
        raise Error('Unexpected Auto recovery dialog patch output')
    return source[:start] + updated + source[start + _SIZE:]
