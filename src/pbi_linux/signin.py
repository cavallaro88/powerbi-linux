# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep native UI objects out of the email dialog's serialized view model."""
import hashlib
from .common import Error


WINDOWS_ORIGINAL_SHA256 = '5284e48755ca5d0911f8af46650d1aa12a36389f008e6005ac5f188071808cd4'
RESOURCE_ORIGINAL_SHA256 = '7c763aa03488af892735911041a2055c7d06ab7baba2e1bda4048a600e1d75a4'
RESOURCE_PATCHED_SHA256 = '1a8e6ddf7d8ae832cd0883b9fb64771469b4a93a04f686e6166605d5d491c436'
_SIZE = 3577
_NAME = b'var EnterEmailDialog;\r\n'
_NAME_OFFSET = 565
_ANCHOR = b'        Object.defineProperty(ViewModel.prototype, "host", {\r\n'
_HOOK = (
    b'        ViewModel.prototype.getJSON=function(){return JSON.stringify({'
    b'email:this.email(),retrySource:this.retrySource,warningMessage:this.warningMessage});};\r\n'
)
_COMMENTS = (
    b'    // When updating, make sure to also update the MessageStatus enum in MessageDetailsDialog.cs.\r\n',
    b'//# sourceMappingURL=C:/__w/1/s/private/Product/PowerBI/ClientWindows/Web/ts/FloatingDialog/EnterEmailDialog.js.map',
)


def _resource(source):
    # dnlib moves resources while remapping WinRT/signing. Identify the same
    # exact resource by its unique name marker and hash, never a fixed PE offset.
    if source.count(_NAME) != 1:
        raise Error('Unsupported email dialog resource; no patch produced')
    start = source.index(_NAME) - _NAME_OFFSET
    if start < 0:
        raise Error('Invalid email dialog resource offset')
    return start, source[start:start + _SIZE]


def resource_hash(source):
    return hashlib.sha256(_resource(source)[1]).hexdigest()


def patch_windows(source, expected_sha256=WINDOWS_ORIGINAL_SHA256):
    """Patch a verified local assembly without changing its PE/resource sizes.

    Setup uses the pinned Microsoft original. A bounded local update may pass
    the whole-file hash already verified against its active installation record.
    Both paths additionally require the exact supported resource contents.
    """
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise Error('Unsupported Desktop assembly for email dialog patch')
    start, resource = _resource(source)
    sha = hashlib.sha256(resource).hexdigest()
    if sha == RESOURCE_PATCHED_SHA256:
        return source
    if sha != RESOURCE_ORIGINAL_SHA256:
        raise Error('Unsupported email dialog contents; no patch produced')
    if resource.count(_ANCHOR) != 1 or any(resource.count(c) != 1 for c in _COMMENTS):
        raise Error('Unexpected email dialog script; no patch produced')
    updated = resource.replace(_ANCHOR, _HOOK + _ANCHOR)
    for comment in _COMMENTS:
        updated = updated.replace(comment, b'')
    if len(updated) > _SIZE:
        raise Error('Email dialog serializer exceeds its resource')
    updated = updated.ljust(_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != RESOURCE_PATCHED_SHA256:
        raise Error('Unexpected email dialog patch output')
    # The three fields are the existing EnterEmailViewModel wire contract.
    # Original native validation and authentication handlers remain in control.
    return source[:start] + updated + source[start + _SIZE:]
