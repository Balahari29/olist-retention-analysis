# DAX measures
Create all measures in one empty table named **`_Measures`** (build_steps.md, Step 6), each in the display folder shown.
Definitions follow `docs/02_KPI_dictionary.md`; money is **R$ (BRL)**.

**Check your build:** the **Expected value** column comes from `outputs/powerbi_expected_values.csv` (computed in SQL
from the same views Power BI loads) unless another file is named. With **no slicers applied**, a card showing the
measure must match to the decimals shown. This is the UAT baseline for Phase 7.

## Format strings
| Kind | Format string (Measure tools → Format → Custom) |
|---|---|
| R$ | `"R$" #,0.00` |
| R$ millions (cards) | `"R$" #,0.00,,"M"` |
| Percentage | `0.00%` |
| Stars / days | `0.00` |

---

## 1. Revenue (folder: Revenue)
```dax
Total Revenue (R$) = SUM ( fact_orders[order_revenue] )
```
Product revenue of valid orders, excluding freight (KPI dictionary). **Expected: R$ 13,449,529.68**

```dax
Orders = COUNTROWS ( fact_orders )
```
Number of valid orders. **Expected: 97,905**

```dax
AOV (R$) = DIVIDE ( [Total Revenue (R$)], [Orders] )
```
Average product value per valid order. **Expected: R$ 137.37**

```dax
Previous Month Revenue (R$) =
CALCULATE ( [Total Revenue (R$)], DATEADD ( dim_date[date_key], -1, MONTH ) )

Revenue MoM % =
VAR CurrentRevenue  = [Total Revenue (R$)]
VAR PreviousRevenue = [Previous Month Revenue (R$)]
RETURN
    IF ( NOT ISBLANK ( PreviousRevenue ), DIVIDE ( CurrentRevenue - PreviousRevenue, PreviousRevenue ) )
```
Change vs the previous calendar month; needs a month in context (e.g. `dim_date[year_month_label]` on the axis).
Blank for the first month. **Expected: 2018-08 → −3.32 %; 2017-11 → +52.06 %** (also `outputs/revenue_mom.csv`)

## 2. Customers (folder: Customers)
```dax
Customers =
CALCULATE ( DISTINCTCOUNT ( dim_customer[customer_unique_id] ), fact_orders )
```
Distinct people (`customer_unique_id`, never `customer_id`) with a valid order in the current filter context. The
`fact_orders` filter argument limits the count to customers who actually have orders under the current slicers.
**Expected: 94,703**

```dax
Repeat Customer % =
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
VAR CustomersWithOrders = COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 1 ) )
VAR RepeatCustomers     = COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 2 ) )
RETURN
    DIVIDE ( RepeatCustomers, CustomersWithOrders )
```
Share of people with 2+ valid orders **inside the selected period** (KPI dictionary). `CALCULATE` turns each
`customer_unique_id` into a filter, so all of that person's `customer_id`s (one per order) are counted together.
**Expected: 3.03 %** (also `outputs/retention_repeat_customers.csv`)

```dax
Cohort Retention % = DIVIDE ( SUM ( retention_cohort_long[active_customers] ),
                              SUM ( retention_cohort_long[cohort_customers] ) )
```
For the cohort matrix (static table). In a cell of cohort × `month_offset` it returns that cohort's retention.
**Expected: 2017-10 cohort, month 1 → 0.71 %** (`outputs/retention_cohort_long.csv`)

## 3. Delivery (folder: Delivery)
```dax
Delivered Orders = CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[in_delivery_scope] = 1 )
```
Orders in delivery scope: delivered, with a date, estimated date on or before the last purchase date (Rule 3).
**Expected: 96,201**

```dax
On-Time Orders = CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_on_time] = 1 )
Late Orders    = CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_late] = 1 )
```
Counts of delivered orders arriving on/before vs after the estimated date. **Expected: Late Orders 6,531**

```dax
On-Time % = DIVIDE ( [On-Time Orders], [Delivered Orders] )
```
Share of delivered orders on or before the estimated date. **Expected: 93.21 %**

