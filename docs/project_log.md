# Project log: phase notes and decisions
Detailed notes moved from the README so it stays readable. Each section was written during the phase named, and every
number cites the `outputs/` file it came from. For the summary see [`README.md`](../README.md).

| Phase | Commit message prefix | What was built |
|---|---|---|
| 0 Setup | `Phase 0` | Folders, venv, requirements, .gitignore, .env template, dataset, git |
| 1 BA documents | `Phase 1` | BRD, KPI dictionary, user stories, process-map steps |
| 2 SQL schema, load, DQ | `Phase 2` | `sql/01`, `sql/02`, `src/load_to_mysql.py`, `src/run_dq_checks.py` |
| 3 SQL analysis | `Phase 3` | Clean layer, retention, delivery, sellers/categories, Power BI views |
| 4 Python notebook | `Phase 4` | RFM, Mann-Whitney test, distance, charts |
| 5 Excel | `Phase 5` | Seller scorecard workbook; seller late-rate precision fix |
| 6 Power BI spec | `Phase 6` | Star-schema export, model spec, DAX, page layout, build steps |
| 7 Wrap-up | `Phase 7` | UAT checklist, insight memo, README, resume bullets, LinkedIn post |

Links in this file are relative to the project root (e.g. `outputs/...`).

## Schema decisions (`sql/01_schema.sql`)
| Decision | Reason |
|---|---|
| Zip code prefixes stored as `CHAR(5)` and read as text by pandas | Keeps leading zeros (e.g. `01003`); stored as numbers they would shrink to 4 digits and stop joining |
| Money as `DECIMAL(10,2)` | Exact sums; `FLOAT` adds rounding errors. Source values have at most 2 decimals |
| `order_reviews` PK = `(review_id, order_id)` | `review_id` alone repeats (one review can be linked to several orders); the pair is unique |
| `order_items` PK = `(order_id, order_item_id)`, `order_payments` PK = `(order_id, payment_sequential)` | Natural composite keys; verified unique while profiling |
| `geolocation` has a surrogate `geolocation_id` PK | Many rows per zip prefix, so there is no natural key |
| **No FK** customers/sellers → geolocation | 157 customer and 7 seller zip prefixes are missing from geolocation ([`outputs/dq_zip_coverage.csv`](outputs/dq_zip_coverage.csv)) |
| **No FK** products → category_translation | 2 categories have no translation row ([`outputs/dq_category_translation.csv`](outputs/dq_category_translation.csv)) |
| FKs kept on during load, parents loaded first | MySQL rejects any orphan row, so a successful load proves referential integrity for every FK |
| Loader: `keep_default_na=False`, `na_values=[""]` | Only empty cells become NULL; pandas' default would also turn text like "NA" into NULL |
| Loader: `encoding="utf-8-sig"` | Strips the byte-order mark (BOM) at the start of `product_category_name_translation.csv` |

### Column renames
| Source column (`olist_products_dataset.csv`) | Table column (`products`) | Why |
|---|---|---|
| `product_name_lenght` | `product_name_length` | Spelling error in the source data |
| `product_description_lenght` | `product_description_length` | Spelling error in the source data |

### Load reconciliation
All 9 tables: rows read by pandas = rows in MySQL, difference 0 ([`outputs/row_counts.csv`](outputs/row_counts.csv)).
Note: the reviews CSV has more *lines* than *rows*, because review comments can contain line breaks inside quoted
fields. Always count rows with a CSV parser, not `wc -l`.

