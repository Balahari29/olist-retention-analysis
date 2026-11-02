-- =====================================================================================
-- 05_analysis_sellers_categories.sql : Q3 (which sellers cause delays) and Q5 (revenue concentration)
-- Revenue = SUM(order_items.price) on valid orders (KPI dictionary; excludes freight).
-- =====================================================================================
USE olist;

-- -------------------------------------------------------------------------------------
-- v_seller_late_rate: one row per seller with >= 30 delivered orders in delivery scope.
-- An order with items from 2 sellers counts once for each seller (lateness is order-level).
-- late_rate_decile: NTILE(10) ordered worst first, so decile 1 = worst 10 % of sellers.
-- Ties are broken by more delivered orders, then seller_id, so the result is repeatable.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_seller_late_rate AS
WITH seller_orders AS (
    SELECT DISTINCT i.seller_id, d.order_id, d.is_late, d.delay_days, r.review_score
    FROM order_items AS i
    JOIN v_order_delivery AS d ON d.order_id = i.order_id
    LEFT JOIN v_order_reviews_dedup AS r ON r.order_id = d.order_id
),
seller_stats AS (
    SELECT
        seller_id,
        COUNT(*)              AS delivered_orders,
        SUM(is_late)          AS late_orders,
        AVG(is_late)          AS late_rate,          -- unrounded, used for ranking
        AVG(delay_days)       AS avg_delay_days,
        AVG(review_score)     AS avg_review_score
    FROM seller_orders
    GROUP BY seller_id
    HAVING COUNT(*) >= 30
)
SELECT
    stats.seller_id,
    sellers.seller_city,
    sellers.seller_state,
    stats.delivered_orders,
    stats.late_orders,
    ROUND(100 * stats.late_rate, 2)       AS late_rate_pct,
    ROUND(stats.avg_delay_days, 2)        AS avg_delay_days,
    ROUND(stats.avg_review_score, 2)      AS avg_review_score,
    RANK()    OVER (ORDER BY stats.late_rate DESC)                                         AS late_rate_rank,
    NTILE(10) OVER (ORDER BY stats.late_rate DESC, stats.delivered_orders DESC, stats.seller_id) AS late_rate_decile
FROM seller_stats AS stats
JOIN sellers ON sellers.seller_id = stats.seller_id;

-- How many sellers pass the 30-order threshold, and how much of the volume they cover
-- @output: seller_eligibility
WITH seller_orders AS (
    SELECT i.seller_id, COUNT(DISTINCT d.order_id) AS delivered_orders
    FROM order_items AS i
    JOIN v_order_delivery AS d ON d.order_id = i.order_id
    GROUP BY i.seller_id
)
SELECT
    COUNT(*)                                       AS sellers_with_delivered_orders,
    SUM(delivered_orders >= 30)                    AS sellers_with_30plus_orders,
    SUM(delivered_orders)                          AS seller_order_pairs,
    SUM(CASE WHEN delivered_orders >= 30 THEN delivered_orders END) AS seller_order_pairs_30plus,
    ROUND(100 * SUM(CASE WHEN delivered_orders >= 30 THEN delivered_orders END) / SUM(delivered_orders), 2)
                                                   AS pct_of_pairs_covered
FROM seller_orders;

-- Seller ranking (US-03), worst first
-- @output: seller_late_rate_ranking
SELECT *
FROM v_seller_late_rate
ORDER BY late_rate_rank, delivered_orders DESC, seller_id;

-- Late orders by seller decile: how much of the lateness the worst 10 % of sellers cause
-- @output: seller_late_rate_by_decile
SELECT
    late_rate_decile,
    COUNT(*)                                                     AS sellers,
    SUM(delivered_orders)                                        AS delivered_orders,
    SUM(late_orders)                                             AS late_orders,
    ROUND(100 * SUM(late_orders) / SUM(delivered_orders), 2)     AS late_rate_pct,
    ROUND(100 * SUM(late_orders) / SUM(SUM(late_orders)) OVER (), 2) AS share_of_all_late_orders_pct,
    MIN(late_rate_pct)                                           AS min_seller_late_rate_pct,
    MAX(late_rate_pct)                                           AS max_seller_late_rate_pct
FROM v_seller_late_rate
GROUP BY late_rate_decile
ORDER BY late_rate_decile;

-- -------------------------------------------------------------------------------------
-- Revenue KPIs overall: Total Revenue, AOV
-- -------------------------------------------------------------------------------------
-- @output: revenue_kpis_overall
SELECT
    COUNT(*)                                     AS valid_orders,
    COUNT(DISTINCT customer_unique_id)           AS customers,
    SUM(order_revenue)                           AS total_revenue,
    ROUND(SUM(order_revenue) / COUNT(*), 2)      AS aov,
    SUM(order_freight)                           AS total_freight
