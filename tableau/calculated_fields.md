# Tableau calculated fields
Every KPI from `powerbi/dax_measures.md`, rewritten for Tableau. Create each one with **Analysis → Create Calculated
Field…** in the **`Olist`** data source (static-table fields say which data source to use). Money is **R$ (BRL)**.

**Check your build:** the **Expected** value comes from `outputs/powerbi_expected_values.csv` (computed in SQL from the
same views) unless another file is named. With **no filters**, a text table showing the field must match to the
decimals shown. This is the UAT baseline (`docs/05_UAT_checklist.md`).

**Field names:** formulas use the CSV column names. If the Data pane shows `Order Id` instead of `order_id`, type it
that way. Columns present in two tables carry a suffix on the second copy, e.g. `[order_id (fact_order_items)]`
(`tableau/data_model.md` §4).

**Number formats** (right-click the field → *Default Properties → Number Format…*):
R$ → *Currency (Custom)*, prefix `R$ `, 2 decimals · % → *Percentage*, 2 decimals · stars/days → *Number (Custom)*, 2 decimals.

**Three Tableau ideas used below:**
- **FIXED** LOD `{FIXED : …}` is calculated **before** normal filters, so it does not change when you filter (the
  equivalent of DAX `REMOVEFILTERS`).
- **INCLUDE** LOD `{INCLUDE [field] : …}` calculates at a finer level (e.g. per customer) **after** filters, then the
  outer aggregation rolls it up.
- **Table calculations** (`LOOKUP`, `RUNNING_SUM`, `TOTAL`) work on the numbers already in the view; set
  *Compute Using* as stated.

---

## 1. Revenue
| Field | Formula | What it does | Expected |
|---|---|---|---|
| Total Revenue (R$) | `SUM([order_revenue])` | Product revenue of valid orders, excluding freight | **R$ 13,449,529.68** |
| Orders | `COUNTD([order_id])` | Number of valid orders | **97,905** |
| AOV (R$) | `[Total Revenue (R$)] / [Orders]` | Average product value per order | **R$ 137.37** |
| Revenue MoM % | `(SUM([order_revenue]) - LOOKUP(SUM([order_revenue]), -1)) / LOOKUP(SUM([order_revenue]), -1)` | Change vs the previous month. Table calculation: put `MONTH([date_key])` (continuous or discrete month) on Columns; *Compute Using* → **Table (across)** | **2018-08: −3.32 %; 2017-11: +52.06 %** |
| Item Revenue (R$) | `SUM([price])` | Revenue at item level: use with category or seller | **R$ 13,449,529.68**; health_beauty **R$ 1,251,145.54** (`outputs/revenue_pareto_category.csv`) |
| Category Cumulative Revenue % | `RUNNING_SUM(SUM([price])) / TOTAL(SUM([price]))` | Pareto running share. Sort categories by `Item Revenue (R$)` descending; *Compute Using* → **category_english** | **health_beauty 9.30 %, pet_shop (rank 18) 81.27 %** (`outputs/revenue_pareto_category.csv`) |

## 2. Customers
| Field | Formula | What it does | Expected |
|---|---|---|---|
| Customers | `COUNTD([customer_unique_id])` | Distinct people (never `customer_id`, which is new for every order) | **94,703** |
| Repeat Flag | `{INCLUDE [customer_unique_id] : IIF(COUNTD([order_id]) >= 2, 1, 0)}` | Per person: 1 if they have 2+ valid orders in the filtered period. INCLUDE runs after filters, so a date filter changes it | (helper) |
| Repeat Customer % | `SUM([Repeat Flag]) / [Customers]` | Share of people with 2+ valid orders | **3.03 %** (also `outputs/retention_repeat_customers.csv`) |
| Cohort Retention % *(data source: `retention_cohort_long`)* | `SUM([active_customers]) / SUM([cohort_customers])` | Share of a cohort buying in a given month after the first; one cell = one cohort × `month_offset` | **2017-10 cohort, month 1: 0.71 %** (`outputs/retention_cohort_long.csv`) |

## 3. Delivery
| Field | Formula | What it does | Expected |
|---|---|---|---|
| Delivered Orders | `SUM([in_delivery_scope])` | Orders in delivery scope (delivered, dated, estimate on/before the last purchase date) | **96,201** |
| On-Time Orders | `SUM([is_on_time])` | Delivered on or before the estimated date | 89,670 = 96,201 − 6,531 |
| Late Orders | `SUM([is_late])` | Delivered after the estimated date | **6,531** (`outputs/delivery_kpis_overall.csv`) |
| On-Time % | `SUM([is_on_time]) / SUM([in_delivery_scope])` | Share delivered on time | **93.21 %** |
| Late % | `SUM([is_late]) / SUM([in_delivery_scope])` | Share delivered late (On-Time % + Late % = 100 %) | **6.79 %** |
| Avg Delay (days) | `AVG([delay_days])` | Days after (+) or before (−) the estimate; blank outside delivery scope is ignored | **−11.81** |
| Avg Delivery Days | `AVG([delivery_days])` | Purchase to delivery | **12.48** |
| Platform Late Rate | `{FIXED : SUM([is_late])} / {FIXED : SUM([in_delivery_scope])}` | Whole-platform late rate that **ignores filters** (FIXED with no dimension). Use as `MIN([Platform Late Rate])` inside other aggregates | **6.79 %** at any filter |

