#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate a public, credential-free model and a thin report."""
import argparse
import json
from pathlib import Path
import uuid
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
p.add_argument('--tables',type=int,default=158)
p.add_argument('--rows',type=int,default=10000)
p.add_argument('--relationships',action='store_true',help='Add a shared dimension and active relationships to the fact tables')
a=p.parse_args()
if not 1<=a.tables<=1000 or not 1<=a.rows<=1000000:
    p.error('tables must be 1..1000 and rows 1..1000000')
if a.relationships and a.tables<3:
    p.error('relationships require at least three tables')
if a.output.exists():
    p.error('output must be a new directory')
model=a.output/'Synthetic.SemanticModel'
report=a.output/'Synthetic.Report'
(model/'definition/tables').mkdir(parents=True)
(model/'definition/cultures').mkdir()
(report/'definition/pages/sales/visuals/sales_table').mkdir(parents=True)
def write(file,value):
    file.write_text(json.dumps(value,indent=2)+'\n')
write(a.output/'Synthetic.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Synthetic.Report'}}], 'settings':{'enableAutoRecovery':True}})
write(model/'definition.pbism',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'4.2','settings':{}})
write(report/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Synthetic.SemanticModel'}}})
(model/'definition/database.tmdl').write_text('database\n\tcompatibilityLevel: 1606\n')
facts=['Fact%03d'%i for i in range(1,a.tables-(1 if a.relationships else 0))]
names=['Table']+facts+(['Dimension'] if a.relationships else [])
(model/'definition/model.tmdl').write_text('model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n\tvalueFilterBehavior: independent\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'+''.join('ref table '+n+'\n' for n in names)+'\nref cultureInfo en-US\n')
(model/'definition/cultures/en-US.tmdl').write_text('cultureInfo en-US\n')
(model/'definition/tables/Table.tmdl').write_text('''table Table
	column Produto
		dataType: string
		summarizeBy: none
		sourceColumn: Produto

	column Vendas
		dataType: int64
		summarizeBy: sum
		sourceColumn: Vendas

	partition Table = m
		mode: import
		source =
			#table(type table [Produto = text, Vendas = Int64.Type], {{"Cafe",120},{"Cha",80},{"Suco",100}})
''')
for n in facts:
    text=f'''table {n}
	column Id
		dataType: int64
		summarizeBy: none
		sourceColumn: Id

	column Amount
		dataType: int64
		summarizeBy: sum
		sourceColumn: Amount

	partition {n} = m
		mode: import
		source =
			let
				Ids = Table.FromList({{1..{a.rows}}}, Splitter.SplitByNothing(), {{"Id"}}),
				Values = Table.AddColumn(Ids, "Amount", each Number.Mod([Id], 100), Int64.Type),
				Typed = Table.TransformColumnTypes(Values, {{{{"Id", Int64.Type}}}})
			in
				Typed
'''
    (model/'definition/tables'/ (n+'.tmdl')).write_text(text)
if a.relationships:
    (model/'definition/tables/Dimension.tmdl').write_text(f'''table Dimension
\tcolumn Id
\t\tdataType: int64
\t\tsummarizeBy: none
\t\tsourceColumn: Id

\tpartition Dimension = m
\t\tmode: import
\t\tsource =
\t\t\tTable.TransformColumnTypes(Table.FromList({{1..{a.rows}}}, Splitter.SplitByNothing(), {{"Id"}}), {{{{"Id", Int64.Type}}}})
''')
    relationships='\n'.join(f'''relationship {uuid.uuid5(uuid.NAMESPACE_URL,'pbi-linux/relationship/'+name)}
\tfromColumn: {name}.Id
\ttoColumn: Dimension.Id
''' for name in facts)
    (model/'definition/relationships.tmdl').write_text(relationships)
write(report/'definition/version.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
themes=report/'StaticResources/SharedResources/BaseThemes'
themes.mkdir(parents=True)
write(themes/'Synthetic.json',{'name':'Synthetic','dataColors':['#247BA0','#70C1B3','#F3B61F'],
    'background':'#FFFFFF','foreground':'#222222','tableAccent':'#247BA0'})
write(report/'definition/report.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json',
    'themeCollection':{'baseTheme':{'name':'Synthetic','type':'SharedResources',
        'reportVersionAtImport':{'visual':'2.13.0','report':'3.4.0','page':'2.3.1'}}},
    'resourcePackages':[{'name':'SharedResources','type':'SharedResources',
        'items':[{'name':'Synthetic','path':'BaseThemes/Synthetic.json','type':'BaseTheme'}]}],
    'settings':{'useDefaultAggregateDisplayName':True}})
write(report/'definition/pages/pages.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json','pageOrder':['sales'],'activePageName':'sales'})
write(report/'definition/pages/sales/page.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json','name':'sales','displayName':'Synthetic sales','displayOption':'FitToPage','height':720,'width':1280})
visual=json.loads((Path(__file__).resolve().parents[1]/'fixtures/table-visual.json').read_text())
visual['name']='sales_table'
write(report/'definition/pages/sales/visuals/sales_table/visual.json',visual)
for name in names:
    file=model/'definition/tables'/(name+'.tmdl')
    text=file.read_text()
    text=text.replace('table '+name+'\n','table '+name+'\n\tlineageTag: '+str(uuid.uuid5(uuid.NAMESPACE_URL,'pbi-linux/'+name))+'\n',1)
    lines=text.splitlines()
    for i in range(len(lines)-1,-1,-1):
        if lines[i].startswith('\tcolumn '):
            column=lines[i].removeprefix('\tcolumn ')
            lines.insert(i+1,'\t\tlineageTag: '+str(uuid.uuid5(uuid.NAMESPACE_URL,'pbi-linux/'+name+'/'+column)))
    text='\n'.join(lines)+'\n\tannotation PBI_ResultType = Table\n'
    file.write_text(text)
with (model/'definition/model.tmdl').open('a') as out:
    out.write('\nannotation PBI_QueryOrder = '+json.dumps(names)+'\n')
write(a.output/'expected.json',{'tables':a.tables,'sales':{'Cafe':120,'Cha':80,'Suco':100},'total':300,
    'fact_rows':a.rows,'fact_tables':facts,'relationships':len(facts) if a.relationships else 0,
    'data_loaded':False})
(a.output/'.gitignore').write_text('**/.pbi/\n')
print(a.output/'Synthetic.pbip')
