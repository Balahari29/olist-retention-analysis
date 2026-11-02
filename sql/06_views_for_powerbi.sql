-- =====================================================================================
-- 06_views_for_powerbi.sql : star schema for Power BI (Phase 6 builds the model on these)
--   facts:      fact_orders (1 row per valid order), fact_order_items (1 row per item of a valid order)
--   dimensions: dim_customer, dim_seller, dim_product, dim_date
-- All views read from the clean layer, so Power BI uses the same rules as the SQL analysis.
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- dim_date: one row per day, whole calendar years from 1 Jan of the first purchase year to 31 Dec of the
-- last delivered/estimated year (Power BI time intelligence expects complete years).
-- Recursive CTE: 730 days, below MySQL's default recursion limit of 1000.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_date AS
WITH RECURSIVE calendar AS (
    SELECT bounds.first_date AS date_key, bounds.last_date
    FROM (SELECT MAKEDATE(YEAR(MIN(purchase_date)), 1) AS first_date,
                 MAKEDATE(YEAR(GREATEST(MAX(DATE(order_delivered_customer_date)),
                                        MAX(DATE(order_estimated_delivery_date)))) + 1, 1) - INTERVAL 1 DAY AS last_date
            FROM v_orders_valid) AS bounds
    UNION ALL
    SELECT date_key + INTERVAL 1 DAY, last_date
    FROM calendar
    WHERE date_key < last_date
)
SELECT
    date_key,
    YEAR(date_key)                                      AS year_number,
    QUARTER(date_key)                                   AS quarter_number,
    MONTH(date_key)                                     AS month_number,
    MONTHNAME(date_key)                                 AS month_name,
    DATE_FORMAT(date_key, '%Y-%m')                      AS year_month_label,
    CAST(DATE_FORMAT(date_key, '%Y-%m-01') AS DATE)     AS month_start,
    DAYOFWEEK(date_key)                                 AS weekday_number,   -- 1 = Sunday
    DAYNAME(date_key)                                   AS weekday_name,
    (DAYOFWEEK(date_key) IN (1, 7))                     AS is_weekend
FROM calendar;

-- -------------------------------------------------------------------------------------
-- dim_customer: one row per customer_id that has a valid order (customer_id is 1:1 with orders,
-- so the state is exactly the state of that order). customer_unique_id is the person, for
-- DISTINCTCOUNT-based measures such as Repeat Customer %.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_customer AS
WITH per_person AS (
    SELECT customer_unique_id, MIN(purchase_month) AS cohort_month, COUNT(*) AS person_valid_orders
    FROM v_orders_valid
    GROUP BY customer_unique_id
)
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    geo.latitude                           AS customer_latitude,
    geo.longitude                          AS customer_longitude,
    person.cohort_month,
    person.person_valid_orders,
    (person.person_valid_orders >= 2)      AS is_repeat_customer
FROM v_orders_valid AS v
JOIN customers  AS c      ON c.customer_id = v.customer_id
JOIN per_person AS person ON person.customer_unique_id = c.customer_unique_id
LEFT JOIN v_geo_by_zip AS geo ON geo.zip_code_prefix = c.customer_zip_code_prefix;

-- -------------------------------------------------------------------------------------
-- dim_seller: sellers with at least one item in a valid order; ranking columns are NULL for
-- sellers below the 30-delivered-order threshold.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_seller AS
SELECT
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    geo.latitude                 AS seller_latitude,
    geo.longitude                AS seller_longitude,
    ranking.late_rate_rank,
    ranking.late_rate_decile,
    (ranking.seller_id IS NOT NULL) AS is_ranked_30plus_orders
FROM sellers AS s
LEFT JOIN v_geo_by_zip       AS geo     ON geo.zip_code_prefix = s.seller_zip_code_prefix
LEFT JOIN v_seller_late_rate AS ranking ON ranking.seller_id   = s.seller_id
WHERE s.seller_id IN (SELECT i.seller_id FROM order_items AS i JOIN v_orders_valid AS v ON v.order_id = i.order_id);

-- -------------------------------------------------------------------------------------
-- dim_product: every product, with the English category name
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_product AS
SELECT
    p.product_id,
    pc.product_category_name     AS category_portuguese,
    pc.category_english,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm
FROM products AS p
JOIN v_product_category AS pc ON pc.product_id = p.product_id;

