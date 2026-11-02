# Tableau data model (Tableau Public, Mac)
The dashboard is built in **Tableau Public** from the CSVs in `tableau/data/` (git-ignored; regenerate with
`.venv/bin/python src/export_views.py`, or unzip `tableau_data.zip`). The files are the same star-schema views as the
Power BI design (`powerbi/model_spec.md`) and already apply the project's data rules, so **no cleaning in Tableau**.
Money is **R$ (BRL)**.

## 1. Two kinds of data source
| Data source | Files | Purpose |
|---|---|---|
| **`Olist`** (main, related tables) | `fact_orders`, `fact_order_items`, `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `rfm_customer_segments` | Every KPI that must respond to filters |
| **Static** (one data source per file, no relationships) | `retention_cohort_long`, `distance_vs_delay_bands`, `retention_first_order_late_vs_on_time`, `rfm_segments` | Results computed in SQL/Python over the whole period; they ignore filters on purpose |

## 2. Relationships in the `Olist` data source (the "noodles")
Tableau relationships must form a **tree**: exactly one path between any two tables. So the model differs from the
Power BI design in one way: `fact_order_items` hangs off `fact_orders` (by `order_id`) instead of having its own date
link, and `dim_date` relates to `fact_orders` only.

```
                  dim_date
                     │  purchase_date = date_key
                     │
rfm_customer_   dim_customer ──── fact_orders  (root: first table dragged onto the canvas)
segments ─────  customer_id = customer_id   │
customer_unique_id                          │  order_id = order_id
  = customer_unique_id                fact_order_items
                                       │            │
                         seller_id = seller_id   product_id = product_id
                                       │            │
                                  dim_seller    dim_product
```

| # | Left table | Right table | Join fields (left = right) |
|---|---|---|---|
| T1 | `fact_orders` | `dim_date` | `purchase_date` = `date_key` |
| T2 | `fact_orders` | `dim_customer` | `customer_id` = `customer_id` |
| T3 | `dim_customer` | `rfm_customer_segments` | `customer_unique_id` = `customer_unique_id` |
| T4 | `fact_orders` | `fact_order_items` | `order_id` = `order_id` |
| T5 | `fact_order_items` | `dim_seller` | `seller_id` = `seller_id` |
| T6 | `fact_order_items` | `dim_product` | `product_id` = `product_id` |

**Performance options:** leave the defaults (*Some records match*, *Many*). They are always correct; stricter settings
are only an optimisation and give wrong results if not exactly true (e.g. `dim_date` has days with no orders).

**Why a fact-to-fact link (T4) is safe here:** relationships aggregate every measure at its own table's level of detail
before combining. `SUM([order_revenue])` from `fact_orders` is never multiplied by the number of items, and
`AVG([review_score])` per seller counts each order once, however many items it has. (In Power BI the same link would
need extra care, which is why the Power BI design avoids it.)

**Not in the main data source:** `fact_order_items[customer_id]` and `fact_order_items[purchase_date]` are left
unrelated: they would create a second path (a cycle), which Tableau does not allow. Customer and date filters still reach
item-level measures through `fact_orders` → T4.

## 3. Data types (Data Source tab: click the type icon above each column)
Tableau guesses types from the file. **Check and correct these**, because a wrong guess loses data:

| Type | Fields |
|---|---|
| **String** (Abc) | every ID: `order_id`, `customer_id`, `customer_unique_id`, `seller_id`, `product_id`, `review_id`; every zip: `customer_zip_code_prefix`, `seller_zip_code_prefix` (keeps the leading zero in `06273`); `order_status`, `delay_bucket`, states, cities, categories, `segment`, `month_name`, `year_month_label`, `weekday_name`, `distance_band`, `first_order_delivery`, `suggested_action` |
| **Number (whole)** (#) | flags `in_delivery_scope`, `is_on_time`, `is_late`, `flag_pickup_before_approval`, `is_repeat_customer`, `is_ranked_30plus_orders`, `is_weekend`; counts and scores `item_count`, `review_score`, `delay_days`, `delivery_days`, `delay_bucket_order`, `order_item_id`, `late_rate_rank`, `late_rate_decile`, `person_valid_orders`, RFM `recency_days`, `frequency`, `r_score`, `f_score`, `m_score`, static `cohort_customers`, `month_offset`, `active_customers`, `orders`, `customers`, `returned_within_6m`, `did_not_return` |
| **Number (decimal)** (#) | money `order_revenue`, `order_freight`, `payment_total`, `price`, `freight_value`, `monetary_brl`, `revenue_brl`, `avg_monetary_brl`; `approval_to_pickup_days`; latitudes/longitudes; static percentages `retention_pct`, `late_pct`, `return_within_6m_pct`, `pct_of_customers`, `revenue_share_pct`, `pct_of_orders`, `avg_delivery_days`, `median_distance_km`, `avg_recency_days`, `avg_orders` |
| **Date** (calendar) | `purchase_date`, `delivered_date`, `estimated_date`, `date_key`, `month_start`, `cohort_month` |
| **Date & Time** | `shipping_limit_date` |

**Geographic role** (Data pane → right-click field → *Geographic Role*): `customer_state`, `seller_state` →
*State/Province* (set *Edit Locations → Country* to **Brazil**); latitude/longitude fields → *Latitude* / *Longitude*.

**Dimensions vs measures:** flag and score fields such as `late_rate_decile`, `delay_bucket_order`, `review_score` and
`month_offset` should be **Dimensions** when used on an axis or as a filter (drag them above the line in the Data
pane, or right-click → *Convert to Dimension*). Keep the 0/1 flags as **Measures** so they can be summed.

## 4. Field names you will see
- Tableau may display `order_id` as **Order Id** and `in_delivery_scope` as **In Delivery Scope**. The calculated fields in
  `calculated_fields.md` use the file names in brackets; type them the way the Data pane shows them.
- A column that exists in two tables gets the table name added for the second copy, e.g.
  **`order_id (fact_order_items)`**, **`is_late (fact_order_items)`**, **`review_score (fact_order_items)`**. Unless a
  formula says `(fact_order_items)`, use the `fact_orders` (or dimension) version.

## 5. Checks after connecting
- Each table has a hidden count field: drag **`fact_orders (Count)`** to a sheet and expect **97,905**;
  `fact_order_items (Count)` **111,752**; `dim_date (Count)` **730**; `rfm_customer_segments (Count)` **94,703**
  (`outputs/powerbi_views_checks.csv`, `outputs/rfm_segments.csv`).
- Zip prefixes: show `customer_zip_code_prefix` in a sheet sorted ascending; the first value starts with **0**.