FROM v_orders_valid;

-- -------------------------------------------------------------------------------------
-- Pareto views: revenue share and running (cumulative) share, highest revenue first.
-- in_first_80pct = 1 for the members needed to reach 80 % of revenue
-- (the member that crosses 80 % is included).
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_pareto_category AS
WITH category_revenue AS (
    SELECT pc.category_english, SUM(i.price) AS revenue, COUNT(DISTINCT i.order_id) AS orders
    FROM order_items AS i
    JOIN v_orders_valid     AS v  ON v.order_id    = i.order_id
    JOIN v_product_category AS pc ON pc.product_id = i.product_id
    GROUP BY pc.category_english
),
running AS (
    SELECT
        category_english,
        revenue,
        orders,
        ROW_NUMBER() OVER (ORDER BY revenue DESC, category_english)                         AS revenue_rank,
        revenue / SUM(revenue) OVER ()                                                      AS revenue_share,
        SUM(revenue) OVER (ORDER BY revenue DESC, category_english ROWS UNBOUNDED PRECEDING)
            / SUM(revenue) OVER ()                                                          AS cumulative_share
    FROM category_revenue
)
SELECT
    revenue_rank,
    category_english,
    revenue,
    orders,
    ROUND(100 * revenue_share, 2)               AS revenue_pct,
    ROUND(100 * cumulative_share, 2)            AS cumulative_pct,
    (cumulative_share - revenue_share < 0.8)    AS in_first_80pct
FROM running;

CREATE OR REPLACE VIEW v_pareto_state AS
WITH state_revenue AS (
    SELECT customer_state, SUM(order_revenue) AS revenue, COUNT(*) AS orders
    FROM v_orders_valid
    GROUP BY customer_state
),
running AS (
    SELECT
        customer_state,
        revenue,
        orders,
        ROW_NUMBER() OVER (ORDER BY revenue DESC, customer_state)                         AS revenue_rank,
        revenue / SUM(revenue) OVER ()                                                    AS revenue_share,
        SUM(revenue) OVER (ORDER BY revenue DESC, customer_state ROWS UNBOUNDED PRECEDING)
            / SUM(revenue) OVER ()                                                        AS cumulative_share
    FROM state_revenue
)
SELECT
    revenue_rank,
    customer_state,
    revenue,
    orders,
    ROUND(100 * revenue_share, 2)               AS revenue_pct,
    ROUND(100 * cumulative_share, 2)            AS cumulative_pct,
    (cumulative_share - revenue_share < 0.8)    AS in_first_80pct
FROM running;

-- @output: revenue_pareto_category
SELECT * FROM v_pareto_category ORDER BY revenue_rank;

-- @output: revenue_pareto_state
SELECT * FROM v_pareto_state ORDER BY revenue_rank;

-- Pareto summary (US-06 AC-2, AC-3): how many members make 80 % of revenue; totals must equal Total Revenue
-- @output: revenue_pareto_summary
SELECT 'product category' AS dimension,
       COUNT(*)                                    AS members,
       SUM(in_first_80pct)                         AS members_for_80pct_revenue,
       ROUND(100 * SUM(in_first_80pct) / COUNT(*), 2) AS pct_of_members,
       SUM(revenue)                                AS total_revenue
FROM v_pareto_category
UNION ALL
SELECT 'customer state', COUNT(*), SUM(in_first_80pct), ROUND(100 * SUM(in_first_80pct) / COUNT(*), 2), SUM(revenue)
FROM v_pareto_state;

-- -------------------------------------------------------------------------------------
-- Month-over-month revenue with LAG (KPI Revenue MoM %)
-- -------------------------------------------------------------------------------------
-- @output: revenue_mom
WITH monthly AS (
    SELECT
        purchase_month,
        COUNT(*)                                  AS orders,
        SUM(order_revenue)                        AS revenue,
        ROUND(SUM(order_revenue) / COUNT(*), 2)   AS aov
    FROM v_orders_valid
    GROUP BY purchase_month
)
SELECT
    purchase_month,
    orders,
    revenue,
    aov,
    LAG(revenue) OVER (ORDER BY purchase_month)                     AS previous_month_revenue,
    revenue - LAG(revenue) OVER (ORDER BY purchase_month)           AS mom_change,
    ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY purchase_month))
              / LAG(revenue) OVER (ORDER BY purchase_month), 2)     AS mom_pct
FROM monthly
ORDER BY purchase_month;
