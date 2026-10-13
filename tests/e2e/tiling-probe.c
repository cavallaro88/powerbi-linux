/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Disposable native-window control for compositor resize experiments. */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static const WCHAR class_name[] = L"PowerBITilingProbe";

static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    switch (message)
    {
    case WM_SIZE:
    {
        RECT rect;
        GetWindowRect(window, &rect);
        printf("SIZE %ld %ld client=%u,%u\n", rect.right - rect.left,
               rect.bottom - rect.top, LOWORD(lparam), HIWORD(lparam));
        break;
    }
    case WM_GETMINMAXINFO:
    {
        MINMAXINFO *info = (void *)lparam;
        info->ptMinTrackSize.x = 400;
        info->ptMinTrackSize.y = 300;
        return 0;
    }
    case WM_PAINT:
    {
        PAINTSTRUCT paint;
        RECT rect;
        HDC dc = BeginPaint(window, &paint);
        GetClientRect(window, &rect);
        FillRect(dc, &rect, (HBRUSH)(COLOR_WINDOW + 1));
        DrawTextW(dc, L"Power BI tiling probe - disposable native window", -1,
                  &rect, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
        EndPaint(window, &paint);
        return 0;
    }
    case WM_TIMER:
        DestroyWindow(window);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

int wmain(int argc, WCHAR **argv)
{
    WNDCLASSW window_class = {0};
    MSG message;
    HWND window;
    BOOL fixed = argc > 1 && !wcscmp(argv[1], L"--fixed");
    int result;

    setvbuf(stdout, NULL, _IONBF, 0);
    window_class.lpfnWndProc = window_proc;
    window_class.hInstance = GetModuleHandleW(NULL);
    window_class.lpszClassName = class_name;
    window_class.hCursor = LoadCursorW(NULL, IDC_ARROW);
    if (!RegisterClassW(&window_class)) return 2;
    window = CreateWindowW(class_name,
                           fixed ? L"PBI tiling probe (fixed)" : L"PBI tiling probe (resizable)",
                           fixed ? (WS_CAPTION | WS_SYSMENU) : WS_OVERLAPPEDWINDOW,
                           100, 100, 900, 600, NULL, NULL, window_class.hInstance, NULL);
    if (!window) return 2;
    printf("READY hwnd=%p fixed=%d\n", window, fixed);
    if (!SetTimer(window, 1, 600000, NULL))
    {
        DestroyWindow(window);
        return 2;
    }
    ShowWindow(window, SW_SHOWNORMAL);
    while ((result = GetMessageW(&message, NULL, 0, 0)) > 0)
    {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    return result < 0 ? 2 : 0;
}
