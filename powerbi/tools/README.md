# PBIP generator and validators
These scripts generated `powerbi/Olist Retention.pbip` and its two folders (Stage 4). They are kept so the build can
be reproduced and re-checked. **Once you edit the report in Power BI Desktop, Desktop's saved files are the source of
truth: re-running the generators overwrites those edits.**

| Script | What it does |
|---|---|
| `build_model.py <powerbi_dir>` | Writes `Olist Retention.SemanticModel/` (TMDL): 6 MySQL views, 7 relationships, 54 measures from `dax_measures.md`. No credentials. |
| `build_report.py <powerbi_dir> <base_theme.json>` | Writes `Olist Retention.Report/` (PBIR): 5 pages + hidden Seller Detail drill-through, theme, and the `.pbip` file. The base theme JSON comes from the Desktop install (`bin\WebView2Resources\minerva\sharedresources\BaseThemes\Fluent2-CY26SU10.json`). |
| `validate_tmdl.ps1 -DefinitionFolder <...SemanticModel\definition>` | Parses the model with Power BI Desktop's own `TmdlSerializer` and prints tables, relationships, sort-by columns and measure folders. |
| `validate_report.py <powerbi_dir> <schema_root>` | Validates every report JSON file against the PBIR JSON schemas shipped inside Power BI Desktop 2.159 (extracted from `Microsoft.PowerBI.ClientResources.dll`), checks every field reference exists in the model, page/visual/resource paths, drill-through binding, and that no credential text is present. Layout checks: visuals overlapping on a page, and KPI cards / slicers whose height (minus padding and title) is likely too small for their text (an estimate from font sizes, not a render). |
| `build_validation_query.py <expected_values.csv> <output.dax>` | Stage 5: writes `powerbi/stage5_validation.dax`, one read-only DAX query with 19 PASS / FAIL checks: the 17 values in `outputs/powerbi_expected_values.csv` (tolerance = half of the last decimal place SQL rounded to; counts must match exactly), including the top seller's identity and value from `outputs/seller_late_rate_ranking.csv`, plus Platform Late Rate with and without filters. Stops without writing if an input is non-numeric, duplicated, missing or unexpected. Run the query in Desktop's DAX query view after a refresh. |

`build_report.py` places visuals on one layout grid (constants near the top): header y 8, slicer row y 72 (300 x 76,
header off, 10 pt title), KPI cards y 162 (92 high, title off, padding 8/12), chart rows y 266 and y 493 (215 high,
442 for two rows). Seller Detail has no slicers: cards at y 76, charts y 180-708.

Not checked by these tools: DAX syntax and results (Power BI Desktop evaluates DAX after refresh; see Stage 5) and the
exact look of each visual.

## Stage 5 validation result (2026-11-18)
- **Refresh:** the model refreshed successfully from MySQL in Power BI Desktop; all 8 tables report a ready state.
- **DAX checks:** `powerbi/stage5_validation.dax` passed 19 of 19 checks (0 failed). The rows returned by Power BI are
  saved in `outputs/stage5_validation_results.csv`.
- **UAT:** Manual UAT is recorded in docs/05_UAT_checklist.md: 43 PASS, 0 Fail, 5 N/A, 3 checklist corrections outstanding.
