// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
// Production manager contains no UI command interpreter or remote debugger.
public class CompositionManager : DiagnosticManager
{
    [DllImport("dcomp.dll", CallingConvention=CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool pbi_dcomp_start_consumer();
    public override void InitializeNewDomain(AppDomainSetup setup)
    {
        base.InitializeNewDomain(setup);
        if (Environment.GetEnvironmentVariable("PBI_COMPOSITION") == "1" &&
            String.Equals(Process.GetCurrentProcess().ProcessName, "PBIDesktop", StringComparison.OrdinalIgnoreCase) &&
            !pbi_dcomp_start_consumer())
            throw new InvalidOperationException("Power BI composition receiver could not start.");
    }
}