```dax
Late % = DIVIDE ( [Late Orders], [Delivered Orders] )
```
Share of delivered orders after the estimated date; On-Time % + Late % = 100 %. **Expected: 6.79 %**

```dax
Avg Delay (days) = AVERAGE ( fact_orders[delay_days] )
```
Average days delivered after (+) or before (−) the estimate; blank for orders outside delivery scope, which
`AVERAGE` ignores. **Expected: −11.81**

```dax
Avg Delivery Days = AVERAGE ( fact_orders[delivery_days] )
```
Purchase to delivery, in days. **Expected: 12.48**

```dax
Platform Late Rate = CALCULATE ( [Late %], REMOVEFILTERS () )
```
Late % of the whole platform, ignoring every slicer: the benchmark for "excess" and for colour rules.
**Expected: 6.79 %** at any filter.

## 4. Satisfaction (folder: Satisfaction)
```dax
Avg Review = AVERAGE ( fact_orders[review_score] )
```
Average score (1-5) of valid orders with a review, one review per order (Rule 2). Includes orders not yet delivered.
**Expected: 4.12**

```dax
Avg Review (delivered) =
CALCULATE ( AVERAGE ( fact_orders[review_score] ), fact_orders[in_delivery_scope] = 1 )
```
Same, delivered orders only: use this next to delivery measures. **Expected: 4.16** (also `outputs/delivery_kpis_overall.csv`)

## 5. Sellers (folder: Sellers), on `fact_order_items`
An order with items from two sellers counts once for each seller (seller-order pairs), as in the SQL ranking.
```dax
Seller Delivered Orders =
CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[in_delivery_scope] = 1 )

Seller Late Orders =
CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[is_late] = 1 )

Seller Late % = DIVIDE ( [Seller Late Orders], [Seller Delivered Orders] )
```
Late rate of the sellers in context. **Expected with `dim_seller[is_ranked_30plus_orders] = 1`: 6.73 %**
(also `outputs/seller_scorecard_totals.csv`)

```dax
Excess Late Orders =
SUMX (
    VALUES ( dim_seller[seller_id] ),
    [Seller Late Orders] - [Seller Delivered Orders] * [Platform Late Rate]
)
```
Late orders above what an average seller of the same size would have; summed seller by seller.
**Expected: top seller `4a3ca9315b744ce9f8e9374361493884` → 51.70; all sellers with 30+ orders → −45.41**

