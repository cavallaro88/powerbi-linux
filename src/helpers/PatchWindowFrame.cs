// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnlib.DotNet.Writer;

class PatchWindowFrame
{
    const string TypeName = "Microsoft.PowerBI.Client.Windows.ResizableFormWithCustomCaption";
    static MethodDef Helper(ModuleDefMD helper, string name)
    {
        if (helper.Assembly.Name != "PowerBIWindowFrame") throw new InvalidDataException("Unexpected frame helper");
        var m = helper.GetTypes().Single(t => t.FullName == "PowerBIWindowFrame").Methods.Single(x => x.Name == name);
        if (!m.IsPublic || !m.IsStatic || m.MethodSig.Params.Count != 1 ||
            m.MethodSig.Params[0].FullName != "System.Windows.Forms.Form" ||
            m.MethodSig.RetType.FullName != (name == "Attach" ? "System.Void" : "System.Boolean"))
            throw new InvalidDataException("Unexpected frame helper signature");
        return m;
    }
    static string Fingerprint(MethodDef method)
    {
        var code = method.Body.Instructions;
        var text = String.Join("\n", code.Select(i => i.OpCode.Code + "|" +
            (i.Operand is Instruction ? "@" + code.IndexOf((Instruction)i.Operand) :
             i.Operand is Local ? "V" + ((Local)i.Operand).Index + ":" + ((Local)i.Operand).Type.FullName :
             i.Operand is IFullName ? ((IFullName)i.Operand).FullName :
             Convert.ToString(i.Operand, System.Globalization.CultureInfo.InvariantCulture))));
        using (var hash = System.Security.Cryptography.SHA256.Create())
            return String.Concat(hash.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text)).Select(x => x.ToString("x2")));
    }
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 2 && args[0] == "--fingerprint")
            {
                using(var m = ModuleDefMD.Load(args[1]))
                    foreach(var method in m.GetTypes().Single(t => t.FullName == TypeName).Methods.Where(x => x.Name == "WndProc" || x.Name == "OnLoad"))
                        Console.WriteLine(method.Name + " " + Fingerprint(method));
                return 0;
            }
            if (args.Length == 4 && args[0] == "--sign-helper")
            {
                using (var helper = ModuleDefMD.Load(args[1]))
                {
                    Helper(helper, "ShouldExtend"); Helper(helper, "Attach");
                    var key = new StrongNameKey(args[3]);
                    helper.Assembly.PublicKey = new PublicKey(key.PublicKey);
                    helper.Assembly.HasPublicKey = true;
                    helper.Write(args[2], new ModuleWriterOptions(helper) { StrongNameKey = key });
                }
                return 0;
            }
            if (args.Length != 3 || Path.GetFullPath(args[0]) == Path.GetFullPath(args[1]))
                throw new ArgumentException("Usage: PatchWindowFrame input.dll output.dll signed-helper.dll");
            using (var module = ModuleDefMD.Load(args[0]))
            using (var helper = ModuleDefMD.Load(args[2]))
            {
                if (module.Assembly.Name != "Microsoft.PowerBI.Client.Windows" ||
                    module.GetAssemblyRefs().Any(x => x.Name == "PowerBIWindowFrame") || !helper.Assembly.HasPublicKey)
                    throw new InvalidDataException("Unsupported/already patched assembly or unsigned helper");
                var type = module.GetTypes().Single(t => t.FullName == TypeName);
                var method = type.Methods.Single(m => m.Name == "WndProc");
                var load = type.Methods.Single(m => m.Name == "OnLoad");
                if (Fingerprint(method) != "3a8cfcf238b5a80777b353795cd0f734e3a6226f76678b9cc288203c076cd66d" ||
                    Fingerprint(load) != "ac90e85db8ba75c2a470cad0daa3da4fa6077c0ecf1f410ec9b67f650c1cd09d")
                    throw new InvalidDataException("Unsupported custom-caption method contents");
                var field = type.Fields.Single(f => f.Name == "clientRect");
                var body = method.Body.Instructions;
                if (method.MethodSig.Params.Count != 1 || method.MethodSig.Params[0].FullName != "System.Windows.Forms.Message&" ||
                    method.IsStatic || body.Count != 119 || method.Body.Variables.Count != 5 ||
                    load.Body.Instructions.Count != 10 || method.Body.ExceptionHandlers.Count != 0)
                    throw new InvalidDataException("Unsupported custom-caption method layout: " + body.Count + "/" + load.Body.Instructions.Count);
                var target = body.Single(i => i.Offset == 0xe6);
                var branch = body.Single(i => i.Offset == 0xa4);
                if (target.OpCode != OpCodes.Ldarg_0 || branch.OpCode != OpCodes.Brfalse_S || branch.Operand != target ||
                    body.Single(i => i.Offset == 0xe7).OpCode != OpCodes.Ldfld ||
                    ((IField)body.Single(i => i.Offset == 0xe7).Operand).Name != "clientRect" ||
                    load.Body.Instructions.Last().OpCode != OpCodes.Ret)
                    throw new InvalidDataException("Unsupported custom-caption control flow");
                var first = Instruction.Create(OpCodes.Ldarg_0);
                var injected = new[] { first, Instruction.Create(OpCodes.Call, module.Import(Helper(helper,"ShouldExtend"))),
                    Instruction.Create(OpCodes.Brfalse, target), Instruction.Create(OpCodes.Ldarg_0),
                    Instruction.Create(OpCodes.Ldloc_1), Instruction.Create(OpCodes.Stfld, field) };
                branch.Operand = first;
                int position = body.IndexOf(target);
                foreach (var i in injected) body.Insert(position++, i);
                int end = load.Body.Instructions.Count - 1;
                load.Body.Instructions.Insert(end++, Instruction.Create(OpCodes.Ldarg_0));
                load.Body.Instructions.Insert(end, Instruction.Create(OpCodes.Call, module.Import(Helper(helper,"Attach"))));
                method.Body.SimplifyBranches(); method.Body.OptimizeBranches();
                module.Write(args[1]);
                Console.WriteLine("Extended eligible normal custom-caption client with transparent resize zones; maximized and owned frames preserved");
            }
            return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e.GetType().Name + ": " + e.Message); return 1; }
    }
}
