using System;
using System.IO;
using System.Reflection;
using System.Globalization;

// Consulta o motor local pelo cliente gerenciado ADOMD (referência).
// Uso: adomd-probe.exe <porta AS> "EVALUATE ... ou SELECT ... FROM $SYSTEM..." [catalogo]
class AdomdProbe
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

    static int Run(string[] args)
    {
        try
        {
            var clientAssembly = typeof(Microsoft.AnalysisServices.AdomdClient.AdomdConnection).Assembly;
            Console.WriteLine("ADOMD CLIENT: " + clientAssembly.FullName);
            Console.WriteLine("ADOMD FROM APP DIRECTORY: " + String.Equals(
                Path.GetDirectoryName(clientAssembly.Location),
                @"C:\Program Files\Microsoft Power BI Desktop\bin", StringComparison.OrdinalIgnoreCase));
            using (var conn = new Microsoft.AnalysisServices.AdomdClient.AdomdConnection(
                "Data Source=localhost:" + args[0] + ";Connect Timeout=10;" +
                (args.Length > 2 ? "Catalog=" + args[2] + ";" : "")))
            {
                Console.WriteLine("ADOMD OPEN");
                conn.Open();
                Console.WriteLine("ADOMD CONNECTED: " + conn.ServerVersion);
                using (var cmd = conn.CreateCommand())
                {
                    cmd.CommandText = args[1];
                    bool dmv = args[1].TrimStart().StartsWith("SELECT", StringComparison.OrdinalIgnoreCase) &&
                               args[1].IndexOf("$SYSTEM", StringComparison.OrdinalIgnoreCase) >= 0;
                    if (dmv) cmd.CommandType = System.Data.CommandType.Text;
                    cmd.CommandTimeout = 30;
                    using (var reader = cmd.ExecuteReader())
                    {
                        Console.WriteLine("FIELDS: " + reader.FieldCount);
                        if (dmv)
                            for (int i = 0; i < reader.FieldCount; i++)
                                Console.WriteLine("FIELD " + i + " " + reader.GetName(i));
                        int rows = 0;
                        while (reader.Read())
                        {
                            Console.WriteLine("ROW " + (++rows));
                            for (int i = 0; i < reader.FieldCount; i++)
                            {
                                object value = reader.GetValue(i);
                                string text = dmv && value is DateTime
                                    ? ((DateTime)value).ToString("o", CultureInfo.InvariantCulture)
                                    : dmv ? Convert.ToString(value, CultureInfo.InvariantCulture) : Convert.ToString(value);
                                if (dmv) text = text.Replace("\\", "\\\\").Replace("\r", "\\r").Replace("\n", "\\n");
                                Console.WriteLine("COL" + i + ": " + text);
                            }
                        }
                    }
                }
            }
            return 0;
        }
        catch (Exception e) { Console.WriteLine(e.ToString()); return 1; }
    }
}
