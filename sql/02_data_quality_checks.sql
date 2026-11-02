-- =====================================================================================
-- 02_data_quality_checks.sql : data-quality checks for the olist database (MySQL 8)
--
-- Each check is ONE SELECT, preceded by a line "-- @check: <output name>".
-- src/run_dq_checks.py runs every check and saves the result to outputs/<output name>.csv.
-- The checks only MEASURE; no rows are changed or filtered. Rules are decided from the results.
-- Gotcha numbers (G1..G6) refer to "Known gotchas" in CLAUDE.md.
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- G1: customer_id is unique per order; customer_unique_id is the real person.
-- If customer_id were a person, some customer_ids would have more than one order.
-- -------------------------------------------------------------------------------------
-- @check: dq_customer_id_vs_unique_id
SELECT
    (SELECT COUNT(*)                           FROM customers) AS customer_rows,
    (SELECT COUNT(DISTINCT customer_id)        FROM customers) AS distinct_customer_id,
    (SELECT COUNT(DISTINCT customer_unique_id) FROM customers) AS distinct_customer_unique_id,
    (SELECT MAX(orders_per_customer_id)
       FROM (SELECT customer_id, COUNT(*) AS orders_per_customer_id
               FROM orders GROUP BY customer_id) AS per_customer_id) AS max_orders_per_customer_id,
    (SELECT COUNT(*)
       FROM (SELECT c.customer_unique_id
               FROM orders AS o
               JOIN customers AS c ON c.customer_id = o.customer_id
              GROUP BY c.customer_unique_id
             HAVING COUNT(DISTINCT o.order_id) >= 2) AS multi) AS unique_ids_with_2plus_orders_any_status;

-- -------------------------------------------------------------------------------------
-- G2: orders per purchase month, to choose the cut-off for cohort and trend analysis.
-- first/last purchase date inside each month show whether the month is complete.
-- -------------------------------------------------------------------------------------
-- @check: dq_orders_per_month
SELECT
    DATE_FORMAT(order_purchase_timestamp, '%Y-%m')  AS purchase_month,
    COUNT(*)                                         AS orders,
    SUM(order_status = 'delivered')                  AS delivered_orders,
    SUM(order_status IN ('canceled', 'unavailable')) AS canceled_or_unavailable_orders,
    SUM(order_status NOT IN ('delivered', 'canceled', 'unavailable')) AS still_in_progress_orders,
    DATE(MIN(order_purchase_timestamp))              AS first_purchase_date,
    DATE(MAX(order_purchase_timestamp))              AS last_purchase_date
FROM orders
GROUP BY purchase_month
ORDER BY purchase_month;

-- -------------------------------------------------------------------------------------
-- G3: geolocation has many rows per zip prefix.
-- -------------------------------------------------------------------------------------
-- @check: dq_geolocation_rows_per_zip
SELECT
    COUNT(*)                         AS zip_prefixes,
    SUM(rows_per_zip)                AS total_rows,
    MIN(rows_per_zip)                AS min_rows_per_zip,
    ROUND(AVG(rows_per_zip), 1)      AS avg_rows_per_zip,
    MAX(rows_per_zip)                AS max_rows_per_zip,
    SUM(rows_per_zip = 1)            AS zips_with_exactly_1_row,
    SUM(rows_per_zip > 1)            AS zips_with_more_than_1_row,
    (SELECT COUNT(*) - COUNT(DISTINCT geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
                                      geolocation_city, geolocation_state)
       FROM geolocation)             AS exact_duplicate_rows
FROM (SELECT geolocation_zip_code_prefix, COUNT(*) AS rows_per_zip
        FROM geolocation
       GROUP BY geolocation_zip_code_prefix) AS per_zip;

-- G3 (extra): coordinates outside Brazil's bounding box (approx. lat -34..6, lng -74..-34)
-- would pull a mean lat/lng off and break the Phase 4 distance calculation.
-- @check: dq_geolocation_outside_brazil
SELECT
    COUNT(*)                                     AS rows_outside_brazil_box,
    COUNT(DISTINCT geolocation_zip_code_prefix)  AS zip_prefixes_affected,
    (SELECT COUNT(*) FROM geolocation)           AS total_rows
FROM geolocation
WHERE geolocation_lat NOT BETWEEN -34 AND 6
   OR geolocation_lng NOT BETWEEN -74 AND -34;

