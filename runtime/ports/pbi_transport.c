/*
 * SPDX-License-Identifier: LGPL-2.1-or-later
 * Owner-process delivery adapted from Neutron's winewayland.drv consumer.
 * Uses public Win32 APIs, so the same Wine 11.18 driver can remain in place.
 * A named mutex guards the complete frame, including its dimensions, against
 * concurrent resize and delivery. Uniform frames are legitimate and retained.
 *
 * The browser presents only on damage, so a frame that is not published is not
 * sent again: the last frame of an animation would stay missing until something
 * else repaints. A publisher therefore waits a bounded time for a lock, and the
 * consumer holds a frame's lock for the copy alone.
 */
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "windef.h"
#include "winbase.h"
#include "wingdi.h"
#include "winuser.h"
#include "wine/debug.h"
#include "pbi_transport.h"

WINE_DEFAULT_DEBUG_CHANNEL(dcomp);

/* A frame of any shape up to the area of an 8K display: an ultrawide or a 5K
 * monitor exceeds 4096 x 2304. The mapping has this fixed size, but the server
 * backs it with a sparse file, so only the pixels of real frames take memory. */
#define MAX_PIXELS ((SIZE_T)7680 * 4320)
#define MAX_SIDE 16384
#define MAX_HOSTS 64
/* Milliseconds a publisher waits in all for the consumer's copy and for other
 * publishers, and the consumer for a publisher's write, for a small frame. Each
 * wait is for one memcpy, so both grow with the frame: COPY_RATE bytes per
 * millisecond is a slow machine's memcpy, and an 8K frame then gets 132 ms more.
 * Wine's tick count advances in steps of up to TICK_STEP, so a deadline taken
 * from it gets that much more, or a wait could end that much early. */
#define PUBLISH_WAIT 50
#define CONSUME_WAIT 8
#define COPY_RATE ((SIZE_T)1000000)
#define TICK_STEP 16
struct shared_frame { LONG sequence, width, height; DWORD publisher, window; BYTE pixels[1]; };
#define FRAME_BYTES (sizeof(struct shared_frame) + MAX_PIXELS * 4)
struct registry { DWORD hwnds[MAX_HOSTS]; };
static HANDLE registry_map, registry_mutex;
static struct registry *registry_view;
static INIT_ONCE registry_once = INIT_ONCE_STATIC_INIT;
static INIT_ONCE consumer_once = INIT_ONCE_STATIC_INIT;

static BOOL acquire(HANDLE mutex, DWORD timeout)
{
    DWORD result = WaitForSingleObject(mutex, timeout);
    return result == WAIT_OBJECT_0 || result == WAIT_ABANDONED;
}

static BOOL frame_fits(LONG width, LONG height)
{
    return width > 0 && height > 0 && width <= MAX_SIDE && height <= MAX_SIDE &&
           (SIZE_T)width * height <= MAX_PIXELS;
}

/* The time left before a deadline taken from GetTickCount64, never negative. */
static DWORD remaining(ULONGLONG deadline)
{
    ULONGLONG now = GetTickCount64();
    return now < deadline ? (DWORD)(deadline - now) : 0;
}

/* v3: the frame mapping grew to the area of an 8K display. A mapping of an older
 * runtime's size under the same name could not be mapped at the new size. */
static void object_name(WCHAR *name, HWND hwnd, BOOL mutex)
{
    wsprintfW(name, mutex ? L"__pbi_dcomp_v3_lock_%08x" : L"__pbi_dcomp_v3_px_%08x",
              (DWORD)(ULONG_PTR)hwnd);
}

static BOOL CALLBACK registry_init(INIT_ONCE *once, void *param, void **context)
{
    registry_mutex = CreateMutexW(NULL, FALSE, L"__pbi_dcomp_v3_registry_lock");
    registry_map = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                                     0, sizeof(struct registry), L"__pbi_dcomp_v3_registry");
    if (registry_map) registry_view = MapViewOfFile(registry_map, FILE_MAP_WRITE, 0, 0,
                                                  sizeof(struct registry));
    if (registry_mutex && registry_view) return TRUE;
    if (registry_view) UnmapViewOfFile(registry_view);
    if (registry_map) CloseHandle(registry_map);
    if (registry_mutex) CloseHandle(registry_mutex);
    registry_view = NULL; registry_map = registry_mutex = NULL;
    return FALSE;
}

