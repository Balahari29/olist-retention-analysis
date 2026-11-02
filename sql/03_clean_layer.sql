-- =====================================================================================
-- 03_clean_layer.sql : views that apply the accepted data rules (README "Data rules")
-- Every analysis query reads from these views, never from raw tables, so a rule is
-- defined in exactly one place. Re-runnable (CREATE OR REPLACE).
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- v_orders_valid  (Rule 1 + Rule 3 window)
-- One row per valid order, with the customer's real identity and order totals.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_orders_valid AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp)                                   AS purchase_date,
    CAST(DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS DATE)  AS purchase_month,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    COALESCE(items.item_count, 0)     AS item_count,
    COALESCE(items.order_revenue, 0)  AS order_revenue,     -- SUM(price): KPI "Total Revenue" excludes freight
    COALESCE(items.order_freight, 0)  AS order_freight,
    payments.payment_total
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
LEFT JOIN (SELECT order_id, COUNT(*) AS item_count, SUM(price) AS order_revenue, SUM(freight_value) AS order_freight
             FROM order_items
            GROUP BY order_id) AS items ON items.order_id = o.order_id
LEFT JOIN (SELECT order_id, SUM(payment_value) AS payment_total
             FROM order_payments
            GROUP BY order_id) AS payments ON payments.order_id = o.order_id
WHERE o.order_status IN ('delivered', 'shipped', 'invoiced', 'processing', 'approved')
  AND o.order_purchase_timestamp >= '2017-01-01'
  AND o.order_purchase_timestamp <  '2018-09-01';

-- -------------------------------------------------------------------------------------
-- v_order_reviews_dedup  (Rule 2)
-- One review per order: the most recently answered one.
-- A review shared by several orders stays on each of them; orders_sharing_review counts how many,
-- so Phase 4 can keep one row per review_id for the hypothesis test.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_order_reviews_dedup AS
WITH ranked_reviews AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (PARTITION BY r.order_id
                           ORDER BY r.review_answer_timestamp DESC, r.review_id DESC) AS review_rank,
        COUNT(*)     OVER (PARTITION BY r.order_id)                                   AS reviews_on_order
    FROM order_reviews AS r
)
SELECT
    order_id,
    review_id,
    review_score,
    review_creation_date,
    review_answer_timestamp,
    reviews_on_order,
    COUNT(*) OVER (PARTITION BY review_id) AS orders_sharing_review
FROM ranked_reviews
WHERE review_rank = 1;

-- -------------------------------------------------------------------------------------
-- v_geo_by_zip
-- One row per zip prefix: mean lat/lng of DISTINCT points inside Brazil's bounding box
-- (same box as dq_geolocation_outside_brazil). Exact duplicate rows are counted once.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_geo_by_zip AS
SELECT
    geolocation_zip_code_prefix  AS zip_code_prefix,
    AVG(geolocation_lat)         AS latitude,
    AVG(geolocation_lng)         AS longitude,
    COUNT(*)                     AS distinct_points_used
FROM (SELECT DISTINCT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng
        FROM geolocation
       WHERE geolocation_lat BETWEEN -34 AND 6
         AND geolocation_lng BETWEEN -74 AND -34) AS points_in_brazil
GROUP BY geolocation_zip_code_prefix;

-- -------------------------------------------------------------------------------------
-- v_product_category
-- English category name; untranslated categories keep the Portuguese name; NULL -> 'unknown'.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_product_category AS
SELECT
    p.product_id,
    p.product_category_name,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_english
FROM products AS p
LEFT JOIN category_translation AS t ON t.product_category_name = p.product_category_name;

-- -------------------------------------------------------------------------------------
-- v_order_delivery  (delivery scope: Rule 1 delivered + Rule 3 estimated-date cut-off + Rule 4 flag)
-- One row per valid, delivered order whose estimated date is on or before the last purchase date
-- in the dataset (orders due after the data ends cannot be late yet).
-- delay_days > 0 = late, 0 = on the estimated date, < 0 = early (DATEDIFF ignores time of day).
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_order_delivery AS
SELECT
    delivered.*,
    CASE
        WHEN delay_days < 0  THEN 'Early'
        WHEN delay_days = 0  THEN 'On time'
        WHEN delay_days <= 3 THEN '1-3 days late'
        WHEN delay_days <= 7 THEN '4-7 days late'
        ELSE                      '7+ days late'          -- 8 days or more (Phase 1 decision 3)
    END                                     AS delay_bucket,
    CASE
        WHEN delay_days < 0  THEN 1
        WHEN delay_days = 0  THEN 2
        WHEN delay_days <= 3 THEN 3
        WHEN delay_days <= 7 THEN 4
        ELSE                      5
    END                                     AS delay_bucket_order,   -- sort order for charts
    (delay_days <= 0)                       AS is_on_time,
    (delay_days > 0)                        AS is_late
