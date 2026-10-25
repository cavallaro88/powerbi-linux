// SPDX-License-Identifier: GPL-3.0-or-later
// Diagnostic fixture only. Uses the user's original DLLs; never submits settings.
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Windows.Forms;

public static class OptionsNativeProbe
{
    const int ThickFrame = 0x40000, Caption = 0xc00000;
    const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    [DllImport("user32.dll")] static extern int GetWindowLongW(IntPtr window, int index);

    static void Assert(bool ok, string message, TextWriter log)
    {
        if (!ok) throw new InvalidOperationException(message);
        log.WriteLine("PASS " + message);
    }

    static void InvalidHandles(Form form, TextWriter log)
    {
        var method = form.GetType().GetMethod("StartResize", Instance);
        var parameter = method.GetParameters()[0].ParameterType;
        foreach (int value in new[] {-1, 8, Int32.MinValue, Int32.MaxValue})
        {
            bool rejected = false;
            try { method.Invoke(form, new[] {Enum.ToObject(parameter, value)}); }
            catch (TargetInvocationException e)
            {
                rejected = e.InnerException is NotSupportedException &&
                    e.InnerException.Message.StartsWith("Unrecognized WindowResizeHandle value:");
            }
            Assert(rejected, "original invalid resize handle rejection " + value, log);
        }
    }

    static void BaseStateCreateParams(Form target, TextWriter log)
    {
        // Exercise each relocated getter in its own process/assembly version.
        // Copy only initialized WinForms base state. No proprietary constructor,
        // browser navigation, report, or visible native window is needed.
        using (var prototype = new Form { FormBorderStyle = FormBorderStyle.None })
        {
            for (var type = typeof(Form); type != null; type = type.BaseType)
                foreach (var field in type.GetFields(Instance | BindingFlags.DeclaredOnly))
                    field.SetValue(target, field.GetValue(prototype));
            var flag = target.GetType().GetProperty("IsResizable", Instance);
            var create = target.GetType().GetProperty("CreateParams", Instance);
            target.Name = "SettingsDialog";
            flag.SetValue(target, true, null);
            Assert((((CreateParams)create.GetValue(target, null)).Style & ThickFrame) != 0,
                "relocated getter enables only the named resizable Options dialog", log);
            flag.SetValue(target, false, null);
            Assert((((CreateParams)create.GetValue(target, null)).Style & ThickFrame) == 0,
                "relocated getter preserves fixed Options style", log);
            flag.SetValue(target, true, null);
            target.Name = "UnrelatedDialog";
            Assert((((CreateParams)create.GetValue(target, null)).Style & ThickFrame) == 0,
                "relocated getter preserves unrelated resizable dialogs", log);
        }
    }

    sealed class ResizeRecorder : NativeWindow
    {
        public int Hit;
        protected override void WndProc(ref Message message)
        {
            if (message.Msg == 0xa1) { Hit = message.WParam.ToInt32(); message.Result = IntPtr.Zero; return; }
            base.WndProc(ref message);
        }
    }

    static void HiddenResizeControl(Form original, TextWriter log)
    {
        var parent = original.GetType().BaseType;
        var parameters = new[] {parent.GetField("uiHost", Instance).GetValue(original),
            parent.GetField("exceptionHandler", Instance).GetValue(original),
            parent.GetField("webDialogViewParams", Instance).GetValue(original)};
        var constructors = original.GetType().GetConstructors(Instance);
        using (var hidden = (Form)constructors[0].Invoke(parameters))
        {
            var flag = hidden.GetType().GetProperty("IsResizable", Instance);
            var create = hidden.GetType().GetProperty("CreateParams", Instance);
            Assert((((CreateParams)create.GetValue(hidden, null)).Style & ThickFrame) == 0,
                "new fixed floating dialog retains fixed style", log);
            flag.SetValue(hidden, true, null);
            hidden.Name = "UnrelatedDialog";
            Assert((((CreateParams)create.GetValue(hidden, null)).Style & ThickFrame) == 0,
                "unrelated resizable floating dialog is unchanged", log);
            hidden.Name = "SettingsDialog";
            var recorder = new ResizeRecorder();
            recorder.AssignHandle(hidden.Handle);
            try
            {
                var method = hidden.GetType().GetMethod("StartResize", Instance);
                var type = method.GetParameters()[0].ParameterType;
                for (int i = 0; i < 8; i++)
                {
                    recorder.Hit = 0;
                    method.Invoke(hidden, new[] {Enum.ToObject(type, i)});
                    Assert(recorder.Hit == 10 + i, "original native resize callback " + i, log);
                }
            }
            finally { recorder.ReleaseHandle(); }
        }
    }

    public static void Check(Form form, TextWriter log)
    {
        if (form.Text != "Options" || form.GetType().FullName !=
                "Microsoft.Mashup.Client.UI.Windows.FloatingDialogWindow")
            throw new InvalidOperationException("Explicit synthetic Options window required");
        Assert(form.Name == "SettingsDialog", "stable culture-independent Options name", log);
        var property = form.GetType().GetProperty("IsResizable", Instance);
        var createParams = form.GetType().GetProperty("CreateParams", Instance);
        bool previous = (bool)property.GetValue(form, null);
        Assert(previous, "original Options resizable flag", log);
        int style = GetWindowLongW(form.Handle, -16);
        Assert((style & ThickFrame) != 0, "native HWND advertises resizing", log);
        Assert((style & Caption) != Caption, "HTML caption has no duplicate native title bar", log);
        try
        {
            property.SetValue(form, false, null);
            Assert((((CreateParams)createParams.GetValue(form, null)).Style & ThickFrame) == 0,
                "fixed dialog CreateParams unchanged", log);
            property.SetValue(form, true, null);
            Assert((((CreateParams)createParams.GetValue(form, null)).Style & ThickFrame) != 0,
                "resizable dialog CreateParams retains resize style", log);
        }
        finally { property.SetValue(form, previous, null); }
        InvalidHandles(form, log);
        HiddenResizeControl(form, log);
    }

    [STAThread]
    public static int Main(string[] args)
    {
        try
        {
            if (args.Length != 2) throw new ArgumentException("UI DLL and dependency directory required");
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                string file = Path.Combine(args[1], new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(file) ? Assembly.LoadFrom(file) : null;
            };
            var assembly = Assembly.LoadFrom(args[0]);
            var type = assembly.GetType("Microsoft.Mashup.Client.UI.Windows.FloatingDialogWindow", true);
            // Invalid enum paths throw before reading this object or invoking Win32.
            // Do not dispose this deliberately uninitialized, never-shown fixture.
            var form = (Form)FormatterServices.GetUninitializedObject(type);
            GC.SuppressFinalize(form);
            InvalidHandles(form, Console.Out);
            BaseStateCreateParams(form, Console.Out);
            return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
}
