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

static int passed, failed, received;
static DWORD child_pid;
static HCURSOR remote_arrow;
static const UINT ids[] = {32512,32513,32514,32515,32644,32645,32649};
static HCURSOR custom_cursor(void)
{
    BYTE and_bits[128], xor_bits[128];
    memset(and_bits,0xff,sizeof(and_bits));memset(xor_bits,0,sizeof(xor_bits));
    xor_bits[0]=0xff;
    return CreateCursor(GetModuleHandleW(NULL),1,1,32,32,and_bits,xor_bits);
}
static void check(BOOL ok, const char *name)
{
    printf("%s %s\n",ok?"PASS":"FAIL",name);fflush(stdout);
    if(ok)passed++;else failed++;
}
static BOOL info(HCURSOR cursor, UINT expected)
{
    ICONINFOEXW i={0};BOOL ok;
    i.cbSize=sizeof(i);ok=GetIconInfoExW(cursor,&i);
    if(ok)
    {
        ok=!i.fIcon && i.hbmMask && i.wResID==expected;
        if(i.hbmColor)DeleteObject(i.hbmColor);
        if(i.hbmMask)DeleteObject(i.hbmMask);
    }
    return ok;
}
static LRESULT CALLBACK window_proc(HWND hwnd,UINT message,WPARAM wparam,LPARAM lparam)
{
    if(message==WM_APP+1)
    {
        char label[80];BOOL ok;
        if(wparam==0)
        {
            ICONINFO i={0};
            ok=!GetIconInfo((HCURSOR)lparam,&i);
            if(i.hbmColor)DeleteObject(i.hbmColor);
            if(i.hbmMask)DeleteObject(i.hbmMask);
            check(ok,"foreign-custom-remains-unsupported");
        }
        else
        {
            if(wparam==32512)remote_arrow=(HCURSOR)lparam;
            snprintf(label,sizeof(label),"foreign-shared-resource-%u",(UINT)wparam);
            check(info((HCURSOR)lparam,(UINT)wparam),label);
        }
        if(++received==sizeof(ids)/sizeof(ids[0])+1)
        {
            DWORD started=GetTickCount();UINT repeat;BOOL ok=TRUE;
            for(repeat=0;repeat<200;repeat++)if(!info(remote_arrow,32512))ok=FALSE;
            printf("Repeated resolution milliseconds=%lu\n",GetTickCount()-started);
            check(ok && GetTickCount()-started<2000,"repeated-cached-resource-resolution");
            PostMessageW(hwnd,WM_APP+4,0,0);
        }
        return 0;
    }
    if(message==WM_APP+4)
    {
        PostThreadMessageW(child_pid,WM_APP+3,(WPARAM)hwnd,0);return 0;
    }
    if(message==WM_APP+3)
    {
        HCURSOR c=LoadCursorW(NULL,MAKEINTRESOURCEW(32651));
        PostMessageW((HWND)wparam,WM_APP+2,0,(LPARAM)c);
        Sleep(1500);return 0;
    }
    if(message==WM_APP+2)
    {
        DWORD started=GetTickCount();ICONINFOEXW data={0};BOOL ok;
        data.cbSize=sizeof(data);ok=GetIconInfoExW((HCURSOR)lparam,&data);
        if(data.hbmColor)DeleteObject(data.hbmColor);
        if(data.hbmMask)DeleteObject(data.hbmMask);
        printf("Unresponsive owner milliseconds=%lu\n",GetTickCount()-started);
        check(!ok && GetTickCount()-started<500,"unresponsive-owner-bounded-failure");
        PostThreadMessageW(child_pid,WM_QUIT,0,0);PostQuitMessage(0);return 0;
    }
    if(message==WM_TIMER){check(FALSE,"owner-response-deadline");PostQuitMessage(0);return 0;}
    return DefWindowProcW(hwnd,message,wparam,lparam);
}
int wmain(int argc,WCHAR **argv)
{
    MSG msg;HWND hwnd;WNDCLASSW cls={0};UINT j;HCURSOR cursor;ICONINFO i={0};
    cls.lpfnWndProc=window_proc;cls.hInstance=GetModuleHandleW(NULL);cls.lpszClassName=L"PbiCursorResourceProbe";
    RegisterClassW(&cls);
    hwnd=CreateWindowW(cls.lpszClassName,L"",0,0,0,0,0,HWND_MESSAGE,0,cls.hInstance,0);
    if(!hwnd)return 3;
    if(argc==3 && !wcscmp(argv[1],L"--child"))
    {
        HWND parent=(HWND)(ULONG_PTR)wcstoull(argv[2],0,16);
        for(j=0;j<sizeof(ids)/sizeof(ids[0]);j++)
        {
            cursor=LoadCursorW(NULL,MAKEINTRESOURCEW(ids[j]));
            PostMessageW(parent,WM_APP+1,ids[j],(LPARAM)cursor);
        }
        cursor=custom_cursor();PostMessageW(parent,WM_APP+1,0,(LPARAM)cursor);
        SetTimer(hwnd,1,15000,NULL);
        while(GetMessageW(&msg,0,0,0)>0){if(msg.message==WM_APP+3)window_proc(hwnd,msg.message,msg.wParam,msg.lParam);else{TranslateMessage(&msg);DispatchMessageW(&msg);}}
        DestroyCursor(cursor);return 0;
    }
    cursor=custom_cursor();check(GetIconInfo(cursor,&i),"local-custom-preserved");
    if(i.hbmColor)DeleteObject(i.hbmColor);
    if(i.hbmMask)DeleteObject(i.hbmMask);
    DestroyCursor(cursor);memset(&i,0,sizeof(i));check(!GetIconInfo(cursor,&i),"destroyed-handle-rejected");
    {
        WCHAR path[MAX_PATH],command[1024];PROCESS_INFORMATION pi={0};STARTUPINFOW si={0};
        si.cb=sizeof(si);GetModuleFileNameW(0,path,MAX_PATH);
        _snwprintf(command,1024,L"\"%ls\" --child %llx",path,(unsigned long long)(ULONG_PTR)hwnd);
        if(!CreateProcessW(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&si,&pi))return 3;
        child_pid=pi.dwThreadId;SetTimer(hwnd,1,12000,NULL);
        while(GetMessageW(&msg,0,0,0)>0){if(msg.message==WM_APP+3)window_proc(hwnd,msg.message,msg.wParam,msg.lParam);else{TranslateMessage(&msg);DispatchMessageW(&msg);}}
        PostThreadMessageW(pi.dwThreadId,WM_QUIT,0,0);
        if(WaitForSingleObject(pi.hProcess,3000)==WAIT_TIMEOUT)TerminateProcess(pi.hProcess,4);
        CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
    }
    printf("RESULT passed=%d failed=%d\n",passed,failed);
    return failed?2:0;
}
