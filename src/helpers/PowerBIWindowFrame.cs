// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public static class PowerBIWindowFrame
{
    const int WS_THICKFRAME = 0x40000, WS_CHILD = 0x40000000;
    static readonly ConditionalWeakTable<Form, Edges> attached = new ConditionalWeakTable<Form, Edges>();
    [StructLayout(LayoutKind.Sequential)] struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] static extern int GetWindowLongW(IntPtr window, int index);
    [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr window, uint command);
    [DllImport("user32.dll")] static extern bool IsZoomed(IntPtr window);
    [DllImport("user32.dll")] static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")] static extern uint GetDpiForWindow(IntPtr window);
    [DllImport("user32.dll")] static extern int GetSystemMetricsForDpi(int index, uint dpi);
    [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr window, IntPtr after, int x, int y, int width, int height, uint flags);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window, int command);
    [DllImport("user32.dll")] static extern bool ValidateRect(IntPtr window, IntPtr rect);
    [DllImport("user32.dll")] static extern IntPtr SendMessageW(IntPtr window, int message, IntPtr wparam, IntPtr lparam);

    public static bool ShouldExtend(Form form)
    {
        if (form == null || form.IsDisposed || !form.IsHandleCreated || !form.TopLevel) return false;
        IntPtr window = form.Handle;
        int style = GetWindowLongW(window, -16);
        return (style & (WS_THICKFRAME | WS_CHILD)) == WS_THICKFRAME &&
            GetWindow(window, 4) == IntPtr.Zero && !IsZoomed(window) && !IsIconic(window);
    }

    public static void Attach(Form form)
    {
        if (form == null || form.IsDisposed || !form.IsHandleCreated || !form.TopLevel ||
            GetWindow(form.Handle, 4) != IntPtr.Zero ||
            (GetWindowLongW(form.Handle, -16) & WS_THICKFRAME) == 0) return;
        attached.GetValue(form, delegate(Form owner) { return new Edges(owner); }).Layout();
    }

    sealed class Edges
    {
        readonly Form form;
        readonly EdgeWindow[] windows = new EdgeWindow[3];
        bool layingOut, disposed;
        public Edges(Form owner)
        {
            form = owner;
            form.SizeChanged += Changed;
            form.Layout += LaidOut;
            form.HandleCreated += Changed;
            form.HandleDestroyed += HandleDestroyed;
            form.Disposed += Disposed;
        }
        void Changed(object sender, EventArgs args) { Layout(); }
        void LaidOut(object sender, LayoutEventArgs args) { Layout(); }
        void HandleDestroyed(object sender, EventArgs args) { Destroy(); }
        void Disposed(object sender, EventArgs args) { disposed = true; Destroy(); }
        void Destroy()
        {
            for (int i = 0; i < windows.Length; i++)
            {
                if (windows[i] != null) windows[i].Close();
                windows[i] = null;
            }
        }
        public void Layout()
        {
            if (layingOut || disposed || !form.IsHandleCreated) return;
            layingOut = true;
            try
            {
                bool show = ShouldExtend(form);
                int width = form.ClientSize.Width, height = form.ClientSize.Height;
                uint dpi = GetDpiForWindow(form.Handle);
                int edge = Math.Max(1, GetSystemMetricsForDpi(32, dpi) + GetSystemMetricsForDpi(92, dpi));
                if (width < edge * 2 || height < edge * 2) show = false;
                for (int i = 0; i < windows.Length; i++)
                {
                    if (windows[i] == null && show) windows[i] = new EdgeWindow(form, i, edge);
                    if (windows[i] == null) continue;
                    if (show)
                    {
                        windows[i].Thickness = edge;
                        SetWindowPos(windows[i].Handle, IntPtr.Zero,
                            i == 1 ? width - edge : i == 2 ? edge : 0,
                            i == 2 ? height - edge : 0,
                            i == 2 ? width - edge * 2 : edge,
                            i == 2 ? edge : height, 0x10);
                    }
                    ShowWindow(windows[i].Handle, show ? 5 : 0);
                }
            }
            finally { layingOut = false; }
        }
    }

    sealed class EdgeWindow : NativeWindow
    {
        readonly Form form;
        readonly int side;
        public int Thickness;
        public EdgeWindow(Form owner, int index, int thickness)
        {
            form = owner; side = index; Thickness = thickness;
            CreateHandle(new CreateParams { Parent = form.Handle, Style = WS_CHILD | 0x10000000,
                ExStyle = 0x20, X = 0, Y = 0, Width = 1, Height = 1, Caption = "" });
        }
        public void Close() { if (Handle != IntPtr.Zero) DestroyHandle(); }
        protected override void WndProc(ref Message message)
        {
            if (message.Msg == 0x84 && ShouldExtend(form))
            {
                Rect rect;
                if (GetWindowRect(form.Handle, out rect))
                {
                    int y = unchecked((short)(message.LParam.ToInt64() >> 16));
                    int hit = side == 0 ? 10 : side == 1 ? 11 : 15;
                    if (side < 2 && y < rect.Top + Thickness) hit = side == 0 ? 13 : 14;
                    else if (side < 2 && y >= rect.Bottom - Thickness) hit = side == 0 ? 16 : 17;
                    message.Result = new IntPtr(hit);
                    return;
                }
            }
            // Input-only transparent children: never erase or paint over WebView.
            if (message.Msg == 0x0f) { ValidateRect(Handle, IntPtr.Zero); message.Result = IntPtr.Zero; return; }
            if (message.Msg == 0x14) { message.Result = new IntPtr(1); return; }
            if (message.Msg >= 0xa0 && message.Msg <= 0xa9)
            {
                message.Result = SendMessageW(form.Handle, message.Msg, message.WParam, message.LParam);
                return;
            }
            base.WndProc(ref message);
        }
    }
}
