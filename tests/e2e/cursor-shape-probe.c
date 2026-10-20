/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
static HCURSOR foreign_arrow;
static HWND main_window;
static LRESULT CALLBACK proc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp)
{
    if(msg==WM_APP+1){foreign_arrow=(HCURSOR)lp;printf("FOREIGN_ARROW %p\n",foreign_arrow);fflush(stdout);return 0;}
    if(msg==WM_SETCURSOR && LOWORD(lp)==HTCLIENT)
    {
        POINT pt;RECT r;GetCursorPos(&pt);ScreenToClient(hwnd,&pt);GetClientRect(hwnd,&r);
        HCURSOR c=pt.x<r.right/2?LoadCursorW(0,IDC_SIZENS):foreign_arrow;
        SetCursor(c);printf("CURSOR region=%s handle=%p\n",pt.x<r.right/2?"resize-ns":"foreign-arrow",c);fflush(stdout);return 1;
    }
    if(msg==WM_PAINT)
    {
        PAINTSTRUCT ps;RECT r;HDC dc=BeginPaint(hwnd,&ps);GetClientRect(hwnd,&r);FillRect(dc,&r,(HBRUSH)(COLOR_WINDOW+1));
        SetBkMode(dc,TRANSPARENT);TextOutW(dc,20,40,L"CURSOR QA: vertical resize",26);TextOutW(dc,r.right/2+15,40,L"CURSOR QA: foreign arrow",24);MoveToEx(dc,r.right/2,0,0);LineTo(dc,r.right/2,r.bottom);EndPaint(hwnd,&ps);return 0;
    }
    if(msg==WM_TIMER){DestroyWindow(hwnd);return 0;}
    if(msg==WM_DESTROY){PostQuitMessage(0);return 0;}
    return DefWindowProcW(hwnd,msg,wp,lp);
}
int wmain(int argc,WCHAR **argv)
{
    if(argc==2 && !wcscmp(argv[1],L"--state"))
    {
        POINT p;CURSORINFO c={0};HWND under,root;RECT r;c.cbSize=sizeof(c);
        GetCursorPos(&p);GetCursorInfo(&c);under=WindowFromPoint(p);root=GetAncestor(under,GA_ROOT);GetWindowRect(root,&r);
        printf("STATE x=%ld y=%ld handle=%p root=%p rect=%ld,%ld,%ld,%ld\n",p.x,p.y,c.hCursor,root,r.left,r.top,r.right,r.bottom);return 0;
    }
    WNDCLASSW wc={0};MSG m;wc.lpfnWndProc=proc;wc.hInstance=GetModuleHandleW(0);wc.lpszClassName=L"PbiVisualCursorQA";RegisterClassW(&wc);
    if(argc==3)
    {
        HWND parent=(HWND)(ULONG_PTR)wcstoull(argv[2],0,16);CreateWindowW(wc.lpszClassName,L"",0,0,0,0,0,HWND_MESSAGE,0,wc.hInstance,0);
        PostMessageW(parent,WM_APP+1,0,(LPARAM)LoadCursorW(0,IDC_ARROW));
        while(GetMessageW(&m,0,0,0)>0){TranslateMessage(&m);DispatchMessageW(&m);}return 0;
    }
    main_window=CreateWindowExW(WS_EX_TOPMOST,wc.lpszClassName,L"Power BI cursor QA - synthetic only",WS_OVERLAPPEDWINDOW,100,100,760,260,0,0,wc.hInstance,0);
    ShowWindow(main_window,SW_SHOWNORMAL);UpdateWindow(main_window);
    {WCHAR p[MAX_PATH],cmd[1024];STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);GetModuleFileNameW(0,p,MAX_PATH);_snwprintf(cmd,1024,L"\"%ls\" --child %llx",p,(unsigned long long)(ULONG_PTR)main_window);
    if(!CreateProcessW(0,cmd,0,0,FALSE,0,0,0,&si,&pi))return 3;
    printf("MAIN %p\n",main_window);fflush(stdout);SetTimer(main_window,1,90000,0);
    while(GetMessageW(&m,0,0,0)>0){TranslateMessage(&m);DispatchMessageW(&m);}PostThreadMessageW(pi.dwThreadId,WM_QUIT,0,0);WaitForSingleObject(pi.hProcess,2000);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);}
    return 0;
}
