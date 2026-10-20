#!/usr/bin/env python3
"""Rebuild the composition sources from pinned upstreams and a small local port.

Neutron's four production patches are applied unchanged first. The local diff
is emitted separately, preserving provenance and allowing review/reproduction.
"""
from pathlib import Path
import difflib
import hashlib
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ARCHIVE = BASE / 'wine-11.18-source.tar.xz'
ARCHIVE_SHA = 'c6282f6d4daecf11f3ab9f9a2b6c598f67be7e28c363ba2cae8a3c44b611e7a4'
NEUTRON_SHA = '5afd8d479ca83f57b56a2350274927647519da90'
DXVK_SHA = '70d7508c01201ed3d4bfb33da42ba834eafe3857'
WINE = ROOT / 'wine-11.18'
NEUTRON = BASE / 'neutron-wine-source'
DXVK = ROOT / 'dxvk-source'
PATCHES = ['neutron-dcomp-bridge', 'neutron-dcomp-crossproc',
           'neutron-dcomp-resize-fixes', 'neutron-dcomp-swapchain-reaper']

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Expected one occurrence: ' + old[:90])
    return text.replace(old, new, 1)

def diff(path, before, after):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile='a/' + path, tofile='b/' + path))

assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA
assert subprocess.check_output(['git', '-C', str(NEUTRON), 'rev-parse', 'HEAD'], text=True).strip() == NEUTRON_SHA
assert subprocess.check_output(['git', '-C', str(DXVK), 'rev-parse', 'HEAD'], text=True).strip() == DXVK_SHA
files = ['dlls/dcomp/device.c', 'dlls/dcomp/dcomp.spec', 'dlls/dcomp/Makefile.in',
         'dlls/winewayland.drv/wayland_keyboard.c',
         'dlls/winewayland.drv/window_surface.c',
         'dlls/winewayland.drv/wayland_pointer.c',
         'dlls/ntdll/unix/virtual.c']
originals = {}
with tarfile.open(ARCHIVE) as archive:
    for name in files:
        originals[name] = archive.extractfile('wine-11.18/' + name).read().decode()
        (WINE / name).write_text(originals[name])
for patch in PATCHES:
    subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(NEUTRON / 'patches' / (patch + '.mypatch'))],
                   cwd=WINE, check=True)
upstream = {name: (WINE / name).read_text() for name in files}
s = upstream[files[0]]
s = replace(s, '#include "wine/exception.h"', '#include "wine/exception.h"\n#include "pbi_transport.h"')
s = replace(s, '    HANDLE px_map;     /* NEUTRON: shared px section for cross-process panels (see below) */\n    void  *px_view;',
            '    struct pbi_transport transport; /* owner-process pixel delivery */\n    BOOL synchronous;')
start = s.index('/* NEUTRON: cross-process CEP panel present path.')
end = s.index('static struct list presentations =', start)
s = s[:start] + '''/* Pick the closest ancestor owned by the main Power BI process. WebView2
 * browser/renderer/GPU processes have different owners; the receiving control
 * belongs to PBIDesktop. Never guess a target from another swapchain's HWND. */
static HWND find_cef_panel_host(HWND hwnd)
{
    WCHAR owner_text[24], cls[128];
    DWORD owner, pid;
    HWND window, host = NULL;
    int depth;
    BOOL webview = FALSE;
    if (!GetEnvironmentVariableW(L"PBI_COMPOSITION_OWNER_PID", owner_text, 24)) return NULL;
    owner = wcstoul(owner_text, NULL, 10);
    if (!owner) return NULL;
    for (window = hwnd, depth = 0; window && depth < 24;
         window = GetAncestor(window, GA_PARENT), depth++)
    {
        if (GetClassNameW(window, cls, 128) > 0 && !wcsncmp(cls, L"Chrome_", 7)) webview = TRUE;
        GetWindowThreadProcessId(window, &pid);
        if (!host && pid == owner) host = window;
    }
    return webview ? host : NULL;
}

''' + s[end:]
start = s.index('        /* NEUTRON cross-process CEP panel:')
end = s.index('    else if (packed)', start)
s = s[:start] + '''        if (pbi_transport_publish(&p->transport, hwnd, p->hwnd, packed, desc.Width, desc.Height) &&
            !p->t_first_deliver)
        {
            p->t_first_deliver = TRUE;
            WARN("pbi-dcomp: publisher pid=%lu host=%p first frame %ux%u synchronous=%d\\n",
                 GetCurrentProcessId(), hwnd, desc.Width, desc.Height, p->synchronous);
        }
    }
''' + s[end:]
s = replace(s, 'if (p->cross_proc && SUCCEEDED(IDXGISwapChain_GetLastPresentCount',
            'if (!p->synchronous && p->cross_proc && SUCCEEDED(IDXGISwapChain_GetLastPresentCount')