## Data-quality findings (`sql/02_data_quality_checks.sql`)
| # | Check | Finding | Source |
|---|---|---|---|
| G1 | customer_id vs customer_unique_id | 99,441 customer_ids but 96,096 customer_unique_ids; every customer_id has exactly 1 order. 2,997 unique customers have 2+ orders (any status, before the valid-order rule) | `outputs/dq_customer_id_vs_unique_id.csv` |
| G2 | Orders per month | 2016-09: 4, 2016-10: 324, **2016-11: no orders**, 2016-12: 1. 2017-01 to 2018-08 are complete months (2017-01: 800 orders, then 1,780+). 2018-09: 16 and 2018-10: 4, none delivered | `outputs/dq_orders_per_month.csv` |
| G3 | Geolocation rows per zip | 1,000,163 rows for 19,015 zip prefixes (avg 52.6, max 1,146 per zip); 279,667 exact duplicate rows; 42 rows (21 zips) outside Brazil's bounding box | `outputs/dq_geolocation_rows_per_zip.csv`, `outputs/dq_geolocation_outside_brazil.csv` |
| G4 | Reviews per order | 98,126 orders have 1 review, 543 have 2, 4 have 3, 768 have none. Of the 547 orders with 2+ reviews, scores differ in 202; answer times always differ | `outputs/dq_reviews_per_order.csv`, `outputs/dq_multi_review_orders.csv` |
| G4 | Orders per review | 764 review_ids cover 2 orders, 25 cover 3. All 789 belong to the same customer_unique_id; 748 to orders bought the same day | `outputs/dq_orders_per_review.csv`, `outputs/dq_multi_order_reviews.csv` |
| G5 | Status distribution | delivered 96,478 (97.02%), shipped 1,107, canceled 625, unavailable 609, invoiced 314, processing 301, created 5, approved 2. 6 canceled orders still have a delivered date | `outputs/dq_order_status_distribution.csv` |
| G5 | Delivered with missing dates | Of 96,478 delivered orders: 8 have no customer-delivery date, 2 no carrier date, 14 no approval date | `outputs/dq_delivered_missing_dates.csv` |
| — | Nulls in key dates | purchase and estimated dates: 0 nulls. approved 160, carrier 1,783, delivered 2,965 nulls (mostly undelivered/canceled orders) | `outputs/dq_null_key_dates.csv` |
| — | Orders with no items | 775 orders: unavailable 603, canceled 164, created 5, invoiced 2, shipped 1 | `outputs/dq_orders_without_items.csv` |
| — | Orders with no payment | 1 (status delivered) | `outputs/dq_orders_without_payment.csv` |
| G6 | Category translation | 610 products (1,603 order items) have no category; `portateis_cozinha_e_preparadores_de_alimentos` (10 products) and `pc_gamer` (3 products) have no English translation | `outputs/dq_category_translation.csv` |
| — | Revenue reconciliation | Of 98,665 orders with items and payments, 98,362 match price + freight = payments within 1 cent; payments higher in 264, lower in 39. Totals: price + freight R$ 15,843,409.78 vs payments R$ 15,846,280.17 | `outputs/dq_revenue_reconciliation.csv` |
| — | Value ranges | No zero prices; 383 items with zero freight; 9 zero-value payments; 2 payments with 0 instalments; 3 `not_defined` payment types | `outputs/dq_value_ranges.csv` |
| PM | Process-map step order | 0 approvals before purchase; 0 estimated dates before purchase; **1,359 carrier pick-ups dated before approval**; 23 deliveries before carrier pick-up; 8,849 of 97,657 orders picked up after the seller's shipping limit | `outputs/dq_process_map_timestamps.csv` |
| PM | Survey timing (step 9) | 88,837 of 99,224 surveys created the same or next day after delivery; 5,127 before delivery (4,713 of them on/after the estimated date); 2,865 for orders with no delivered date | `outputs/dq_review_timing.csv` |

## Data rules (accepted 2026-11-02, applied in `sql/03_clean_layer.sql`)
**Rule 1: Valid orders** (view `v_orders_valid`)
- `order_status IN ('delivered','shipped','invoiced','processing','approved')`. Excludes `canceled` and `unavailable`
  (no completed sale; most unavailable orders have no items) and `created` (5 orders: no approval and no items).
- Purchases from 2017-01-01 to 2018-08-31 only (Rule 3). Applying the window here means every KPI
  (revenue, retention, delivery) uses the same set of orders.

**Rule 2: Duplicate reviews** (view `v_order_reviews_dedup`)
- One order, several reviews (547 orders): keep the review with the latest `review_answer_timestamp`
  (`review_id` as tie-breaker). This is the customer's final opinion.
- One review, several orders (789 reviews): the review stays on **each** linked order, so order-level delivery
  can be compared with a score. The view carries `orders_sharing_review` for this.
- **Phase 4 hypothesis test: one row per `review_id`**, so a single survey answer covering several orders is not
  counted several times (that would inflate the sample size and make the p-value look stronger than it is).

**Rule 3: Analysis window and observation windows**
- Trends, cohorts and all KPIs: purchases **2017-01-01 to 2018-08-31** (20 complete months). 2016 is excluded
  (329 orders, no orders in 2016-11); 2018-09/10 are excluded (20 orders, none delivered).
  Source: `outputs/dq_orders_per_month.csv`.
