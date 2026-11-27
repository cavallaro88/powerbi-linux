# SPDX-License-Identifier: GPL-3.0-or-later
"""Let the Options dialog appear, in 2.159.1231.0 and 2.160.1151.0.

A floating dialog is created fully transparent (Opacity 0, a layered window)
and fades in when its page calls the host's onShow. ModalDialog.showDialog
makes that call only while window auto-size is on, and the Options recipe
(options_layout) turns auto-size off so that the resizable dialog follows its
native client area. Options therefore stayed transparent. A compositor that
ignores a window's opacity (no wp_alpha_modifier_v1) showed it anyway;
Hyprland honours it, so Options was an empty frame over a disabled Desktop.

The page now calls onShow itself, on the deferred tick the original code used,
followed by the maximized-state callback that came with it. Auto-size stays off.
"""
import hashlib
import struct
from .common import Error

# The complete Microsoft.Mashup.Client.UI.dll of each build after
# legacy_html.patch_ui, dialog_serializers.patch_ui and this module.
UI_PATCHED_SHA256 = {
    '2.159.1231.0': '17c4dfc2498e8efae390cb4bbcf30f5322d0323d73fcbf7ea0a5ceb96f5af080',
    '2.160.1151.0': '36d72e618d119eb07d98da2f9dd3eeb7cd74ea70ab07e96a27feee061ae0efd0',
}

_MARKER = b'var KoOptionsDialog;\r\n(function (KoOptionsDialog) {\r\n'
_MARKER_OFFSET, _SIZE = 513, 2296
# The Options dialog script as the Options recipe leaves it, and with this change.
_ORIGINAL = '97995eeb9be3a15d20e13b416a29320b78cf01ef760dcca38dadfca6b700b390'
_PATCHED = '01762648e26f0bac20d741f0b8ce2ff73fab4d3b5a372a8e252d47bceccb9d41'
_SHOW = b'KoFloatingDialog.show({enableWindowAutoSize:false});\r\n'
_ON_SHOW = (b'TrackedTimer.setTimeout(function(){KoFloatingDialog.host.onShow();'
            b'if(KoFloatingDialog._viewModel.showDismissButton!==false)'
            b'KoFloatingDialog.onMaximizedStateChanged();},0);\r\n')


def _locate(source):
    # Found by a unique marker and checked against the .NET resource length
    # prefix, never by a fixed offset: dnlib may move resources in other builds.
    if source.count(_MARKER) != 1:
        raise Error('Unsupported Options dialog resource; no patch produced')
    start = source.index(_MARKER) - _MARKER_OFFSET
    if start < 4 or struct.unpack_from('<I', source, start - 4)[0] != _SIZE:
        raise Error('Invalid Options dialog resource offset')
    return start


def _resource_hash(source):
    start = _locate(source)
    return hashlib.sha256(source[start:start + _SIZE]).hexdigest()


def patch_ui(source):
    """Make the Options page call onShow; sizes and other bytes are unchanged."""
    start = _locate(source)
    resource = source[start:start + _SIZE]
    sha = hashlib.sha256(resource).hexdigest()
    if sha == _PATCHED:
        return source
    if sha != _ORIGINAL:
        raise Error('Unsupported Options dialog contents; no patch produced')
    if resource.count(_SHOW) != 1:
        raise Error('Unexpected Options dialog script; no patch produced')
    # The call takes the place of padding left by the Options recipe.
    updated = resource.rstrip(b' ').replace(_SHOW, _SHOW + _ON_SHOW)
    if len(updated) > _SIZE:
        raise Error('Options dialog show call exceeds its resource')
    updated = updated.ljust(_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != _PATCHED:
        raise Error('Unexpected Options dialog patch output')
    return source[:start] + updated + source[start + _SIZE:]


def patched(source):
    """True when the Options page calls onShow itself."""
    return _resource_hash(source) == _PATCHED
