// SPDX-License-Identifier: GPL-3.0-or-later
// Reflect the host preference into this Wine prefix; Desktop owns its theme choice.
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32;

public static class PowerBIThemeSync
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr SendMessageTimeoutW(IntPtr window, uint message, UIntPtr wParam,
        string lParam, uint flags, uint timeout, out UIntPtr result);

    public static int Main(string[] args)
    {
        if (args.Length != 1 || (args[0] != "light" && args[0] != "dark"))
            return 2;
        try
        {
            using (var key = Registry.CurrentUser.CreateSubKey(
                @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"))
            {
                key.SetValue("AppsUseLightTheme", args[0] == "light" ? 1 : 0,
                    RegistryValueKind.DWord);
            }
            // Desktop's original WndProc handles this exact string. Its theme
            // service ignores the notification for explicit Light/Dark choices.
            UIntPtr result;
            SendMessageTimeoutW(new IntPtr(0xffff), 0x001a, UIntPtr.Zero,
                "ImmersiveColorSet", 0x0002, 200, out result);
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("Theme synchronization failed: " + error.Message);
            return 1;
        }
    }
}
