using System;
using System.IO;
using System.Reflection;

// Testa o Connector/NET instalado em ADO.NET Providers/MySql direto contra um
// servidor, fora do Power BI. Senha vem da variável PBI_MYSQL_PASSWORD.
// Uso: mysql-probe.exe <host> <porta> <usuario> <banco> "SELECT ..." [seq,schema]
class MySqlProbe
{
    static string dir = @"C:\Program Files\Microsoft Power BI Desktop\bin\ADO.NET Providers\MySql";
    static int Main(string[] args)
    {
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string candidate = Path.Combine(dir, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        };
        return Run(args);
    }

    static int Run(string[] args)
    {
        try
        {
            string password = Environment.GetEnvironmentVariable("PBI_MYSQL_PASSWORD") ?? "";
            string cs = "server=" + args[0] + ";port=" + args[1] + ";user=" + args[2] +
                        ";password=" + password + ";database=" + args[3] +
                        ";SslMode=None;ConnectionTimeout=15;DefaultCommandTimeout=120;";
            using (var conn = new MySql.Data.MySqlClient.MySqlConnection(cs))
            {
                Console.WriteLine("OPEN...");
                conn.Open();
                Console.WriteLine("OPEN OK " + conn.ServerVersion);
                using (var cmd = conn.CreateCommand())
                {
                    cmd.CommandText = args[4];
                    string head = cmd.CommandText.Substring(0, Math.Min(60, cmd.CommandText.Length));
                    Console.WriteLine("EXEC " + head.Replace("\n", " "));
                    var watch = System.Diagnostics.Stopwatch.StartNew();
                    string[] modes = args.Length > 5 ? args[5].Split(',') : new string[0];
                    var behavior = Array.IndexOf(modes, "seq") >= 0
                        ? System.Data.CommandBehavior.SequentialAccess : System.Data.CommandBehavior.Default;
                    Console.WriteLine("BEHAVIOR " + behavior);
                    using (var reader = cmd.ExecuteReader(behavior))
                    {
                        Console.WriteLine("READER OK fields=" + reader.FieldCount + " @" + watch.ElapsedMilliseconds + "ms");
                        if (Array.IndexOf(modes, "schema") >= 0)
                        {
                            var table = reader.GetSchemaTable();
                            Console.WriteLine("SCHEMA OK rows=" + table.Rows.Count + " @" + watch.ElapsedMilliseconds + "ms");
                        }
                        for (int i = 0; i < reader.FieldCount; i++)
                            Console.WriteLine("  col" + i + " " + reader.GetName(i) + " : " + reader.GetFieldType(i).Name);
                        int n = 0;
                        while (reader.Read())
                        {
                            n++;
                            for (int i = 0; i < reader.FieldCount; i++)
                            {
                                object value = reader.GetValue(i);
                                if (n == 1)
                                    Console.WriteLine("  row1 col" + i + " = " + (value == DBNull.Value ? "NULL" : value.ToString()));
                            }
                            if (n % 1000 == 0) Console.WriteLine("rows " + n + " @" + watch.ElapsedMilliseconds + "ms");
                        }
                        Console.WriteLine("ROWS " + n + " @" + watch.ElapsedMilliseconds + "ms");
                    }
                }
            }
            Console.WriteLine("DONE");
            return 0;
        }
        catch (Exception e) { Console.WriteLine("ERR " + e); return 1; }
    }
}
