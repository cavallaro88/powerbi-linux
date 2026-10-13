// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Reflection;
class EnableModernEditor
{
    static int Main()
    {
        string temporary = null;
        try {
            const string id = "e15d38dd-cda0-403b-93b0-53f698069dec";
            var bin = @"C:\Program Files\Microsoft Power BI Desktop\bin";
            AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
                var candidate = Path.Combine(bin, new AssemblyName(e.Name).Name + ".dll");
                return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
            };
            var asm = Assembly.LoadFrom(Path.Combine(bin, "Microsoft.Mashup.Document.dll"));
            // PackageStorageManager requires the running Desktop's Unity services.
            // Use its local storage implementation directly during offline setup.
            var folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "Power BI Desktop");
            temporary = Path.Combine(Path.GetTempPath(), "powerbi-linux-features-" + Guid.NewGuid().ToString("N"));
            var managerType = asm.GetType("Microsoft.Mashup.Host.Document.Storage.Local.FileLocalStorageManager", true);
            var manager = Activator.CreateInstance(managerType, new object[] {folder, temporary, 16 * 1024 * 1024});
            var type = asm.GetType("Microsoft.Mashup.Host.Document.Storage.Local.LocalFeatureSwitchStorage", true);
            var storage = Activator.CreateInstance(type, new object[] {manager});
            var get = type.GetMethod("GetFeatureSwitches", BindingFlags.Public | BindingFlags.Instance);
            var set = type.GetMethod("SetFeatureSwitches", BindingFlags.Public | BindingFlags.Instance);
            var value = get.Invoke(storage, null);
            value.GetType().GetMethod("Set", new Type[] {typeof(string), typeof(bool)}).Invoke(value, new object[] {id, true});
            set.Invoke(storage, new object[] {value});
            var verify = get.Invoke(storage, null);
            object[] args = new object[] {id, false};
            return (bool)verify.GetType().GetMethod("TryGetBool").Invoke(verify, args) && (bool)args[1] ? 0 : 1;
        } catch (Exception error) { Console.Error.WriteLine("Could not enable the modern Power Query editor: " + error); return 1; }
        finally { if (temporary != null && Directory.Exists(temporary)) Directory.Delete(temporary, true); }
    }
}
