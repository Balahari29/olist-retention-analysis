# Power BI model specification
**Source:** CSV files in `powerbi/data/`, exported from the MySQL views in `sql/06_views_for_powerbi.sql` (plus the RFM
table written by `notebooks/analysis.ipynb`) by `src/export_views.py`. All money is **R$ (BRL)**.
The views apply the accepted data rules (README "Data rules"), so **no cleaning is done in Power BI**: Power Query only
sets data types.

## 1. Star schema at a glance
```
                         rfm_customer_segments
                                   │ 1
                                   │ (customer_unique_id)
                                   ▼ *
  dim_date ──1───*──▶ fact_orders ◀──*───1── dim_customer
     │ 1                (one row per valid order)
     │
     └──────*──▶ fact_order_items ◀──*───1── dim_seller
                 (one row per item) ◀──*───1── dim_product

  Static tables, no relationships: retention_cohort_long, distance_vs_delay_bands,
  retention_first_order_late_vs_on_time, rfm_segment_summary   (from outputs/; whole period, not filtered by slicers)
```

## 2. Tables
| Table | File | Grain (one row per …) | Key | Rows |
|---|---|---|---|---|
| `fact_orders` | `powerbi/data/fact_orders.csv` | valid order (Rule 1, window 2017-01 to 2018-08) | `order_id` | 97,905 |
| `fact_order_items` | `powerbi/data/fact_order_items.csv` | item of a valid order | `order_id` + `order_item_id` | 111,752 |
| `dim_customer` | `powerbi/data/dim_customer.csv` | `customer_id` (1:1 with orders; `customer_unique_id` = the person) | `customer_id` | 97,905 |
| `dim_seller` | `powerbi/data/dim_seller.csv` | seller with at least one item in a valid order | `seller_id` | 3,029 |
| `dim_product` | `powerbi/data/dim_product.csv` | product | `product_id` | 32,951 |
| `dim_date` | `powerbi/data/dim_date.csv` | calendar day, 2017-01-01 to 2018-12-31 | `date_key` | 730 |
| `rfm_customer_segments` | `powerbi/data/rfm_customer_segments.csv` | person (`customer_unique_id`) | `customer_unique_id` | 94,703 |
| `retention_cohort_long` | `outputs/retention_cohort_long.csv` | cohort month × months since first purchase | (none) | 210 |
| `distance_vs_delay_bands` | `outputs/distance_vs_delay_bands.csv` | distance band (km) | (none) | 6 |
| `retention_first_order_late_vs_on_time` | `outputs/retention_first_order_late_vs_on_time.csv` | first-order delivery group | (none) | 3 |
| `rfm_segment_summary` | `outputs/rfm_segments.csv` | RFM segment (with suggested action) | (none) | 8 |

Row counts: `outputs/powerbi_views_checks.csv` and the export log. Check them in Power BI with a card showing `COUNTROWS(table)`.

## 3. Data types to set in Power Query
**Rule for every table:** turn **off** automatic type detection (build_steps.md, Step 2) and set types by hand.
IDs and zip prefixes are **Text**: a zip such as `06273` loses its leading zero as a number, and a hex ID made of
digits plus one `e` can be misread as scientific notation. 0/1 flags stay **Whole Number** so they can be summed.
Empty cells load as `null` (blank), which is intended (e.g. delivery columns of orders outside delivery scope).

| Table | Text | Whole Number | Decimal Number | Date | Date/Time |
|---|---|---|---|---|---|
| `fact_orders` | order_id, customer_id, order_status, delay_bucket, review_id | item_count, in_delivery_scope, delay_days, delay_bucket_order, is_on_time, is_late, delivery_days, flag_pickup_before_approval, review_score | order_revenue, order_freight, payment_total, approval_to_pickup_days | purchase_date, delivered_date, estimated_date | – |
| `fact_order_items` | order_id, product_id, seller_id, customer_id | order_item_id, in_delivery_scope, is_late, delay_days, review_score | price, freight_value | purchase_date | shipping_limit_date |
| `dim_customer` | customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state | person_valid_orders, is_repeat_customer | customer_latitude, customer_longitude | cohort_month | – |
| `dim_seller` | seller_id, seller_zip_code_prefix, seller_city, seller_state | late_rate_rank, late_rate_decile, is_ranked_30plus_orders | seller_latitude, seller_longitude | – | – |
| `dim_product` | product_id, category_portuguese, category_english | product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm | – | – | – |
| `dim_date` | month_name, year_month_label, weekday_name | year_number, quarter_number, month_number, weekday_number, is_weekend | – | date_key, month_start | – |
| `rfm_customer_segments` | customer_unique_id, segment | recency_days, frequency, r_score, f_score, m_score | monetary_brl | – | – |
| `retention_cohort_long` | – | cohort_customers, month_offset, active_customers | retention_pct | cohort_month | – |
| `distance_vs_delay_bands` | distance_band | orders | late_pct, avg_delivery_days, median_distance_km, pct_of_orders | – | – |
| `retention_first_order_late_vs_on_time` | first_order_delivery | customers, returned_within_6m, did_not_return | return_within_6m_pct | – | – |
| `rfm_segment_summary` | segment, suggested_action | customers | pct_of_customers, revenue_brl, revenue_share_pct, avg_recency_days, avg_orders, avg_monetary_brl | – | – |

