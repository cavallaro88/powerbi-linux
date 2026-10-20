# SPDX-License-Identifier: GPL-3.0-or-later
"""Render only Quill font/size selectors in WebView's own top layer."""
import hashlib
from pathlib import Path
from .common import Error

DOCUMENT = 'WebView2Resources/minerva/reportView.html'
ORIGINAL_SHA256 = '0a03d24a6967d3026e8e910399cddd51ef668efd8f9b700a874f55f63059c41a'
PATCHED_SHA256 = '1d45d1ed9faf3253e1013941dc3be9bc51ff5415f8994e77e9e873c9671ae708'
STYLE = (b'\n<style>\n' + Path(__file__).with_suffix('.css').read_bytes()
         + b'</style>\n<script>\n' + Path(__file__).with_suffix('.js').read_bytes() + b'</script>\n')
STYLE_SHA256 = 'fec9b0371165d4d1ebbee96b2b86835420cf458961be9a2f5ff06dfb8dd7557f'


def patch_document(source):
    if hashlib.sha256(STYLE).hexdigest() != STYLE_SHA256:
        raise Error('Unsupported text picker recipe; no patch produced')
    sha = hashlib.sha256(source).hexdigest()
    if sha == PATCHED_SHA256:
        return source
    if sha != ORIGINAL_SHA256:
        raise Error('Unsupported text picker document; no patch produced')
    if source.count(b'</head>') != 1:
        raise Error('Unexpected text picker document structure')
    updated = source.replace(b'</head>', STYLE + b'</head>')
    if hashlib.sha256(updated).hexdigest() != PATCHED_SHA256:
        raise Error('Unexpected text picker patch output')
    return updated
