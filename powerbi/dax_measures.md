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