static BOOL register_host(HWND hwnd, ULONGLONG deadline)
{
    int i, free_slot = -1;
    BOOL found = FALSE;
    if (!InitOnceExecuteOnce(&registry_once, registry_init, NULL, NULL) ||
        !acquire(registry_mutex, remaining(deadline)))
        return FALSE;
    for (i = 0; i < MAX_HOSTS; i++)
    {
        if (registry_view->hwnds[i] == (DWORD)(ULONG_PTR)hwnd) { found = TRUE; break; }
        if (!registry_view->hwnds[i] || !IsWindow((HWND)(ULONG_PTR)registry_view->hwnds[i]))
            if (free_slot < 0) free_slot = i;
    }
    if (!found && free_slot >= 0)
    {
        registry_view->hwnds[free_slot] = (DWORD)(ULONG_PTR)hwnd;
        found = TRUE;
    }
    ReleaseMutex(registry_mutex);
    return found;
}

void pbi_transport_close(struct pbi_transport *transport)
{
    if (transport->view) UnmapViewOfFile(transport->view);
    if (transport->mapping) CloseHandle(transport->mapping);
    if (transport->mutex) CloseHandle(transport->mutex);
    memset(transport, 0, sizeof(*transport));
}

static BOOL publish_until(struct pbi_transport *transport, HWND hwnd, HWND window,
                          const void *pixels, UINT width, UINT height, ULONGLONG deadline)
{
    struct shared_frame *frame;
    WCHAR name[64];
    if (width > MAX_SIDE || height > MAX_SIDE || !frame_fits(width, height))
    {
        static LONG reported;
        /* Nothing can be shown for this window; say so once in the session log. */
        if (width && height && !InterlockedExchange(&reported, 1))
            ERR("pbi-dcomp: frame %ux%u for host %p exceeds the transport limit of %Iu pixels; "
                "this content stays blank\n", width, height, hwnd, MAX_PIXELS);
        return FALSE;
    }
    if (transport->hwnd && transport->hwnd != hwnd) pbi_transport_close(transport);
    if (!transport->view)
    {
        object_name(name, hwnd, TRUE);
        transport->mutex = CreateMutexW(NULL, FALSE, name);
        object_name(name, hwnd, FALSE);
        transport->mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                                                0, (DWORD)FRAME_BYTES, name);
        if (transport->mapping) transport->view = MapViewOfFile(transport->mapping,
                                                               FILE_MAP_WRITE, 0, 0, FRAME_BYTES);
        if (!transport->mutex || !transport->view) { pbi_transport_close(transport); return FALSE; }
        transport->hwnd = hwnd;
    }
    if (!register_host(hwnd, deadline) || !acquire(transport->mutex, remaining(deadline)))
    {
        WARN("pbi-dcomp: frame dropped, lock still held at the deadline host=%p %ux%u\n",
             hwnd, width, height);
        return FALSE;
    }
    frame = transport->view;
    frame->width = width; frame->height = height; frame->publisher = GetCurrentProcessId();
    frame->window = (DWORD)(ULONG_PTR)window;
    memcpy(frame->pixels, pixels, (SIZE_T)width * height * 4);
    InterlockedIncrement(&frame->sequence);
    ReleaseMutex(transport->mutex);
    return TRUE;
}

/* The wait for one frame: the base wait plus the time a slow copy of it takes. */
static DWORD frame_wait(DWORD base, UINT width, UINT height)
{
    if (!frame_fits(width, height)) return base;  /* refused before any copy */
    return base + (DWORD)((SIZE_T)width * height * 4 / COPY_RATE);
}

BOOL pbi_transport_publish(struct pbi_transport *transport, HWND hwnd, HWND window,
                           const void *pixels, UINT width, UINT height)
{
    return publish_until(transport, hwnd, window, pixels, width, height,
                         GetTickCount64() + TICK_STEP + frame_wait(PUBLISH_WAIT, width, height));
}

struct consumer_slot
{
    struct pbi_transport transport;
    LONG sequence;
    DWORD publisher;
    ULONGLONG refreshed;
    BYTE *copy;
    SIZE_T capacity;
    ULONGLONG diagnosed;
};

