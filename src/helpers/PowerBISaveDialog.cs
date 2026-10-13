// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Drawing;
using System.Windows.Forms;

// This helper asks a question only. Desktop performs any saving or closing.
public static class PowerBISaveDialog
{
    public static int Show(IWin32Window owner, string title, string message,
                           string saveLabel, string discardLabel, string cancelLabel)
    {
        try
        {
            using (var dialog = new Form())
            using (var layout = new TableLayoutPanel())
            using (var buttons = new FlowLayoutPanel())
            using (var question = new Label())
            using (var save = new Button())
            using (var discard = new Button())
            using (var cancel = new Button())
            {
                dialog.Text = title;
                dialog.Name = "PowerBISaveDialog";
                dialog.FormBorderStyle = FormBorderStyle.FixedDialog;
                dialog.StartPosition = FormStartPosition.CenterParent;
                dialog.AutoScaleMode = AutoScaleMode.Font;
                dialog.AutoSize = true;
                dialog.AutoSizeMode = AutoSizeMode.GrowAndShrink;
                dialog.MinimizeBox = false;
                dialog.MaximizeBox = false;
                dialog.ShowInTaskbar = false;
                dialog.Padding = new Padding(16);
                layout.AutoSize = true;
                layout.AutoSizeMode = AutoSizeMode.GrowAndShrink;
                layout.Dock = DockStyle.Fill;
                layout.ColumnCount = 1;
                layout.RowCount = 2;
                question.Text = message;
                question.AutoSize = true;
                question.MaximumSize = new Size(560, 0);
                question.Margin = new Padding(0, 0, 0, 16);
                buttons.AutoSize = true;
                buttons.WrapContents = false;
                buttons.Anchor = AnchorStyles.Right;
                buttons.Margin = Padding.Empty;
                Configure(save, "Save", saveLabel, DialogResult.Yes);
                Configure(discard, "Discard", discardLabel, DialogResult.No);
                Configure(cancel, "Cancel", cancelLabel, DialogResult.Cancel);
                buttons.Controls.AddRange(new Control[] { save, discard, cancel });
                layout.Controls.Add(question, 0, 0);
                layout.Controls.Add(buttons, 0, 1);
                dialog.Controls.Add(layout);
                // Enter, Escape and the title-bar close button preserve changes.
                dialog.AcceptButton = cancel;
                dialog.CancelButton = cancel;
                dialog.Shown += delegate { cancel.Select(); };
                DialogResult result = dialog.ShowDialog(owner);
                return result == DialogResult.Yes ? 6 : result == DialogResult.No ? 7 : 2;
            }
        }
        catch (Exception)
        {
            Console.Error.WriteLine("Power BI Linux: native save question failed; returning Cancel.");
            return 2;
        }
    }

    static void Configure(Button button, string name, string label, DialogResult result)
    {
        if (String.IsNullOrEmpty(label)) throw new ArgumentException("Missing button label");
        button.Name = name;
        button.Text = label;
        button.DialogResult = result;
        button.AutoSize = true;
        button.MinimumSize = new Size(90, 30);
        button.Padding = new Padding(8, 2, 8, 2);
        button.Margin = new Padding(4, 0, 0, 0);
    }
}
