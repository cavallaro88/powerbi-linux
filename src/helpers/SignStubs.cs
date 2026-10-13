// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using dnlib.DotNet;
using dnlib.DotNet.Writer;

class SignStubs
{
    static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine("Usage: SignStubs input.dll output.dll stubs.snk");
            return 2;
        }
        try
        {
            var key = new StrongNameKey(args[2]);
            using (var module = ModuleDefMD.Load(args[0]))
            {
                if (module.Assembly.Name != "WinRTStubs")
                {
                    Console.Error.WriteLine("Expected WinRTStubs. No output written.");
                    return 1;
                }
                module.Assembly.PublicKey = new PublicKey(key.PublicKey);
                module.Assembly.HasPublicKey = true;
                var options = new ModuleWriterOptions(module);
                options.StrongNameKey = key;
                module.Write(args[1], options);
            }
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("Stub signing failed: " + error.Message);
            return 1;
        }
    }
}
