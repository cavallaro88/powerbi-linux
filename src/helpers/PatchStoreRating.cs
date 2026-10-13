// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

// The Windows Store rating prompt runs after a successful publish. Its async
// state machine loads unavailable WinRT contracts even when its UWP gate is
// false. Fedora has no Windows Store: return a completed Task at the entrypoint.
class PatchStoreRating
{
    const string TypeName = "Microsoft.PowerBI.Client.Windows.PowerBIService.StoreRating";
    static int Main(string[] args)
    {
        if (args.Length != 2) { Console.Error.WriteLine("Usage: PatchStoreRating input.dll output.dll"); return 2; }
        try
        {
            using (var module = ModuleDefMD.Load(args[0]))
            {
                var type = module.GetTypes().Single(t => t.FullName == TypeName);
                var method = type.Methods.Single(m => m.Name == "PromptForRatingAsync");
                if (method.IsStatic || method.MethodSig.RetType.FullName != "System.Threading.Tasks.Task" ||
                    method.MethodSig.Params.Count != 1 || method.MethodSig.Params[0].FullName !=
                    "Microsoft.PowerBI.Client.Windows.Services.IPowerBIWindowService" ||
                    method.Body == null || method.Body.Instructions.Count != 20 ||
                    method.Body.Instructions.Count(i => i.OpCode == OpCodes.Call && i.Operand.ToString().Contains("::Start<")) != 1)
                    throw new InvalidDataException("Unsupported Store rating entrypoint");
                var machine = type.NestedTypes.Single(t => t.Name == "<PromptForRatingAsync>d__8");
                var move = machine.Methods.Single(m => m.Name == "MoveNext");
                if (move.Body == null || !move.Body.Instructions.Any(i => i.Operand != null &&
                    i.Operand.ToString().Contains("System.WindowsRuntimeSystemExtensions::GetAwaiter")))
                    throw new InvalidDataException("Unsupported Store rating state machine");
                var body = new CilBody();
                var importer = new Importer(module);
                body.Instructions.Add(Instruction.Create(OpCodes.Call, importer.Import(
                    typeof(System.Threading.Tasks.Task).GetProperty("CompletedTask").GetGetMethod())));
                body.Instructions.Add(Instruction.Create(OpCodes.Ret));
                method.Body = body;
                module.Write(args[1]);
                Console.WriteLine("Disabled Windows Store rating entrypoint; publish flow unchanged");
                return 0;
            }
        }
        catch (Exception e) { Console.Error.WriteLine(e.GetType().Name + ": " + e.Message); return 1; }
    }
}
