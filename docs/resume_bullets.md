# Resume bullets: Olist Customer Retention & Delivery Experience Analysis
Project line: **Olist Customer Retention & Delivery Analysis** | MySQL, Python, Excel, Power BI | github.com/Balahari29
Each bullet is under 2 lines; every number traces to the file in *Source* (use these to answer "how did you get that?").

## Version A: Data Analyst roles
- Modelled 99K Olist e-commerce orders (9 tables, 1M geolocation rows) in MySQL with 19 data-quality checks; every
  table loaded with a 0-row reconciliation difference.
  *Source: `outputs/row_counts.csv`, `outputs/dq_*.csv` (19 files)*
- Showed late deliveries cost 2.02 review stars (Mann-Whitney, rank-biserial −0.64), then found 74% of late reviews
  were written before delivery, cutting the true gap to 0.76.
  *Source: `outputs/hypothesis_test_results.csv`, `outputs/hypothesis_test_conclusion.txt`*
- Segmented 94,703 customers with RFM in Python: "New – high value" buyers are 16% of customers but 29% of revenue,
  the recommended second-purchase target.
  *Source: `outputs/rfm_segments.csv`*

## Version B: Business Analyst roles
- Wrote a BRD, KPI dictionary and 6 user stories for 3 stakeholders, then a 51-check UAT plan with SQL-computed
  expected values for every dashboard KPI.
  *Source: `docs/01_BRD.md`-`docs/03_user_stories.md`, `docs/05_UAT_checklist.md`, `outputs/powerbi_expected_values.csv`*
- Recommended sending review surveys only after delivery: 74% of late-order reviews came before the parcel arrived,
  inflating the late penalty from 0.76 to 2.02 stars.
  *Source: `outputs/hypothesis_test_results.csv`, `docs/06_insight_memo.md`*
- Built an Excel seller scorecard (XLOOKUP, What-If) ranking 625 sellers by excess late orders; the top 20 caused 457,
  and the #1 seller ranked only #135 on late rate.
  *Source: `excel/seller_scorecard.xlsx`, `outputs/seller_excess_summary.csv`, `outputs/seller_late_rate_ranking.csv`*

## Notes
- Power BI: say **"designed a Power BI star schema and DAX measures"** until the .pbix is built and passes
  `docs/05_UAT_checklist.md`; then it can become "built a 4-page Power BI dashboard".
- "99K orders" = 99,441 raw orders loaded; analyses use 97,905 valid orders (`outputs/clean_layer_checks.csv`).
