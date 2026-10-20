// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Text;using System.Windows.Forms;
class Int64HtmlProbe {
 [STAThread]static int Main(string[] args){
  var log=new StringBuilder();var form=new Form{Text="Teste Int64 HTML — encerramento automático",Width=480,Height=160};var browser=new WebBrowser{Dock=DockStyle.Fill,ScriptErrorsSuppressed=true};form.Controls.Add(browser);var timeout=new Timer{Interval=12000};bool done=false;int rc=1;
  Action run=delegate{if(done||browser.Document==null||browser.Document.GetElementById("ready")==null)return;done=true;try{log.AppendLine("documentMode="+browser.Document.InvokeScript("eval",new object[]{"document.documentMode"}));
    object[] values={(int)4096,(double)4096,(long)4096,(long)-1,(long)1099511627776,(double)9007199254740991,(long)9007199254740991};int passed=0;
    foreach(object value in values){browser.Document.InvokeScript("store",new object[]{value,(value is double?((double)value).ToString("R",System.Globalization.CultureInfo.InvariantCulture):Convert.ToString(value,System.Globalization.CultureInfo.InvariantCulture))});object actual=browser.Document.InvokeScript("inspectValue",new object[0]);log.AppendLine(value.GetType().Name+" "+value+" => "+(actual==null?"NULL":actual.ToString()));if(actual!=null&&actual.ToString().Contains("\"sameValue\":true")&&actual.ToString().Contains("\"type\":\"number\""))passed++;}
    rc=passed==values.Length?0:2;
  }catch(Exception e){log.AppendLine("ERROR "+e.GetType().FullName+" "+e.HResult.ToString("x8"));}finally{File.WriteAllText(args[0],log.ToString());form.Close();}};
  browser.DocumentCompleted+=delegate{form.BeginInvoke(run);};var poll=new Timer{Interval=150};poll.Tick+=delegate{run();};poll.Start();form.Shown+=delegate{browser.DocumentText="<html><head><meta http-equiv='X-UA-Compatible' content='IE=11'/><script>function store(x,expected){window.probeValue=x;window.expectedValue=expected;return 'stored';}function inspectValue(){try{return JSON.stringify({type:typeof window.probeValue,sameValue:window.probeValue===Number(window.expectedValue),value:window.probeValue,text:String(window.probeValue),plusOne:window.probeValue+1});}catch(e){return 'ERROR '+String(e);}}</script></head><body><p id='ready'>Teste próprio de números; nenhuma configuração ou relatório.</p></body></html>";timeout.Start();};timeout.Tick+=delegate{File.WriteAllText(args[0],"TIMEOUT");form.Close();};Application.Run(form);timeout.Dispose();browser.Dispose();form.Dispose();return rc;
 }
}
