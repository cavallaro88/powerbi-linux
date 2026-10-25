// SPDX-License-Identifier: GPL-3.0-or-later
// Actual pinned Engine constructors only: no connection, credentials, SQL or report.
using System;
using System.IO;
using System.Reflection;

class OdbcEnvironmentProbe
{
    static readonly BindingFlags Flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;

    static int Main(string[] args)
    {
        if (args.Length != 3 || (args[2] != "success" && args[2] != "env-failure")) return 2;
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs request) {
            string path = Path.Combine(args[0], new AssemblyName(request.Name).Name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        var assembly = Assembly.LoadFrom(Path.Combine(args[0], "Microsoft.MashupEngine.dll"));
        var interopType = assembly.GetType("Microsoft.Mashup.Engine1.Library.Odbc.Interop.OdbcInterop", true);
        var envType = assembly.GetType("Microsoft.Mashup.Engine1.Library.Odbc.Interop.OdbcEnvironmentHandle", true);
        int failures = 0;
        foreach (bool pooling in new bool[] { false, true })
        {
            object interop = null;
            try
            {
                interop = Activator.CreateInstance(interopType, Flags, null, new object[] { args[1] }, null);
                using ((IDisposable)Activator.CreateInstance(envType, Flags, null,
                       new object[] { interop, pooling }, null)) { }
                Console.WriteLine("ENV pooling=" + pooling + " success");
                if (args[2] != "success") failures++;
            }
            catch (Exception error)
            {
                while (error.InnerException != null) error = error.InnerException;
                Console.WriteLine("ENV pooling=" + pooling + " exception=" + error.GetType().Name + " message=" + error.Message);
                if (args[2] != "env-failure" || !error.Message.Contains("Failed to allocate ODBC handle of type 'ENV'"))
                    failures++;
            }
            finally
            {
                if (interop != null)
                {
                    var library = interopType.GetField("libraryHandle", Flags).GetValue(interop) as IDisposable;
                    if (library != null) library.Dispose();
                }
            }
        }
        Console.WriteLine("NETWORK_ATTEMPTED false");
        return failures == 0 ? 0 : 1;
    }
}
