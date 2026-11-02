-- =====================================================================================
-- 04_analysis_delivery.sql : Business questions Q2 (late delivery vs review) and Q3 (where delays happen)
-- Source: v_order_delivery (delivered, has delivered date, estimated date <= last purchase date)
--         v_order_reviews_dedup (one review per order, Rule 2)
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- Delivery KPIs overall: On-Time Delivery %, Late Order %, Avg Delivery Delay, Avg Review Score
-- -------------------------------------------------------------------------------------
-- @output: delivery_kpis_overall
SELECT
    COUNT(*)                               AS delivered_orders_in_scope,
    SUM(d.is_late)                         AS late_orders,
    ROUND(100 * AVG(d.is_on_time), 2)      AS on_time_pct,
    ROUND(100 * AVG(d.is_late), 2)         AS late_pct,
    ROUND(AVG(d.delay_days), 2)            AS avg_delay_days,       -- negative = early on average
    ROUND(AVG(d.delivery_days), 2)         AS avg_delivery_days,    -- purchase to delivery
    COUNT(r.review_score)                  AS orders_with_review,
    ROUND(AVG(r.review_score), 2)          AS avg_review_score
FROM v_order_delivery AS d
LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = d.order_id;

-- -------------------------------------------------------------------------------------
-- Delay bucket vs review score (US-02 AC-1).
-- pct_1_2_star = share of reviewed orders that scored 1 or 2.
-- -------------------------------------------------------------------------------------
-- @output: delivery_buckets_vs_review
SELECT
    d.delay_bucket_order,
    d.delay_bucket,
    COUNT(*)                                            AS orders,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS pct_of_orders,
    COUNT(r.review_score)                               AS orders_with_review,
    ROUND(AVG(r.review_score), 2)                       AS avg_review_score,
    ROUND(100 * AVG(r.review_score <= 2), 2)            AS pct_1_2_star
FROM v_order_delivery AS d
LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = d.order_id
GROUP BY d.delay_bucket_order, d.delay_bucket
ORDER BY d.delay_bucket_order;

-- -------------------------------------------------------------------------------------
-- On-time % by purchase month (trend)
-- -------------------------------------------------------------------------------------
-- @output: delivery_ontime_by_month
SELECT
    purchase_month,
    COUNT(*)                            AS delivered_orders,
    ROUND(100 * AVG(is_on_time), 2)     AS on_time_pct,
    ROUND(100 * AVG(is_late), 2)        AS late_pct,
    ROUND(AVG(delay_days), 2)           AS avg_delay_days,
    ROUND(AVG(delivery_days), 2)        AS avg_delivery_days
FROM v_order_delivery
GROUP BY purchase_month
ORDER BY purchase_month;

-- -------------------------------------------------------------------------------------
-- On-time % by customer state (US-04 AC-3), worst late rate first
-- -------------------------------------------------------------------------------------
-- @output: delivery_ontime_by_state
SELECT
    d.customer_state,
    COUNT(*)                               AS delivered_orders,
    SUM(d.is_late)                         AS late_orders,
    ROUND(100 * AVG(d.is_on_time), 2)      AS on_time_pct,
    ROUND(100 * AVG(d.is_late), 2)         AS late_pct,
    ROUND(AVG(d.delay_days), 2)            AS avg_delay_days,
    ROUND(AVG(d.delivery_days), 2)         AS avg_delivery_days,
    ROUND(AVG(r.review_score), 2)          AS avg_review_score
FROM v_order_delivery AS d
LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = d.order_id
GROUP BY d.customer_state
ORDER BY late_pct DESC;

-- -------------------------------------------------------------------------------------
-- Approval-to-pick-up time (Rule 4: flagged orders excluded from this timing only)
-- -------------------------------------------------------------------------------------
-- @output: delivery_approval_to_pickup
SELECT
    COUNT(*)                                     AS delivered_orders_in_scope,
    SUM(flag_pickup_before_approval)             AS flagged_pickup_before_approval,
    COUNT(approval_to_pickup_days)               AS orders_timed,
    ROUND(AVG(approval_to_pickup_days), 2)       AS avg_approval_to_pickup_days,
    ROUND(AVG(CASE WHEN is_late = 1 THEN approval_to_pickup_days END), 2) AS avg_days_late_orders,
    ROUND(AVG(CASE WHEN is_late = 0 THEN approval_to_pickup_days END), 2) AS avg_days_on_time_orders
FROM v_order_delivery;

-- -------------------------------------------------------------------------------------
-- Late-rate spikes: are the explanations CONSISTENT with the data? (not proof)
-- (a) Correios strike from 12 March 2018, reported in SP, RJ, MA, TO: strike states vs others by month
-- -------------------------------------------------------------------------------------
-- @output: delivery_spike_strike_states
SELECT
    purchase_month,
    CASE WHEN customer_state IN ('SP', 'RJ', 'MA', 'TO') THEN 'SP, RJ, MA, TO' ELSE 'other states' END AS state_group,
    COUNT(*)                          AS delivered_orders,
    ROUND(100 * AVG(is_late), 2)      AS late_pct
FROM v_order_delivery
WHERE purchase_month BETWEEN '2018-01-01' AND '2018-05-01'
GROUP BY purchase_month, state_group
ORDER BY purchase_month, state_group;

-- (b) Black Friday 2017 (24 Nov): orders bought in Black Friday week vs the rest of November 2017
-- @output: delivery_spike_black_friday
SELECT
    CASE WHEN purchase_date BETWEEN '2017-11-20' AND '2017-11-26' THEN 'Black Friday week (20-26 Nov)'
         ELSE 'rest of November' END   AS purchase_period,
    COUNT(*)                          AS delivered_orders,
    ROUND(100 * AVG(is_late), 2)      AS late_pct,
    ROUND(AVG(delivery_days), 2)      AS avg_delivery_days
FROM v_order_delivery
WHERE purchase_month = '2017-11-01'
GROUP BY purchase_period
ORDER BY purchase_period;

-- -------------------------------------------------------------------------------------
-- Late % by product category (US-04). An order is counted once per category it contains.
-- has_100plus_orders: small categories can top the list by chance, so titles use only flagged rows.
-- -------------------------------------------------------------------------------------
-- @output: delivery_late_by_category
SELECT
    pc.category_english,
    COUNT(DISTINCT d.order_id)                                                       AS delivered_orders,
    COUNT(DISTINCT CASE WHEN d.is_late = 1 THEN d.order_id END)                      AS late_orders,
    ROUND(100 * CAST(COUNT(DISTINCT CASE WHEN d.is_late = 1 THEN d.order_id END) AS DOUBLE)
              / COUNT(DISTINCT d.order_id), 2)                                       AS late_pct,
    (COUNT(DISTINCT d.order_id) >= 100)                                              AS has_100plus_orders
FROM v_order_delivery AS d
JOIN order_items        AS i  ON i.order_id    = d.order_id
JOIN v_product_category AS pc ON pc.product_id = i.product_id
GROUP BY pc.category_english
ORDER BY late_pct DESC;
