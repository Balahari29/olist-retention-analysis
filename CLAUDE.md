# Olist Customer Retention & Delivery Experience Analysis

Portfolio project for Fresher Data Analyst / Business Analyst roles (Chennai and other Indian cities).
Owner: Bala Hariharan B — github.com/Balahari29

## Goal
Show, with one end-to-end project: SQL data modeling, pandas analysis, a hypothesis test, Power BI (star schema + DAX),
advanced Excel, BA documents (BRD, KPI dictionary, user stories, UAT), and business recommendations.

## Business questions (everything we build must answer one of these)
1. What % of customers buy again, and what does monthly cohort retention look like?
2. Do late deliveries lower review scores, and by how much? (hypothesis test)
3. Which sellers, categories and states cause the most delivery delays?
4. Which customer segments (RFM) should marketing target?
5. How concentrated is revenue across categories and states (Pareto)?

## Rules for Claude
- **Teaching mode.** I have to defend every line in interviews. Before running a query or code block, explain in 2–3
  lines what it does and why. After results, ask me what I think they mean before giving your interpretation.
- **Never invent numbers.** Every figure in docs, memo, README or resume bullets must come from a query/notebook
  output saved under `outputs/`. Cite the file it came from.
- Work one phase at a time. At the end of each phase, summarise what was done and stop for my review.
- Keep code readable over clever: comments, meaningful names, no one-letter variables.
- Commit after each phase with a clear message (I'll push to GitHub).

## Stack
- Python 3.11+ in a venv: pandas, numpy, scipy, matplotlib, seaborn, sqlalchemy, pymysql, openpyxl, jupyter
- MySQL 8 (window functions needed). Database name: `olist`
- Power BI Desktop (Windows) — Claude writes the model spec + DAX; I build it in Desktop
- Excel (Power Query) — Claude writes M code + layout spec; I paste it in Excel
- draw.io for the process map

## Dataset
Kaggle: `olistbr/brazilian-ecommerce` (9 CSVs, ~100K orders, 2016–2018).
Download with the Kaggle CLI (`kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip`)
or manually from Kaggle into `data/raw/`. Raw data is never edited and is git-ignored.

### Known gotchas (check each one in Phase 2)
- `customer_id` is unique **per order**. Repeat customers must use `customer_unique_id`.
- The first and last few months are sparse/partial — decide and document a cut-off for cohort and trend analysis.
- `olist_geolocation_dataset` has many rows per zip prefix — aggregate (e.g. mean lat/lng) before joining.
- Some orders have more than one review, and some reviews cover multiple orders — check and decide rule.
- Delivered orders with missing delivery dates; canceled/unavailable orders — define which statuses are in scope.
- Product categories are in Portuguese — join the translation CSV.

## Folder structure
```
olist-retention-analysis/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .gitignore                 # data/raw, .venv, *.pbix backups, .env
├── .env                       # MySQL credentials (never committed)
├── data/raw/                  # Kaggle CSVs
├── docs/
│   ├── 01_BRD.md
│   ├── 02_KPI_dictionary.md
│   ├── 03_user_stories.md
│   ├── 04_process_map.drawio  (+ .png export)
│   ├── 05_UAT_checklist.md
│   └── 06_insight_memo.md
├── sql/
│   ├── 01_schema.sql
│   ├── 02_data_quality_checks.sql
│   ├── 03_analysis_retention.sql
│   ├── 04_analysis_delivery.sql
│   ├── 05_analysis_sellers_categories.sql
│   └── 06_views_for_powerbi.sql
├── src/
│   ├── load_to_mysql.py
│   └── export_views.py
├── notebooks/
│   └── analysis.ipynb         # RFM, hypothesis test, haversine distance, charts
├── excel/
│   ├── seller_scorecard.xlsx
│   └── power_query_m_code.txt
├── powerbi/
│   ├── model_spec.md          # star schema, relationships, date table
│   ├── dax_measures.md
│   ├── page_layout.md
│   └── olist_dashboard.pbix   (built by me)
├── outputs/                   # CSV results of every query/test used in docs
└── images/                    # chart PNGs + dashboard screenshots for README
```

## Phases
0. **Setup** — folders, venv, requirements.txt, .gitignore, .env template, download data, git init.
1. **BA documents (draft)** — BRD, KPI dictionary (formula, source table, owner), 5–6 user stories with acceptance
   criteria. Stakeholders: Head of Customer Experience, Logistics Manager, Marketing Manager. Draft the process map
   steps as text; I'll draw it in draw.io.
2. **SQL: schema + load + data quality** — CREATE TABLEs with PKs/FKs, Python loader, data-quality checks for every
   gotcha above. Save DQ results to `outputs/`. Document decisions in README.
3. **SQL analysis** — cohort retention (first-purchase month via CTE/window), delay buckets
   (`delivered_customer_date - estimated_delivery_date`: early / on time / 1–3 / 4–7 / 7+ days late) vs avg review,
   seller late-rate ranking with NTILE (min order threshold), category + state Pareto, MoM trend with LAG.
   Create views for Power BI.
4. **Python notebook** — RFM scoring with `pd.qcut` + named segments; Mann-Whitney U test (late vs on-time review
   scores) with effect size and plain-English conclusion; seller→customer haversine distance vs delay; clean charts.
5. **Excel** — seller scorecard: Power Query import, pivot + slicers, XLOOKUP against a Targets sheet,
   conditional formatting for bottom-10% sellers, what-if Data Table ("if late deliveries fall by X%…").
6. **Power BI spec** — star schema (fact_orders, fact_order_items, dim_customer, dim_seller, dim_product, dim_date),
   DAX: Total Revenue, AOV, Repeat Customer %, On-Time Delivery %, Avg Review Score, Late Order %, Revenue MoM %.
   Pages: Executive Overview / Delivery vs Satisfaction / Customer Segments (RFM) / Seller Performance (drill-through).
   Each visual maps to a user story ID.
7. **UAT + wrap-up** — UAT checklist (each dashboard KPI vs SQL query, pass/fail), 1-page insight memo with
   3 recommendations + estimated impact, README (questions, ER diagram, decisions, findings, screenshots,
   limitations), 3 resume bullets and a LinkedIn post draft — all numbers from `outputs/`.
