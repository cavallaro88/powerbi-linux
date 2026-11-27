// SPDX-License-Identifier: GPL-3.0-or-later
// Native helper for cursor-wake.py. It locates the WebView host whose client
// area is W x H and either moves Wine's cursor with SendInput or checks that
// the thread owning the host's top-level window still answers a sent message.
//   cursor-wake-probe.exe W H move X Y   client coordinates of the host
//   cursor-wake-probe.exe W H park       onto the caption hit-test area, a window of the UI thread
//   cursor-wake-probe.exe W H ping MS    exit 0 when WM_NULL is answered within MS
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

static class CursorWakeProbe
{
    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public MOUSEINPUT mi; }
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int left, top, right, bottom; }
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int x, y; }
    delegate bool EnumProc(IntPtr hwnd, IntPtr param);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc proc, IntPtr param);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr parent, EnumProc proc, IntPtr param);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassNameW(IntPtr hwnd, StringBuilder text, int count);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr hwnd, ref POINT point);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int index);
    [DllImport("user32.dll")] static extern int GetWindowLongW(IntPtr hwnd, int index);
    [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr hwnd, uint flags);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] static extern uint SendInput(uint count, INPUT[] inputs, int size);
    [DllImport("user32.dll")] static extern IntPtr SendMessageTimeoutW(IntPtr hwnd, uint msg, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr result);

    static IntPtr host = IntPtr.Zero, caption = IntPtr.Zero;
    static int best;

    static string ClassOf(IntPtr hwnd) { var s = new StringBuilder(160); GetClassNameW(hwnd, s, 160); return s.ToString(); }

    static void MoveTo(int screenX, int screenY)
    {
        var input = new INPUT[1];
        int vx = GetSystemMetrics(76), vy = GetSystemMetrics(77), vw = GetSystemMetrics(78), vh = GetSystemMetrics(79);
        input[0].mi.dx = (int)Math.Round((screenX - vx) * 65535.0 / (vw - 1));
        input[0].mi.dy = (int)Math.Round((screenY - vy) * 65535.0 / (vh - 1));
        input[0].mi.dwFlags = 0x0001 | 0x8000 | 0x4000; // move, absolute, virtual desktop
        if (SendInput(1, input, Marshal.SizeOf(typeof(INPUT))) != 1) { Console.WriteLine("SendInput failed"); Environment.Exit(3); }
    }

    static int Main(string[] args)
    {
        if (args.Length < 3) { Console.WriteLine("usage: W H move X Y | park | ping MS"); return 2; }
        SetThreadDpiAwarenessContext(new IntPtr(-4));
        int width = int.Parse(args[0]), height = int.Parse(args[1]);
        EnumProc visit = null;
        visit = (hwnd, param) =>
        {
            RECT rect;
            if (IsWindowVisible(hwnd) && ClassOf(hwnd).StartsWith("Chrome_") && GetClientRect(hwnd, out rect)
                && Math.Abs(rect.right - width) <= 6 && Math.Abs(rect.bottom - height) <= 6 && rect.right * rect.bottom > best)
            { host = hwnd; best = rect.right * rect.bottom; }
            if (param == IntPtr.Zero) EnumChildWindows(hwnd, visit, new IntPtr(1));
            return true;
        };
        EnumWindows(visit, IntPtr.Zero);
        if (host == IntPtr.Zero) { Console.WriteLine("HOST_NOT_FOUND " + width + "x" + height); return 2; }
        IntPtr root = GetAncestor(host, 2);
        if ((GetWindowLongW(root, -16) & 0x08000000) != 0) { Console.WriteLine("ROOT_DISABLED a dialog is open"); return 2; }
        uint pid, thread = GetWindowThreadProcessId(root, out pid);
        switch (args[2])
        {
            case "move":
            {
                var point = new POINT { x = int.Parse(args[3]), y = int.Parse(args[4]) };
                ClientToScreen(host, ref point);
                MoveTo(point.x, point.y); Thread.Sleep(40); MoveTo(point.x + 2, point.y + 1);
                Console.WriteLine("MOVED");
                return 0;
            }
            case "park":
            {
                EnumChildWindows(root, (hwnd, param) =>
                {
                    uint owner; if (caption == IntPtr.Zero && IsWindowVisible(hwnd) && GetWindowThreadProcessId(hwnd, out owner) == thread
                        && ClassOf(hwnd).Contains("NonClientHitTestArea")) caption = hwnd;
                    return true;
                }, IntPtr.Zero);
                if (caption == IntPtr.Zero) { Console.WriteLine("CAPTION_AREA_NOT_FOUND"); return 2; }
                RECT rect; GetWindowRect(caption, out rect);
                MoveTo((rect.left + rect.right) / 2, (rect.top + rect.bottom) / 2); Thread.Sleep(40);
                MoveTo((rect.left + rect.right) / 2 + 2, (rect.top + rect.bottom) / 2 + 1);
                Console.WriteLine("PARKED");
                return 0;
            }
            case "ping":
            {
                IntPtr result; var start = DateTime.UtcNow;
                bool answered = SendMessageTimeoutW(root, 0, IntPtr.Zero, IntPtr.Zero, 0, uint.Parse(args[3]), out result) != IntPtr.Zero;
                Console.WriteLine((answered ? "ANSWERED " : "NO_ANSWER ") + (int)(DateTime.UtcNow - start).TotalMilliseconds + " ms thread " + thread.ToString("x4"));
                return answered ? 0 : 1;
            }
        }
        Console.WriteLine("unknown command " + args[2]);
        return 2;
    }
}
