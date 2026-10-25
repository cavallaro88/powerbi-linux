# SPDX-License-Identifier: GPL-3.0-or-later
"""Guarded Options-only layout and selection correction for the two recipes."""
import hashlib
import struct
from pathlib import Path
from .common import Error

BASELINES = {
    'a700f3e4b37e586d5529518176573ad62c88c79fe76525a46d0a437b23d0a855': ('2.158.1177.0', 0),
    'a2c3db990ed08e371356aec9055d9d46026978413472512873385593917e6c94': ('2.159.883.0', 256),
}
PATCHED = {
    '2.158.1177.0': '4b83723847d64750786289d7eb86c23e40a2b5f276f3ef5b9e58652b1872a560',
    '2.159.883.0': '5bf9af170da38c355ab2c3350651e5fed4a3321f3144af7d0ec77a80e4bd4220',
}
JQUERY_OFFSET, JQUERY_SIZE = 9028422, 4401
OPTIONS_OFFSET, OPTIONS_SIZE = 8977334, 2296
OPTIONS_BASE_SHA256 = '98c2ceab28611a983e55846929e28b30f66dfb369ac2ae454a5b1c1ec58df459'


def _transform_resources(source, delta):
    jquery = source[JQUERY_OFFSET + delta:JQUERY_OFFSET + delta + JQUERY_SIZE]
    # Reclaim only indentation and full-line non-license comments. Preserve the
    # existing selectors, security fix, textOverflow hook and all executable code.
    jquery = b'\n'.join(line.strip() for line in jquery.splitlines()
                        if not line.lstrip().startswith(b'//') or b'Copyright' in line)
    helper = Path(__file__).with_name('options_layout.js').read_bytes()
    helper = b''.join(line.strip() for line in helper.splitlines()
                      if not line.lstrip().startswith(b'//'))
    jquery += b'\n// Power BI Linux: GPL-3.0-or-later; Options layout.\n' + helper
    options = source[OPTIONS_OFFSET + delta:OPTIONS_OFFSET + delta + OPTIONS_SIZE]
    if hashlib.sha256(options).hexdigest() != OPTIONS_BASE_SHA256:
        raise Error('Unexpected Options interaction resource')
    lines = options.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines)
               if line.startswith(b'_groupTabControl.load($(".o-group-options")).then(')]
    if len(matches) != 1:
        raise Error('Unexpected Options interaction hook')
    lines[matches[0]] = (b'_groupTabControl.load($(".o-group-options")).then(function(){'
                         b'powerbiOptionsLayout(_groupTabControl);});\r\n')
    options = b''.join(lines)
    if options.count(b'KoFloatingDialog.show();') != 1:
        raise Error('Unexpected Options auto-size hook')
    # The dialog now follows its native client area. Content-driven host sizing
    # would feed the new non-client border back into the requested size and
    # repeatedly shrink it. Preserve all other show/cancel/maximize callbacks.
    options = options.replace(b'KoFloatingDialog.show();',
                              b'KoFloatingDialog.show({enableWindowAutoSize:false});')
    if len(jquery) > JQUERY_SIZE or len(options) > OPTIONS_SIZE:
        raise Error('Options interaction patch exceeds its resources')
    output = bytearray(source)
    output[JQUERY_OFFSET + delta:JQUERY_OFFSET + delta + JQUERY_SIZE] = jquery.ljust(JQUERY_SIZE, b' ')
    output[OPTIONS_OFFSET + delta:OPTIONS_OFFSET + delta + OPTIONS_SIZE] = options.ljust(OPTIONS_SIZE, b' ')
    return bytes(output)


# Keep the PE size, resource locations and metadata table layout unchanged.
# Compact the original eight-way StartResize switch to an unsigned range check
# and handle + 10, preserving its original error block and native callback.
# Its freed method-body bytes hold the extended CreateParams getter. Only that
# getter's MethodDef RVA changes. The original drop shadow remains; WS_THICKFRAME
# is added only for the culture-independent SettingsDialog Name with its original
# IsResizable flag. Other dialogs keep their styles. The relocated fat getter
# header is four-byte aligned; its body has no locals and a maximum stack of four.
_NATIVE = {
    0: (286368,
        '6a542d1d4c1bb19d6df1d9591792d903c3d6d7b7694bc93360172f7d2f2e8007',
        bytes.fromhex('aa031d350b02031f0a5828cc1800062a280400000a7249090470038ce7040002282300000a739b04000a7a000330040045000000000000000228320a000a25256f330a000a2000000200606f340a000a0228ae1800062c2402285609000a72d71a087028ca00000a2c1225256fad0a000a2000000400606fae0a000a2a00000000'),
        (103822128, 277935, 294092)),
    256: (286560,
        'de850fae8525e76cde164a1675530cc5d1a62e3c9de2d27dd9533dcd262d978d',
        bytes.fromhex('aa031d350b02031f0a5828cf1800062a280400000a7249090470038ce8040002282300000a739c04000a7a000330040045000000000000000228380a000a25256f390a000a2000000200606f3a0a000a0228b11800062c2402285709000a72d71a087028ca00000a2c1225256fb30a000a2000000400606fb40a000a2a00000000'),
        (103822456, 278127, 294284)),
}


def _native_resize(source, delta):
    offset, expected, replacement, (row, old_rva, new_rva) = _NATIVE[delta]
    if (hashlib.sha256(source[offset:offset + len(replacement)]).hexdigest() != expected or
            struct.unpack_from('<I', source, row)[0] != old_rva):
        raise Error('Unsupported native Options resize method layout')
    output = bytearray(source)
    output[offset:offset + len(replacement)] = replacement
    struct.pack_into('<I', output, row, new_rva)
    return bytes(output)


def _transform(source, delta):
    return _native_resize(_transform_resources(source, delta), delta)


def patch(source):
    sha = hashlib.sha256(source).hexdigest()
    if sha in PATCHED.values():
        return source
    if sha not in BASELINES:
        raise Error('Unsupported HTML assembly for Options interaction patch')
    version, delta = BASELINES[sha]
    result = _transform(source, delta)
    if len(result) != len(source) or hashlib.sha256(result).hexdigest() != PATCHED[version]:
        raise Error('Unexpected Options interaction assembly output')
    return result
