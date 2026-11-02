-- =====================================================================================
-- 03_analysis_retention.sql : Business question Q1 (repeat purchase and cohort retention)
-- Source: v_orders_valid (Rule 1 statuses, Rule 3 window 2017-01 to 2018-08).
-- A customer is a customer_unique_id, never a customer_id (customer_id is unique per order).
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- KPI Repeat Customer %: share of customers with 2 or more valid orders
-- -------------------------------------------------------------------------------------
-- @output: retention_repeat_customers
WITH orders_per_customer AS (
    SELECT customer_unique_id, COUNT(DISTINCT order_id) AS valid_orders
    FROM v_orders_valid
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*)                                          AS customers,
    SUM(valid_orders >= 2)                            AS repeat_customers,
    ROUND(100 * SUM(valid_orders >= 2) / COUNT(*), 2) AS repeat_customer_pct,
    MAX(valid_orders)                                 AS max_orders_by_one_customer
FROM orders_per_customer;

-- How many customers placed 1, 2, 3 ... orders
-- @output: retention_orders_per_customer
WITH orders_per_customer AS (
    SELECT customer_unique_id, COUNT(DISTINCT order_id) AS valid_orders
    FROM v_orders_valid
    GROUP BY customer_unique_id
)
SELECT
    valid_orders,
    COUNT(*)                                             AS customers,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)     AS pct_of_customers
FROM orders_per_customer
GROUP BY valid_orders
ORDER BY valid_orders;

-- -------------------------------------------------------------------------------------
-- KPI Cohort Retention %, long format (one row per cohort x month offset) for Power BI.
-- Cohort = month of the customer's first valid order. month_offset 0 = first month.
-- Only offsets the cohort has been observed for are produced (equal-window rule):
-- 0 % means "observed, nobody came back"; a missing offset means "not observable yet".
-- -------------------------------------------------------------------------------------
-- @output: retention_cohort_long
WITH RECURSIVE
customer_months AS (
    SELECT
        customer_unique_id,
        purchase_month,
        MIN(purchase_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM v_orders_valid
),
activity AS (                       -- one row per customer per active month
    SELECT DISTINCT
        customer_unique_id,
        cohort_month,
        TIMESTAMPDIFF(MONTH, cohort_month, purchase_month) AS month_offset
    FROM customer_months
),
cohort_info AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customers,
        TIMESTAMPDIFF(MONTH, cohort_month, (SELECT MAX(purchase_month) FROM v_orders_valid)) AS months_observed
    FROM activity
    WHERE month_offset = 0
    GROUP BY cohort_month
),
month_offsets AS (                  -- 0, 1, 2 ... up to the longest observation period
    SELECT 0 AS month_offset
    UNION ALL
    SELECT month_offset + 1 FROM month_offsets
    WHERE month_offset < (SELECT MAX(months_observed) FROM cohort_info)
),
active_counts AS (
    SELECT cohort_month, month_offset, COUNT(*) AS active_customers
    FROM activity
    GROUP BY cohort_month, month_offset
)
SELECT
    info.cohort_month,
    info.cohort_customers,
    offsets.month_offset,
    COALESCE(counts.active_customers, 0)                                         AS active_customers,
    ROUND(100 * COALESCE(counts.active_customers, 0) / info.cohort_customers, 2) AS retention_pct
FROM cohort_info AS info
JOIN month_offsets AS offsets ON offsets.month_offset <= info.months_observed
LEFT JOIN active_counts AS counts
       ON counts.cohort_month = info.cohort_month AND counts.month_offset = offsets.month_offset
ORDER BY info.cohort_month, offsets.month_offset;

-- -------------------------------------------------------------------------------------
-- Cohort retention matrix, wide format (months 1-12) for the README and Excel.
-- NULL = not observable yet for that cohort.
-- -------------------------------------------------------------------------------------
-- @output: retention_cohort_matrix
WITH
customer_months AS (
    SELECT customer_unique_id, purchase_month,
           MIN(purchase_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM v_orders_valid
),
activity AS (
    SELECT DISTINCT customer_unique_id, cohort_month,
           TIMESTAMPDIFF(MONTH, cohort_month, purchase_month) AS month_offset
    FROM customer_months
),
cohort_info AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers,
           TIMESTAMPDIFF(MONTH, cohort_month, (SELECT MAX(purchase_month) FROM v_orders_valid)) AS months_observed
    FROM activity
    WHERE month_offset = 0
    GROUP BY cohort_month
)
SELECT
    info.cohort_month,
    info.cohort_customers,
    info.months_observed,
    CASE WHEN info.months_observed >= 1  THEN ROUND(100 * SUM(a.month_offset = 1)  / info.cohort_customers, 2) END AS m1,
    CASE WHEN info.months_observed >= 2  THEN ROUND(100 * SUM(a.month_offset = 2)  / info.cohort_customers, 2) END AS m2,
    CASE WHEN info.months_observed >= 3  THEN ROUND(100 * SUM(a.month_offset = 3)  / info.cohort_customers, 2) END AS m3,
    CASE WHEN info.months_observed >= 4  THEN ROUND(100 * SUM(a.month_offset = 4)  / info.cohort_customers, 2) END AS m4,
    CASE WHEN info.months_observed >= 5  THEN ROUND(100 * SUM(a.month_offset = 5)  / info.cohort_customers, 2) END AS m5,
    CASE WHEN info.months_observed >= 6  THEN ROUND(100 * SUM(a.month_offset = 6)  / info.cohort_customers, 2) END AS m6,
    CASE WHEN info.months_observed >= 7  THEN ROUND(100 * SUM(a.month_offset = 7)  / info.cohort_customers, 2) END AS m7,
    CASE WHEN info.months_observed >= 8  THEN ROUND(100 * SUM(a.month_offset = 8)  / info.cohort_customers, 2) END AS m8,
    CASE WHEN info.months_observed >= 9  THEN ROUND(100 * SUM(a.month_offset = 9)  / info.cohort_customers, 2) END AS m9,
    CASE WHEN info.months_observed >= 10 THEN ROUND(100 * SUM(a.month_offset = 10) / info.cohort_customers, 2) END AS m10,
    CASE WHEN info.months_observed >= 11 THEN ROUND(100 * SUM(a.month_offset = 11) / info.cohort_customers, 2) END AS m11,
    CASE WHEN info.months_observed >= 12 THEN ROUND(100 * SUM(a.month_offset = 12) / info.cohort_customers, 2) END AS m12