- **Delivery KPIs** (view `v_order_delivery`): `order_status = 'delivered'`, a non-NULL delivered date, **and an
  estimated delivery date on or before the dataset's last purchase date** (`MAX(order_purchase_timestamp)` over
  all orders, 2018-10-17). Orders whose deadline falls after the data ends cannot yet be late, so including them
  would bias late rates downwards.
- **Cohorts:** retention month *k* is reported only for cohorts observed for at least *k* months, and cohorts are
  compared on an **equal observation window** (repeat purchase within months 1-6 after the first order,
  only for cohorts with 6 full months of follow-up).

**Rule 4: Timestamp anomalies** (view `v_order_delivery`)
- Orders whose carrier pick-up is dated before payment approval (1,359 in all orders, see
  `outputs/dq_process_map_timestamps.csv`) are **flagged** (`flag_pickup_before_approval = 1`), not dropped.
- They are excluded **only** from approval-to-pick-up timing (`approval_to_pickup_days` is NULL for them) and stay
  in every other KPI.

**Category names** (view `v_product_category`): English name from `category_translation`; the 2 untranslated
categories keep their Portuguese name; products with no category become `'unknown'`.

## Delivery late-rate spikes: possible explanations (consistent with the data, not proof)
Late Order % by purchase month is mostly 1-7 %, with three spikes: 2017-11 (12.4 %), 2018-02 (14.13 %) and
2018-03 (18.96 %) (`outputs/delivery_ontime_by_month.csv`). The data cannot show *why*; these explanations fit the
timing, and the checks below show where they fit and where they do not.

**2017-11: Black Friday 2017 (24 November).** Orders rose from 4,547 to 7,421 (+63.2 %) and revenue rose +52.06 %
month over month (`outputs/revenue_mom.csv`). Orders bought in Black Friday week (20-26 Nov) were late 17.26 % of the
time vs 9.17 % for the rest of November (`outputs/delivery_spike_black_friday.csv`). This **fits** a volume surge
overloading sellers and carriers.

**2018-03: Correios (national postal service) strike that began on 12 March 2018.** A union federation notice
listed the SP, RJ, Bauru (SP), MA and TO bases as joining; on 13 March the labour court (TST) ruled against the strike
and assemblies in several states voted to return to work from 14 March. The **timing fits** (March is the peak month).
The **state pattern does not clearly fit**: in 2018-03 orders to SP, RJ, MA and TO were late 15.57 % vs 23.23 % for all
other states (`outputs/delivery_spike_strike_states.csv`). A wider national stoppage, or another cause, would explain this better than
a strike limited to those states.

**2018-02** was already high in both state groups (14.47 % and 13.71 %) *before* the strike began, so the strike
does not explain February. **Open question:** what explains it? This is a limitation to state in the memo.

Sources for the strike dates: news coverage from March 2018 (e.g. Congresso em Foco, BNews) and a FINDECT union
notice from 28 Feb 2018. Add the exact links you cite to the final README.

## Distance vs delay: reading the correlations
Spearman ρ between seller-to-customer distance and **delivery days** is 0.541, but with the **late flag** only 0.069
(`outputs/distance_correlation.csv`). Two reasons:
1. Olist's estimated delivery dates already **scale with distance**, so long routes are slow but mostly still within
   their (longer) estimate.
2. ρ is small **partly because "late" is a rare yes/no flag** (6.79 % of delivered orders, `outputs/delivery_kpis_overall.csv`).
   A 0/1 variable that is almost always 0 is one huge tie, which limits how large any rank correlation can get,
   even when the effect is real.

The banded view shows the effect clearly: late % rises from 4.49 % (0-100 km) to 11.64 % (1,500+ km)
(`outputs/distance_vs_delay_bands.csv`). **Long routes are under-buffered:** the estimate grows with distance, but not
enough.

## Interpretation decisions (for the Phase 7 insight memo)
1. **Late delivery vs reviews:** the headline is **2.02 stars** lower for late orders, explained by the **0.76-star** gap among
   reviews written after delivery: 74 % of late reviews were written before the parcel arrived
   (`outputs/hypothesis_test_results.csv`, `outputs/hypothesis_test_conclusion.txt`).
   **Recommendation #1:** send the review survey only after delivery is confirmed, and add proactive delay notifications.
2. **Estimated dates:** add more buffer to long routes (see the distance section above).
3. **Marketing:** target **New - high value** customers (15.56 % of customers, 29.4 % of revenue, `outputs/rfm_segments.csv`)
   with a second-purchase campaign, keeping a **random holdout group** to measure the lift.
