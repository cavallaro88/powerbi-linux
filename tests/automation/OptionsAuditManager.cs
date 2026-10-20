// SPDX-License-Identifier: GPL-3.0-or-later
// Diagnostic copy only: never installed as the production AppDomain manager.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

public class OptionsAuditManager : CompositionManager
{
    [DllImport("dcomp.dll", CallingConvention = CallingConvention.Cdecl)]
    static extern bool pbi_dcomp_start_consumer();
    static string directory;
    static Timer timer;

    public override void InitializeNewDomain(AppDomainSetup setup)
    {
        base.InitializeNewDomain(setup);
        if (System.Diagnostics.Process.GetCurrentProcess().ProcessName != "PBIOptionsAudit") return;
        directory = Environment.GetEnvironmentVariable("PBI_OPTIONS_AUDIT_DIR");
        if (String.IsNullOrEmpty(directory) || !Directory.Exists(directory))
            throw new InvalidOperationException("Explicit private audit directory required");
        pbi_dcomp_start_consumer();
        Application.Idle += Start;
    }

    static void Start(object sender, EventArgs args)
    {
        if (Application.OpenForms.Count == 0) return;
        Application.Idle -= Start;
        timer = new Timer { Interval = 200 };
        timer.Tick += Tick;
        timer.Start();
    }

    static void Tick(object sender, EventArgs args)
    {
        var request = Path.Combine(directory, "request.txt");
        if (!File.Exists(request)) return;
        var command = File.ReadAllText(request).Trim();
        File.Delete(request);
        var log = new StringBuilder();
        try
        {
            bool synthetic = false;
            foreach (Form form in Application.OpenForms)
                if (form.GetType().FullName == "Microsoft.PowerBI.Client.Windows.MainForm" && form.Text == "Synthetic")
                    synthetic = true;
            if (!synthetic) throw new InvalidOperationException("Synthetic fixture main window required");
            log.AppendLine("SCOPE synthetic-options");
            foreach (Form form in Application.OpenForms)
                if (form.Text == "Options") Inspect(form, log, command, 0);
        }
        catch (Exception exc) { log.AppendLine("ERROR " + exc.GetType().FullName); }
        File.WriteAllText(Path.Combine(directory, "response.txt"), log.ToString());
    }

    static void Inspect(Control control, StringBuilder log, string command, int depth)
    {
        if (depth > 15) return;
        var browser = control as WebBrowser;
        if (browser != null && browser.Document != null && command == "inspect")
        {
            var script = File.ReadAllText(Path.Combine(directory, "inspect.js"));
            log.AppendLine("SCRIPT " + browser.Document.InvokeScript("eval", new object[] { script }));
        }
        foreach (Control child in control.Controls) Inspect(child, log, command, depth + 1);
    }
}
