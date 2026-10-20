// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Runtime.ExceptionServices;
using System.Reflection;
using System.Globalization;
using System.Collections.Generic;

public class DiagnosticManager : AppDomainManager
{
    [ThreadStatic] private static bool handling;
    private static bool logFull;
    private static readonly bool diagnosticsEnabled =
        Environment.GetEnvironmentVariable("PBI_DIAGNOSTICS") == "1";
    public override void InitializeNewDomain(AppDomainSetup setup)
    {
        if (diagnosticsEnabled)
        {
            Log("Diagnostic manager initialized\r\n");
            AppDomain.CurrentDomain.FirstChanceException += OnException;
        }
        if (Environment.GetEnvironmentVariable("PBI_CULTURE_WORKAROUND") == "1")
        {
            AppDomain.CurrentDomain.AssemblyLoad += delegate(object sender, AssemblyLoadEventArgs e) {
                if(e.LoadedAssembly.GetName().Name != "Microsoft.PowerBI.Client.Windows") return;
                var cultures = new List<CultureInfo>();
                var directory = Path.GetDirectoryName(e.LoadedAssembly.Location);
                foreach(var culture in CultureInfo.GetCultures(CultureTypes.AllCultures))
                {
                    try {
                        if (!culture.Equals(CultureInfo.InvariantCulture) && !culture.TextInfo.IsRightToLeft && Directory.Exists(Path.Combine(directory,culture.Name))) cultures.Add(culture);
                    }
                    catch { Log("Skipping invalid Wine culture: " + culture.Name + "\r\n"); }
                }
                var helper=e.LoadedAssembly.GetType("Microsoft.PowerBI.Client.Windows.DefaultUICultureHelper",true);
                helper.GetMethod("SetSupportedCultures",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{cultures});
                Log("Applied supported culture workaround: " + cultures.Count + " cultures\r\n");
            };
        }
    }
    private static void Log(string message)
    {
        if (!diagnosticsEnabled || logFull) return;
        try {
            const string file = @"C:\powerbi-firstchance.log";
            if (File.Exists(file) && new FileInfo(file).Length >= 64L * 1024 * 1024) {
                logFull = true;
                return;
            }
            File.AppendAllText(file, message);
        }
        catch { }
    }
    private static void OnException(object sender, FirstChanceExceptionEventArgs args)
    {
        if (handling) return;
        handling = true;
        try
        {
            Log(DateTime.Now.ToString("O") + " " + args.Exception.ToString() + "\r\n" + Environment.StackTrace + "\r\n\r\n");
        }
        catch { }
        finally { handling = false; }
    }
}