-- G3 (extra): customer / seller zip prefixes that have no geolocation row (no FK was possible).
-- @check: dq_zip_coverage
SELECT 'customers' AS entity,
       COUNT(DISTINCT customer_zip_code_prefix) AS distinct_zips,
       COUNT(DISTINCT CASE WHEN g.zip IS NULL THEN customer_zip_code_prefix END) AS zips_missing_from_geolocation,
       SUM(g.zip IS NULL) AS rows_with_missing_zip,
       COUNT(*) AS total_rows
FROM customers AS c
LEFT JOIN (SELECT DISTINCT geolocation_zip_code_prefix AS zip FROM geolocation) AS g
       ON g.zip = c.customer_zip_code_prefix
UNION ALL
SELECT 'sellers',
       COUNT(DISTINCT seller_zip_code_prefix),
       COUNT(DISTINCT CASE WHEN g.zip IS NULL THEN seller_zip_code_prefix END),
       SUM(g.zip IS NULL),
       COUNT(*)
FROM sellers AS s
LEFT JOIN (SELECT DISTINCT geolocation_zip_code_prefix AS zip FROM geolocation) AS g
       ON g.zip = s.seller_zip_code_prefix;

-- -------------------------------------------------------------------------------------
-- G4: reviews. (a) how many reviews each order has (0, 1, 2, ...)
-- -------------------------------------------------------------------------------------
-- @check: dq_reviews_per_order
SELECT reviews_on_order, COUNT(*) AS orders
FROM (SELECT o.order_id, COUNT(r.review_id) AS reviews_on_order
        FROM orders AS o
        LEFT JOIN order_reviews AS r ON r.order_id = o.order_id
       GROUP BY o.order_id) AS per_order
GROUP BY reviews_on_order
ORDER BY reviews_on_order;

-- G4 (b): orders with more than one review: do the scores disagree, and are the reviews answered at different times?
-- @check: dq_multi_review_orders
SELECT
    COUNT(*)                          AS orders_with_2plus_reviews,
    SUM(distinct_scores > 1)          AS orders_where_scores_differ,
    SUM(distinct_answer_times > 1)    AS orders_where_answer_times_differ
FROM (SELECT order_id,
             COUNT(DISTINCT review_score)            AS distinct_scores,
             COUNT(DISTINCT review_answer_timestamp) AS distinct_answer_times
        FROM order_reviews
       GROUP BY order_id
      HAVING COUNT(*) > 1) AS multi;

-- G4 (c): how many orders each review_id is linked to
-- @check: dq_orders_per_review
SELECT orders_per_review, COUNT(*) AS review_ids
FROM (SELECT review_id, COUNT(*) AS orders_per_review
        FROM order_reviews
       GROUP BY review_id) AS per_review
GROUP BY orders_per_review
ORDER BY orders_per_review;

-- G4 (d): reviews linked to several orders: same customer? same purchase day?
-- If one customer bought several orders at once and got one survey, the review applies to each order.
-- @check: dq_multi_order_reviews
SELECT
    COUNT(*)                                AS review_ids_with_2plus_orders,
    SUM(distinct_customers = 1)             AS same_customer_unique_id,
    SUM(distinct_purchase_days = 1)         AS same_purchase_day
FROM (SELECT r.review_id,
             COUNT(DISTINCT c.customer_unique_id)            AS distinct_customers,
             COUNT(DISTINCT DATE(o.order_purchase_timestamp)) AS distinct_purchase_days
        FROM order_reviews AS r
        JOIN orders    AS o ON o.order_id    = r.order_id
        JOIN customers AS c ON c.customer_id = o.customer_id
       GROUP BY r.review_id
      HAVING COUNT(*) > 1) AS multi;

-- -------------------------------------------------------------------------------------
-- G5: order statuses, and which data each status has (dates, items, payments, reviews).
-- -------------------------------------------------------------------------------------
-- @check: dq_order_status_distribution
SELECT
    order_status,
    COUNT(*)                                                    AS orders,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)            AS pct_of_orders,
    SUM(order_approved_at IS NOT NULL)                          AS with_approved_date,
    SUM(order_delivered_carrier_date IS NOT NULL)               AS with_carrier_date,
    SUM(order_delivered_customer_date IS NOT NULL)              AS with_delivered_date,
    SUM(EXISTS (SELECT 1 FROM order_items    AS i WHERE i.order_id = o.order_id)) AS with_items,
    SUM(EXISTS (SELECT 1 FROM order_payments AS p WHERE p.order_id = o.order_id)) AS with_payment,
    SUM(EXISTS (SELECT 1 FROM order_reviews  AS r WHERE r.order_id = o.order_id)) AS with_review
FROM orders AS o
GROUP BY order_status
ORDER BY orders DESC;

