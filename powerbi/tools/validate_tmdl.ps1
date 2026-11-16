param([string]$DefinitionFolder)
# Parse a TMDL folder with Power BI Desktop's own TmdlSerializer and summarise what it read.
$bin = (Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop").InstallLocation + "\bin"
[AppDomain]::CurrentDomain.add_AssemblyResolve({ param($s, $e)
    $n = (New-Object Reflection.AssemblyName($e.Name)).Name; $p = Join-Path $bin "$n.dll"
    if (Test-Path $p) { [Reflection.Assembly]::LoadFrom($p) } else { $null } })
[void][Reflection.Assembly]::LoadFrom("$bin\Microsoft.PowerBI.Tabular.dll")
try {
    $db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($DefinitionFolder)
} catch {
    "TMDL PARSE FAILED"; $ex = $_.Exception; while ($ex) { "  " + $ex.GetType().Name + ": " + $ex.Message; $ex = $ex.InnerException }; exit 1
}
$m = $db.Model
"TMDL PARSE OK  compatibilityLevel=$($db.CompatibilityLevel)  culture=$($m.Culture)  discourageImplicitMeasures=$($m.DiscourageImplicitMeasures)"
"Expressions: " + (($m.Expressions | ForEach-Object { $_.Name }) -join ", ")
foreach ($t in $m.Tables) {
    $calc = ($t.Columns | Where-Object { $_.Type -eq "Calculated" }).Count
    "Table {0,-22} cols={1,2} calcCols={2} measures={3,2} partition={4} dataCategory={5}" -f $t.Name, ($t.Columns | Where-Object { $_.Type -ne "RowNumber" }).Count, $calc, $t.Measures.Count, $t.Partitions[0].SourceType, $t.DataCategory
}
"Relationships:"
foreach ($r in $m.Relationships) {
    "  {0}.{1} ({2}) -> {3}.{4} ({5})  crossFilter={6} active={7}" -f $r.FromTable.Name, $r.FromColumn.Name, $r.FromCardinality, $r.ToTable.Name, $r.ToColumn.Name, $r.ToCardinality, $r.CrossFilteringBehavior, $r.IsActive
}
"Sort-by columns: " + (($m.Tables | ForEach-Object { $_.Columns } | Where-Object { $_.SortByColumn } | ForEach-Object { "$($_.Table.Name)[$($_.Name)] by $($_.SortByColumn.Name)" }) -join "; ")
"Key column: " + (($m.Tables | ForEach-Object { $_.Columns } | Where-Object { $_.IsKey } | ForEach-Object { "$($_.Table.Name)[$($_.Name)]" }) -join ", ")
"Measure folders: " + (($m.Tables["_Measures"].Measures | Group-Object DisplayFolder | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ", ")
