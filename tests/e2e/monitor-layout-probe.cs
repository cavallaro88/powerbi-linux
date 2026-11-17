// SPDX-License-Identifier: GPL-3.0-or-later
// Print the monitor layout that Wine reports. Run in a disposable prefix on a
// desktop with more than one output: every monitor must keep its own position.
// Exit code 1 means two monitors share an origin (the single-mode placement loss
// corrected by wine-11.18-single-mode-position.patch).
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

class MonitorLayoutProbe
{
    [StructLayout(LayoutKind.Sequential)]
    struct RECT
    {
        public int left, top, right, bottom;
        public override string ToString() { return "(" + left + "," + top + ")-(" + right + "," + bottom + ")"; }
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct MONITORINFOEX
    {
        public int size;
        public RECT monitor;
        public RECT work;
        public uint flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string device;
    }

    delegate bool MonitorProc(IntPtr monitor, IntPtr dc, ref RECT rect, IntPtr data);
    [DllImport("user32")] static extern bool EnumDisplayMonitors(IntPtr dc, IntPtr clip, MonitorProc proc, IntPtr data);
    [DllImport("user32", CharSet = CharSet.Unicode)] static extern bool GetMonitorInfoW(IntPtr monitor, ref MONITORINFOEX info);
    [DllImport("user32")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
    [DllImport("user32")] static extern IntPtr GetDesktopWindow();
    [DllImport("user32")] static extern bool GetWindowRect(IntPtr window, out RECT rect);
    [DllImport("user32")] static extern int GetSystemMetrics(int index);

    static int Main()
    {
        // Physical pixels: DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2.
        SetThreadDpiAwarenessContext(new IntPtr(-4));
        RECT desktop;
        GetWindowRect(GetDesktopWindow(), out desktop);
        Console.WriteLine("desktop window " + desktop + " virtual " + GetSystemMetrics(76) + "," + GetSystemMetrics(77)
            + " " + GetSystemMetrics(78) + "x" + GetSystemMetrics(79) + " monitors=" + GetSystemMetrics(80));
        var origins = new HashSet<string>();
        bool overlap = false;
        EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, delegate(IntPtr monitor, IntPtr dc, ref RECT rect, IntPtr data)
        {
            var info = new MONITORINFOEX();
            info.size = Marshal.SizeOf(typeof(MONITORINFOEX));
            GetMonitorInfoW(monitor, ref info);
            Console.WriteLine("monitor " + info.device + " rect " + info.monitor + " work " + info.work + " primary=" + (info.flags & 1));
            if (!origins.Add(info.monitor.left + "," + info.monitor.top)) overlap = true;
            return true;
        }, IntPtr.Zero);
        Console.WriteLine(overlap ? "FAIL: monitors share an origin" : "PASS: every monitor has its own origin");
        return overlap ? 1 : 0;
    }
}
