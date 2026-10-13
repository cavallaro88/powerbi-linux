// SPDX-License-Identifier: GPL-3.0-or-later
// Drives ONLY this process's synthetic forms, never a Desktop window.
using System;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Microsoft.PowerBI.Client.Windows;

class SaveDialogProbe
{
    [DllImport("user32.dll")]
    static extern bool IsWindowEnabled(IntPtr window);
    [STAThread]
    static int Main()
    {
        try
        {
            Application.EnableVisualStyles();
            using (var owner = new MainForm())
            {
                owner.Text = "Teste sintético — proprietário";
                owner.Show();
                var handler = new ApplicationCloseHandler(owner);
                foreach (var action in new[] { "Save", "Discard", "Cancel", "Enter", "Escape", "Close" })
                {
                    Exception error = null;
                    bool exercised = false;
                    using (var timer = new Timer())
                    {
                        timer.Interval = 250;
                        timer.Tick += delegate {
                            Form dialog = Application.OpenForms.Cast<Form>().SingleOrDefault(f => f.Name == "PowerBISaveDialog");
                            if (dialog == null) return;
                            timer.Stop();
                            try
                            {
                                if (IsWindowEnabled(owner.Handle) || !dialog.Visible || dialog.Width < 250 || dialog.Height < 80)
                                    throw new Exception("Invalid modal ownership or dialog dimensions");
                                foreach (var label in new[] { new[] {"Save", "Salvar"}, new[] {"Discard", "Não salvar"}, new[] {"Cancel", "Cancelar"} })
                                {
                                    var button = dialog.Controls.Find(label[0], true).Single() as Button;
                                    if (button == null || button.Text != label[1] || !button.Visible)
                                        throw new Exception("Localized button missing: " + label[0]);
                                }
                                var cancel = (Button)dialog.Controls.Find("Cancel", true).Single();
                                if (dialog.AcceptButton != cancel || dialog.CancelButton != cancel)
                                    throw new Exception("Unsafe default action");
                                exercised = true;
                                if (action == "Close") dialog.Close();
                                else if (action == "Enter") dialog.AcceptButton.PerformClick();
                                else if (action == "Escape") dialog.CancelButton.PerformClick();
                                else ((Button)dialog.Controls.Find(action, true).Single()).PerformClick();
                            }
                            catch (Exception exception) { error = exception; dialog.Close(); }
                        };
                        timer.Start();
                        int result = (int)handler.ShowYesNoCancelSaveChangesPrompt();
                        int expected = action == "Save" ? 6 : action == "Discard" ? 7 : 2;
                        if (error != null) throw error;
                        if (!exercised || result != expected || !IsWindowEnabled(owner.Handle))
                            throw new Exception("Incorrect response or owner remained disabled: " + action + "=" + result);
                        Console.WriteLine("PASS " + action + "=" + result);
                    }
                }
                owner.Close();
            }
            Console.WriteLine("PASS synthetic patched method; no Desktop report accessed");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
