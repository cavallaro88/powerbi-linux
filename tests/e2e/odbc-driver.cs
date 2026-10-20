// SPDX-License-Identifier: GPL-3.0-or-later
// Offline Windows driver/DSN discovery and handle checks. No SQL or connection.
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32;

class OdbcDriverProbe
{
    [DllImport("odbc32.dll")] static extern short SQLAllocHandle(short kind, IntPtr parent, out IntPtr handle);
    [DllImport("odbc32.dll")] static extern short SQLSetEnvAttr(IntPtr env, int attr, IntPtr value, int length);
    [DllImport("odbc32.dll")] static extern short SQLFreeHandle(short kind, IntPtr handle);
    [DllImport("odbc32.dll", CharSet=CharSet.Unicode)] static extern short SQLDriversW(IntPtr env, ushort direction,
        StringBuilder name, short capacity, out short length, StringBuilder attrs, short attrCapacity, out short attrLength);
    [DllImport("odbc32.dll", CharSet=CharSet.Unicode)] static extern short SQLDataSourcesW(IntPtr env, ushort direction,
        StringBuilder name, short capacity, out short length, StringBuilder description, short descCapacity, out short descLength);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr LoadLibraryEx(string path, IntPtr file, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Ansi)] static extern IntPtr GetProcAddress(IntPtr library, string name);
    [DllImport("kernel32.dll")] static extern bool FreeLibrary(IntPtr library);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate short Alloc(short kind, IntPtr parent, out IntPtr handle);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate short Free(short kind, IntPtr handle);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate short SetEnv(IntPtr env, int attr, IntPtr value, int length);

    static void Success(short rc, string name) { if (rc != 0 && rc != 1) throw new Exception(name + " returned " + rc); }
    static T Function<T>(IntPtr library, string name) where T : class
    {
        IntPtr ptr = GetProcAddress(library, name);
        if (ptr == IntPtr.Zero) throw new Exception("Missing export " + name);
        return Marshal.GetDelegateForFunctionPointer(ptr, typeof(T)) as T;
    }
    static void Probe(string driver, string dsn)
    {
        if (IntPtr.Size != 8) throw new Exception("Expected x64 process");
        string path;
        using (var key = Registry.LocalMachine.OpenSubKey(@"Software\ODBC\ODBCINST.INI\" + driver))
        {
            if (key == null) throw new Exception("Driver registry entry absent");
            path = key.GetValue("Driver") as string;
            if (String.IsNullOrEmpty(path)) throw new Exception("Driver path absent");
        }
        Console.WriteLine("REGISTRY_DRIVER " + driver);
        Console.WriteLine("FILE_VERSION " + FileVersionInfo.GetVersionInfo(path).FileVersion);
        IntPtr env;
        Success(SQLAllocHandle(1, IntPtr.Zero, out env), "manager ENV");
        try
        {
            Success(SQLSetEnvAttr(env, 200, new IntPtr(3), 0), "manager ODBC3");
            bool found = false;
            for (ushort direction = 2; ; direction = 1)
            {
                var name = new StringBuilder(1024); var attrs = new StringBuilder(8192); short length, attrLength;
                short rc = SQLDriversW(env, direction, name, 1024, out length, attrs, 8192, out attrLength);
                if (rc == 100) break;
                Success(rc, "SQLDriversW");
                if (name.ToString() == driver) found = true;
            }
            if (!found) throw new Exception("Driver not enumerated by actual ODBC manager");
            Console.WriteLine("MANAGER_ENUMERATES_DRIVER true");
            if (dsn.Length != 0)
            {
                bool foundDsn = false;
                for (ushort direction = 2; ; direction = 1)
                {
                    var name = new StringBuilder(1024); var description = new StringBuilder(1024); short length, descLength;
                    short rc = SQLDataSourcesW(env, direction, name, 1024, out length, description, 1024, out descLength);
                    if (rc == 100) break;
                    Success(rc, "SQLDataSourcesW");
                    if (name.ToString() == dsn && description.ToString() == driver) foundDsn = true;
                }
                if (!foundDsn) throw new Exception("Requested DSN/driver pair not enumerated");
                Console.WriteLine("MANAGER_ENUMERATES_DSN true");
            }
        }
        finally { Success(SQLFreeHandle(1, env), "free manager ENV"); }

        IntPtr library = LoadLibraryEx(path, IntPtr.Zero, 8);
        if (library == IntPtr.Zero) throw new Exception("Driver load failed: " + Marshal.GetLastWin32Error());
        try
        {
            var alloc = Function<Alloc>(library, "SQLAllocHandle");
            var free = Function<Free>(library, "SQLFreeHandle");
            var set = Function<SetEnv>(library, "SQLSetEnvAttr");
            foreach (string name in new [] { "SQLDriverConnectW", "SQLGetDiagRecW", "SQLCancel" })
                if (GetProcAddress(library, name) == IntPtr.Zero) throw new Exception("Missing export " + name);
            Success(alloc(1, IntPtr.Zero, out env), "driver ENV");
            try
            {
                Success(set(env, 200, new IntPtr(3), 0), "driver ODBC3");
                IntPtr dbc;
                Success(alloc(2, env, out dbc), "driver DBC");
                Success(free(2, dbc), "free driver DBC");
            }
            finally { Success(free(1, env), "free driver ENV"); }
            Console.WriteLine("DRIVER_ENV_DBC_ALLOCATE_RELEASE passed");
        }
        finally { FreeLibrary(library); }
        Console.WriteLine("NETWORK_ATTEMPTED false");
    }
    static int Main(string[] args)
    {
        if (args.Length < 1 || args.Length > 2) return 2;
        try { Probe(args[0], args.Length == 2 ? args[1] : ""); return 0; }
        catch (Exception error) { Console.Error.WriteLine(error.Message); return 1; }
    }
}
