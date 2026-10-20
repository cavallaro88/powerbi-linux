// SPDX-License-Identifier: GPL-3.0-or-later
// Disposable actual Desktop base-class fixture. No report/services are constructed.
using System;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;

class ManagedFrameProbe
{
    [StructLayout(LayoutKind.Sequential)]
    struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    struct Point { public int X, Y; }
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr window, ref Point point);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(Point point);
    [DllImport("user32.dll")] static extern IntPtr SendMessageW(IntPtr window, int message, IntPtr a, IntPtr b);
    [DllImport("user32.dll")] static extern int GetWindowLongW(IntPtr window, int index);
    [DllImport("user32.dll")] static extern int SetWindowLongW(IntPtr window, int index, int value);
    [DllImport("user32.dll")] static extern bool IsZoomed(IntPtr window);
    static string mode;
    static Type formType;

    static void Assert(bool value, string label)
    {
        if (!value) throw new InvalidOperationException(label);
        Console.WriteLine("PASS " + label);
    }
    static int[] Insets(Form form)
    {
        Rect window, client;
        Point point = new Point();
        GetWindowRect(form.Handle, out window);
        GetClientRect(form.Handle, out client);
        ClientToScreen(form.Handle, ref point);
        int[] result = {point.X - window.Left, point.Y - window.Top,
            window.Right - point.X - client.Right, window.Bottom - point.Y - client.Bottom};
        Console.WriteLine("INSETS " + String.Join(",", result));
        return result;
    }
    static void Check(Form form)
    {
        var inset = Insets(form);
        int border = mode == "candidate" ? 0 : 4;
        Assert(inset.SequenceEqual(new[] {border, 0, border, border}), "normal frame geometry (96 DPI)");
        Assert((GetWindowLongW(form.Handle, -16) & 0x40000) != 0, "resize style retained");
        Rect window;
        GetWindowRect(form.Handle, out window);
        var points = new[] {
            new Point {X = window.Left + 1, Y = (window.Top + window.Bottom) / 2},
            new Point {X = window.Right - 2, Y = (window.Top + window.Bottom) / 2},
            new Point {X = (window.Left + window.Right) / 2, Y = window.Bottom - 2}};
        for (int i = 0; i < points.Length; i++)
        {
            var point = points[i];
            var target = WindowFromPoint(point);
            Assert(target != IntPtr.Zero, "edge window exists " + i);
            int hit = SendMessageW(target, 0x84, IntPtr.Zero,
                new IntPtr((point.Y << 16) | (point.X & 65535))).ToInt32();
            Console.WriteLine("HIT " + i + " " + target.ToString("x") + " " + hit);
            Assert(hit == new[] {10, 11, 15}[i], "edge hit test " + i);
        }
    }
    static void CalculationControls()
    {
        // Hidden disposable HWND: test native style-dependent calculations without
        // treating a compositor's asynchronous maximize policy as an API oracle.
        using (var form = (Form)Activator.CreateInstance(formType, true))
        {
            IntPtr window = form.Handle;
            int style = GetWindowLongW(window, -16);
            IntPtr memory = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Rect)));
            try
            {
                foreach (bool maximized in new[] {true, false})
                {
                    SetWindowLongW(window, -16, maximized ? style | 0x1000000 : style);
                    Assert(IsZoomed(window) == maximized, "controlled native maximize flag");
                    var rect = new Rect {Left = 0, Top = 0, Right = 900, Bottom = 600};
                    Marshal.StructureToPtr(rect, memory, false);
                    object[] args = {Message.Create(window, 0x83, IntPtr.Zero, memory)};
                    formType.GetMethod("WndProc", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(form, args);
                    rect = (Rect)Marshal.PtrToStructure(memory, typeof(Rect));
                    int[] actual = {rect.Left, rect.Top, 900 - rect.Right, 600 - rect.Bottom};
                    int border = mode == "candidate" ? 0 : 4;
                    int[] expected = maximized ? new[] {4, 4, 4, 5} : new[] {border, 0, border, border};
                    Assert(actual.SequenceEqual(expected), maximized ?
                        "original maximized calculation preserved" : "normal calculation after maximize flag cleared");
                }
            }
            finally {SetWindowLongW(window, -16, style); Marshal.FreeHGlobal(memory);}
        }
    }
    static void Controls(Form parent)
    {
        using (var owned = (Form)Activator.CreateInstance(formType, true))
        {
            owned.Text = "PBI frame probe (owned control)";
            owned.Owner = parent;
            owned.Show();
            Application.DoEvents();
            var inset = Insets(owned);
            Assert(inset[0] == 4 && inset[2] == 4 && inset[3] == 4, "owned frame preserved");
            owned.Close();
        }
        using (var fixedForm = (Form)Activator.CreateInstance(formType, true))
        {
            fixedForm.FormBorderStyle = FormBorderStyle.FixedSingle;
            fixedForm.Text = "PBI frame probe (fixed control)";
            fixedForm.Show();
            Application.DoEvents();
            var inset = Insets(fixedForm);
            Assert(inset[0] > 0 && inset[2] > 0 && (GetWindowLongW(fixedForm.Handle, -16) & 0x40000) == 0,
                "fixed frame preserved");
            fixedForm.Close();
        }
        CalculationControls();
    }
    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string selected = args[0], app = args[1];
            mode = args[2];
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                string name = new AssemblyName(e.Name).Name + ".dll";
                string path = Path.Combine(selected, name);
                if (!File.Exists(path)) path = Path.Combine(app, name);
                return File.Exists(path) ? Assembly.LoadFrom(path) : null;
            };
            var assembly = Assembly.LoadFrom(Path.Combine(selected, "Microsoft.PowerBI.Client.Windows.dll"));
            formType = assembly.GetType("Microsoft.PowerBI.Client.Windows.ResizableFormWithCustomCaption", true);
            using (var form = (Form)Activator.CreateInstance(formType, true))
            using (var timer = new Timer {Interval = 300000})
            {
                form.Text = "PBI frame probe (" + mode + ")";
                form.StartPosition = FormStartPosition.Manual;
                form.Location = new System.Drawing.Point(0, 0);
                form.Size = new Size(900, 600);
                form.BackColor = Color.FromArgb(40, 130, 190);
                form.Controls.Add(new Panel {Dock = DockStyle.Fill, BackColor = form.BackColor});
                form.Shown += delegate {
                    form.BeginInvoke((Action)delegate {
                        try
                        {
                            Check(form);
                            Controls(form);
                            Console.WriteLine("READY hwnd=" + form.Handle.ToString("x"));
                            if (!args.Contains("--hold")) form.Close();
                        }
                        catch (Exception e) {Console.WriteLine(e); Environment.ExitCode = 1; form.Close();}
                    });
                };
                timer.Tick += delegate {form.Close();};
                timer.Start();
                Application.Run(form);
            }
            return Environment.ExitCode;
        }
        catch (Exception e) {Console.WriteLine(e); return 1;}
    }
}
