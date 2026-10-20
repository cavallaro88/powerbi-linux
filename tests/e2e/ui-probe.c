/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Bounded native window probe: avoids starting another .NET runtime.
 *
 * Read-only commands: windows, children, find, rect.
 * Bounded automation commands: click (main window), click-hwnd, click-screen,
 * focus, text, keys, command, sendmsg.
 */
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <tlhelp32.h>
#include <winternl.h>
static HWND main_window;

static void utf8(const WCHAR *wide, char *output, int capacity)
{
    if (!WideCharToMultiByte(CP_UTF8, 0, wide, -1, output, capacity, NULL, NULL))
        output[0] = '\0';
}

static BOOL match(const WCHAR *value, const char *pattern)
{
    WCHAR wide[512];
    if (!strcmp(pattern, "-")) return TRUE;
    MultiByteToWideChar(CP_UTF8, 0, pattern, -1, wide, 512);
    return wcsstr(value, wide) != NULL;
}

static BOOL CALLBACK list(HWND hwnd, LPARAM unused)
{
    WCHAR title[512], cls[256];
    char title_utf8[2048], cls_utf8[1024];
    RECT rect;
    DWORD pid;
    if (!IsWindowVisible(hwnd)) return TRUE;
    GetWindowTextW(hwnd,title,512); GetClassNameW(hwnd,cls,256);
    GetWindowRect(hwnd,&rect); GetWindowThreadProcessId(hwnd,&pid);
    utf8(title,title_utf8,sizeof(title_utf8)); utf8(cls,cls_utf8,sizeof(cls_utf8));
    printf("WINDOW hwnd=%p owner=%lu owned=%d enabled=%d rect=%ld,%ld,%ld,%ld class=%s title=%s\n",
           hwnd,pid,GetWindow(hwnd,GW_OWNER)!=NULL,IsWindowEnabled(hwnd),rect.left,rect.top,rect.right,rect.bottom,cls_utf8,title_utf8);
    return TRUE;
}

struct find_state { const char *title; const char *cls; int count; };

static BOOL CALLBACK find_proc(HWND hwnd, LPARAM state)
{
    struct find_state *s = (struct find_state *)state;
    WCHAR title[512], cls[256];
    char title_utf8[2048], cls_utf8[1024];
    RECT rect;
    GetWindowTextW(hwnd,title,512); GetClassNameW(hwnd,cls,256);
    if (!match(title, s->title) || !match(cls, s->cls)) return TRUE;
    GetWindowRect(hwnd,&rect);
    utf8(title,title_utf8,sizeof(title_utf8)); utf8(cls,cls_utf8,sizeof(cls_utf8));
    printf("FOUND hwnd=%p visible=%d enabled=%d rect=%ld,%ld,%ld,%ld class=%s title=%s\n",
           hwnd,IsWindowVisible(hwnd),IsWindowEnabled(hwnd),
           rect.left,rect.top,rect.right,rect.bottom,cls_utf8,title_utf8);
    s->count++;
    return TRUE;
}

static int depth_of(HWND hwnd)
{
    int depth = 0;
    while ((hwnd = GetParent(hwnd)) != NULL && depth < 16) depth++;
    return depth;
}

static BOOL CALLBACK children_proc(HWND hwnd, LPARAM unused)
{
    WCHAR title[512], cls[256];
    char title_utf8[2048], cls_utf8[1024];
    RECT rect;
    int depth = depth_of(hwnd), i;
    GetWindowTextW(hwnd,title,512); GetClassNameW(hwnd,cls,256);
    GetWindowRect(hwnd,&rect);
    utf8(title,title_utf8,sizeof(title_utf8)); utf8(cls,cls_utf8,sizeof(cls_utf8));
    for (i = 0; i < depth; i++) putchar(' ');
    printf("CHILD hwnd=%p visible=%d enabled=%d rect=%ld,%ld,%ld,%ld class=%s title=%s\n",
           hwnd,IsWindowVisible(hwnd),IsWindowEnabled(hwnd),
           rect.left,rect.top,rect.right,rect.bottom,cls_utf8,title_utf8);
    return TRUE;
}

