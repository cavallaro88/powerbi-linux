// SPDX-License-Identifier: GPL-3.0-or-later
// Diagnostic fixture only. Shows a form and reports its window state whenever it changes.
// Usage: window-state-probe.exe normal|maximized SECONDS [after-fixed]
// With after-fixed a small fixed-size form is shown first: a tiling compositor
// floats it and gives it the focus before the main form asks for its place.
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

static class WindowStateProbe
{
    [DllImport("user32.dll")] static extern int GetWindowLong(IntPtr window, int index);

    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length < 2 || (args[0] != "normal" && args[0] != "maximized"))
        {
            Console.WriteLine("Usage: window-state-probe.exe normal|maximized SECONDS [after-fixed]");
            return 2;
        }
        Form helper = null;
        if (args.Length > 2 && args[2] == "after-fixed")
        {
            helper = new Form { Text = "pbi-window-state-helper", FormBorderStyle = FormBorderStyle.FixedDialog,
                                StartPosition = FormStartPosition.Manual, Bounds = new Rectangle(300, 300, 320, 160) };
            helper.Show();
            var until = DateTime.UtcNow.AddMilliseconds(1200);
            while (DateTime.UtcNow < until) { Application.DoEvents(); System.Threading.Thread.Sleep(20); }
        }
        var form = new Form { Text = "pbi-window-state-probe", StartPosition = FormStartPosition.Manual,
                              Bounds = new Rectangle(100, 100, 900, 600) };
        if (args[0] == "maximized") form.WindowState = FormWindowState.Maximized;
        string last = null;
        var poll = new Timer { Interval = 100 };
        poll.Tick += (sender, e) =>
        {
            // WS_MAXIMIZE is 0x01000000: the style, not the form's own idea of its state.
            string now = String.Format("STATE {0} style={1:x8} size={2}x{3}",
                (GetWindowLong(form.Handle, -16) & 0x01000000) != 0 ? "maximized" : "normal",
                GetWindowLong(form.Handle, -16), form.Width, form.Height);
            if (now != last) { Console.WriteLine(now); last = now; }
        };
        var stop = new Timer { Interval = int.Parse(args[1]) * 1000 };
        stop.Tick += (sender, e) => form.Close();
        form.Shown += (sender, e) => { poll.Start(); stop.Start(); };
        Application.Run(form);
        if (helper != null) helper.Close();
        return 0;
    }
}
