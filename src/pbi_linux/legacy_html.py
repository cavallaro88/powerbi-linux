# SPDX-License-Identifier: GPL-3.0-or-later
"""Restore Wine's legacy HTML registration after the application installers."""
from pathlib import Path
import hashlib
import re
from .common import Error, run, wine_env


REGISTRATIONS = {
    r'PROTOCOLS\Handler\about': '{3050F406-98B5-11CF-BB82-00AA00BDCE0B}',
    r'PROTOCOLS\Handler\res': '{3050F3BC-98B5-11CF-BB82-00AA00BDCE0B}',
    r'MIME\Database\Content Type\text/html': '{25336920-03F9-11CF-8FD0-00AA00686F13}',
}

UI_ORIGINAL_SHA256 = '28829058269cd42b5f731db43f94bcf34baf50d1cdf1ad624c0696468e3fadb7'
UI_PATCHED_SHA256 = 'a700f3e4b37e586d5529518176573ad62c88c79fe76525a46d0a437b23d0a855'
_PERMISSIONS_ASSEMBLY_SHA256 = '8aee5abdd62ef384f49e08cb9931093dab7a1b8df1ddb885af9d0b1ea4358c62'
_LIST_PATCHED_SHA256 = 'd7090533813cfce872e79b5bfe7d968af5461c6ee8b7a3ba6110e9358abd586e'
_CREDENTIALS_PATCHED_SHA256 = '16dcd45c8a7111ce39e3967cbc36d80116d87c0b4e2945b3af39840c9504841c'
_TEXT_OVERFLOW_SHA256 = '7cedcac43961e8f0abaa986b7130050ca3bceb43721c07228952e4047e899d40'
_RESOURCE_OFFSET, _RESOURCE_SIZE = 9028422, 4401
_ANCHOR = (
    b'    // In IE8, :focusable selects hidden INPUT elements as well, which fails when we try to call\r\n'
    b'    // focus() on them. So here we replace the selector with one that filters out those elements.\r\n'
)
_REMOVED_COMMENT = b'    // JQuery strips \\r from \\r\\n. \r\n    // See: http://api.jquery.com/val/\r\n'
_HOOK = (
    b'    // Wine: bypass the textOverflow property setter.\r\n'
    b'    try{document.createElement("div").style.textOverflow="ellipsis";}\r\n'
    b'    catch(e){if(e.number===-2147467263)$.cssHooks.textOverflow={set:function(n,v){'
    b'n.style.setProperty("text-overflow",v,"");}};else throw e;}\r\n'
)
_DIALOG_OFFSET, _DIALOG_SIZE = 8877875, 2403
_SHOW = b'        ClientShared.ModalDialog.showDialog(options);\r\n'
_DIALOG_HOOK = (
    b'setTimeout(function(){if($(".modal-main.o-group-challengeDialog").length){'
    b'$(".modal-leftBar.js-maxHeight").css("height","");'
    b'ClientShared.ModalDialog.resizeMaxHeights();'
    b'ClientShared.ModalDialog._resizeHost($("#modalDialog"));}},0);\r\n'
)
_DIALOG_COMMENTS = (
    b'        /// <param name="dialogResult" type="Number" />\r\n',
    b'        /// <param name="returnValue" type="Object" />\r\n',
    b'        /// <returns type="$.Deferred" />\r\n',
    b'// remove a test only dependence on editor.js\r\n',
    b'// The editor is not busy and has finished all queued blocking and non-blocking tasks\r\n',
    b'// The editor is busy executing a task that requires the editor to be blocked\r\n',
)
_SOURCES_OFFSET, _SOURCES_SIZE = 8948239, 22577
_SOURCES_ORIGINAL = '4cdedd35d3d6331abe432fb04fdc9d5b074a3004ac62b5f79592ba38d60ff1ae'
_SOURCES_PATCHED = 'e0a70ae8d5e1a46dfd709e1deda27bd1887c85a292dee2e6fab4e7f18fc2722d'
_SOURCES_SHOW = b'        KoFloatingDialog.show({\r\n            enableWindowAutoSize: true\r\n        });\r\n'
_SOURCES_HOOK = b'        setTimeout(function(){var l=_viewModel._virtualizedList;if(l&&l._numberOfItemsInPage===0)l._onResize();},0);\r\n'
_SOURCES_COMMENTS = (
    b'        // This method allows to exclude _tabbingManager and _selectionEventHandler from the serialization\r\n',
    b'            // Reset the selected count, since view model changes can modify the count without going through knockout \r\n',
)
_PERMISSIONS_OFFSET, _PERMISSIONS_SIZE = 8973278, 4052
_PERMISSIONS_ORIGINAL = 'f282a621fec318a19a9a5f3637b79ce5f7d85d1125f58c4eb94bcd3f5b441b8f'
_PERMISSIONS_PATCHED = '31ddd388983611243e143956c1dd3ff08ddf78a0c408062e33f8e7d720b8360e'
_PERMISSIONS_ANCHOR = b'        ViewModel.prototype.updateViewModel = function (jsonViewModel) {\r\n'
# The original JsonViewModel contract. Native host and button objects are not
# wire data: traversing them in ko.toJSON calls COM members with wrong arity.
_PERMISSIONS_FIELDS = (
    'credentialType supportsEncryption isEncrypted firewallSetting firewallSettingNames '
    'nativeQueriesCount resourceName displayName iconClass supportsNativeQuery '
    'hasCredential supportsCredential canEditPrivacyLevel'
)
_PERMISSIONS_HOOK = (
    '        ViewModel.prototype.getJSON=function(){var o={},v=this;$.each("' +
    _PERMISSIONS_FIELDS + '".split(" "),function(_,k){o[k]=ko.utils.unwrapObservable(v[k]);});'
    'return JSON.stringify(o);};\r\n'
).encode('ascii')
_OPTIONS_OFFSET, _OPTIONS_SIZE = 8977334, 2296
_OPTIONS_ORIGINAL = '01d48fae31004dc42d752308d2fff0c04ed29d0eff6e8907c61787caecc03f1b'
_OPTIONS_PATCHED = '98c2ceab28611a983e55846929e28b30f66dfb369ac2ae454a5b1c1ec58df459'
_OPTIONS_ANCHOR = b'        _groupTabControl.load($(".o-group-options"));\r\n'
_OPTIONS_HOOK = (
    b'        _groupTabControl.load($(".o-group-options")).then(function(){'
    b'var fit=function(){var p=_groupTabControl.panes.element[0],b=document.querySelector(".o-group-body");'
    b'p.style.maxHeight=Math.max(0,b.getBoundingClientRect().bottom-p.getBoundingClientRect().top)+"px";};'
    b'$(window).on("resize",function(){setTimeout(fit,0);});setTimeout(fit,0);});\r\n'
)