4. **Framing the delivery impact:** lead with **customers affected**, not the platform average. A 20 % cut in late
   orders means about **1,306 fewer late, poorly reviewed orders**, while the platform-wide average review moves only
   **+0.01 to +0.03 stars** (4.16 to 4.17-4.19) because only 6.79 % of orders are late (`excel/seller_scorecard.xlsx`
   What-If sheet; inputs from `outputs/delivery_kpis_overall.csv`, `outputs/hypothesis_test_results.csv`). The effect
   is concentrated on the affected customers and on seller ratings, so the recommendation stands; the average change
   is context only.

## Excel seller scorecard (`excel/`)
`excel/seller_scorecard.xlsx` is built by `src/build_seller_scorecard.py` from `excel/seller_scorecard_data.csv`
(625 sellers with 30+ delivered orders). Sheets: **KPI** tiles, **Scorecard** (XLOOKUP, status, bottom-10 % highlight,
excess-late ranking), **What-If** (review uplift range from the hypothesis test), **Targets** (labelled assumptions),
**Data** (Excel Table). Only inputs are typed; every result is a formula. Power Query, the PivotTable/slicer and the
Data Table are manual steps in `excel/manual_steps.md`.

**Verification:** the workbook was recalculated with a formula engine (0 errors), and its KPI tiles match
`outputs/seller_scorecard_totals.csv`: 625 sellers, late 6.73 % (seller-order pairs), average review 4.13,
revenue R$ 10,334,128.62.

**Precision fix found by this check:** MySQL rounds `AVG()` and integer division to 4 decimals
(`div_precision_increment`). The seller late rate and platform rate were therefore rounded, so near-equal sellers
tied in `RANK`/`NTILE` and excess late orders were off by up to 0.02. `v_seller_late_rate` now divides in `DOUBLE`.
Deciles 1-4 were unchanged; one seller moved from decile 5 to 6 (`outputs/seller_late_rate_by_decile.csv`).

## Does a late first order reduce repeat purchase? (not significant)
Customers whose **first** valid order arrived late returned within 6 months **1.47 %** of the time (54 of 3,667) vs
**1.79 %** (922 of 51,566) after an on-time first order: **−0.32 percentage points, 95 % CI −0.72 to +0.09,
p = 0.161** (two-proportion z-test; chi-square 1.96 = z²). **Not statistically significant.**
The test is underpowered: with only 54 repeat buyers in the late group it could reliably detect only gaps of about
**0.63 points** or more, so a smaller real effect cannot be ruled out. The direction matches the review finding but
this data cannot confirm it. Equal 6-month observation window (cohorts 2017-01 to 2018-02, 56,338 customers);
1,105 customers whose first order was outside delivery scope are excluded from the test.
Sources: `outputs/retention_first_order_late_vs_on_time.csv` (SQL), `outputs/retention_first_order_late_test.csv`,
`outputs/retention_first_order_late_conclusion.txt` (notebook section 2b).

## Power BI (`powerbi/`)
The .pbix is built on Windows from CSV snapshots of the star-schema views, so the PC needs no MySQL.
- `powerbi/data/*.csv`: `fact_orders`, `fact_order_items`, `dim_customer`, `dim_seller`, `dim_product`, `dim_date`,
  `rfm_customer_segments`. **Regenerate** on the Mac with `.venv/bin/python src/run_analysis.py` (rebuilds the views),
  run the notebook (rewrites `rfm_customer_segments`), then `.venv/bin/python src/export_views.py`.
  **The CSVs are not in git** (`powerbi/data/` is git-ignored). **Regenerate with `export_views.py`, then copy the
  folder to the Windows PC.** For an easy copy, zip it from the project root:
  `zip -r powerbi_data.zip powerbi/data outputs/retention_cohort_long.csv outputs/distance_vs_delay_bands.csv
  outputs/retention_first_order_late_vs_on_time.csv outputs/rfm_segments.csv` (the zip is git-ignored too).
- `powerbi/model_spec.md`: tables, keys, relationships, date table, Power Query data types.
- `powerbi/dax_measures.md`: every KPI as DAX, each with the value it must show, from `outputs/powerbi_expected_values.csv`
  (computed in SQL from the same views; the UAT baseline).
- `powerbi/page_layout.md`: 4 pages + drill-through, visuals mapped to user stories, insight titles with sources,
  slicer plan, one-colour "bad" rule.
- `powerbi/build_steps.md`: click-by-click Power BI Desktop steps for a beginner.
