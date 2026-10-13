// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

class PatchShared
{
    static int Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.Error.WriteLine("Usage: PatchShared input.dll output.dll");
            return 2;
        }
        string inPath = args[0];
        string outPath = args[1];

        var mod = ModuleDefMD.Load(inPath);

        TypeDef type = null;
        foreach (var t in mod.GetTypes())
        {
            if (t.Namespace == "Microsoft.PowerBI.Client.Shared" && t.Name == "PowerBIConstants")
            {
                type = t;
                break;
            }
        }
        if (type == null)
        {
            Console.Error.WriteLine("PowerBIConstants type not found. No output written.");
            return 1;
        }
        var method = type.FindMethod("GetInstalledPath");
        if (method == null)
        {
            Console.Error.WriteLine("GetInstalledPath method not found. No output written.");
            return 1;
        }

        var importer = new Importer(mod);
        var asmGetExecuting = importer.Import(typeof(System.Reflection.Assembly).GetMethod("GetExecutingAssembly"));
        var getLocation = importer.Import(typeof(System.Reflection.Assembly).GetProperty("Location").GetGetMethod());
        var getDirName = importer.Import(typeof(System.IO.Path).GetMethod("GetDirectoryName", new Type[] { typeof(string) }));

        var body = new CilBody();
        body.Instructions.Add(OpCodes.Call.ToInstruction(asmGetExecuting));
        body.Instructions.Add(OpCodes.Callvirt.ToInstruction(getLocation));
        body.Instructions.Add(OpCodes.Call.ToInstruction(getDirName));
        body.Instructions.Add(OpCodes.Ret.ToInstruction());
        method.Body = body;

        mod.Write(outPath);
        Console.WriteLine("patched GetInstalledPath");
        return 0;
    }
}
