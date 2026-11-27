/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Browser frames reach their host while its main window is disabled by a modal dialog.
 *
 * A disposable main window holds one browser-like host (class Chrome_WidgetWin_0,
 * like WebView2's), and this process runs the runtime's frame receiver. Each step
 * publishes a solid colour for the host and reads the host's pixels back:
 *   1. main window enabled (control);
 *   2. main window disabled, as Desktop's is while a modal dialog is open;
 *   3. disabled, with an owned dialog over part of the host.
 * Before the correction, steps 2 and 3 never received a frame, so the host kept
 * whatever was painted before the dialog opened (or the empty background). */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

#define WIDTH 480
#define HEIGHT 360

typedef BOOL (CDECL *start_consumer_fn)(void);
typedef BOOL (CDECL *publish_fn)(HWND, HWND, const void *, UINT, UINT, UINT);

static int passed, failed;

static LRESULT CALLBACK host_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    PAINTSTRUCT paint;
    switch (message)
    {
    case WM_ERASEBKGND:
        return 1;
    case WM_PAINT:
        /* The receiver paints the host; the probe never does. */
        BeginPaint(window, &paint);
        EndPaint(window, &paint);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

static void pump(DWORD milliseconds)
{
    DWORD end = GetTickCount() + milliseconds;
    MSG message;
    while ((LONG)(end - GetTickCount()) > 0)
    {
        while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE))
        {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
        Sleep(10);
    }
}

/* Read a host pixel until it shows the expected colour or three seconds pass. */
static BOOL shows(HWND host, int x, int y, COLORREF expected, COLORREF *seen)
{
    int i;
    for (i = 0; i < 60; i++)
    {
        HDC dc = GetDC(host);
        *seen = GetPixel(dc, x, y);
        ReleaseDC(host, dc);
        if (*seen == expected) return TRUE;
        pump(50);
    }
    return FALSE;
}

static void step(const char *name, publish_fn publish, HWND host, DWORD *pixels,
                 DWORD bgra, COLORREF expected, int x, int y)
{
    COLORREF seen = CLR_INVALID;
    int i;
    for (i = 0; i < WIDTH * HEIGHT; i++) pixels[i] = bgra;
    if (!publish(host, host, pixels, WIDTH, HEIGHT, WIDTH * 4))
    {
        printf("FAIL %s: frame not published\n", name);
        failed++;
        return;
    }
    if (shows(host, x, y, expected, &seen))
    {
        printf("PASS %s\n", name);
        passed++;
    }
    else
    {
        printf("FAIL %s: pixel (%d,%d) is %06lx, expected %06lx\n", name, x, y,
               (unsigned long)seen, (unsigned long)expected);
        failed++;
    }
}

int wmain(void)
{
    WNDCLASSW owner_class = {0}, host_class = {0}, dialog_class = {0};
    HINSTANCE instance = GetModuleHandleW(NULL);
    start_consumer_fn start_consumer;
    publish_fn publish;
    HMODULE dcomp;
    HWND owner, host, dialog;
    RECT client;
    DWORD *pixels;

    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    dcomp = LoadLibraryW(L"dcomp.dll");
    start_consumer = dcomp ? (start_consumer_fn)GetProcAddress(dcomp, "pbi_dcomp_start_consumer") : NULL;
    publish = dcomp ? (publish_fn)GetProcAddress(dcomp, "pbi_dcomp_publish") : NULL;
    if (!start_consumer || !publish)
    {
        printf("FAIL setup: this runtime's dcomp.dll has no frame receiver\nRESULT passed=0 failed=1\n");
        return 1;
    }

    owner_class.lpfnWndProc = DefWindowProcW;
    owner_class.hInstance = instance;
    owner_class.hbrBackground = GetStockObject(WHITE_BRUSH);
    owner_class.lpszClassName = L"PowerBIModalFramesOwner";
    host_class.lpfnWndProc = host_proc;
    host_class.hInstance = instance;
    host_class.lpszClassName = L"Chrome_WidgetWin_0";
    dialog_class.lpfnWndProc = DefWindowProcW;
    dialog_class.hInstance = instance;
    dialog_class.hbrBackground = GetStockObject(LTGRAY_BRUSH);
    dialog_class.lpszClassName = L"PowerBIModalFramesDialog";
    if (!RegisterClassW(&owner_class) || !RegisterClassW(&host_class) || !RegisterClassW(&dialog_class))
    {
        printf("FAIL setup: window classes\nRESULT passed=0 failed=1\n");
        return 1;
    }
    owner = CreateWindowExW(0, owner_class.lpszClassName, L"Power BI modal frames probe - disposable",
                            WS_OVERLAPPED | WS_CAPTION | WS_CLIPCHILDREN | WS_VISIBLE,
                            100, 100, WIDTH + 64, HEIGHT + 96, NULL, NULL, instance, NULL);
    GetClientRect(owner, &client);
    host = CreateWindowExW(0, host_class.lpszClassName, L"", WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS,
                           0, 0, client.right, client.bottom, owner, NULL, instance, NULL);
    pixels = malloc(WIDTH * HEIGHT * 4);
    if (!owner || !host || !pixels || !start_consumer())
    {
        printf("FAIL setup: windows or receiver\nRESULT passed=0 failed=1\n");
        return 1;
    }
    pump(500);

    /* The receiver stretches the frame over the host's client area; sample its lower right. */
    GetClientRect(host, &client);
    step("enabled main window", publish, host, pixels, 0x00ff0000, RGB(255, 0, 0),
         client.right * 5 / 6, client.bottom * 5 / 6);

    EnableWindow(owner, FALSE);
    pump(200);
    step("disabled main window", publish, host, pixels, 0x0000ff00, RGB(0, 255, 0),
         client.right * 5 / 6, client.bottom * 5 / 6);

    /* An owned dialog over the upper left of the host, as Options sits over Desktop. */
    GetWindowRect(host, &client);
    dialog = CreateWindowExW(WS_EX_DLGMODALFRAME, dialog_class.lpszClassName, L"Modal",
                             WS_POPUP | WS_CAPTION | WS_VISIBLE, client.left, client.top,
                             (client.right - client.left) / 2, (client.bottom - client.top) / 2,
                             owner, NULL, instance, NULL);
    pump(200);
    GetClientRect(host, &client);
    step("disabled main window under an owned dialog", publish, host, pixels, 0x000000ff, RGB(0, 0, 255),
         client.right * 5 / 6, client.bottom * 5 / 6);

    if (dialog) DestroyWindow(dialog);
    EnableWindow(owner, TRUE);
    DestroyWindow(owner);
    free(pixels);
    printf("RESULT passed=%d failed=%d\n", passed, failed);
    return failed ? 1 : 0;
}