s = replace(s, 'if (p->swapchain && p->present_hwnd && IsWindow(p->present_hwnd))',
            'if (!p->synchronous && p->swapchain && p->present_hwnd && IsWindow(p->present_hwnd) && IsWindowVisible(p->present_hwnd))')
s = replace(s, 'static void register_presentation(HWND hwnd, IUnknown *content)',
            'static void register_presentation(HWND hwnd, IUnknown *content, BOOL synchronous)')
s = replace(s, '    target = host ? host : hwnd;', '''    if (synchronous && !host) { IDXGISwapChain_Release(swapchain); return; }
    target = host ? host : hwnd;''')
start = s.index('    if (host && !GetPropW(host, L"__wine_dcomp_present"))')
end = s.index('    InitOnceExecuteOnce(&presentations_once', start)
s = s[:start] + '''    /* Child windows already draw into their owner's surface in standard Wine.
     * No cross-process SetWindowPos/FRAMECHANGED or Adobe-specific surface flags. */
''' + s[end:]
s = replace(s, '            p->present_hwnd = target;',
            '            p->synchronous = synchronous;\n            p->present_hwnd = target;')
s = replace(s, '\n        p->present_hwnd = target;',
            '\n        p->synchronous = synchronous;\n        p->present_hwnd = target;')
start = s.index('            /* NEUTRON: presentation gone')
end = s.index('            list_remove(&p->entry);', start)
s = s[:start] + s[end:]
s = replace(s, '        if (p->px_view) UnmapViewOfFile(p->px_view);\n        if (p->px_map) CloseHandle(p->px_map);',
            '        pbi_transport_close(&p->transport);')
s = replace(s, '        register_presentation(hwnd, visual->content);',
            '        register_presentation(hwnd, visual->content, FALSE);')
start = s.index('void dcomp_register_external(HWND hwnd, IUnknown *swapchain)')
end = s.index('\nHRESULT WINAPI DCompositionCreateDevice', start)
s = s[:start] + '''void dcomp_register_external(HWND hwnd, IUnknown *swapchain)
{
    struct presentation *p;
    /* A composition swapchain has no HWND until SetRoot/Commit binds its visual.
     * Falling back to the last surface factory's window can target another tab.
     * HWND swapchains are captured on their Present thread BEFORE flip rotation,
     * so legitimate uniform/empty frames don't require a blank-frame heuristic. */
    if (!hwnd || !find_cef_panel_host(hwnd) || !IsWindowVisible(hwnd)) return;
    register_presentation(hwnd, swapchain, TRUE);
    EnterCriticalSection(&presentations_cs);
    LIST_FOR_EACH_ENTRY(p, &presentations, struct presentation, entry)
    {
        if (p->hwnd == hwnd && p->synchronous)
        {
            blit_swapchain_to_hwnd(p);
            break;
        }
    }
    LeaveCriticalSection(&presentations_cs);
}
''' + s[end:]
(WINE / files[0]).write_text(s)
spec = upstream[files[1]] + '@ cdecl pbi_dcomp_start_consumer()\n@ cdecl pbi_dcomp_resolve_host(ptr)\n@ cdecl pbi_dcomp_publish(ptr ptr ptr long long long)\n'
(WINE / files[0]).write_text(s + '\nHWND pbi_dcomp_resolve_host(HWND hwnd) { return find_cef_panel_host(hwnd); }\n')
(WINE / files[1]).write_text(spec)
makefile = upstream[files[2]].replace('\tdevice.c', '\tdevice.c \\\n\tpbi_transport.c')
(WINE / files[2]).write_text(makefile)
for name in ('pbi_transport.c', 'pbi_transport.h'):
    (WINE / 'dlls/dcomp' / name).write_bytes((ROOT / name).read_bytes())
