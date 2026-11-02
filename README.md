# Olist Customer Retention & Delivery Experience Analysis

End-to-end analytics project on the Brazilian e-commerce dataset from Olist (Kaggle `olistbr/brazilian-ecommerce`):
SQL data modelling, pandas analysis, a hypothesis test, Excel, Power BI and BA documentation.
*Work in progress. This README is extended each phase; the full version (ER diagram, findings, screenshots,
limitations) comes in Phase 7.*

## Business questions
1. What % of customers buy again, and what does monthly cohort retention look like?
2. Do late deliveries lower review scores, and by how much?
3. Which sellers, categories and states cause the most delivery delays?
4. Which customer segments (RFM) should marketing target?
5. How concentrated is revenue across categories and states (Pareto)?

BA documents: [`docs/01_BRD.md`](docs/01_BRD.md), [`docs/02_KPI_dictionary.md`](docs/02_KPI_dictionary.md),
[`docs/03_user_stories.md`](docs/03_user_stories.md), [`docs/04_process_map_steps.md`](docs/04_process_map_steps.md).

## How to reproduce
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # exact versions: requirements-lock.txt
cp .env.example .env                                                   # then fill in your MySQL credentials
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
.venv/bin/python src/load_to_mysql.py    # runs sql/01_schema.sql, loads 9 CSVs, writes outputs/row_counts.csv
.venv/bin/python src/run_dq_checks.py    # runs sql/02_data_quality_checks.sql, writes outputs/dq_*.csv
```
Environment used: Python 3.12, MySQL 8.4 LTS (Homebrew `mysql@8.4`; any MySQL 8.0+ works, since window functions are required).

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
| — | Revenue reconciliation | Of 98,665 orders with items and payments, 98,362 match price + freight = payments within 1 cent; payments higher in 264, lower in 39. Totals: price + freight 15,843,409.78 vs payments 15,846,280.17 | `outputs/dq_revenue_reconciliation.csv` |
| — | Value ranges | No zero prices; 383 items with zero freight; 9 zero-value payments; 2 payments with 0 instalments; 3 `not_defined` payment types | `outputs/dq_value_ranges.csv` |
| PM | Process-map step order | 0 approvals before purchase; 0 estimated dates before purchase; **1,359 carrier pick-ups dated before approval**; 23 deliveries before carrier pick-up; 8,849 of 97,657 orders picked up after the seller's shipping limit | `outputs/dq_process_map_timestamps.csv` |
| PM | Survey timing (step 9) | 88,837 of 99,224 surveys created the same or next day after delivery; 5,127 before delivery (4,713 of them on/after the estimated date); 2,865 for orders with no delivered date | `outputs/dq_review_timing.csv` |

## Proposed rules (PROPOSED, not yet applied; awaiting review)
**1. Valid order statuses**
- *Revenue, AOV, repeat customers, cohorts:* `order_status IN ('delivered','shipped','invoiced','processing','approved')`.
  Excludes `canceled` and `unavailable` (no completed sale; most unavailable orders have no items) and `created`
  (5 orders: no approval and no items). Shipped/invoiced/processing orders are real purchases still in progress.
- *Delivery KPIs and the review-vs-delay test:* `order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL`
  (excludes the 8 delivered orders without a date and the 6 canceled orders that have one).

**2. Duplicate reviews**
- *One order, several reviews (547 orders):* keep the review with the latest `review_answer_timestamp`
  (answer times always differ, so this never ties; `review_id` as a tie-breaker anyway). This is the customer's final opinion.
- *One review, several orders (789 reviews):* keep the review on **each** linked order. All of these belong to one
  customer, mostly for orders bought the same day, so it is one survey covering one basket. Delay and review are
  compared at order level, so each order needs its own score.

**3. Analysis date window**
- *Trends and cohorts:* purchases from **2017-01-01 to 2018-08-31** (20 complete months). 2016 is excluded because it
  has only 329 orders and no orders at all in 2016-11 (a gap breaks month-over-month and cohort sequences);
  2018-09 and 2018-10 are excluded because they contain 20 orders and none were delivered.
- *Cohort caveat:* later cohorts have less time to come back (the 2018-08 cohort can only show month 0), so
  retention for month *k* is shown only for cohorts observed for at least *k* months.
- *Delivery caveat:* recent months still have undelivered orders (e.g. 70 in progress in 2018-08), so their
  on-time rates are based only on orders already delivered.

**Other proposed handling (Phase 3/4):** products with no category → `'unknown'`; add English names for the 2
untranslated categories; drop the 42 out-of-Brazil geolocation rows, then average lat/lng per zip before joining.
