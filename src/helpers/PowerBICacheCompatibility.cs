// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections;
using System.Reflection;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

[assembly: AssemblyVersion("1.0.0.0")]

public static class PowerBICacheCompatibility
{
    // Keep every string, escape and numeric token byte-for-byte. Only JSON
    // whitespace outside strings is removed; parsed values must remain equal.
    public static string CompactJson(string text)
    {
        if (String.IsNullOrEmpty(text)) return text;
        var compact = new StringBuilder(text.Length);
        bool quoted = false, escaped = false;
        foreach (char c in text)
        {
            if (quoted)
            {
                compact.Append(c);
                if (escaped) escaped = false;
                else if (c == '\\') escaped = true;
                else if (c == '"') quoted = false;
            }
            else if (c == '"') { quoted = true; compact.Append(c); }
            else if (c != ' ' && c != '\t' && c != '\r' && c != '\n') compact.Append(c);
        }
        string value = compact.ToString();
        if (value == text) return text;
        try
        {
            return JToken.DeepEquals(JToken.Parse(text), JToken.Parse(value)) ? value : text;
        }
        catch (JsonException) { return text; } // Let the original model API report invalid input.
    }

    static object Property(object instance, string name)
    {
        if (instance == null) return null;
        var property = instance.GetType().GetProperty(name, BindingFlags.Instance | BindingFlags.Public);
        return property == null ? null : property.GetValue(instance, null);
    }

    public static void NormalizeDatabase(object database)
    {
        var cultures = Property(Property(database, "Model"), "Cultures") as IEnumerable;
        if (cultures == null) return;
        foreach (var culture in cultures)
        {
            object metadata = Property(culture, "LinguisticMetadata");
            if (metadata == null) continue;
            var content = metadata.GetType().GetProperty("Content", BindingFlags.Instance | BindingFlags.Public);
            if (content == null || !content.CanRead || !content.CanWrite || content.PropertyType != typeof(string)) continue;
            string original = (string)content.GetValue(metadata, null);
            string compact = CompactJson(original);
            if (compact != original) content.SetValue(metadata, compact, null);
        }
    }
}
