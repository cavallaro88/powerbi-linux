// SPDX-License-Identifier: GPL-3.0-or-later
// Disposable Import table: replace placeholders locally, never commit credentials.
// Forces schema metadata; does not select a business table or request native SQL.
let
    Source = AmazonRedshift.Database("REPLACE_HOST:5439", "REPLACE_DATABASE"),
    FirstSchema = Table.FirstN(Source, 1),
    Probe = Table.FromRecords(List.Transform(Table.ToRecords(FirstSchema), each [
        Produto = if Text.Length([Name]) >= 0 then "Redshift ODBC probe"
                  else error "Missing schema name",
        Vendas = 1
    ])),
    Typed = Table.TransformColumnTypes(Probe, {{"Produto", type text}, {"Vendas", Int64.Type}})
in
    Typed