# WinForms converts the HKL to Int32 before extracting its LANGID. Windows HKLs
# with bit 31 set are signed handles on x64; zero-extension of E001/Fxxx causes
# IntPtr.ToInt32 to overflow. Preserve the low 32 bits and sign-extend the handle.
keyboard = upstream[files[3]]
keyboard = replace(keyboard, 'return ULongToHandle(MAKELONG(locale, 0xe001));',
                   'return LongToHandle(MAKELONG(locale, 0xe001));')
keyboard = keyboard.replace('(HKL)(UINT_PTR)MAKELONG(locale,', '(HKL)(INT_PTR)(LONG)MAKELONG(locale,')
(WINE / files[3]).write_text(keyboard)
surface = upstream[files[4]]
surface = replace(surface, '#include <stdlib.h>', '#include <stdlib.h>\n#include <stdio.h>\n#include <time.h>')
surface = replace(surface, '    BOOL layered;', '    BOOL layered;\n    uint64_t pbi_last_dump;')
surface = replace(surface, '/***********************************************************************\n *           wayland_window_surface_flush',
                  (ROOT / 'wayland-dump.inc').read_text() + '\n/***********************************************************************\n *           wayland_window_surface_flush')
surface = replace(surface, '    wl_display_flush(process_wayland.wl_display);',
                  '    if (flushed) pbi_dump_submitted_surface(wws, shm_buffer);\n    wl_display_flush(process_wayland.wl_display);')
(WINE / files[4]).write_text(surface)
(ROOT / 'wine-11.18-wayland-diagnostics.patch').write_text(diff(files[4], upstream[files[4]], surface))
(ROOT / 'wine-11.18-wayland-hkl.patch').write_text(diff(files[3], upstream[files[3]], keyboard))
cursor_patch = (NEUTRON / 'patches/neutron-zzzzzzzzzzzw-winewayland-cursor-keep-last-on-unresolvable-handle.mypatch').read_text()
(ROOT / 'neutron-cursor-upstream.patch').write_text(cursor_patch[cursor_patch.index('--- a/'):])
subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(ROOT / 'neutron-cursor-upstream.patch')], cwd=WINE, check=True)
pointer = (WINE / files[5]).read_text()
pointer = replace(pointer, 'if (v < 0) v = neutron_gate("NEUTRON_CURSOR_KEEP", TRUE);',
                  'if (v < 0) { const char *e = getenv("PBI_CURSOR_KEEP"); v = !e || e[0] != \'0\'; }')
pointer = pointer.replace('getenv("NEUTRON_WL_DIAG")', 'getenv("PBI_COMPOSITION_DIAG")')
pointer = pointer.replace('ERR("neutron-cursorkeep:', 'WARN("pbi-cursor-keep:')
pointer = pointer.replace('NEUTRON_CURSOR_KEEP=0', 'PBI_CURSOR_KEEP=0')
pointer = pointer.replace('NEUTRON_WL_DIAG=1', 'PBI_COMPOSITION_DIAG=1')
(WINE / files[5]).write_text(pointer)
(ROOT / 'wine-11.18-wayland-cursor.patch').write_text(diff(files[5], upstream[files[5]], pointer))
virtual = upstream[files[6]]
virtual = replace(virtual, '/***********************************************************************\n *           map_file_into_view',
                  (ROOT / 'pe-section-cache.inc').read_text() + '\n/***********************************************************************\n *           map_file_into_view')
virtual = replace(virtual, '        if (mmap( host_addr, host_size, prot, flags, fd, offset ) != MAP_FAILED)',
                  '        if (pbi_map_cached_pe_section(view, fd, host_addr, size, host_size, offset, prot, vprot, removable))\n            return STATUS_SUCCESS;\n\n        if (mmap( host_addr, host_size, prot, flags, fd, offset ) != MAP_FAILED)')
(WINE / files[6]).write_text(virtual)
(ROOT / 'wine-11.18-pe-section-cache.patch').write_text(diff(files[6], upstream[files[6]], virtual))
(ROOT / 'pbi-dcomp-adaptation.patch').write_text(''.join(
    diff(name, upstream[name], (WINE / name).read_text()) for name in files))
(ROOT / 'wine-11.18-composition.patch').write_text(''.join(
    diff(name, originals[name], (WINE / name).read_text()) for name in files) + ''.join(
    diff('dlls/dcomp/' + name, '', (ROOT / name).read_text()) for name in ('pbi_transport.c', 'pbi_transport.h')))

