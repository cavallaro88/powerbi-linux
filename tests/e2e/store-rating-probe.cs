// SPDX-License-Identifier: GPL-3.0-or-later
// Offline entrypoint check: no constructed services, window, report or network.
using System;using System.IO;using System.Reflection;using System.Runtime.Serialization;using System.Threading.Tasks;
class RatingProbe {
 static int Main(string[] args) {
  string dir=args[0]; AppDomain.CurrentDomain.AssemblyResolve+=(s,e)=>{string path=Path.Combine(dir,new AssemblyName(e.Name).Name+".dll");if(!File.Exists(path) && args.Length>1)path=Path.Combine(args[1],new AssemblyName(e.Name).Name+".dll");return File.Exists(path)?Assembly.LoadFrom(path):null;};
  try {var a=Assembly.LoadFrom(Path.Combine(dir,"Microsoft.PowerBI.Client.Windows.dll"));var t=a.GetType("Microsoft.PowerBI.Client.Windows.PowerBIService.StoreRating",true);var obj=FormatterServices.GetUninitializedObject(t);var m=t.GetMethod("PromptForRatingAsync");var result=(Task)m.Invoke(obj,new object[]{null});result.GetAwaiter().GetResult();Console.WriteLine("COMPLETED: rating entrypoint with all dependencies null; no report or network provided");return 0;}
  catch(Exception e){while(e is TargetInvocationException && e.InnerException!=null)e=e.InnerException;Console.WriteLine(e);return 1;}
 }
}