static BOOL CALLBACK find_main(HWND hwnd, LPARAM unused)
{
    WCHAR title[512];
    const WCHAR *suffix = L" - Power BI Desktop";
    size_t length;
    if (!IsWindowVisible(hwnd)) return TRUE;
    GetWindowTextW(hwnd, title, 512);
    length = wcslen(title);
    if (length >= wcslen(suffix) && !wcscmp(title + length-wcslen(suffix), suffix))
    { main_window = hwnd; return FALSE; }
    return TRUE;
}

static BOOL CALLBACK close_pbi(HWND hwnd, LPARAM snapshot_arg)
{
    DWORD pid;
    HANDLE snapshot=(HANDLE)snapshot_arg;
    PROCESSENTRY32W entry={.dwSize=sizeof(entry)};
    if (!IsWindowVisible(hwnd) || GetWindow(hwnd,GW_OWNER)) return TRUE;
    GetWindowThreadProcessId(hwnd,&pid);
    if (Process32FirstW(snapshot,&entry)) do {
        if (entry.th32ProcessID==pid && !_wcsicmp(entry.szExeFile,L"PBIDesktop.exe")) {
            PostMessageW(hwnd,WM_CLOSE,0,0);
            puts("CLOSE REQUESTED");
            break;
        }
    } while(Process32NextW(snapshot,&entry));
    return TRUE;
}

static HWND parse_hwnd(const char *text)
{
    /* Base 16 accepts both "0x..." and the %p form without the 0x prefix. */
    return (HWND)(ULONG_PTR)strtoull(text, NULL, 16);
}

static void send_key(HWND hwnd, UINT vk)
{
    UINT scan = MapVirtualKeyW(vk, MAPVK_VK_TO_VSC);
    LPARAM down = 1 | ((LPARAM)(scan & 0xff) << 16);
    LPARAM up = down | (1L << 30) | (1L << 31);
    PostMessageW(hwnd, WM_KEYDOWN, vk, down);
    PostMessageW(hwnd, WM_KEYUP, vk, up);
}

static void send_click(HWND hwnd, int x, int y)
{
    LPARAM point = MAKELPARAM(x, y);
    PostMessageW(hwnd, WM_MOUSEMOVE, 0, point);
    PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, point);
    PostMessageW(hwnd, WM_LBUTTONUP, 0, point);
}

static void screen_click(int x, int y)
{
    SetCursorPos(x, y);
    Sleep(80);
    mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0);
    Sleep(60);
    mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0);
}

