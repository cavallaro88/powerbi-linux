// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
class CacheCompatibilityProbe
{
    public class Metadata { public string Content { get; set; } }
    public class Culture { public Metadata LinguisticMetadata { get; set; } }
    public class Model { public List<Culture> Cultures { get; set; } }
    public class Database { public Model Model { get; set; } }
    static int Main(string[] args)
    {
        AppDomain.CurrentDomain.AssemblyResolve += (s,e) => {
            string path=Path.Combine(args[0],new AssemblyName(e.Name).Name+".dll");
            return File.Exists(path)?Assembly.LoadFrom(path):null;
        };
        return Run();
    }
    static int Run()
    {
        string source="{\r\n \"Label\":\"space inside \\\"quotes\\\" and \\\\ escape\", \"Big\":9007199254740993, \"Precise\":1.2300000000000001, \"Values\":[true,false,null] }";
        string compact=PowerBICacheCompatibility.CompactJson(source);
        var checks=new Dictionary<string,bool>();
        checks["whitespace_removed"]=compact.Length<source.Length;
        checks["strings_preserved"]=compact.Contains("space inside \\\"quotes\\\" and \\\\ escape");
        checks["integer_token_preserved"]=compact.Contains("9007199254740993");
        checks["decimal_token_preserved"]=compact.Contains("1.2300000000000001");
        checks["idempotent"]=PowerBICacheCompatibility.CompactJson(compact)==compact;
        checks["null_preserved"]=PowerBICacheCompatibility.CompactJson(null)==null;
        string bad="{ \"invalid\": ";checks["invalid_input_preserved"]=PowerBICacheCompatibility.CompactJson(bad)==bad;
        string comment="{\"x\":1,// comment\n\"y\":2}";checks["line_comment_semantics_preserved"]=PowerBICacheCompatibility.CompactJson(comment)==comment;
        var m=new Metadata {Content=source};var db=new Database {Model=new Model {Cultures=new List<Culture>{new Culture {LinguisticMetadata=m},new Culture {LinguisticMetadata=null}}}};
        PowerBICacheCompatibility.NormalizeDatabase(db);checks["only_in_memory_content_normalized"]=m.Content==compact;
        PowerBICacheCompatibility.NormalizeDatabase(null);checks["null_database_preserves_original_guard"]=true;
        foreach(var item in checks)Console.WriteLine((item.Value?"PASS ":"FAIL ")+item.Key);
        foreach(var item in checks)if(!item.Value)return 1;
        Console.WriteLine("RESULT passed="+checks.Count);return 0;
    }
}
