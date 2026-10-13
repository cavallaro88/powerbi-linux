// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnlib.DotNet.Writer;

class PatchCacheCompatibility
{
    static MethodDef HelperMethod(ModuleDefMD helper)
    {
        if (helper.Assembly.Name != "PowerBICacheCompatibility") throw new InvalidOperationException("Unexpected cache helper");
        var method = helper.GetTypes().Single(t => t.FullName == "PowerBICacheCompatibility").Methods.Single(m => m.Name == "NormalizeDatabase");
        if (!method.IsPublic || !method.IsStatic || method.MethodSig.RetType.FullName != "System.Void" ||
            method.MethodSig.Params.Count != 1 || method.MethodSig.Params[0].FullName != "System.Object")
            throw new InvalidOperationException("Unsupported cache helper signature");
        return method;
    }
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 4 && args[0] == "--sign-helper")
            {
                using (var helper = ModuleDefMD.Load(args[1]))
                {
                    HelperMethod(helper);var key = new StrongNameKey(args[3]);
                    helper.Assembly.PublicKey = new PublicKey(key.PublicKey);helper.Assembly.HasPublicKey = true;
                    helper.Write(args[2], new ModuleWriterOptions(helper) { StrongNameKey = key });
                }
                return 0;
            }
            if (args.Length != 3) { Console.Error.WriteLine("Usage: PatchCacheCompatibility input.dll output.dll signed-helper.dll; or --sign-helper input.dll output.dll key.snk");return 2; }
            if (Path.GetFullPath(args[0]) == Path.GetFullPath(args[1])) throw new InvalidOperationException("Output must differ from input");
            using (var module = ModuleDefMD.Load(args[0]))
            using (var helper = ModuleDefMD.Load(args[2]))
            {
                var normalize = HelperMethod(helper);
                if (!helper.Assembly.HasPublicKey || helper.Assembly.PublicKey.Data.Length == 0) throw new InvalidOperationException("Cache helper must be signed");
                if (module.Assembly.Name != "Microsoft.PowerBI.Client.Windows" || module.GetAssemblyRefs().Any(r => r.Name == "PowerBICacheCompatibility"))
                    throw new InvalidOperationException("Unsupported or already patched Desktop assembly");
                var method = module.GetTypes().Single(t => t.FullName == "Microsoft.PowerBI.Client.Windows.AnalysisServices.TmslApplier")
                    .Methods.Single(m => m.Name == "CopyModelPreservingHigherCompatibilityLevel");
                if (!method.IsStatic || method.MethodSig.RetType.FullName != "System.Void" || method.MethodSig.Params.Count != 2 ||
                    method.MethodSig.Params[0].FullName != "Microsoft.PowerBI.Modeling.Contracts.AnalysisServices.ITomDatabase" ||
                    method.MethodSig.Params[1].FullName != "Microsoft.AnalysisServices.Tabular.Database" || method.Body == null)
                    throw new InvalidOperationException("Unsupported model-copy signature");
                var body = method.Body.Instructions;
                if (body.Count < 8 || body[0].OpCode != OpCodes.Ldarg_0 || body[body.Count-1].OpCode != OpCodes.Ret ||
                    body[body.Count-2].OpCode != OpCodes.Callvirt || !(body[body.Count-2].Operand is IMethod) ||
                    ((IMethod)body[body.Count-2].Operand).FullName != "System.Void Microsoft.AnalysisServices.Tabular.Model::CopyTo(Microsoft.AnalysisServices.Tabular.Model)")
                    throw new InvalidOperationException("Unexpected model-copy body");
                body.Insert(0, Instruction.Create(OpCodes.Ldarg_1));
                body.Insert(1, Instruction.Create(OpCodes.Call, module.Import(normalize)));
                module.Write(args[1]);
                Console.WriteLine("Normalized linguistic JSON before original model-copy/update; metadata application preserved");
            }
            return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e.GetType().Name + ": " + e.Message);return 1; }
    }
}