FROM cohort_info AS info
JOIN activity AS a ON a.cohort_month = info.cohort_month
GROUP BY info.cohort_month, info.cohort_customers, info.months_observed
ORDER BY info.cohort_month;

-- -------------------------------------------------------------------------------------
-- Equal observation window: share of each cohort that bought again within months 1-6
-- after the first month. Only cohorts with 6 full months of follow-up are compared.
-- -------------------------------------------------------------------------------------
-- @output: retention_cohort_6m_window
WITH
customer_months AS (
    SELECT customer_unique_id, purchase_month,
           MIN(purchase_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM v_orders_valid
),
customer_return AS (                -- one row per customer: did they return in months 1-6?
    SELECT
        customer_unique_id,
        cohort_month,
        MAX(TIMESTAMPDIFF(MONTH, cohort_month, purchase_month) BETWEEN 1 AND 6) AS returned_within_6m
    FROM customer_months
    GROUP BY customer_unique_id, cohort_month
)
SELECT
    cohort_month,
    COUNT(*)                                          AS cohort_customers,
    SUM(returned_within_6m)                           AS returned_within_6m,
    ROUND(100 * SUM(returned_within_6m) / COUNT(*), 2) AS return_within_6m_pct
FROM customer_return
WHERE TIMESTAMPDIFF(MONTH, cohort_month, (SELECT MAX(purchase_month) FROM v_orders_valid)) >= 6
GROUP BY cohort_month
ORDER BY cohort_month;

-- -------------------------------------------------------------------------------------
-- Does a late FIRST order reduce the chance of a second purchase?
-- First order = earliest valid order per customer (ties broken by order_id).
-- Equal observation window (Rule 3): only customers whose first order is in a cohort with
-- 6 full months of follow-up; "returned" = a valid order in calendar months 1-6 after the first.
-- First orders outside delivery scope (not delivered, no date) cannot be late/on time: shown separately.
-- The significance test (chi-square / two-proportion z-test) is in notebooks/analysis.ipynb.
-- -------------------------------------------------------------------------------------
-- @output: retention_first_order_late_vs_on_time
WITH
ordered AS (
    SELECT
        customer_unique_id,
        order_id,
        purchase_month,
        ROW_NUMBER() OVER (PARTITION BY customer_unique_id
                           ORDER BY order_purchase_timestamp, order_id) AS order_number,
        MIN(purchase_month) OVER (PARTITION BY customer_unique_id)      AS cohort_month
    FROM v_orders_valid
),
first_orders AS (
    SELECT customer_unique_id, order_id AS first_order_id, cohort_month
    FROM ordered
    WHERE order_number = 1
),
returned AS (                       -- 1 if the customer has a valid order 1-6 months after the first month
    SELECT customer_unique_id,
           MAX(TIMESTAMPDIFF(MONTH, cohort_month, purchase_month) BETWEEN 1 AND 6) AS returned_within_6m
    FROM ordered
    GROUP BY customer_unique_id
)
SELECT
    CASE
        WHEN d.order_id IS NULL THEN 'First order not in delivery scope'
        WHEN d.is_late = 1      THEN 'First order late'
        ELSE                         'First order on time'
    END                                                         AS first_order_delivery,
    COUNT(*)                                                    AS customers,
    SUM(r.returned_within_6m)                                   AS returned_within_6m,
    COUNT(*) - SUM(r.returned_within_6m)                        AS did_not_return,
    ROUND(100 * CAST(SUM(r.returned_within_6m) AS DOUBLE) / COUNT(*), 3) AS return_within_6m_pct
FROM first_orders AS f
JOIN returned AS r ON r.customer_unique_id = f.customer_unique_id
LEFT JOIN v_order_delivery AS d ON d.order_id = f.first_order_id
WHERE TIMESTAMPDIFF(MONTH, f.cohort_month, (SELECT MAX(purchase_month) FROM v_orders_valid)) >= 6
GROUP BY first_order_delivery
ORDER BY first_order_delivery;
