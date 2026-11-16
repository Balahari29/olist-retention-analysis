# PBIP generator and validators
These scripts generated `powerbi/Olist Retention.pbip` and its two folders (Stage 4). They are kept so the build can
be reproduced and re-checked. **Once you edit the report in Power BI Desktop, Desktop's saved files are the source of
truth: re-running the generators overwrites those edits.**

| Script | What it does |
|---|---|
| `build_model.py <powerbi_dir>` | Writes `Olist Retention.SemanticModel/` (TMDL): 6 MySQL views, 7 relationships, 54 measures from `dax_measures.md`. No credentials. |
| `build_report.py <powerbi_dir> <base_theme.json>` | Writes `Olist Retention.Report/` (PBIR): 5 pages + hidden Seller Detail drill-through, theme, and the `.pbip` file. The base theme JSON comes from the Desktop install (`bin\WebView2Resources\minerva\sharedresources\BaseThemes\Fluent2-CY26SU10.json`). |
| `validate_tmdl.ps1 -DefinitionFolder <...SemanticModel\definition>` | Parses the model with Power BI Desktop's own `TmdlSerializer` and prints tables, relationships, sort-by columns and measure folders. |
| `validate_report.py <powerbi_dir> <schema_root>` | Validates every report JSON file against the PBIR JSON schemas shipped inside Power BI Desktop 2.159 (extracted from `Microsoft.PowerBI.ClientResources.dll`), checks every field reference exists in the model, page/visual/resource paths, drill-through binding, and that no credential text is present. |

Not checked by these tools: DAX syntax and results (Power BI Desktop evaluates DAX after refresh; see Stage 5) and the
exact look of each visual.
