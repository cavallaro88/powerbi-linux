// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using dnlib.DotNet;

class PatchWinRT
{
    static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine("Usage: PatchWinRT input.dll output.dll stubs.snk");
            return 2;
        }
        string inPath = args[0];
        string outPath = args[1];
        string keyPath = args[2];

        var key = new StrongNameKey(keyPath);
        byte[] pubKey = key.PublicKey;

        var mod = ModuleDefMD.Load(inPath);
        int changed = 0;
        foreach (var ar in mod.GetAssemblyRefs())
        {
            string n = ar.Name;
            if (n == "Windows.Foundation.UniversalApiContract" || n == "Windows.Foundation.FoundationContract")
            {
                ar.Name = "WinRTStubs";
                ar.Version = new Version(1, 0, 0, 0);
                ar.HasPublicKey = true;
                ar.ContentType = AssemblyAttributes.ContentType_Default;
                ar.PublicKeyOrToken = new PublicKey(pubKey);
                changed++;
            }
        }
        if (changed != 2)
        {
            Console.Error.WriteLine("Expected two original WinRT references; found " + changed + ". No output written.");
            return 1;
        }
        mod.Write(outPath);
        Console.WriteLine("done changed=" + changed + " pubkeylen=" + pubKey.Length);
        return 0;
    }
}