-- -------------------------------------------------------------------------------------
-- fact_orders: one row per valid order. Delivery columns are NULL when the order is outside
-- delivery scope (in_delivery_scope = 0); review columns are NULL when there is no review.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_orders AS
SELECT
    v.order_id,
    v.customer_id,
    v.purchase_date,                                   -- relationship to dim_date
    v.order_status,
    v.item_count,
    v.order_revenue,
    v.order_freight,
    v.payment_total,
    (d.order_id IS NOT NULL)                           AS in_delivery_scope,
    DATE(v.order_delivered_customer_date)              AS delivered_date,
    DATE(v.order_estimated_delivery_date)              AS estimated_date,
    d.delay_days,
    d.delay_bucket,
    d.delay_bucket_order,
    d.is_on_time,
    d.is_late,
    d.delivery_days,
    d.flag_pickup_before_approval,
    d.approval_to_pickup_days,
    r.review_id,
    r.review_score
FROM v_orders_valid AS v
LEFT JOIN v_order_delivery      AS d ON d.order_id = v.order_id
LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = v.order_id;

-- -------------------------------------------------------------------------------------
-- fact_order_items: one row per item of a valid order. Order-level delivery and review columns
-- are repeated on each item so seller and category pages can filter without fact-to-fact joins.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    v.customer_id,
    v.purchase_date,
    i.price,
    i.freight_value,
    i.shipping_limit_date,
    (d.order_id IS NOT NULL)          AS in_delivery_scope,
    d.is_late,
    d.delay_days,
    r.review_score
FROM order_items AS i
JOIN v_orders_valid             AS v ON v.order_id = i.order_id
LEFT JOIN v_order_delivery      AS d ON d.order_id = i.order_id
LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = i.order_id;

-- -------------------------------------------------------------------------------------
-- Check: row counts and reconciliation (both facts must give the same Total Revenue as
-- revenue_kpis_overall; keys must be unique in each dimension)
-- -------------------------------------------------------------------------------------
-- @output: powerbi_views_checks
SELECT 'fact_orders rows'                     AS item, COUNT(*) AS value FROM fact_orders
UNION ALL SELECT 'fact_orders distinct order_id',      COUNT(DISTINCT order_id) FROM fact_orders
UNION ALL SELECT 'fact_orders SUM(order_revenue) R$',     SUM(order_revenue) FROM fact_orders
UNION ALL SELECT 'fact_order_items rows',              COUNT(*) FROM fact_order_items
UNION ALL SELECT 'fact_order_items SUM(price) R$',        SUM(price) FROM fact_order_items
UNION ALL SELECT 'dim_customer rows',                  COUNT(*) FROM dim_customer
UNION ALL SELECT 'dim_customer distinct customer_id',  COUNT(DISTINCT customer_id) FROM dim_customer
UNION ALL SELECT 'dim_seller rows',                    COUNT(*) FROM dim_seller
UNION ALL SELECT 'dim_seller ranked (30+ orders)',     SUM(is_ranked_30plus_orders) FROM dim_seller
UNION ALL SELECT 'dim_product rows',                   COUNT(*) FROM dim_product
UNION ALL SELECT 'dim_date rows',                      COUNT(*) FROM dim_date
UNION ALL SELECT 'fact_order_items products missing from dim_product',
                 COUNT(*) FROM fact_order_items WHERE product_id NOT IN (SELECT product_id FROM dim_product)
UNION ALL SELECT 'fact_orders dates missing from dim_date',
                 COUNT(*) FROM fact_orders WHERE purchase_date NOT IN (SELECT date_key FROM dim_date);