def patch_options(source):
    """Keep the existing Options scroll pane inside the visible dialog body."""
    sha = hashlib.sha256(source).hexdigest()
    if sha == UI_PATCHED_SHA256:
        return source
    if sha != _PERMISSIONS_ASSEMBLY_SHA256:
        raise Error('Unsupported HTML assembly for Options layout patch')
    resource = source[_OPTIONS_OFFSET:_OPTIONS_OFFSET + _OPTIONS_SIZE]
    if (hashlib.sha256(resource).hexdigest() != _OPTIONS_ORIGINAL or
            resource.count(_OPTIONS_ANCHOR) != 1):
        raise Error('Unexpected Options layout resource')
    updated = re.sub(rb'(?m)^ +', b'', resource.replace(_OPTIONS_ANCHOR, _OPTIONS_HOOK))
    if len(updated) > _OPTIONS_SIZE:
        raise Error('Options layout hook exceeds its resource')
    updated = updated.ljust(_OPTIONS_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != _OPTIONS_PATCHED:
        raise Error('Unexpected Options layout resource output')
    output = source[:_OPTIONS_OFFSET] + updated + source[_OPTIONS_OFFSET + _OPTIONS_SIZE:]
    if hashlib.sha256(output).hexdigest() != UI_PATCHED_SHA256:
        raise Error('Unexpected Options layout assembly output')
    return output


def patch_permissions(source):
    """Upgrade the verified source-list recipe without altering permission handlers."""
    sha = hashlib.sha256(source).hexdigest()
    if sha == UI_PATCHED_SHA256:
        return source
    if sha == _PERMISSIONS_ASSEMBLY_SHA256:
        return patch_options(source)
    if sha != _LIST_PATCHED_SHA256:
        raise Error('Unsupported HTML assembly for permissions serializer patch')
    resource = source[_PERMISSIONS_OFFSET:_PERMISSIONS_OFFSET + _PERMISSIONS_SIZE]
    if (hashlib.sha256(resource).hexdigest() != _PERMISSIONS_ORIGINAL or
            resource.count(_PERMISSIONS_ANCHOR) != 1):
        raise Error('Unexpected permissions resource')
    updated = resource.replace(_PERMISSIONS_ANCHOR, _PERMISSIONS_HOOK + _PERMISSIONS_ANCHOR)
    # Reclaim indentation only. Retain copyright, comments, newlines and PE/IL layout.
    updated = re.sub(rb'(?m)^ +', b'', updated)
    if len(updated) > _PERMISSIONS_SIZE:
        raise Error('Permissions serializer exceeds its resource')
    updated = updated.ljust(_PERMISSIONS_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != _PERMISSIONS_PATCHED:
        raise Error('Unexpected permissions resource output')
    output = source[:_PERMISSIONS_OFFSET] + updated + source[_PERMISSIONS_OFFSET + _PERMISSIONS_SIZE:]
    if hashlib.sha256(output).hexdigest() != _PERMISSIONS_ASSEMBLY_SHA256:
        raise Error('Unexpected permissions assembly output')
    return patch_options(output)


def patch_source_list(source):
    """Bounded upgrade from the previous supported HTML recipe, also used locally."""
    sha = hashlib.sha256(source).hexdigest()
    if sha == UI_PATCHED_SHA256:
        return source
    if sha == _PERMISSIONS_ASSEMBLY_SHA256:
        return patch_options(source)
    if sha == _LIST_PATCHED_SHA256:
        return patch_permissions(source)
    if sha != _CREDENTIALS_PATCHED_SHA256:
        raise Error('Unsupported HTML assembly for data source list patch')
    resource = source[_SOURCES_OFFSET:_SOURCES_OFFSET + _SOURCES_SIZE]
    if (hashlib.sha256(resource).hexdigest() != _SOURCES_ORIGINAL or
            resource.count(_SOURCES_SHOW) != 1 or any(resource.count(c) != 1 for c in _SOURCES_COMMENTS)):
        raise Error('Unexpected data source list resource')
    updated = resource.replace(_SOURCES_SHOW, _SOURCES_SHOW + _SOURCES_HOOK)
    for comment in _SOURCES_COMMENTS:
        updated = updated.replace(comment, b'')
    if len(updated) > _SOURCES_SIZE:
        raise Error('Data source list hook exceeds its resource')
    updated = updated.ljust(_SOURCES_SIZE, b' ')
    if hashlib.sha256(updated).hexdigest() != _SOURCES_PATCHED:
        raise Error('Unexpected data source list resource output')
    output = source[:_SOURCES_OFFSET] + updated + source[_SOURCES_OFFSET + _SOURCES_SIZE:]
    if hashlib.sha256(output).hexdigest() != _LIST_PATCHED_SHA256:
        raise Error('Unexpected data source list assembly output')
    return patch_permissions(output)


def patch_ui(source):
    """Change two supported embedded JS resources, retaining PE/IL layout."""
    if hashlib.sha256(source).hexdigest() != UI_ORIGINAL_SHA256:
        raise Error('Unsupported legacy HTML assembly; no patch produced')
    resource = source[_RESOURCE_OFFSET:_RESOURCE_OFFSET + _RESOURCE_SIZE]
    if resource.count(_ANCHOR) != 1 or resource.count(_REMOVED_COMMENT) != 1:
        raise Error('Unexpected legacy HTML resource; no patch produced')
    updated = resource.replace(_ANCHOR, _HOOK).replace(_REMOVED_COMMENT, b'')
    if len(updated) > _RESOURCE_SIZE:
        raise Error('Legacy HTML hook exceeds its resource')
    output = (source[:_RESOURCE_OFFSET] + updated.ljust(_RESOURCE_SIZE, b' ') +
              source[_RESOURCE_OFFSET + _RESOURCE_SIZE:])
    if len(output) != len(source) or hashlib.sha256(output).hexdigest() != _TEXT_OVERFLOW_SHA256:
        raise Error('Unexpected legacy HTML patch result; no patch produced')
    # Error display can size the credential sidebar before the floating dialog
    # gets its final width, and the inline height then survives the synchronous
    # sizing pass. Re-run the dialog's own sizing one tick after showDialog,
    # only when the credential challenge is present. Other dialogs are untouched.
    resource = output[_DIALOG_OFFSET:_DIALOG_OFFSET + _DIALOG_SIZE]
    if resource.count(_SHOW) != 1 or any(resource.count(c) != 1 for c in _DIALOG_COMMENTS):
        raise Error('Unexpected floating dialog resource; no patch produced')
    updated = resource.replace(_SHOW, _SHOW + _DIALOG_HOOK)
    for comment in _DIALOG_COMMENTS:
        updated = updated.replace(comment, b'')
    if len(updated) > _DIALOG_SIZE:
        raise Error('Legacy dialog sizing hook exceeds its resource')
    output = (output[:_DIALOG_OFFSET] + updated.ljust(_DIALOG_SIZE, b' ') +
              output[_DIALOG_OFFSET + _DIALOG_SIZE:])
    if len(output) != len(source) or hashlib.sha256(output).hexdigest() != _CREDENTIALS_PATCHED_SHA256:
        raise Error('Unexpected legacy HTML patch result; no patch produced')
    return patch_source_list(output)


def register(prefix, runtime, log):
    # wineboot deliberately disables mshtml during .NET bootstrap. Its COM
    # classes can exist while its INF protocol/MIME registrations are missing.
    # Register both installed Wine implementations, never a downloaded IE DLL.
    env = wine_env(prefix)
    env['WINEDLLOVERRIDES'] += ';mshtml=b'
    wine = Path(runtime) / 'bin/wine'
    for directory in ('system32', 'syswow64'):
        run([wine, 'C:\\windows\\' + directory + '\\regsvr32.exe', '/s',
             'C:\\windows\\' + directory + '\\mshtml.dll'], env=env, log=log)
    # Read the live registry: Wine may not have flushed its text files yet.
    for key, expected in REGISTRATIONS.items():
        output = run([wine, 'reg.exe', 'query', 'HKCR\\' + key, '/v', 'CLSID'],
                     env=env)
        if not re.search(r'\bCLSID\s+REG_SZ\s+' + re.escape(expected) + r'\s*$',
                         output, re.IGNORECASE | re.MULTILINE):
            raise Error('Legacy HTML registration failed: ' + key)


def missing_registrations(prefix):
    """Inspect persisted Wine registry files without starting a Wine session."""
    values = {}
    for filename in ('system.reg', 'user.reg'):
        current = None
        for line in (Path(prefix) / filename).read_text().splitlines():
            if line.startswith('['):
                current = line[1:line.index(']')].replace('\\\\', '\\').casefold()
            elif current is not None:
                match = re.fullmatch(r'"CLSID"="([^"]*)"', line, re.IGNORECASE)
                if match:
                    values[current] = match.group(1).casefold()
    return [key for key, expected in REGISTRATIONS.items()
            if values.get(('Software\\Classes\\' + key).casefold()) != expected.casefold()]