# Wine's oledb32 only converts BSTR/I8 sources to I8 and lacks the VARIANT case
# for I8/BOOL destinations. Power BI's report layer (MsolapWrapper) binds
# numeric/boolean columns through those conversions and read zeros without it.
# Backport the two VARIANT cases that upstream Wine added later.
oledb32_path = 'dlls/oledb32/convert.c'
with tarfile.open(ARCHIVE) as archive:
    oledb32_original = archive.extractfile('wine-11.18/' + oledb32_path).read().decode()
oledb32 = oledb32_original
oledb32 = replace(oledb32,
    '''        case DBTYPE_BSTR:        hr = VarI8FromStr(*(WCHAR**)src, LOCALE_USER_DEFAULT, 0, d); break;
        case DBTYPE_I8:          *d = *(LONGLONG*)src; hr = S_OK;              break;
        default: FIXME("Unimplemented conversion %04x -> I8\\n", src_type); return E_NOTIMPL;''',
    '''        case DBTYPE_BSTR:        hr = VarI8FromStr(*(WCHAR**)src, LOCALE_USER_DEFAULT, 0, d); break;
        case DBTYPE_I8:          *d = *(LONGLONG*)src; hr = S_OK;              break;
        case DBTYPE_VARIANT:
            VariantInit(&tmp);
            if ((hr = VariantChangeType(&tmp, src, 0, VT_I8)) == S_OK)
                *d = V_I8(&tmp);
            break;
        default: FIXME("Unimplemented conversion %04x -> I8\\n", src_type); return E_NOTIMPL;''')
oledb32 = replace(oledb32,
    '''        case DBTYPE_BOOL:        *d = *(VARIANT_BOOL*)src; hr = S_OK;            break;
        case DBTYPE_DECIMAL:     hr = VarBoolFromDec(src, d);                    break;
        default: FIXME("Unimplemented conversion %04x -> BOOL\\n", src_type); return E_NOTIMPL;''',
    '''        case DBTYPE_BOOL:        *d = *(VARIANT_BOOL*)src; hr = S_OK;            break;
        case DBTYPE_DECIMAL:     hr = VarBoolFromDec(src, d);                    break;
        case DBTYPE_VARIANT:
            VariantInit(&tmp);
            if ((hr = VariantChangeType(&tmp, src, 0, VT_BOOL)) == S_OK)
                *d = V_BOOL(&tmp);
            break;
        default: FIXME("Unimplemented conversion %04x -> BOOL\\n", src_type); return E_NOTIMPL;''')
(WINE / oledb32_path).write_text(oledb32)
(ROOT / 'wine-11.18-oledb32-variant.patch').write_text(diff(oledb32_path, oledb32_original, oledb32))

# Owned toplevels (dialogs) must be marked as transient for their owner;
# otherwise the compositor can keep a modal dialog behind the main window.
wayland_window_path = 'dlls/winewayland.drv/window.c'
with tarfile.open(ARCHIVE) as archive:
    wayland_window_original = archive.extractfile('wine-11.18/' + wayland_window_path).read().decode()
wayland_window = replace(wayland_window_original,
    '''    case WAYLAND_SURFACE_ROLE_TOPLEVEL:
        wayland_surface_make_toplevel(surface);
        break;''',
    '''    case WAYLAND_SURFACE_ROLE_TOPLEVEL:
        wayland_surface_make_toplevel(surface);
        /* Owned toplevels (dialogs) are marked as transient for their owner
         * so compositors keep them above the owner window. Without this the
         * modal dialog could stay behind the main window under Wayland. */
        if (owner_surface && owner_surface->role == WAYLAND_SURFACE_ROLE_TOPLEVEL &&
            owner_surface->xdg_toplevel)
            xdg_toplevel_set_parent(surface->xdg_toplevel, owner_surface->xdg_toplevel);
        break;''')
wayland_window = replace(wayland_window,
    '''{
    HWND owner = NtUserGetAncestor(hwnd, GA_ROOT);
    struct wayland_surface *owner_surface;
    struct wayland_win_data *data, *owner_data;
    BOOL managed, fullscreen = swp_flags & WINE_SWP_FULLSCREEN;''',
    '''{
    HWND owner = NtUserGetAncestor(hwnd, GA_ROOT);
    HWND gw_owner = NtUserGetWindowRelative(hwnd, GW_OWNER);
    struct wayland_surface *owner_surface;
    struct wayland_win_data *data, *owner_data;
    BOOL managed, fullscreen = swp_flags & WINE_SWP_FULLSCREEN;''')