-- G5: delivered orders with missing dates
-- @check: dq_delivered_missing_dates
SELECT
    COUNT(*)                                       AS delivered_orders,
    SUM(order_approved_at IS NULL)                 AS missing_approved_date,
    SUM(order_delivered_carrier_date IS NULL)      AS missing_carrier_date,
    SUM(order_delivered_customer_date IS NULL)     AS missing_delivered_customer_date
FROM orders
WHERE order_status = 'delivered';

-- -------------------------------------------------------------------------------------
-- Nulls in key date columns (all orders, all statuses)
-- -------------------------------------------------------------------------------------
-- @check: dq_null_key_dates
SELECT 'orders' AS table_name, 'order_purchase_timestamp' AS column_name,
       SUM(order_purchase_timestamp IS NULL) AS null_rows, COUNT(*) AS total_rows FROM orders
UNION ALL SELECT 'orders', 'order_approved_at',             SUM(order_approved_at IS NULL),             COUNT(*) FROM orders
UNION ALL SELECT 'orders', 'order_delivered_carrier_date',  SUM(order_delivered_carrier_date IS NULL),  COUNT(*) FROM orders
UNION ALL SELECT 'orders', 'order_delivered_customer_date', SUM(order_delivered_customer_date IS NULL), COUNT(*) FROM orders
UNION ALL SELECT 'orders', 'order_estimated_delivery_date', SUM(order_estimated_delivery_date IS NULL), COUNT(*) FROM orders
UNION ALL SELECT 'order_items',   'shipping_limit_date',     SUM(shipping_limit_date IS NULL),     COUNT(*) FROM order_items
UNION ALL SELECT 'order_reviews', 'review_creation_date',    SUM(review_creation_date IS NULL),    COUNT(*) FROM order_reviews
UNION ALL SELECT 'order_reviews', 'review_answer_timestamp', SUM(review_answer_timestamp IS NULL), COUNT(*) FROM order_reviews;

-- -------------------------------------------------------------------------------------
-- Orders with no items / no payment, by status
-- -------------------------------------------------------------------------------------
-- @check: dq_orders_without_items
SELECT o.order_status, COUNT(*) AS orders_without_items
FROM orders AS o
WHERE NOT EXISTS (SELECT 1 FROM order_items AS i WHERE i.order_id = o.order_id)
GROUP BY o.order_status
ORDER BY orders_without_items DESC;

-- @check: dq_orders_without_payment
SELECT o.order_status, COUNT(*) AS orders_without_payment
FROM orders AS o
WHERE NOT EXISTS (SELECT 1 FROM order_payments AS p WHERE p.order_id = o.order_id)
GROUP BY o.order_status
ORDER BY orders_without_payment DESC;

-- -------------------------------------------------------------------------------------
-- G6: product categories with no English translation (and products with no category)
-- -------------------------------------------------------------------------------------
-- @check: dq_category_translation
SELECT
    COALESCE(p.product_category_name, '(NULL - no category)') AS product_category_name,
    COUNT(*) AS products,
    (SELECT COUNT(*) FROM order_items AS i
       JOIN products AS p2 ON p2.product_id = i.product_id
      WHERE p2.product_category_name <=> p.product_category_name) AS order_items_affected
FROM products AS p
LEFT JOIN category_translation AS t ON t.product_category_name = p.product_category_name
WHERE t.product_category_name IS NULL
GROUP BY p.product_category_name
ORDER BY products DESC;

-- -------------------------------------------------------------------------------------
-- Revenue reconciliation (KPI dictionary note 1): items (price + freight) vs payments, per order
-- -------------------------------------------------------------------------------------
-- @check: dq_revenue_reconciliation
SELECT
    COUNT(*)                                          AS orders_with_items_and_payments,
    SUM(ABS(items_total - payments_total) <= 0.01)    AS orders_matching_within_1_cent,
    SUM(payments_total - items_total > 0.01)          AS orders_payment_higher,
    SUM(items_total - payments_total > 0.01)          AS orders_payment_lower,
    SUM(items_price)                                  AS total_price_brl,
    SUM(items_freight)                                AS total_freight_brl,
    SUM(items_total)                                  AS total_price_plus_freight_brl,
    SUM(payments_total)                               AS total_payment_value_brl
FROM (SELECT i.order_id, i.items_price, i.items_freight,
             i.items_price + i.items_freight AS items_total,
             p.payments_total
        FROM (SELECT order_id, SUM(price) AS items_price, SUM(freight_value) AS items_freight
                FROM order_items GROUP BY order_id) AS i
        JOIN (SELECT order_id, SUM(payment_value) AS payments_total
                FROM order_payments GROUP BY order_id) AS p ON p.order_id = i.order_id) AS per_order;

