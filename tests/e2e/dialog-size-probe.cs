// SPDX-License-Identifier: GPL-3.0-or-later
// Native helper for dialog-size.py. It reports or closes the first visible
// top-level window whose title contains TEXT.
//   dialog-size-probe.exe find TEXT    prints "FOUND hwnd WxH maximized=0|1 owner-disabled=0|1", exit 0; else exit 1
//   dialog-size-probe.exe close TEXT   posts WM_CLOSE to that window
using System;
using System.Runtime.InteropServices;
using System.Text;

static class DialogSizeProbe
{
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int left, top, right, bottom; }
    delegate bool EnumProc(IntPtr hwnd, IntPtr param);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc proc, IntPtr param);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowTextW(IntPtr hwnd, StringBuilder text, int count);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] static extern int GetWindowLongW(IntPtr hwnd, int index);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr hwnd, uint command);
    [DllImport("user32.dll")] static extern bool PostMessageW(IntPtr hwnd, uint msg, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);

    static int Main(string[] args)
    {
        if (args.Length != 2) { Console.WriteLine("usage: find TEXT | close TEXT"); return 2; }
        SetThreadDpiAwarenessContext(new IntPtr(-4));
        IntPtr found = IntPtr.Zero;
        EnumWindows((hwnd, param) =>
        {
            var title = new StringBuilder(300); GetWindowTextW(hwnd, title, 300);
            if (found == IntPtr.Zero && IsWindowVisible(hwnd) && title.ToString().Contains(args[1])) found = hwnd;
            return true;
        }, IntPtr.Zero);
        if (found == IntPtr.Zero) { Console.WriteLine("NOT_FOUND"); return 1; }
        if (args[0] == "close") { PostMessageW(found, 0x0010, IntPtr.Zero, IntPtr.Zero); Console.WriteLine("CLOSE_POSTED"); return 0; }
        RECT rect; GetWindowRect(found, out rect);
        IntPtr owner = GetWindow(found, 4);
        bool ownerDisabled = owner != IntPtr.Zero && (GetWindowLongW(owner, -16) & 0x08000000) != 0;
        Console.WriteLine("FOUND " + found.ToString("x") + " " + (rect.right - rect.left) + "x" + (rect.bottom - rect.top)
            + " maximized=" + ((GetWindowLongW(found, -16) & 0x01000000) != 0 ? 1 : 0) + " owner-disabled=" + (ownerDisabled ? 1 : 0));
        return 0;
    }
}