static int probe_main(int argc, char **argv)
{
    DWORD_PTR response;
    DWORD pid, error;
    ULONGLONG start;
    BOOL alive;
    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    if (argc==2 && !strcmp(argv[1],"close-pbi")) {
        HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
        if (snapshot==INVALID_HANDLE_VALUE) return 5;
        EnumWindows(close_pbi,(LPARAM)snapshot);
        CloseHandle(snapshot);
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "windows"))
    { EnumWindows(list,0); return 0; }
    if (argc == 3 && !strcmp(argv[1], "responsive")) {
        BOOL ready=SendMessageTimeoutW(parse_hwnd(argv[2]),WM_NULL,0,0,
                        SMTO_ABORTIFHUNG|SMTO_BLOCK,2000,&response)!=0;
        printf("RESPONDS %d\n",ready);
        return ready ? 0 : 3;
    }
    if (argc == 3 && !strcmp(argv[1], "children"))
    { EnumChildWindows(parse_hwnd(argv[2]), children_proc, 0); return 0; }
    if (argc == 4 && !strcmp(argv[1], "find"))
    {
        struct find_state state = {argv[2], argv[3], 0};
        EnumWindows(find_proc, (LPARAM)&state);
        if (!state.count)
        {
            HWND top;
            for (top = GetTopWindow(NULL); top; top = GetWindow(top, GW_HWNDNEXT))
            {
                if (!IsWindowVisible(top)) continue;
                EnumChildWindows(top, find_proc, (LPARAM)&state);
            }
        }
        return state.count ? 0 : 7;
    }
    if (argc == 3 && !strcmp(argv[1], "rect"))
    {
        RECT rect; POINT corner = {0, 0};
        HWND hwnd = parse_hwnd(argv[2]);
        GetWindowRect(hwnd, &rect);
        ClientToScreen(hwnd, &corner);
        printf("RECT hwnd=%p window=%ld,%ld,%ld,%ld client_origin=%ld,%ld\n",
               hwnd, rect.left, rect.top, rect.right, rect.bottom, corner.x, corner.y);
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "focus"))
    { printf("FOCUS %d\n", SetForegroundWindow(parse_hwnd(argv[2]))); return 0; }
    if (argc == 5 && !strcmp(argv[1], "click-hwnd"))
    { send_click(parse_hwnd(argv[2]), atoi(argv[3]), atoi(argv[4])); return 0; }
    if (argc == 4 && !strcmp(argv[1], "click-screen"))
    { screen_click(atoi(argv[2]), atoi(argv[3])); return 0; }
    if (argc == 4 && !strcmp(argv[1], "text"))
    {
        WCHAR wide[4096];
        MultiByteToWideChar(CP_UTF8, 0, argv[3], -1, wide, 4096);
        printf("TEXT %d\n", SetWindowTextW(parse_hwnd(argv[2]), wide));
        return 0;
    }
    if (argc >= 4 && !strcmp(argv[1], "keys"))
    {
        int i;
        for (i = 3; i < argc; i++) send_key(parse_hwnd(argv[2]), (UINT)atoi(argv[i]));
        return 0;
    }
    if (argc == 4 && !strcmp(argv[1], "command"))
    {
        HWND hwnd = parse_hwnd(argv[2]);
        UINT id = (UINT)atoi(argv[3]);
        PostMessageW(hwnd, WM_COMMAND, MAKEWPARAM(id, BN_CLICKED), 0);
        return 0;
    }
    if (argc == 6 && !strcmp(argv[1], "sendmsg"))
    {
        HWND hwnd = parse_hwnd(argv[2]);
        UINT msg = (UINT)strtoul(argv[3], NULL, 0);
        WPARAM wp = (WPARAM)strtoull(argv[4], NULL, 0);
        LPARAM lp = (LPARAM)strtoull(argv[5], NULL, 0);
        printf("SENDMSG %d\n", PostMessageW(hwnd, msg, wp, lp));
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "clipboard"))
    {
        WCHAR wide[65536];
        HGLOBAL mem;
        size_t bytes;
        MultiByteToWideChar(CP_UTF8, 0, argv[2], -1, wide, 65536);
        if (!OpenClipboard(NULL)) { puts("CLIPBOARD 0"); return 0; }
        EmptyClipboard();
        bytes = (wcslen(wide) + 1) * sizeof(WCHAR);
        mem = GlobalAlloc(GMEM_MOVEABLE, bytes);
        if (mem)
        {
            memcpy(GlobalLock(mem), wide, bytes);
            GlobalUnlock(mem);
            SetClipboardData(CF_UNICODETEXT, mem);
        }
        CloseClipboard();
        printf("CLIPBOARD %d\n", mem != NULL);
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "gpu"))
    {
        typedef LONG (WINAPI *Query)(HANDLE,ULONG,void*,ULONG,ULONG*);
        Query query=(Query)GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryInformationProcess");
        HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
        PROCESSENTRY32W entry={.dwSize=sizeof(entry)};
        if (snapshot==INVALID_HANDLE_VALUE || !query) return 5;
        if (Process32FirstW(snapshot,&entry)) do {
            HANDLE process;
            PROCESS_BASIC_INFORMATION info;
            PEB peb;
            RTL_USER_PROCESS_PARAMETERS parameters;
            WCHAR command[32768];
            BOOL gpu=FALSE;
            if (_wcsicmp(entry.szExeFile,L"msedgewebview2.exe")) continue;
            process=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,FALSE,entry.th32ProcessID);
            if (!process) continue;
            if (!query(process,0,&info,sizeof(info),NULL) &&
                ReadProcessMemory(process,info.PebBaseAddress,&peb,sizeof(peb),NULL) &&
                ReadProcessMemory(process,peb.ProcessParameters,&parameters,sizeof(parameters),NULL) &&
                parameters.CommandLine.Length<sizeof(command) &&
                ReadProcessMemory(process,parameters.CommandLine.Buffer,command,parameters.CommandLine.Length,NULL))
            {
                command[parameters.CommandLine.Length/sizeof(WCHAR)]=0;
                gpu=wcsstr(command,L"--type=gpu-process")!=NULL;
            }
            CloseHandle(process);
            if (gpu) { printf("0x%lx\n",entry.th32ProcessID); CloseHandle(snapshot); return 0; }
        } while(Process32NextW(snapshot,&entry));
        CloseHandle(snapshot); return 6;
    }
    EnumWindows(find_main, 0);
    if (!main_window) { puts("PBI_WINDOW_NOT_FOUND"); return 2; }
    GetWindowThreadProcessId(main_window, &pid);
    start = GetTickCount64();
    alive = SendMessageTimeoutW(main_window, WM_NULL, 0, 0, SMTO_ABORTIFHUNG | SMTO_BLOCK, 2000, &response) != 0;
    error = GetLastError();
    printf("PBI_UI hwnd=%p owner=%lu responds=%d enabled=%d elapsed_ms=%llu error=%lu\n", main_window, pid, alive, IsWindowEnabled(main_window), GetTickCount64()-start, error);
    if (!alive) return 3;
    if (argc == 4 && !strcmp(argv[1], "resize"))
        SetWindowPos(main_window, NULL, 0, 0, atoi(argv[2]), atoi(argv[3]), SWP_NOMOVE | SWP_NOZORDER | SWP_ASYNCWINDOWPOS);
    if (argc == 4 && !strcmp(argv[1], "click"))
    {
        HWND target;
        POINT point = {atoi(argv[2]), atoi(argv[3])};
        ClientToScreen(main_window, &point);
        target = WindowFromPoint(point);
        if (!target || GetAncestor(target, GA_ROOT) != main_window) return 4;
        ScreenToClient(target, &point);
        PostMessageW(target, WM_MOUSEMOVE, 0, MAKELPARAM(point.x,point.y));
        PostMessageW(target, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(point.x,point.y));
        PostMessageW(target, WM_LBUTTONUP, 0, MAKELPARAM(point.x,point.y));
        printf("CLICK hwnd=%p x=%ld y=%ld\n",target,point.x,point.y);
    }
    return 0;
}

/* Windows' narrow argv uses the current ANSI code page, whereas the text and
 * clipboard commands below decode UTF-8. Preserve paths with accents by using
 * the Unicode entry point and converting once. Build with -municode. */
int wmain(int argc, WCHAR **wide_argv)
{
    char **argv = calloc(argc + 1, sizeof(*argv));
    int i, result;
    if (!argv) return 7;
    for (i = 0; i < argc; i++) {
        int size = WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, NULL, 0, NULL, NULL);
        if (!size || !(argv[i] = malloc(size))) {
            while (i > 0) free(argv[--i]);
            free(argv);
            return 7;
        }
        WideCharToMultiByte(CP_UTF8, 0, wide_argv[i], -1, argv[i], size, NULL, NULL);
    }
    result = probe_main(argc, argv);
    for (i = 0; i < argc; i++) free(argv[i]);
    free(argv);
    return result;
}