-- -------------------------------------------------------------------------------------
-- Value ranges: zero or odd values that could distort averages
-- -------------------------------------------------------------------------------------
-- @check: dq_value_ranges
SELECT 'order_items.price = 0' AS rule_checked, COUNT(*) AS rows_found FROM order_items WHERE price = 0
UNION ALL SELECT 'order_items.freight_value = 0',               COUNT(*) FROM order_items    WHERE freight_value = 0
UNION ALL SELECT 'order_payments.payment_value = 0',            COUNT(*) FROM order_payments WHERE payment_value = 0
UNION ALL SELECT 'order_payments.payment_installments = 0',     COUNT(*) FROM order_payments WHERE payment_installments = 0
UNION ALL SELECT 'order_payments.payment_type = not_defined',   COUNT(*) FROM order_payments WHERE payment_type = 'not_defined'
UNION ALL SELECT 'products.product_weight_g = 0',               COUNT(*) FROM products       WHERE product_weight_g = 0
UNION ALL SELECT 'products with NULL dimensions/weight',        COUNT(*) FROM products       WHERE product_weight_g IS NULL OR product_length_cm IS NULL;

-- -------------------------------------------------------------------------------------
-- Process map (Phase 1) assumptions vs timestamps: does each step happen in the expected order?
-- violations = rows where the later step is dated BEFORE the earlier one (both dates present).
-- -------------------------------------------------------------------------------------
-- @check: dq_process_map_timestamps
SELECT 'S->2  approved before purchase'          AS step_check,
       SUM(order_approved_at IS NOT NULL) AS rows_checked,
       SUM(order_approved_at < order_purchase_timestamp) AS violations
FROM orders
UNION ALL
SELECT '2->5  handed to carrier before approval',
       SUM(order_delivered_carrier_date IS NOT NULL AND order_approved_at IS NOT NULL),
       SUM(order_delivered_carrier_date < order_approved_at)
FROM orders
UNION ALL
SELECT '5->7  delivered to customer before carrier pick-up',
       SUM(order_delivered_customer_date IS NOT NULL AND order_delivered_carrier_date IS NOT NULL),
       SUM(order_delivered_customer_date < order_delivered_carrier_date)
FROM orders
UNION ALL
SELECT 'S->7  delivered before purchase',
       SUM(order_delivered_customer_date IS NOT NULL),
       SUM(order_delivered_customer_date < order_purchase_timestamp)
FROM orders
UNION ALL
SELECT '3     estimated delivery date before purchase',
       COUNT(*),
       SUM(order_estimated_delivery_date < order_purchase_timestamp)
FROM orders
UNION ALL
-- Pain point 1: seller hands over AFTER the latest shipping_limit_date of the order
SELECT '4->5  carrier pick-up after shipping limit (late hand-over)',
       COUNT(*),
       SUM(o.order_delivered_carrier_date > limits.latest_shipping_limit)
FROM orders AS o
JOIN (SELECT order_id, MAX(shipping_limit_date) AS latest_shipping_limit
        FROM order_items GROUP BY order_id) AS limits ON limits.order_id = o.order_id
WHERE o.order_delivered_carrier_date IS NOT NULL;

-- Process map step 9 assumption: "survey sent when the order is delivered or the estimated date is reached".
-- Buckets = days from delivery to review_creation_date; also counts surveys created on/after the estimated date.
-- @check: dq_review_timing
SELECT
    CASE
        WHEN o.order_delivered_customer_date IS NULL                                  THEN '0 order has no delivered date'
        WHEN DATEDIFF(r.review_creation_date, o.order_delivered_customer_date) < 0    THEN '1 survey before delivery'
        WHEN DATEDIFF(r.review_creation_date, o.order_delivered_customer_date) <= 1   THEN '2 same day or next day'
        WHEN DATEDIFF(r.review_creation_date, o.order_delivered_customer_date) <= 7   THEN '3 2-7 days after delivery'
        ELSE                                                                               '4 more than 7 days after delivery'
    END                                                                   AS survey_timing,
    COUNT(*)                                                              AS reviews,
    SUM(DATE(r.review_creation_date) >= DATE(o.order_estimated_delivery_date)) AS created_on_or_after_estimated_date
FROM order_reviews AS r
JOIN orders AS o ON o.order_id = r.order_id
GROUP BY survey_timing
ORDER BY survey_timing;
