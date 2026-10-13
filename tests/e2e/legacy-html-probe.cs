// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Forms;

[ComVisible(true), ClassInterface(ClassInterfaceType.AutoDispatch)]
public class LegacyHtmlBridge
{
    public bool Called;
    public void Ready(string marker) { Called = marker == "pbi-linux-offline-probe"; }
}

class LegacyHtmlProbe
{
    [STAThread]
    static int Main()
    {
        bool passed = false;
        var clock = Stopwatch.StartNew();
        using (var form = new Form { Text = "Power BI Linux — offline HTML test", Width = 480, Height = 200 })
        using (var browser = new WebBrowser { Dock = DockStyle.Fill, ScriptErrorsSuppressed = true })
        using (var timer = new Timer { Interval = 200 })
        {
            var bridge = new LegacyHtmlBridge();
            browser.ObjectForScripting = bridge;
            form.Controls.Add(browser);
            form.Shown += delegate {
                timer.Start();
                browser.DocumentText = "<html><body>pbi-linux-offline-probe<script>" +
                    "try{window.external.Ready('pbi-linux-offline-probe');}catch(e){}" +
                    "</script></body></html>";
            };
            timer.Tick += delegate {
                try
                {
                    var document = browser.Document;
                    if (document != null && document.Body != null &&
                        document.Body.InnerText.Contains("pbi-linux-offline-probe"))
                    {
                        var value = document.InvokeScript("eval", new object[] { "6 * 7" });
                        if (Convert.ToInt32(value) == 42 && bridge.Called)
                        {
                            passed = true;
                            Console.WriteLine("PASS HTML body, JavaScript and native callback");
                            form.Close();
                            return;
                        }
                    }
                    if (clock.Elapsed.TotalSeconds >= 15)
                    {
                        Console.WriteLine("FAIL ready=" + browser.ReadyState +
                            " document=" + (document != null) + " native_callback=" + bridge.Called);
                        form.Close();
                    }
                }
                catch (Exception error)
                {
                    Console.WriteLine("FAIL " + error.GetType().Name + ": " + error.Message);
                    form.Close();
                }
            };
            Application.Run(form);
        }
        return passed ? 0 : 1;
    }
}
