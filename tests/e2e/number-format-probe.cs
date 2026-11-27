// SPDX-License-Identifier: GPL-3.0-or-later
// Number formatting and currency conversion that Power BI Desktop relies on.
// VarFormat: Analysis Services formats DAX FORMAT() results through oleaut32.
// IDataConvert: the MSOLAP provider converts VARIANT cells to bound currency columns.
// VarDecRound: .NET Framework rounds System.Decimal (Math.Round, Convert.ToInt64) through oleaut32.
using System;
using System.Globalization;
using System.Runtime.InteropServices;

[ComImport, Guid("0C733A8D-2A1C-11CE-ADE5-00AA0044773D"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IDataConvert {
  [PreserveSig] int DataConvert(ushort srcType, ushort dstType, UIntPtr srcLen, out UIntPtr dstLen, IntPtr src,
    IntPtr dst, UIntPtr dstMax, uint srcStatus, out uint dstStatus, byte precision, byte scale, uint flags);
}

static class NumberFormatProbe {
  [DllImport("oleaut32.dll", CharSet = CharSet.Unicode)]
  static extern int VarFormat(ref object value, string format, int firstDay, int firstWeek, uint flags,
    [MarshalAs(UnmanagedType.BStr)] out string result);

  [DllImport("oleaut32.dll")]
  static extern int VarDecRound(ref decimal value, int decimals, out decimal result);

  static int failures;

  static void Check(string label, decimal actual, decimal expected) {
    var c = CultureInfo.InvariantCulture;
    bool ok = actual == expected && actual.ToString(c) == expected.ToString(c);
    if (!ok) failures++;
    Console.WriteLine("{0} {1} = {2}, expected {3}", ok ? "PASS" : "FAIL", label, actual.ToString(c),
      expected.ToString(c));
  }

  static void Round(decimal value, int decimals, decimal expected) {
    decimal actual;
    int hr = VarDecRound(ref value, decimals, out actual);
    if (hr != 0) { failures++; Console.WriteLine("FAIL VarDecRound({0}, {1}) hr {2:X8}", value, decimals, hr); return; }
    Check(string.Format(CultureInfo.InvariantCulture, "VarDecRound({0}, {1})", value, decimals), actual, expected);
  }

  static void Format(object value, string format, string expected) {
    string actual;
    int hr = VarFormat(ref value, format, 1, 1, 0, out actual);
    bool ok = hr == 0 && actual == expected;
    if (!ok) failures++;
    Console.WriteLine("{0} VarFormat({1}, {2}) = {3} (hr {4:X8}), expected {5}",
      ok ? "PASS" : "FAIL", value, format, actual, hr, expected);
  }

  static void ToCurrency(IDataConvert convert, object value) {
    IntPtr variant = Marshal.AllocHGlobal(24), cy = Marshal.AllocHGlobal(8);
    try {
      Marshal.GetNativeVariantForObject(value, variant);
      Marshal.WriteInt64(cy, 0);
      UIntPtr length; uint status;
      int hr = convert.DataConvert(12 /* DBTYPE_VARIANT */, 6 /* DBTYPE_CY */, (UIntPtr)24, out length,
        variant, cy, (UIntPtr)8, 0, out status, 0, 0, 0);
      long actual = Marshal.ReadInt64(cy);
      bool ok = hr == 0 && status == 0 && actual == 2584094100L;
      if (!ok) failures++;
      Console.WriteLine("{0} DataConvert(VARIANT vt {1} -> CY) = {2} (hr {3:X8}, status {4}), expected 2584094100",
        ok ? "PASS" : "FAIL", Marshal.ReadInt16(variant), actual, hr, status);
    } finally {
      Marshal.FreeHGlobal(variant);
      Marshal.FreeHGlobal(cy);
    }
  }

  static int Main() {
    Format(4376023.0, "$#,0,K", "$4,376K");
    Format(21000, "#,0,K", "21K");
    Format(258409.41m, "\\$#,0,K", "$258K");
    Format(600.0, "#,0,K", "1K");
    Format(499.0, "#,0,K", "0K");
    Format(-4376023.0, "$#,0,K;($#,0,K)", "($4,376K)");
    Format(1234567.0, "#,0,,\"M\"", "1M");
    Format(1234567.0, "#,", "1235");
    Format(1234567.0, "#,##0,", "1,235");
    Format(0.6, "0", "1");
    Format(9.96, "0.0", "10.0");
    // Existing Wine conformance cases, verified on Windows: commas between digits stay as they were.
    Format(100000, "#,###,###,###", "100,000");
    Format(123456789, "###, ###, ###", "123, 456, 789");
    Format(123456789, "#,#.#", "123,456,789.");
    Format(1, "0,000,000,000", "0,000,000,001");

    var convert = (IDataConvert)Activator.CreateInstance(
      Type.GetTypeFromCLSID(new Guid("C8B522D1-5CF3-11CE-ADE5-00AA0044773D")));
    ToCurrency(convert, new CurrencyWrapper(258409.41m));
    ToCurrency(convert, 258409.41m);
    ToCurrency(convert, 258409.41);

    // Round half to even, as on Windows (.NET documents Math.Round(decimal) as banker's rounding).
    Round(258.40941m, 0, 258m);
    Round(258409.41m, 0, 258409m);
    Round(258409.51m, 0, 258410m);
    Round(-258409.41m, 0, -258409m);
    Round(1.049m, 1, 1.0m);
    Round(1.050m, 1, 1.0m);
    Round(1.150m, 1, 1.2m);
    Round(2.5m, 0, 2m);
    Round(3.5m, 0, 4m);
    Round(-2.5m, 0, -2m);
    Round(0.15m, 1, 0.2m);
    Check("Math.Round(258.40941m)", Math.Round(258.40941m, 0), 258m);
    Check("Math.Round(2.5m)", Math.Round(2.5m), 2m);
    Check("Convert.ToInt64(258409.41m)", Convert.ToInt64(258409.41m), 258409m);
    Check("decimal.ToOACurrency(1.23456m)", decimal.FromOACurrency(decimal.ToOACurrency(1.23456m)), 1.2346m);

    Console.WriteLine(failures == 0 ? "COMPLETED: number formats" : "FAILED: " + failures + " cases");
    return failures == 0 ? 0 : 1;
  }
}
