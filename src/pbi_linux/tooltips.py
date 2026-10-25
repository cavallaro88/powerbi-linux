# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard the in-page browser title tooltip correction after the picker recipe."""
import hashlib
from pathlib import Path
from .common import Error
from . import text_pickers

ORIGINAL_SHA256 = text_pickers.PATCHED_SHA256
PATCHED_SHA256 = '9acd09d12a94153533812cee98050bb210f51150ec4ca2727afebf3985a1fba9'
FRAGMENT = b'\n<script>\n' + Path(__file__).with_suffix('.js').read_bytes() + b'</script>\n'
FRAGMENT_SHA256 = '6706e792aa61c6b295cc342e297dd67ab3def5baf6c99a35e7aac9828592be04'


def patch_document(source):
    if hashlib.sha256(FRAGMENT).hexdigest() != FRAGMENT_SHA256:
        raise Error('Unsupported tooltip recipe; no patch produced')
    sha = hashlib.sha256(source).hexdigest()
    if sha == PATCHED_SHA256:
        return source
    if sha != ORIGINAL_SHA256:
        raise Error('Unsupported tooltip document; no patch produced')
    if source.count(b'</head>') != 1:
        raise Error('Unexpected tooltip document structure')
    result = source.replace(b'</head>', FRAGMENT + b'</head>')
    if hashlib.sha256(result).hexdigest() != PATCHED_SHA256:
        raise Error('Unexpected tooltip patch output')
    return result
