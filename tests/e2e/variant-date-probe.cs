// SPDX-License-Identifier: GPL-3.0-or-later
// Round-trip OLE Automation dates through VariantTimeToSystemTime and
// SystemTimeToVariantTime, as Analysis Services does for a trace StopTime.
// Desktop sends DateTime.MaxValue at every start; a failed round trip makes the
// engine launch SQLDUMPER. Exit code 1 means a date that converts to a
// SYSTEMTIME could not be converted back (corrected by
// wine-11.18-oleaut32-max-date.patch).
using System;
using System.Runtime.InteropServices;

class VariantDateProbe
{
    [StructLayout(LayoutKind.Sequential)]
    struct SYSTEMTIME { public ushort year, month, dayOfWeek, day, hour, minute, second, milliseconds; }

    [DllImport("oleaut32")] static extern int VariantTimeToSystemTime(double time, out SYSTEMTIME systemTime);
    [DllImport("oleaut32")] static extern int SystemTimeToVariantTime(ref SYSTEMTIME systemTime, out double time);

    static int Main()
    {
        double[] values =
        {
            DateTime.MaxValue.ToOADate(),              // 9999-12-31 23:59:59.9999999
            2958465.0,                                 // 9999-12-31 00:00:00
            2958465.999994,                            // rounds down to 23:59:59
            2958465.999995,                            // last half second
            new DateTime(2026, 12, 31, 23, 59, 59, 600).ToOADate(),  // ordinary rollover must still round up
            0.0,
            -657434.0,                                 // 0100-01-01, the minimum
        };
        int failures = 0;
        foreach (double value in values)
        {
            SYSTEMTIME st;
            double back = double.NaN;
            int converted = VariantTimeToSystemTime(value, out st);
            int restored = converted != 0 ? SystemTimeToVariantTime(ref st, out back) : 0;
            bool ok = converted != 0 && restored != 0 && st.year <= 9999;
            if (!ok) failures++;
            Console.WriteLine(String.Format("{0,-22:R} {1:D4}-{2:D2}-{3:D2} {4:D2}:{5:D2}:{6:D2} to={7} back={8} {9:R} {10}",
                value, st.year, st.month, st.day, st.hour, st.minute, st.second, converted, restored, back, ok ? "ok" : "FAIL"));
        }
        SYSTEMTIME beyond;
        bool rejected = VariantTimeToSystemTime(2958466.0, out beyond) == 0;
        Console.WriteLine("2958466 (year 10000) rejected=" + rejected);
        if (!rejected) failures++;
        Console.WriteLine(failures == 0 ? "PASS" : "FAIL: " + failures);
        return failures == 0 ? 0 : 1;
    }
}