wayland_window = replace(wayland_window,
    '''    if (!(data = wayland_win_data_get(hwnd))) return;
    owner_data = owner && owner != hwnd ? wayland_win_data_get(owner) : NULL;
    owner_surface = owner_data ? owner_data->wayland_surface : NULL;''',
    '''    if (!(data = wayland_win_data_get(hwnd))) return;
    owner_data = owner && owner != hwnd ? wayland_win_data_get(owner) : NULL;
    owner_surface = owner_data ? owner_data->wayland_surface : NULL;
    /* Toplevel dialogs are owned via GW_OWNER, not the ancestor chain. */
    if (!owner_data && gw_owner && gw_owner != hwnd)
    {
        owner_data = wayland_win_data_get(gw_owner);
        owner_surface = owner_data ? owner_data->wayland_surface : NULL;
    }''')
(WINE / wayland_window_path).write_text(wayland_window)
(ROOT / 'wine-11.18-wayland-parent.patch').write_text(diff(wayland_window_path, wayland_window_original, wayland_window))

# Wine reports host RAM to Windows apps. Clamp it to the cgroup v2 limits so
# the CLR, Chromium (WebView2) and the AS engine size heaps and caches for the
# cgroup and are not OOM-killed when the host has more memory than the limit.
cgroup_inc = (ROOT / 'cgroup-memory.inc').read_text()
cgroup_diffs = []
cgroup_targets = {
    'dlls/ntdll/unix/virtual.c': (
        'void virtual_get_system_info( SYSTEM_BASIC_INFORMATION *info, BOOL wow64 )',
        '    info->unknown                 = 0;',
        '''    {
        struct pbi_cgroup_memory cgroup_memory;
        unsigned long long total;

        pbi_get_cgroup_memory( &cgroup_memory );
        if (cgroup_memory.max)
        {
            total = (unsigned long long)info->MmHighestPhysicalPage * page_size;
            if (total > cgroup_memory.max)
                info->MmHighestPhysicalPage = max( 1, cgroup_memory.max / page_size );
        }
    }

'''),
    'dlls/ntdll/unix/system.c': (
        'static void get_performance_info( SYSTEM_PERFORMANCE_INFORMATION *info )',
        '    /* Titan Quest refuses to run if TotalPageFile <= TotalPhys */',
        '''    {
        struct pbi_cgroup_memory cgroup_memory;
        unsigned long long available;

        pbi_get_cgroup_memory( &cgroup_memory );
        if (cgroup_memory.max)
        {
            if (totalram > cgroup_memory.max) totalram = cgroup_memory.max;
            available = cgroup_memory.current < cgroup_memory.max ?
                        cgroup_memory.max - cgroup_memory.current : 0;
            if (freeram > available) freeram = available;
        }
        if (cgroup_memory.swap_max)
        {
            if (totalswap > cgroup_memory.swap_max) totalswap = cgroup_memory.swap_max;
            available = cgroup_memory.swap_current < cgroup_memory.swap_max ?
                        cgroup_memory.swap_max - cgroup_memory.swap_current : 0;
            if (freeswap > available) freeswap = available;
        }
    }

'''),
}
for path, (func_anchor, call_anchor, clamp) in cgroup_targets.items():
    if path.endswith('virtual.c'):
        # Current tree: refreshed above with the PE cache patch.
        before = (WINE / path).read_text()
    else:
        with tarfile.open(ARCHIVE) as archive:
            before = archive.extractfile('wine-11.18/' + path).read().decode()
    text = replace(before, func_anchor, cgroup_inc + '\n' + func_anchor)
    text = replace(text, call_anchor, clamp + call_anchor)
    (WINE / path).write_text(text)
    cgroup_diffs.append(diff(path, before, text))
(ROOT / 'wine-11.18-cgroup-memory.patch').write_text(''.join(cgroup_diffs))

subprocess.run(['python3', str(ROOT / 'port-dxvk-gdi.py')], check=True)
print('Wine 11.18: four Neutron patches + owner-process transport + oledb32 VARIANT cases; DXVK 3.1: scoped GDI presentation.')