## 4. Satisfaction
| Field | Formula | What it does | Expected |
|---|---|---|---|
| Avg Review | `AVG([review_score])` | Average score (1-5) of valid orders with a review, one review per order | **4.12** |
| Avg Review (delivered) | `AVG(IF [in_delivery_scope] = 1 THEN [review_score] END)` | Same, delivered orders only: use next to delivery measures | **4.16** (also `outputs/delivery_kpis_overall.csv`) |

## 5. Sellers
An order with items from two sellers counts once for **each** seller (seller-order pairs), as in the SQL ranking.
Counting distinct `seller|order` keys gives that pair count at **any** level, one seller or many.

| Field | Formula | What it does | Expected |
|---|---|---|---|
| Seller-Order Key | `[seller_id] + "|" + [order_id (fact_order_items)]` | Row-level key of one seller-order pair | (helper) |
| Seller Delivered Orders | `COUNTD(IF [in_delivery_scope (fact_order_items)] = 1 THEN [Seller-Order Key] END)` | Delivered seller-order pairs | top seller **1,772** |
| Seller Late Orders | `COUNTD(IF [is_late (fact_order_items)] = 1 THEN [Seller-Order Key] END)` | Late seller-order pairs | top seller **172**; decile 1 **853** (`outputs/seller_late_rate_by_decile.csv`) |
| Seller Late % | `[Seller Late Orders] / [Seller Delivered Orders]` | Late rate of the sellers in the view | **6.73 %** with `is_ranked_30plus_orders` = 1; top seller **9.71 %** |
| Excess Late Orders | `[Seller Late Orders] - [Seller Delivered Orders] * MIN([Platform Late Rate])` | Late orders above what an average seller of the same size would have. Linear, so the total for a group of sellers is the sum of their excesses | top seller `4a3ca9315b744ce9f8e9374361493884` **51.70**; all sellers with 30+ orders **−45.41** |
| Seller Avg Review | `[Avg Review (delivered)]` with `seller_id` in the view | Relationships count each order once per seller, however many items it has | top seller **3.85** (`outputs/seller_late_rate_ranking.csv`) |
| Seller Avg Delay (days) | `[Avg Delay (days)]` with `seller_id` in the view | Same idea, for delay | top seller **−9.53** |
| Seller Revenue (R$) | `[Item Revenue (R$)]` with `seller_id` in the view | Item revenue of the seller | top seller **R$ 200,326.12** (`excel/seller_scorecard_data.csv`) |
| Share of Seller Late Orders | `[Seller Late Orders] / TOTAL([Seller Late Orders])` | Share of late seller-orders per decile. *Compute Using* → **late_rate_decile** | decile 1 **15.56 %**, decile 3 **23.60 %** (with `is_ranked_30plus_orders` = 1) |

## 6. Segments (RFM)
| Field | Formula | What it does | Expected |
|---|---|---|---|
| Segment Customers | `COUNTD([customer_unique_id (rfm_customer_segments)])` | Customers in a segment (scored once over the whole window) | New - high value **14,737** |
| Segment Revenue (R$) | `SUM([monetary_brl])` | Revenue of the segment | New - high value **R$ 3,953,859.18** (`outputs/rfm_segments.csv`) |
| % of Customers | `[Segment Customers] / TOTAL([Segment Customers])` | *Compute Using* → **segment** | New - high value **15.56 %** |
| % of Revenue | `SUM([monetary_brl]) / TOTAL(SUM([monetary_brl]))` | *Compute Using* → **segment** | New - high value **29.40 %** |

## 7. Colour rule (one "bad" colour)
| Field | Formula | Use |
|---|---|---|
| Late vs Platform | `IF [Late %] > MIN([Platform Late Rate]) THEN "Worse than platform" ELSE "At or better than platform" END` | Drag to **Color**; *Edit Colors*: Worse = **#EB6834** (orange), At or better = **#2A78D6** (blue) |
| Seller Late vs Platform | `IF [Seller Late %] > MIN([Platform Late Rate]) THEN "Worse than platform" ELSE "At or better than platform" END` | Same colours, seller sheets |
| Delay Bucket Group | `IF [delay_bucket_order] >= 3 THEN "Late" ELSE "On time or early" END` | Colour for the review-by-delay chart: Late = orange, other = blue |
| Decile Group | `IF [late_rate_decile] = 1 THEN "Worst 10%" ELSE "Other deciles" END` | Colour for the decile chart: Worst 10% = orange, other = blue |

Orange **#EB6834** is used **only** for "bad" (`powerbi/page_layout.md`, colour rule). Default marks **#2A78D6**,
reference lines and "not significant" bars grey **#B5B4AF**.