/* WindowFromPoint stops at a disabled window and never looks at its children:
 * Desktop's main window is disabled while a modal dialog is open, and its
 * browser hosts would then count as covered. Descend to the deepest visible
 * child at the point, as WindowFromPoint does for an enabled window. */
static HWND deepest_window_from_point(POINT point)
{
    HWND window = WindowFromPoint(point), child;
    POINT client;
    int depth;
    for (depth = 0; window && depth < 24; ++depth)
    {
        client = point;
        if (!ScreenToClient(window, &client)) break;
        child = ChildWindowFromPointEx(window, client, CWP_SKIPINVISIBLE);
        if (!child || child == window) break;
        window = child;
    }
    return window;
}

/* WS_VISIBLE is also set on WebView2's preloaded proxy windows. Confirm that
 * this host is actually exposed in the Win32 window tree. Sampling its client
 * area handles partial coverage by a popup without painting hidden siblings. */
static BOOL host_exposed(HWND host)
{
    RECT rect;
    POINT point;
    HWND window;
    WCHAR cls[128];
    DWORD pid;
    int x, y, depth;
    if (!GetClientRect(host, &rect) || rect.right <= 0 || rect.bottom <= 0) return FALSE;
    for (y = 0; y < 3; ++y) for (x = 0; x < 3; ++x)
    {
        point.x = (2*x+1)*rect.right/6;
        point.y = (2*y+1)*rect.bottom/6;
        ClientToScreen(host, &point);
        for (window = deepest_window_from_point(point), depth = 0; window && depth < 24;
             window = GetAncestor(window, GA_PARENT), ++depth)
        {
            GetWindowThreadProcessId(window, &pid);
            if (pid != GetCurrentProcessId()) continue;
            GetClassNameW(window, cls, 128);
            if (wcsncmp(cls, L"Chrome_", 7)) continue;
            if (window == host) return TRUE;
            break;
        }
    }
    return FALSE;
}

