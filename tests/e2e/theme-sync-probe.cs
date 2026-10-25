// SPDX-License-Identifier: GPL-3.0-or-later
// Run only in an isolated Wine prefix. Uses synthetic settings, never a report.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Remoting.Messaging;
using System.Runtime.Remoting.Proxies;
using System.Runtime.Serialization;
using System.Threading;
using System.Windows.Forms;

class ThemeSyncProbe
{
    const BindingFlags Instance = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
    class Settings : RealProxy
    {
        public string Selection = "System";
        public Settings(Type type) : base(type) { }
        public override IMessage Invoke(IMessage message)
        {
            var call = (IMethodCallMessage)message;
            if (call.MethodName == "get_AppTheme")
                return new ReturnMessage(Selection, null, 0, call.LogicalCallContext, call);
            return new ReturnMessage(new InvalidOperationException("Unexpected settings write: " + call.MethodName), call);
        }
    }
    class Receiver : Form
    {
        public Action Changed;
        public int Notifications;
        protected override void WndProc(ref Message message)
        {
            if (message.Msg == 0x001a && Marshal.PtrToStringUni(message.LParam) == "ImmersiveColorSet")
            {
                Notifications++;
                Changed();
            }
            base.WndProc(ref message);
        }
    }
    static void Check(bool condition, string name)
    {
        if (!condition) throw new Exception(name);
        Console.WriteLine("PASS " + name);
    }
    static void Apply(string helper, string theme, Receiver receiver)
    {
        int before = receiver.Notifications;
        using (var process = Process.Start(new ProcessStartInfo(helper, theme) { UseShellExecute = false }))
        {
            var timer = Stopwatch.StartNew();
            while (!process.HasExited && timer.ElapsedMilliseconds < 8000)
            {
                Application.DoEvents();
                Thread.Sleep(10);
            }
            Check(process.HasExited && process.ExitCode == 0, "helper " + theme);
            Application.DoEvents();
        }
        Check(receiver.Notifications > before, "native ImmersiveColorSet notification");
    }
    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string bin = Path.GetFullPath(args[0]);
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e)
            {
                string file = Path.Combine(bin, new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(file) ? Assembly.LoadFrom(file) : null;
            };
            var assembly = Assembly.LoadFrom(Path.Combine(bin, "Microsoft.PowerBI.Client.Windows.dll"));
            var type = assembly.GetType("Microsoft.PowerBI.Client.Windows.Services.ThemeService", true);
            object service = FormatterServices.GetUninitializedObject(type);
            var field = type.GetField("powerBIUserSettings", Instance);
            var settings = new Settings(field.FieldType);
            field.SetValue(service, settings.GetTransparentProxy());
            type.GetField("windowsThemeService", Instance).SetValue(service,
                Activator.CreateInstance(type.GetNestedType("WindowsThemeService", BindingFlags.NonPublic), true));
            var onChanged = type.GetMethod("OnWindowsThemeChanged", Instance);
            var current = type.GetProperty("CurrentTheme", Instance);
            Func<string> name = () => current.GetValue(service, null).GetType().Name;
            Action<string> set = value => type.GetField("currentTheme", Instance).SetValue(service,
                Activator.CreateInstance(assembly.GetType("Microsoft.PowerBI.Client.Windows.Themes." + value + "Theme"),
                    Instance, null, new object[] { null }, null));
            using (var receiver = new Receiver())
            {
                receiver.Changed = () => onChanged.Invoke(service, null);
                IntPtr handle = receiver.Handle;
                Apply(args[1], "dark", receiver);
                Check(name() == "DarkTheme" && settings.Selection == "System", "System follows dark");
                Apply(args[1], "light", receiver);
                Check(name() == "LightTheme" && settings.Selection == "System", "System follows light");
                settings.Selection = "Light";
                set("Light");
                Apply(args[1], "dark", receiver);
                Check(name() == "LightTheme" && settings.Selection == "Light", "explicit Light preserved");
                settings.Selection = "Dark";
                set("Dark");
                Apply(args[1], "light", receiver);
                Check(name() == "DarkTheme" && settings.Selection == "Dark", "explicit Dark preserved");
                settings.Selection = "System";
                onChanged.Invoke(service, null);
                Check(name() == "LightTheme", "return to System reads latest preference");
            }
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
