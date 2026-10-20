using System;
using System.Collections;
using System.IO;
using System.Reflection;

// Refresh full de uma tabela no modelo aberto (via TMSL/AMO) ou listagem de
// bancos/tabelas do workspace (modo --list). O TMSL vira job assíncrono no
// Power BI Desktop: confirme o commit pelas DMVs de partições/comandos.
// Uso: refresh-probe.exe <porta AS> --list
//      refresh-probe.exe <porta AS> <tabela> [id-do-banco]
//      refresh-probe.exe <porta AS> --batch <id-do-banco> "t1,t2,..."
//      refresh-probe.exe <porta AS> --all <id-do-banco>
// PBI_AS_TIMEOUT ajusta o timeout do XMLA (padrão 1800 s).
class RefreshProbe
{
    static int Main(string[] args)
    {
        Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new System.Text.UTF8Encoding(false)) { AutoFlush = true });
        string bin = @"C:\Program Files\Microsoft Power BI Desktop\bin";
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string candidate = Path.Combine(bin, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        };
        return Run(args);
    }

    static object Property(object instance, string name)
    {
        if (instance == null) return null;
        var property = instance.GetType().GetProperty(name);
        return property != null ? property.GetValue(instance, null) : null;
    }

    static ArrayList Tables(object database)
    {
        var tables = new ArrayList();
        try {
            object model = Property(database, "Model");
            if (model == null) return tables;
            var collection = Property(model, "Tables") as IEnumerable;
            if (collection == null) return tables;
            foreach (var table in collection) tables.Add(table);
        } catch (Exception) { tables.Clear(); }
        return tables;
    }

    static int Run(string[] args)
    {
        try
        {
            var asm = Assembly.LoadFrom(Path.Combine(@"C:\Program Files\Microsoft Power BI Desktop\bin", "Microsoft.PowerBI.Amo.dll"));
            var serverType = asm.GetType("Microsoft.AnalysisServices.Server", true);
            var server = Activator.CreateInstance(serverType);
            string asTimeout = Environment.GetEnvironmentVariable("PBI_AS_TIMEOUT") ?? "1800";
            serverType.GetMethod("Connect", new Type[] { typeof(string) }).Invoke(server,
                new object[] { "Data Source=localhost:" + args[0] + ";Timeout=" + asTimeout + ";Connect Timeout=10" });
            var databases = (IEnumerable)serverType.GetProperty("Databases").GetValue(server, null);
            object database = null;
            foreach (var candidate in databases)
            {
                var tables = Tables(candidate);
                Console.WriteLine("DB " + Property(candidate, "ID") + " | " + Property(candidate, "Name") +
                                  " | tables=" + tables.Count);
                if (args.Length >= 3) {
                    if (string.Equals((string)Property(candidate, "ID"), args[2], StringComparison.OrdinalIgnoreCase))
                        database = candidate;
                } else if (tables.Count > 0) {
                    database = candidate;
                }
                if (args[1] == "--list") database = candidate;
            }
            if (database == null) { Console.WriteLine("NO DB"); return 1; }
            if (args[1] == "--list") return 0;
            string id = (string)Property(database, "ID");
            if (args[1] == "--all")
            {
                string all = "{\"refresh\":{\"type\":\"full\",\"objects\":[{\"database\":\"" + id + "\"}]}}";
                if (!ExecuteRefresh(serverType, server, all, "todos os objetos @ " + id)) {
                    Console.WriteLine("REFRESH ERR: erros na resposta XMLA");
                    return 1;
                }
                Console.WriteLine("REFRESH OK");
                return 0;
            }
            string[] wanted = args[1] == "--batch" ? args[3].Split(',') : new string[] { args[1] };
            var names = new ArrayList();
            foreach (var table in Tables(database)) names.Add((string)Property(table, "Name"));
            var missing = new ArrayList();
            foreach (var want in wanted) if (!names.Contains(want)) missing.Add(want);
            if (missing.Count > 0) {
                Console.WriteLine("TABLE NOT FOUND: " + string.Join(", ", (string[])missing.ToArray(typeof(string))) +
                                  " (buscada em " + id + ")");
                Console.WriteLine("TABLES: " + string.Join(", ", (string[])names.ToArray(typeof(string))));
                return 1;
            }
            var objects = new ArrayList();
            if (args[1] == "--batch")
            {
                // Sequencial de propósito: o lote num único comando avalia as
                // tabelas em paralelo e cada container reabre o fluxo de
                // credenciais, travando sem prompt preenchido. Erros não
                // interrompem o sweep; o resumo sai no fim.
                int failures = 0;
                foreach (var want in wanted)
                {
                    string one = "{\"refresh\":{\"type\":\"full\",\"objects\":[{\"database\":\"" + id +
                                 "\",\"table\":\"" + want.Replace("\"", "\\\"") + "\"}]}}";
                    var watch = System.Diagnostics.Stopwatch.StartNew();
                    if (!ExecuteRefresh(serverType, server, one, want))
                    {
                        failures++;
                        Console.WriteLine("ERR " + want + " " + watch.ElapsedMilliseconds + "ms");
                        continue;
                    }
                    Console.WriteLine("OK " + want + " " + watch.ElapsedMilliseconds + "ms");
                }
                if (failures > 0) {
                    Console.WriteLine("REFRESH ERR: " + failures + " tabela(s) com erro");
                    return 1;
                }
                Console.WriteLine("REFRESH OK");
                return 0;
            }
            objects.Add("{\"database\":\"" + id + "\",\"table\":\"" + args[1].Replace("\"", "\\\"") + "\"}");
            string tmsl = "{\"refresh\":{\"type\":\"full\",\"objects\":[" +
                          string.Join(",", (string[])objects.ToArray(typeof(string))) + "]}}";
            if (!ExecuteRefresh(serverType, server, tmsl, args[1])) {
                Console.WriteLine("REFRESH ERR: erros na resposta XMLA");
                return 1;
            }
            Console.WriteLine("REFRESH OK");
            return 0;
        }
        catch (TargetInvocationException e) { Console.WriteLine("REFRESH ERR: " + e.InnerException); return 1; }
        catch (Exception e) { Console.WriteLine("REFRESH ERR: " + e.ToString()); return 1; }
    }

    static bool ExecuteRefresh(Type serverType, object server, string tmsl, string label)
    {
        Console.WriteLine("REFRESH " + label);
        // Execute retorna XmlaResultCollection mesmo quando a resposta contém erros.
        var results = (IEnumerable)serverType.GetMethod("Execute", new Type[] { typeof(string) })
            .Invoke(server, new object[] { tmsl });
        bool hasErrors = false;
        foreach (var result in results)
        {
            var messages = Property(result, "Messages") as IEnumerable;
            if (messages == null) continue;
            foreach (var message in messages)
            {
                string kind = message.GetType().Name;
                if (kind == "XmlaError") hasErrors = true;
                Console.WriteLine("XMLA " + kind + " code=" +
                                  (Property(message, "ErrorCode") ?? Property(message, "WarningCode") ?? Property(message, "Code")) +
                                  " source=" + Property(message, "Source") +
                                  " description=" + Property(message, "Description"));
            }
        }
        return !hasErrors;
    }
}
