// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnlib.DotNet.Writer;

class PatchSavePrompt
{
    static MethodDef DialogMethod(ModuleDefMD module)
    {
        if (module.Assembly.Name != "PowerBISaveDialog")
            throw new InvalidOperationException("Unexpected native dialog assembly");
        var show = module.GetTypes().Single(t => t.FullName == "PowerBISaveDialog")
            .Methods.Single(m => m.Name == "Show");
        if (!show.IsStatic || !show.IsPublic || show.MethodSig.RetType.FullName != "System.Int32" ||
            show.MethodSig.Params.Count != 6 ||
            show.MethodSig.Params[0].FullName != "System.Windows.Forms.IWin32Window" ||
            show.MethodSig.Params.Skip(1).Any(p => p.FullName != "System.String"))
            throw new InvalidOperationException("Unsupported native dialog signature");
        return show;
    }

    static int Main(string[] args)
    {
        if (args.Length != 4)
        {
            Console.Error.WriteLine("Usage: PatchSavePrompt input.dll output.dll mashup-ui.dll signed-dialog.dll\n" +
                                    "       PatchSavePrompt --sign-dialog input.dll output.dll key.snk");
            return 2;
        }
        try
        {
            if (args[0] == "--sign-dialog")
            {
                using (var module = ModuleDefMD.Load(args[1]))
                {
                    DialogMethod(module);
                    var key = new StrongNameKey(args[3]);
                    module.Assembly.PublicKey = new PublicKey(key.PublicKey);
                    module.Assembly.HasPublicKey = true;
                    module.Write(args[2], new ModuleWriterOptions(module) { StrongNameKey = key });
                }
                return 0;
            }
            if (Path.GetFullPath(args[0]) == Path.GetFullPath(args[1]))
                throw new InvalidOperationException("Output must differ from input");
            using (var ui = ModuleDefMD.Load(args[2]))
            using (var native = ModuleDefMD.Load(args[3]))
            using (var module = ModuleDefMD.Load(args[0]))
            {
                var show = DialogMethod(native);
                if (!native.Assembly.HasPublicKey || native.Assembly.PublicKey.Data.Length == 0)
                    throw new InvalidOperationException("Native dialog must be signed");
                if (module.Assembly.Name != "Microsoft.PowerBI.Client.Windows" ||
                    ui.Assembly.Name != "Microsoft.Mashup.Client.UI")
                    throw new InvalidOperationException("Unexpected Desktop or Mashup assembly");
                var result = ui.GetTypes().Single(t => t.FullName == "Microsoft.Mashup.Client.UI.Shared.ModalDialogResult");
                foreach (var pair in new[] { new { Name="Yes", Value=6 }, new { Name="No", Value=7 }, new { Name="Cancel", Value=2 } })
                {
                    var field = result.Fields.Single(f => f.Name == pair.Name);
                    if (field.Constant == null || Convert.ToInt32(field.Constant.Value) != pair.Value)
                        throw new InvalidOperationException("Unsupported modal result mapping");
                }
                var type = module.GetTypes().Single(t => t.FullName == "Microsoft.PowerBI.Client.Windows.ApplicationCloseHandler");
                var method = type.Methods.Single(m => m.Name == "ShowYesNoCancelSaveChangesPrompt");
                if (method.IsStatic || method.MethodSig.Params.Count != 0 || method.Body == null ||
                    method.MethodSig.RetType.FullName != result.FullName || method.Body.Instructions.Count != 10)
                    throw new InvalidOperationException("Unsupported close/save method");
                var original = method.Body.Instructions;
                var owner = original[1].Operand as IField;
                var getters = Enumerable.Range(3, 5).Select(i => original[i].Operand as IMethod).ToArray();
                var names = new[] { "get_PowerBIProductName", "get_SaveChangesPromptMessage",
                    "get_SaveChangesPromptSaveButtonLabel", "get_SaveChangesPromptDontSaveButtonLabel", "get_CancelButtonText" };
                var service = original[2].Operand as IMethod;
                var dialog = original[8].Operand as IMethod;
                if (original[0].OpCode != OpCodes.Ldarg_0 || original[1].OpCode != OpCodes.Ldfld ||
                    owner == null || owner.Name != "mainForm" ||
                    owner.FieldSig.Type.FullName != "Microsoft.PowerBI.Client.Windows.MainForm" ||
                    original[2].OpCode != OpCodes.Callvirt || service == null || service.Name != "get_WindowService" ||
                    getters.Where((g, i) => g == null || g.Name != names[i] ||
                        original[i+3].OpCode != OpCodes.Call || g.MethodSig.Params.Count != 0 ||
                        g.MethodSig.RetType.FullName != "Microsoft.Mashup.DocumentServices.Strings.LocalizedString").Any() ||
                    original[8].OpCode != OpCodes.Callvirt || dialog == null ||
                    dialog.Name != "ShowYesNoCancelDialog" || dialog.MethodSig.Params.Count != 5 ||
                    original[9].OpCode != OpCodes.Ret)
                    throw new InvalidOperationException("Unexpected close/save instructions");
                var localized = module.GetTypes().SelectMany(t => t.Methods)
                    .Where(m => m.Body != null).SelectMany(m => m.Body.Instructions)
                    .Select(i => i.Operand as IMethod).First(m => m != null && m.Name == "op_Implicit" &&
                        m.DeclaringType.FullName == "Microsoft.Mashup.DocumentServices.Strings.LocalizedString" &&
                        m.MethodSig.Params.Count == 1 && m.MethodSig.Params[0].FullName == m.DeclaringType.FullName &&
                        m.MethodSig.RetType.FullName == "System.String");
                var body = new CilBody();
                body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
                body.Instructions.Add(Instruction.Create(OpCodes.Ldfld, owner));
                foreach (var getter in getters)
                {
                    body.Instructions.Add(Instruction.Create(OpCodes.Call, getter));
                    body.Instructions.Add(Instruction.Create(OpCodes.Call, localized));
                }
                body.Instructions.Add(Instruction.Create(OpCodes.Call, module.Import(show)));
                body.Instructions.Add(Instruction.Create(OpCodes.Ret));
                method.Body = body;
                module.Write(args[1]);
            }
            Console.WriteLine("Native close/save question patched; localized labels; Yes=6 No=7 Cancel=2.");
            return 0;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine(exception.Message + ". No patch activation performed.");
            return 1;
        }
    }
}