FROM (
    SELECT
        v.order_id,
        v.customer_id,
        v.customer_unique_id,
        v.customer_state,
        v.purchase_date,
        v.purchase_month,
        v.order_approved_at,
        v.order_delivered_carrier_date,
        v.order_delivered_customer_date,
        v.order_estimated_delivery_date,
        DATEDIFF(v.order_delivered_customer_date, v.order_estimated_delivery_date)  AS delay_days,
        DATEDIFF(v.order_delivered_customer_date, v.order_purchase_timestamp)       AS delivery_days,
        -- Rule 4: flag, do not drop. COALESCE: no carrier or approval date -> not flagged
        COALESCE(v.order_delivered_carrier_date < v.order_approved_at, 0)          AS flag_pickup_before_approval,
        -- Approval-to-pick-up timing only where the step order is valid
        CASE WHEN v.order_delivered_carrier_date >= v.order_approved_at
             THEN ROUND(TIMESTAMPDIFF(HOUR, v.order_approved_at, v.order_delivered_carrier_date) / 24, 2)
        END                                                                         AS approval_to_pickup_days
    FROM v_orders_valid AS v
    WHERE v.order_status = 'delivered'
      AND v.order_delivered_customer_date IS NOT NULL
      AND DATE(v.order_estimated_delivery_date) <= (SELECT DATE(MAX(order_purchase_timestamp)) FROM orders)
) AS delivered;

-- -------------------------------------------------------------------------------------
-- Check: what each view contains, and how many rows each rule removed
-- -------------------------------------------------------------------------------------
-- @output: clean_layer_checks
SELECT 'orders (raw)'                                          AS item, COUNT(*) AS value FROM orders
UNION ALL SELECT 'v_orders_valid rows',                         COUNT(*) FROM v_orders_valid
UNION ALL SELECT 'v_orders_valid distinct order_id',            COUNT(DISTINCT order_id) FROM v_orders_valid
UNION ALL SELECT 'v_orders_valid orders with 0 items',          SUM(item_count = 0) FROM v_orders_valid
UNION ALL SELECT 'valid delivered orders in window',            SUM(order_status = 'delivered') FROM v_orders_valid
UNION ALL SELECT '  removed: no delivered date',                SUM(order_status = 'delivered' AND order_delivered_customer_date IS NULL) FROM v_orders_valid
UNION ALL SELECT '  removed: estimated date after last purchase date',
                 SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
                     AND DATE(order_estimated_delivery_date) > (SELECT DATE(MAX(order_purchase_timestamp)) FROM orders))
          FROM v_orders_valid
UNION ALL SELECT 'v_order_delivery rows',                       COUNT(*) FROM v_order_delivery
UNION ALL SELECT 'v_order_delivery flagged pick-up before approval', SUM(flag_pickup_before_approval) FROM v_order_delivery
UNION ALL SELECT 'order_reviews (raw)',                         COUNT(*) FROM order_reviews
UNION ALL SELECT 'v_order_reviews_dedup rows',                  COUNT(*) FROM v_order_reviews_dedup
UNION ALL SELECT 'v_order_reviews_dedup distinct order_id',     COUNT(DISTINCT order_id) FROM v_order_reviews_dedup
UNION ALL SELECT 'v_order_reviews_dedup distinct review_id',    COUNT(DISTINCT review_id) FROM v_order_reviews_dedup
UNION ALL SELECT 'v_geo_by_zip zip prefixes',                   COUNT(*) FROM v_geo_by_zip
UNION ALL SELECT 'v_product_category rows',                     COUNT(*) FROM v_product_category
UNION ALL SELECT 'v_product_category unknown',                  SUM(category_english = 'unknown') FROM v_product_category;