static void consume(struct consumer_slot *slot, HWND hwnd)
{
    struct pbi_transport *transport = &slot->transport;
    struct shared_frame *frame;
    WCHAR name[64];
    LONG sequence, width, height;
    DWORD publisher, owner;
    HWND window;
    SIZE_T bytes;
    BYTE *copy;
    HDC dc;
    RECT rect;
    BITMAPINFO bmi = {0};
    ULONGLONG now = GetTickCount64();
    if (!transport->view)
    {
        object_name(name, hwnd, TRUE);
        transport->mutex = OpenMutexW(SYNCHRONIZE | MUTEX_MODIFY_STATE, FALSE, name);
        object_name(name, hwnd, FALSE);
        transport->mapping = OpenFileMappingW(FILE_MAP_READ, FALSE, name);
        if (transport->mapping) transport->view = MapViewOfFile(transport->mapping,
                                                               FILE_MAP_READ, 0, 0, FRAME_BYTES);
        if (!transport->mutex || !transport->view) { pbi_transport_close(transport); return; }
        transport->hwnd = hwnd;
    }
    /* Look without the lock: a publisher counts the sequence last, so an unchanged
     * header means there is nothing to fetch, and a torn one is read again below. */
    frame = transport->view;
    sequence = frame->sequence; width = frame->width; height = frame->height; publisher = frame->publisher;
    window = (HWND)(ULONG_PTR)frame->window;
    if (!sequence || !frame_fits(width, height) ||
        (sequence == slot->sequence && publisher == slot->publisher && now - slot->refreshed < 500))
        return;
    /* The window tree is examined before the lock is taken: these calls reach the
     * server and other processes, and a publisher must not lose a frame to them. */
    if (!IsWindow(window) || !IsWindowVisible(window) || !host_exposed(hwnd)) return;
    GetWindowThreadProcessId(GetAncestor(window, GA_ROOT), &owner);
    if (owner != GetCurrentProcessId()) return;
    bytes = (SIZE_T)width * height * 4;
    if (bytes > slot->capacity)
    {
        copy = realloc(slot->copy, bytes);
        if (!copy) return;
        slot->copy = copy; slot->capacity = bytes;
    }
    if (!acquire(transport->mutex, frame_wait(CONSUME_WAIT, width, height))) return;
    sequence = frame->sequence; width = frame->width; height = frame->height; publisher = frame->publisher;
    bytes = (SIZE_T)width * height * 4;
    /* Resized or retargeted since the look above: the next tick takes it. */
    if ((HWND)(ULONG_PTR)frame->window != window || !frame_fits(width, height) || bytes > slot->capacity)
    { ReleaseMutex(transport->mutex); return; }
    memcpy(slot->copy, frame->pixels, bytes);
    ReleaseMutex(transport->mutex);
    /* The browser child may have its own foreign-process surface. Deliver to
     * the owner proxy, but only when that proxy is exposed. Using its DC with
     * WS_CLIPCHILDREN would exclude the browser's entire content area. */
    if (!GetClientRect(hwnd, &rect) || rect.right <= 0 || rect.bottom <= 0) return;
    if (!(dc = GetDCEx(hwnd, NULL, DCX_CACHE | DCX_CLIPSIBLINGS))) return;
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width; bmi.bmiHeader.biHeight = -height;
    bmi.bmiHeader.biPlanes = 1; bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;
    SetStretchBltMode(dc, COLORONCOLOR);
    if (now-slot->diagnosed>2000 && GetEnvironmentVariableA("PBI_COMPOSITION_DIAG",NULL,0))
    {
        char directory[700], path[1024];
        RECT clip;
        RECT screen;
        POINT point;
        HWND hit;
        HWND ancestor;
        WCHAR cls[128];
        DWORD pid;
        int i;
        int region=GetClipBox(dc,&clip);
        GetWindowRect(hwnd,&screen);
        point.x=(screen.left+screen.right)/2;point.y=(screen.top+screen.bottom)/2;
        hit=WindowFromPoint(point);
        ancestor=hit;
        for(i=0;ancestor && i<24;++i,ancestor=GetAncestor(ancestor,GA_PARENT))
        {
            GetWindowThreadProcessId(ancestor,&pid);
            GetClassNameW(ancestor,cls,128);
            if(pid==GetCurrentProcessId() && !wcsncmp(cls,L"Chrome_",7)) break;
        }
        WARN("pbi-frame: host=%p source=%p sequence=%ld previous=%ld visible=%d clip=%d rect=%s\n",
             hwnd,window,sequence,slot->sequence,IsWindowVisible(window),region,wine_dbgstr_rect(&clip));
        WARN("pbi-layout: host=%p style=%lx ex=%lx root=%p rect=%s center-hit=%p owner-host=%p\n",
             hwnd,GetWindowLongW(hwnd,GWL_STYLE),GetWindowLongW(hwnd,GWL_EXSTYLE),GetAncestor(hwnd,GA_ROOT),wine_dbgstr_rect(&screen),hit,ancestor);
        if (GetEnvironmentVariableA("PBI_WAYLAND_CAPTURE_DIR",directory,sizeof(directory)))
        {
            BITMAPFILEHEADER header={0};
            DWORD written;
            HANDLE file;
            snprintf(path,sizeof(path),"Z:%s/publisher-%08x.bmp",directory,(unsigned int)(ULONG_PTR)hwnd);
            file=CreateFileA(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
            if(file!=INVALID_HANDLE_VALUE)
            {
                header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(BITMAPINFOHEADER);
                header.bfSize=header.bfOffBits+bytes;
                WriteFile(file,&header,sizeof(header),&written,NULL);
                WriteFile(file,&bmi.bmiHeader,sizeof(BITMAPINFOHEADER),&written,NULL);
                WriteFile(file,slot->copy,bytes,&written,NULL);CloseHandle(file);
            }
        }
        slot->diagnosed=now;
    }
    if (StretchDIBits(dc, 0, 0, rect.right, rect.bottom, 0, 0, width, height,
                     slot->copy, &bmi, DIB_RGB_COLORS, SRCCOPY) != GDI_ERROR)
    {
        if (!slot->refreshed) WARN("pbi-dcomp: owner pid=%lu delivered host=%p %ldx%ld publisher=%lu\n",
                                   GetCurrentProcessId(), hwnd, width, height, publisher);
        slot->sequence = sequence; slot->publisher = publisher; slot->refreshed = now;
    }
    ReleaseDC(hwnd, dc);
    GdiFlush();
}

static DWORD WINAPI consumer_thread(void *arg)
{
    struct consumer_slot slots[MAX_HOSTS] = {0};
    DWORD hosts[MAX_HOSTS], self = GetCurrentProcessId();
    int i;
    MSG message;
    /* Coordinates used for the readback are physical pixels. */
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    for (;;)
    {
        /* Lock contention is not window destruction. Keep the receiver's
         * mappings/copies intact and retry the next tick. */
        if (!InitOnceExecuteOnce(&registry_once, registry_init, NULL, NULL) || !acquire(registry_mutex, 0))
        { Sleep(16); continue; }
        memcpy(hosts, registry_view->hwnds, sizeof(hosts));
        ReleaseMutex(registry_mutex);
        for (i = 0; i < MAX_HOSTS; i++)
        {
            HWND hwnd = (HWND)(ULONG_PTR)hosts[i];
            DWORD owner = 0;
            if (hwnd) GetWindowThreadProcessId(hwnd, &owner);
            if (slots[i].transport.hwnd && (slots[i].transport.hwnd != hwnd || !IsWindow(hwnd)))
            {
                pbi_transport_close(&slots[i].transport);
                free(slots[i].copy); memset(&slots[i], 0, sizeof(slots[i]));
            }
            if (owner == self && IsWindowVisible(hwnd)) consume(&slots[i], hwnd);
        }
        /* An empty PeekMessage is Wine 11.18's public path to flush this process's
         * window surfaces. It replaces Neutron's private driver/win32u operation.
         * The receiver has its own empty message queue and owns no windows. */
        PeekMessageW(&message, NULL, 0, 0, PM_NOREMOVE);
        Sleep(16);
    }
    return 0;
}

static BOOL CALLBACK consumer_init(INIT_ONCE *once, void *param, void **context)
{
    HANDLE thread;
    WCHAR owner[24];
    wsprintfW(owner, L"%lu", GetCurrentProcessId());
    if (!SetEnvironmentVariableW(L"PBI_COMPOSITION_OWNER_PID", owner)) return FALSE;
    thread = CreateThread(NULL, 0, consumer_thread, NULL, 0, NULL);
    if (!thread) return FALSE;
    CloseHandle(thread);
    WARN("pbi-dcomp: receiver started owner=%lu\n", GetCurrentProcessId());
    return TRUE;
}

BOOL pbi_dcomp_start_consumer(void)
{
    return InitOnceExecuteOnce(&consumer_once, consumer_init, NULL, NULL);
}

/* Called after the D3D11 context flush, rather than from a DXGI pre-Present
 * hook. Each process publishes at most 64 live owner HWNDs. The caller holds the
 * graphics context lock, so all the waits on other publishers and on the
 * consumer share one deadline, TICK_STEP + frame_wait(PUBLISH_WAIT); none of
 * them takes a graphics lock. */
BOOL pbi_dcomp_publish(HWND hwnd, HWND window, const void *pixels, UINT width, UINT height, UINT pitch)
{
    static struct pbi_transport writers[MAX_HOSTS];
    static LONG busy;
    int i, available = -1;
    BOOL result = FALSE;
    ULONGLONG deadline;
    if (!IsWindow(hwnd) || !IsWindow(window) || !pixels || pitch != width * 4) return FALSE;
    deadline = GetTickCount64() + TICK_STEP + frame_wait(PUBLISH_WAIT, width, height);
    while (InterlockedCompareExchange(&busy, 1, 0))
    {
        if (!remaining(deadline)) return FALSE;
        Sleep(1);
    }
    for (i = 0; i < MAX_HOSTS; ++i)
    {
        if (writers[i].hwnd && !IsWindow(writers[i].hwnd)) pbi_transport_close(&writers[i]);
        if (writers[i].hwnd == hwnd) { available = i; break; }
        if (!writers[i].hwnd && available < 0) available = i;
    }
    if (available >= 0)
    {
        BOOL first = !writers[available].hwnd;
        result = publish_until(&writers[available], hwnd, window, pixels, width, height, deadline);
        if (first && result) WARN("pbi-dcomp: direct publisher pid=%lu host=%p %ux%u\n",
                                 GetCurrentProcessId(), hwnd, width, height);
    }
    InterlockedExchange(&busy, 0);
    return result;
}