-- -------------------------------------------------------------------------------------
-- Expected values for every DAX measure (powerbi/dax_measures.md), computed from the SAME views
-- Power BI loads, at full (DOUBLE) precision. This is the UAT baseline for Phase 7.
-- -------------------------------------------------------------------------------------
-- @output: powerbi_expected_values
WITH
order_totals AS (
    SELECT SUM(order_revenue) AS revenue, COUNT(*) AS orders,
           SUM(in_delivery_scope) AS delivered_in_scope, SUM(is_on_time) AS on_time, SUM(is_late) AS late,
           AVG(CAST(delay_days AS DOUBLE)) AS avg_delay, AVG(CAST(delivery_days AS DOUBLE)) AS avg_delivery_days,
           AVG(CAST(review_score AS DOUBLE)) AS avg_review_all,
           AVG(CASE WHEN in_delivery_scope = 1 THEN CAST(review_score AS DOUBLE) END) AS avg_review_delivered
    FROM fact_orders
),
person_orders AS (
    SELECT c.customer_unique_id, COUNT(*) AS orders
    FROM fact_orders AS f JOIN dim_customer AS c ON c.customer_id = f.customer_id
    GROUP BY c.customer_unique_id
),
monthly_revenue AS (
    SELECT DATE_FORMAT(purchase_date, '%Y-%m') AS month_label, SUM(order_revenue) AS revenue
    FROM fact_orders GROUP BY month_label
),
seller_pairs AS (                   -- seller-order pairs in delivery scope, as in fact_order_items
    SELECT DISTINCT seller_id, order_id, is_late
    FROM fact_order_items
    WHERE in_delivery_scope = 1
),
seller_excess AS (
    SELECT p.seller_id, s.is_ranked_30plus_orders,
           SUM(p.is_late) - COUNT(*) * (SELECT CAST(late AS DOUBLE) / delivered_in_scope FROM order_totals) AS excess
    FROM seller_pairs AS p JOIN dim_seller AS s ON s.seller_id = p.seller_id
    GROUP BY p.seller_id, s.is_ranked_30plus_orders
)
SELECT 'Total Revenue (R$)' AS measure, 'all valid orders 2017-01 to 2018-08' AS filter_context, ROUND(revenue, 2) AS expected_value FROM order_totals
UNION ALL SELECT 'Orders', 'all', orders FROM order_totals
UNION ALL SELECT 'AOV (R$)', 'all', ROUND(revenue / orders, 4) FROM order_totals
UNION ALL SELECT 'Customers', 'all (distinct customer_unique_id)', COUNT(*) FROM person_orders
UNION ALL SELECT 'Repeat Customer %', 'all', ROUND(100 * CAST(SUM(orders >= 2) AS DOUBLE) / COUNT(*), 4) FROM person_orders
UNION ALL SELECT 'Delivered Orders (in scope)', 'all', delivered_in_scope FROM order_totals
UNION ALL SELECT 'On-Time %', 'all', ROUND(100 * CAST(on_time AS DOUBLE) / delivered_in_scope, 4) FROM order_totals
UNION ALL SELECT 'Late %', 'all', ROUND(100 * CAST(late AS DOUBLE) / delivered_in_scope, 4) FROM order_totals
UNION ALL SELECT 'Avg Delay (days)', 'all (negative = early)', ROUND(avg_delay, 4) FROM order_totals
UNION ALL SELECT 'Avg Delivery Days', 'all', ROUND(avg_delivery_days, 4) FROM order_totals
UNION ALL SELECT 'Avg Review', 'all valid orders with a review', ROUND(avg_review_all, 4) FROM order_totals
UNION ALL SELECT 'Avg Review (delivered)', 'orders in delivery scope with a review', ROUND(avg_review_delivered, 4) FROM order_totals
UNION ALL SELECT 'Revenue MoM %', 'month = 2018-08 (vs 2018-07)',
          ROUND(100 * (MAX(CASE WHEN month_label = '2018-08' THEN revenue END) - MAX(CASE WHEN month_label = '2018-07' THEN revenue END))
                / MAX(CASE WHEN month_label = '2018-07' THEN revenue END), 4) FROM monthly_revenue
UNION ALL SELECT 'Revenue MoM %', 'month = 2017-11 (vs 2017-10)',
          ROUND(100 * (MAX(CASE WHEN month_label = '2017-11' THEN revenue END) - MAX(CASE WHEN month_label = '2017-10' THEN revenue END))
                / MAX(CASE WHEN month_label = '2017-10' THEN revenue END), 4) FROM monthly_revenue
UNION ALL SELECT 'Excess Late Orders', 'sellers with 30+ delivered orders (is_ranked_30plus_orders = 1)', ROUND(SUM(excess), 2)
          FROM seller_excess WHERE is_ranked_30plus_orders = 1
UNION ALL SELECT 'Excess Late Orders', 'top seller by excess (rank 1)', ROUND(MAX(excess), 2) FROM seller_excess
UNION ALL SELECT 'Seller Late %', 'sellers with 30+ delivered orders (seller-order pairs)',
          ROUND(100 * CAST(SUM(p.is_late) AS DOUBLE) / COUNT(*), 4)
          FROM seller_pairs AS p JOIN dim_seller AS s ON s.seller_id = p.seller_id WHERE s.is_ranked_30plus_orders = 1;
