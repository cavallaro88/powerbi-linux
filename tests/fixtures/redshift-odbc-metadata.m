// SPDX-License-Identifier: GPL-3.0-or-later
// Disposable Import table for the external AWS Windows MSI driver.
// Replace endpoint/database placeholders locally; enter credentials in Desktop.
// Forces metadata navigation without selecting business tables or native SQL.
let
    Source = Odbc.DataSource(
        "Driver={Amazon Redshift (x64)};Server=REPLACE_HOST;Port=5439;Database=REPLACE_DATABASE;SSLMode=verify-full;",
        [HierarchicalNavigation=true]),
    FirstEntry = Table.FirstN(Source, 1),
    Probe = Table.FromRecords(List.Transform(Table.ToRecords(FirstEntry), each [
        Produto = if Text.Length([Name]) >= 0 then "Redshift MSI probe"
                  else error "Missing metadata name",
        Vendas = 1
    ])),
    Typed = Table.TransformColumnTypes(Probe, {{"Produto", type text}, {"Vendas", Int64.Type}})
in
    Typed
