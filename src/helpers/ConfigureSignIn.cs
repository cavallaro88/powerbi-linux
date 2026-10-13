// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Reflection;

// Run during offline provisioning. Use Desktop's own settings API so its
// storage implementation preserves unrelated preferences and credential parts.
class ConfigureSignIn
{
    static object Create(Type type, params object[] args)
    {
        return Activator.CreateInstance(type, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                                        null, args, null);
    }

    static int Main(string[] args)
    {
        if ((args.Length != 2 && args.Length != 3) || (args[0] != "--enable" && args[0] != "--check")) {
            Console.Error.WriteLine("Usage: ConfigureSignIn --enable|--check DESKTOP_BIN [SETTINGS_DIRECTORY]");
            return 2;
        }
        string temporary = null;
        try {
            string bin = Path.GetFullPath(args[1]);
            string folder = args.Length == 3 ? Path.GetFullPath(args[2]) :
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "Power BI Desktop");
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                var candidate = Path.Combine(bin, new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
            };
            var asm = Assembly.LoadFrom(Path.Combine(bin, "Microsoft.Mashup.Document.dll"));
            temporary = Path.Combine(Path.GetTempPath(), "powerbi-linux-signin-" + Guid.NewGuid().ToString("N"));
            var managerType = asm.GetType("Microsoft.Mashup.Host.Document.Storage.Local.FileLocalStorageManager", true);
            var manager = Create(managerType, folder, temporary, 16 * 1024 * 1024);
            var storageType = asm.GetType("Microsoft.Mashup.Host.Document.Storage.Local.LocalUISettingsStorage", true);
            var storage = Create(storageType, manager);
            var settingsType = asm.GetType("Microsoft.Mashup.Host.Document.UISettings", true);
            var settings = Create(settingsType, storage);
            var preference = settingsType.GetProperty("UseSystemBrowserForAuthentication");
            if (args[0] == "--enable") preference.SetValue(settings, true, null);
            // Re-read through a new settings object, rather than the setter's cache.
            var verify = Create(settingsType, storage);
            bool enabled = (bool)preference.GetValue(verify, null);
            Console.WriteLine("System authentication browser: " + (enabled ? "enabled" : "disabled"));
            return enabled ? 0 : 1;
        }
        catch (Exception error) {
            // Avoid dumping settings, account identifiers or authentication data.
            var cause = error.GetBaseException();
            Console.Error.WriteLine("Could not configure the authentication browser: " + cause.GetType().FullName + " (" + cause.HResult.ToString("x8") + ")");
            return 1;
        }
        finally {
            if (temporary != null && Directory.Exists(temporary)) Directory.Delete(temporary, true);
        }
    }
}