**Data Category** (Column tools → Data category): `customer_state` and `seller_state` → *State or Province*;
latitude/longitude columns → *Latitude* / *Longitude*.

## 4. Relationships
Create them by hand (turn off "Autodetect new relationships", build_steps.md Step 1).

| # | From (many side) | To (one side) | Cardinality | Cross-filter direction | Active |
|---|---|---|---|---|---|
| R1 | `fact_orders[purchase_date]` | `dim_date[date_key]` | Many to one (*:1) | Single | Yes |
| R2 | `fact_orders[customer_id]` | `dim_customer[customer_id]` | Many to one (*:1) | Single | Yes |
| R3 | `dim_customer[customer_unique_id]` | `rfm_customer_segments[customer_unique_id]` | Many to one (*:1) | Single | Yes |
| R4 | `fact_order_items[purchase_date]` | `dim_date[date_key]` | Many to one (*:1) | Single | Yes |
| R5 | `fact_order_items[seller_id]` | `dim_seller[seller_id]` | Many to one (*:1) | Single | Yes |
| R6 | `fact_order_items[product_id]` | `dim_product[product_id]` | Many to one (*:1) | Single | Yes |
| R7 (optional) | `fact_orders[delivered_date]` | `dim_date[date_key]` | Many to one (*:1) | Single | **No** (use with `USERELATIONSHIP` for "by delivery date" analysis) |

**About R2:** each order has its own `customer_id`, so both columns are unique and Power BI may propose **One to one**.
Change it to **Many to one** with **Single** direction. If Power BI does not allow that, keep One to one: it is safe
here *because* of the next rule.

**Deliberately NOT related (and why):**
- `fact_order_items[customer_id]` → `dim_customer`: with R1, R2 and R4 it would create two filter paths from
  `dim_date` to `fact_order_items`, and Power BI would deactivate one without telling you. Customer filters belong on
  pages built on `fact_orders`.
- `fact_orders` ↔ `fact_order_items`: no fact-to-fact joins. The order-level delivery and review columns are already
  copied onto each item (`in_delivery_scope`, `is_late`, `delay_days`, `review_score`).
- Static tables (`retention_cohort_long`, `distance_vs_delay_bands`, `retention_first_order_late_vs_on_time`, `rfm_segment_summary`): their
  numbers come from SQL/Python over the whole period; slicers must not change them. Their visuals say so in the subtitle.
- `rfm_customer_segments` has no date relationship: segments are scored once over the whole window (reference date 2018-08-30).

## 5. Date table
- Select `dim_date` → **Table tools → Mark as date table** → date column **`date_key`**.
- **Sort by column:** `month_name` by `month_number`; `year_month_label` by `month_start`; `weekday_name` by `weekday_number`.
- Turn off **Auto date/time** (build_steps.md Step 1); `dim_date` replaces the hidden automatic date tables.
- Use `dim_date` columns (not `fact_orders[purchase_date]`) on every axis and slicer, so time intelligence (`DATEADD`) works.

## 6. Hide from report view
Hide (right-click → *Hide in report view*) the key columns on the many side (`fact_orders[customer_id]`,
`fact_orders[purchase_date]`, `fact_order_items[seller_id]`, `[product_id]`, `[purchase_date]`, `[customer_id]`,
`dim_customer[customer_unique_id]` is kept visible for counting), and the raw flag columns once the measures exist,
so report builders use measures instead of summing columns by accident.
