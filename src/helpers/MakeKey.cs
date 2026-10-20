// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Security.Cryptography;
class MakeKey
{
    static int Main(string[] args)
    {
        if (args.Length != 1) return 2;
        var parameters = new CspParameters();
        parameters.KeyNumber = (int)KeyNumber.Signature;
        using (var rsa = new RSACryptoServiceProvider(2048, parameters))
        {
            rsa.PersistKeyInCsp = false;
            File.WriteAllBytes(args[0], rsa.ExportCspBlob(true));
        }
        return 0;
    }
}