```dax
Seller Avg Review =
AVERAGEX (
    SUMMARIZE (
        FILTER ( fact_order_items, fact_order_items[in_delivery_scope] = 1 ),
        fact_order_items[order_id], fact_order_items[review_score]
    ),
    fact_order_items[review_score]
)
```
One score per order (an order's score is repeated on each of its items, so it is de-duplicated first).
**Expected: top seller → 3.85** (`outputs/seller_late_rate_ranking.csv`)

```dax
Seller Avg Delay (days) =
AVERAGEX (
    SUMMARIZE (
        FILTER ( fact_order_items, fact_order_items[in_delivery_scope] = 1 ),
        fact_order_items[order_id], fact_order_items[delay_days]
    ),
    fact_order_items[delay_days]
)
```
**Expected: top seller → −9.53**

```dax
Seller Revenue (R$) = SUM ( fact_order_items[price] )
```
Item revenue of the sellers in context. **Expected: top seller → R$ 200,326.12** (`excel/seller_scorecard_data.csv`);
no filter → R$ 13,449,529.68 (same as Total Revenue).

## 6. Segments (folder: Segments), on `rfm_customer_segments`
```dax
Segment Customers = COUNTROWS ( rfm_customer_segments )

Segment Revenue (R$) = SUM ( rfm_customer_segments[monetary_brl] )

% of Customers =
DIVIDE ( [Segment Customers], CALCULATE ( [Segment Customers], REMOVEFILTERS ( rfm_customer_segments[segment] ) ) )

% of Revenue =
DIVIDE ( [Segment Revenue (R$)], CALCULATE ( [Segment Revenue (R$)], REMOVEFILTERS ( rfm_customer_segments[segment] ) ) )
```
Size and value of each RFM segment (scored once over the whole window). **Expected: New - high value → 14,737
customers, 15.56 % of customers, 29.40 % of revenue** (`outputs/rfm_segments.csv`)

## 7. Colour rule (folder: Formatting)
```dax
Colour - Late vs Platform =
IF ( [Late %] > [Platform Late Rate], "#EB6834", "#2A78D6" )

Colour - Seller Late vs Platform =
IF ( [Seller Late %] > [Platform Late Rate], "#EB6834", "#2A78D6" )
```
Returns the **one "bad" colour** (orange) when worse than the platform, otherwise the default blue. Used via
*Format → Bars → Colors → fx → Format style: Field value* (build_steps.md, Step 9).

## 8. Helper measures used by `page_layout.md`
```dax
Item Revenue (R$) = SUM ( fact_order_items[price] )
```
Revenue at item level: use it with `dim_product` or `dim_seller` (they filter `fact_order_items`, not `fact_orders`).
**Expected: no filter → R$ 13,449,529.68; category health_beauty → R$ 1,251,145.54** (`outputs/revenue_pareto_category.csv`)

```dax
Category Cumulative Revenue % =
VAR CurrentRevenue = [Item Revenue (R$)]
VAR AllCategories  = ALLSELECTED ( dim_product[category_english] )
VAR CategoriesAtOrAbove =
    FILTER ( AllCategories, [Item Revenue (R$)] >= CurrentRevenue )
RETURN
    DIVIDE ( SUMX ( CategoriesAtOrAbove, [Item Revenue (R$)] ),
             SUMX ( AllCategories, [Item Revenue (R$)] ) )
```
Running share of revenue, highest category first (Pareto). **Expected: health_beauty 9.30 %, watches_gifts 18.19 %,
rank 17 computers 79.68 %, rank 18 pet_shop 81.27 % (the category that crosses 80 %)** (`outputs/revenue_pareto_category.csv`)

```dax
Late Orders (seller sum) = SUMX ( VALUES ( dim_seller[seller_id] ), [Seller Late Orders] )
Delivered Orders (seller sum) = SUMX ( VALUES ( dim_seller[seller_id] ), [Seller Delivered Orders] )
Share of Seller Late Orders =
DIVIDE ( [Late Orders (seller sum)],
         CALCULATE ( [Late Orders (seller sum)], REMOVEFILTERS ( dim_seller[late_rate_decile] ) ) )
```
Adds up seller by seller, so an order shared by two sellers counts once for each (as in the SQL decile table).
**Expected with `is_ranked_30plus_orders = 1`: decile 1 → 853 late orders, 15.56 % share; decile 3 → 1,294, 23.60 %**
(`outputs/seller_late_rate_by_decile.csv`)

```dax
Seller Detail Title =
"Seller " & SELECTEDVALUE ( dim_seller[seller_id], "(select one seller)" )
    & "  |  " & SELECTEDVALUE ( dim_seller[seller_city] ) & " - " & SELECTEDVALUE ( dim_seller[seller_state] )
```
Dynamic title for the drill-through page.

---

## 9. Additions for the 5-page Power BI Project (PBIP) build
Added for the 5-page report connected **directly to MySQL** (six views only, no CSVs, no RFM table). Sections 1-8 are
unchanged and reused as-is. Every addition is built from an existing measure or an existing SQL column, so no
business definition changes. Expected values come from the `outputs/` file named.

**Not loaded in this build:** section 6 (*Segments*, needs `rfm_customer_segments`) and the static-table measure
`Cohort Retention %` in section 2 (needs `retention_cohort_long`). The live cohort measures in 9.2 replace the latter.

### 9.1 Revenue (folder: Revenue)
```dax
Item Orders = DISTINCTCOUNT ( fact_order_items[order_id] )
```
Orders with at least one item in the current context (category, seller). **Distinct**, because an order with three
items has three rows in `fact_order_items`. **Expected: health_beauty → 8,757** (`revenue_pareto_category.csv`)

```dax
Revenue Change vs Previous Month (R$) =
VAR PreviousRevenue = [Previous Month Revenue (R$)]
RETURN
    IF ( NOT ISBLANK ( PreviousRevenue ), [Total Revenue (R$)] - PreviousRevenue )
```
**Expected: 2017-02 → R$ 124,861.08** (`revenue_mom.csv`)

```dax
Category Revenue Share % =
DIVIDE ( [Item Revenue (R$)], CALCULATE ( [Item Revenue (R$)], ALLSELECTED ( dim_product[category_english] ) ) )

Category Revenue Rank =
IF (
    ISINSCOPE ( dim_product[category_english] ),
    RANKX ( ALLSELECTED ( dim_product[category_english] ), [Item Revenue (R$)], , DESC )
)

Categories for 80% Revenue =
COUNTROWS (
    FILTER ( ALLSELECTED ( dim_product[category_english] ), [Category Cumulative Revenue %] < 0.8 )
) + 1
```
**Expected: health_beauty → 9.30 %, rank 1; categories for 80 % → 18 of 74** (`revenue_pareto_category.csv`,
`revenue_pareto_summary.csv`). "+ 1" adds the category that crosses 80 % (pet_shop, 81.27 %).

```dax
State Revenue Share % =
DIVIDE ( [Total Revenue (R$)], CALCULATE ( [Total Revenue (R$)], ALLSELECTED ( dim_customer[customer_state] ) ) )

State Cumulative Revenue % =
VAR CurrentRevenue = [Total Revenue (R$)]
VAR AllStates      = ALLSELECTED ( dim_customer[customer_state] )
VAR StatesAtOrAbove = FILTER ( AllStates, [Total Revenue (R$)] >= CurrentRevenue )
RETURN
    DIVIDE ( SUMX ( StatesAtOrAbove, [Total Revenue (R$)] ), SUMX ( AllStates, [Total Revenue (R$)] ) )

States for 80% Revenue =
COUNTROWS ( FILTER ( ALLSELECTED ( dim_customer[customer_state] ), [State Cumulative Revenue %] < 0.8 ) ) + 1
```
Same Pareto logic as `Category Cumulative Revenue %`, on order revenue by customer state.
**Expected: SP → 38.30 % share, 38.30 % cumulative; states for 80 % → 7 of 27** (`revenue_pareto_state.csv`)

AOV trend: use the existing `[AOV (R$)]` with `dim_date[year_month_label]` on the axis.
**Expected: 2017-01 → R$ 152.60** (`revenue_mom.csv`)

### 9.2 Customers and retention (folders: Customers, Customers\Cohort)
```dax
Repeat Customers =
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
RETURN
    COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 2 ) )

One-time Customers =
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
RETURN
    COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] = 1 ) )
```
The numerator logic of the existing `Repeat Customer %`, split out. Counted **inside the selected period**, per person
(`customer_unique_id`). **Expected: 2,874 repeat, 91,829 one-time** (`retention_repeat_customers.csv`,
`retention_orders_per_customer.csv`); Repeat + One-time = Customers (94,703).

```dax
Orders per Customer = DIVIDE ( [Orders], [Customers] )
```
**Expected: 97,905 / 94,703 = 1.0338**

**Customer segmentation (calculated columns on `dim_customer`, built from the SQL columns, no new rule):**
```dax
Customer Type = IF ( dim_customer[is_repeat_customer] = 1, "Repeat", "One-time" )

Order Count Band =
SWITCH ( TRUE (),
    dim_customer[person_valid_orders] = 1, "1 order",
    dim_customer[person_valid_orders] = 2, "2 orders",
    dim_customer[person_valid_orders] = 3, "3 orders",
    "4+ orders" )

Order Count Band Sort = MIN ( dim_customer[person_valid_orders], 4 )
```
These describe the person over the **whole window** (2017-01 to 2018-08), as the SQL columns do; the date slicer changes
the customer counts in the chart, not a person's band. Sort `Order Count Band` by `Order Count Band Sort`.
**Expected with `[Customers]`: 1 order → 91,829; 2 → 2,639; 3 → 187; 4+ → 48** (`retention_orders_per_customer.csv`)

**Cohort retention (live, replaces the static `retention_cohort_long` table).** A small disconnected table supplies
the month offsets for the matrix columns:
```dax
Cohort Month Offset = SELECTCOLUMNS ( GENERATESERIES ( 0, 19, 1 ), "month_offset", [Value] )
```
```dax
Cohort Customers = DISTINCTCOUNT ( dim_customer[customer_unique_id] )

Cohort Active Customers =
VAR CohortStart    = SELECTEDVALUE ( dim_customer[cohort_month] )
VAR MonthOffset    = SELECTEDVALUE ( 'Cohort Month Offset'[month_offset] )
VAR TargetMonth    = EDATE ( CohortStart, MonthOffset )
VAR LastOrderDate  = CALCULATE ( MAX ( fact_orders[purchase_date] ), REMOVEFILTERS () )
VAR LastDataMonth  = DATE ( YEAR ( LastOrderDate ), MONTH ( LastOrderDate ), 1 )
RETURN
    IF (
        NOT ISBLANK ( CohortStart ) && NOT ISBLANK ( MonthOffset ) && TargetMonth <= LastDataMonth,
        CALCULATE ( [Customers], REMOVEFILTERS ( dim_date ), dim_date[month_start] = TargetMonth ) + 0
    )

Cohort Retention % (live) =
VAR ActiveCustomers = [Cohort Active Customers]
RETURN
    IF ( NOT ISBLANK ( ActiveCustomers ), DIVIDE ( ActiveCustomers, [Cohort Customers] ) )
```
Matrix: rows `dim_customer[cohort_month]`, columns `'Cohort Month Offset'[month_offset]`. Same rules as
`sql/03_analysis_retention.sql`: cohort = month of the person's first valid order, offset 0 = 100 %, months not yet
observable are blank (equal-window rule), observed months with no buyers show 0. Ignores the date slicer (cohorts are
defined over the whole window). **Expected: 2017-01 cohort → 753 customers, offset 1 → 3 (0.40 %); 2017-10, offset 1 →
0.71 %** (`retention_cohort_long.csv`, 210 cells)

### 9.3 Delivery (folder: Delivery)
```dax
Late % vs Platform (pp) = [Late %] - [Platform Late Rate]
```
Percentage points above (+) or below (−) the platform late rate; tooltip for the state and month charts.
**Expected: AL → 21.46 % − 6.79 % = +14.67 pp** (`delivery_ontime_by_state.csv`)

Delay-bucket analysis and review vs delay use the existing measures on the SQL column `fact_orders[delay_bucket]`
(sort by `delay_bucket_order`): `[Delivered Orders]`, `[Avg Review (delivered)]`.
**Expected: Early → 88,379 orders, 4.29 stars; 7+ days late → 2,860 orders, 1.70 stars** (`delivery_buckets_vs_review.csv`)

### 9.4 Sellers (folders: Sellers, Sellers\Helpers), on `fact_order_items`
```dax
Total Sellers = DISTINCTCOUNT ( fact_order_items[seller_id] )

Ranked Sellers = CALCULATE ( [Total Sellers], dim_seller[is_ranked_30plus_orders] = 1 )
```
Sellers with at least one item in context; ranked = 30+ delivered orders (SQL threshold).
**Expected: 3,029 sellers; 625 ranked** (`powerbi_views_checks.csv`, `seller_scorecard_totals.csv`)

```dax
Seller Late % (pairs) = DIVIDE ( [Late Orders (seller sum)], [Delivered Orders (seller sum)] )
```
Exactly the SQL definition: **seller-order pairs**, so an order shipped by two sellers counts once for each.
The existing `Seller Late %` uses `DISTINCTCOUNT ( order_id )` over the whole selection, so with several sellers in
context a shared order counts **once**. For one seller the two are identical; across many sellers they can differ.
**Expected with `is_ranked_30plus_orders = 1`: 6.7331 % (5,483 / 81,433 pairs)** (`seller_scorecard_totals.csv`).

**Stage 3 logic check (`src/validate_dax_logic.py` → `outputs/dax_logic_validation.csv`, a pandas emulation of
each measure on the MySQL views; Power BI itself is checked in Stage 5):** across all 625 ranked sellers,
`Seller Late % (pairs)` = **6.7331 %** (81,433 pairs) and matches SQL; the existing `Seller Late %` gives **6.7937 %**
(80,530 distinct orders, because 903 delivered orders were shipped by two or more ranked sellers) and does **not**.
For a single seller both give the same value (top seller 9.71 %). So: use `Seller Late % (pairs)` and
`Delivered Orders (seller sum)` on KPI cards and any visual that groups several sellers (state, decile, category);
the existing measures stay correct inside one-seller rows and the drill-through page.

**Rounding note:** `seller_late_rate_by_decile.csv` sums per-seller excess values that SQL has already rounded to
2 decimals, so its decile totals can differ from `[Excess Late Orders]` (which sums unrounded values) by up to
**0.04** (63 sellers × ±0.005). Same definition, different rounding; compare deciles to ±0.05.

```dax
Seller Late Rate Rank = SELECTEDVALUE ( dim_seller[late_rate_rank] )

Excess Late Rank =
IF (
    ISINSCOPE ( dim_seller[seller_id] ),
    RANKX ( ALLSELECTED ( dim_seller[seller_id] ), [Excess Late Orders], , DESC )
)
```
`Seller Late Rate Rank` shows the SQL ranking (whole period, ranked sellers only; blank otherwise).
`Excess Late Rank` ranks the sellers in the visual by the existing `[Excess Late Orders]`.
**Expected: seller `4a3ca9315b744ce9f8e9374361493884` → late-rate rank 135, excess rank 1** (`excel/seller_scorecard_data.csv`)

Decile chart: `dim_seller[late_rate_decile]` with the existing `[Share of Seller Late Orders]`, `[Seller Late % (pairs)]`
and `[Excess Late Orders]`. **Expected: decile 1 → 853 late orders, 15.56 % share, 496.70 excess**
(`seller_late_rate_by_decile.csv`)

### 9.5 Display folders (all measures in `_Measures`)
| Folder | Measures |
|---|---|
| Revenue | Total Revenue (R$), Orders, AOV (R$), Previous Month Revenue (R$), Revenue MoM %, Revenue Change vs Previous Month (R$), Item Revenue (R$), Item Orders |
| Revenue\Pareto | Category Revenue Share %, Category Revenue Rank, Category Cumulative Revenue %, Categories for 80% Revenue, State Revenue Share %, State Cumulative Revenue %, States for 80% Revenue |
| Customers | Customers, Repeat Customers, One-time Customers, Repeat Customer %, Orders per Customer |
| Customers\Cohort | Cohort Customers, Cohort Active Customers, Cohort Retention % (live) |
| Delivery | Delivered Orders, On-Time Orders, Late Orders, On-Time %, Late %, Avg Delay (days), Avg Delivery Days, Platform Late Rate, Late % vs Platform (pp) |
| Satisfaction | Avg Review, Avg Review (delivered) |
| Sellers | Total Sellers, Ranked Sellers, Seller Delivered Orders, Seller Late Orders, Seller Late %, Seller Late % (pairs), Excess Late Orders, Seller Late Rate Rank, Excess Late Rank, Seller Avg Review, Seller Avg Delay (days), Seller Revenue (R$), Share of Seller Late Orders, Seller Detail Title |
| Sellers\Helpers | Late Orders (seller sum), Delivered Orders (seller sum) |
| Formatting | Colour - Late vs Platform, Colour - Seller Late vs Platform |

### 9.6 Format strings for the additions
| Measure | Format |
|---|---|
| Revenue Change vs Previous Month (R$) | `"R$" #,0.00` |
| Item Orders, Repeat Customers, One-time Customers, Cohort Customers, Cohort Active Customers, Total Sellers, Ranked Sellers, Categories/States for 80% Revenue, ranks | `#,0` |
| Orders per Customer | `0.0000` |
| Category/State Revenue Share %, Category/State Cumulative Revenue %, Cohort Retention % (live), Seller Late % (pairs) | `0.00%` |
| Late % vs Platform (pp) | `+0.00%;-0.00%;0.00%` (shown as points, e.g. +14.67%) |
