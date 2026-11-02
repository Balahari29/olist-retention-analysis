# KPI Dictionary
**Project:** Olist Customer Retention & Delivery Experience Analysis
**Version:** 0.1 (draft, Phase 1) | **Date:** 2026-11-02

> One definition per KPI, used everywhere (SQL, Python, Excel, Power BI). **Currency: all money is in Brazilian
> reais, R$ (BRL)**; output columns with money end in `_brl`. Targets are **[TBD]** until baselines are
> calculated and saved to `outputs/`.

## Shared definitions
| Term | Definition |
|---|---|
| **Customer** | A distinct `customers.customer_unique_id`. Never `customer_id`, which changes with every order. |
| **Valid order** | An order whose `orders.order_status` is not `canceled` or `unavailable`. Final status list **[TBD]** in Phase 2. |
| **Delivered order** | `orders.order_status = 'delivered'` **and** `orders.order_delivered_customer_date` is not NULL. |
| **Delay (days)** | `DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)`. Negative = early, 0 = on the estimated date, positive = late. MySQL `DATEDIFF` compares dates only and ignores time of day. |
| **Analysis window** | Months between the Phase 2 cut-offs **[TBD]**; partial first/last months are excluded from trend and cohort KPIs. |

## KPIs
| KPI | Business definition | Exact formula | Source tables.columns | Owner | Refresh | Target |
|---|---|---|---|---|---|---|
| **Total Revenue** (R$) | Value of products sold on valid orders, in R$, excluding freight. | `SUM(order_items.price)` over valid orders | `order_items.price`, `order_items.order_id` → `orders.order_status` | Marketing Manager | Monthly | [TBD] |
| **AOV** (Average Order Value, R$) | Average product value of one valid order, in R$. | `Total Revenue / COUNT(DISTINCT orders.order_id)` over valid orders | `order_items.price`, `orders.order_id`, `orders.order_status` | Marketing Manager | Monthly | [TBD] |
| **Repeat Customer %** | Share of customers who placed two or more valid orders. | `COUNT(customers with ≥ 2 DISTINCT valid order_id) / COUNT(DISTINCT customer_unique_id with ≥ 1 valid order) × 100` | `customers.customer_unique_id`, `customers.customer_id` → `orders.customer_id`, `orders.order_id`, `orders.order_status` | Marketing Manager | Monthly | [TBD] |
| **On-Time Delivery %** | Share of delivered orders that arrived on or before the estimated delivery date. | `COUNT(delivered orders WHERE Delay ≤ 0) / COUNT(delivered orders) × 100` | `orders.order_status`, `orders.order_delivered_customer_date`, `orders.order_estimated_delivery_date` | Logistics Manager | Weekly | [TBD] |
| **Late Order %** | Share of delivered orders that arrived after the estimated delivery date. | `COUNT(delivered orders WHERE Delay > 0) / COUNT(delivered orders) × 100` (so On-Time % + Late % = 100%) | Same as On-Time Delivery % | Logistics Manager | Weekly | [TBD] |
| **Avg Delivery Delay** | Average number of days delivered orders arrived after (+) or before (−) the estimate. | `AVG(Delay)` over delivered orders | Same as On-Time Delivery % | Logistics Manager | Weekly | [TBD] |
| **Avg Review Score** | Average customer rating (1–5) of orders. | `AVG(order_reviews.review_score)` using one review per order (proposed: most recent `review_answer_timestamp`; rule **[TBD]**) | `order_reviews.review_score`, `order_reviews.order_id`, `order_reviews.review_answer_timestamp` | Head of Customer Experience | Weekly | [TBD] |
| **Cohort Retention %** (month *k*) | Of customers whose first valid order was in month M, the share who placed a valid order again in month M + *k*. | Cohort month = `MIN(order_purchase_timestamp)` per `customer_unique_id`, truncated to month. Retention(M, *k*) = `COUNT(DISTINCT customers in cohort M with a valid order in month M + k) / COUNT(DISTINCT customers in cohort M) × 100`, for *k* = 1, 2, 3 … | `customers.customer_unique_id`, `orders.customer_id`, `orders.order_purchase_timestamp`, `orders.order_status` | Marketing Manager | Monthly | [TBD] |

## Notes and design decisions (to confirm in Phase 2)
1. **Why `price` and not `payment_value` for revenue:** `price` is stored per item, so revenue can be split by
   seller and category (needed for Pareto, Q5). `payment_value` is per order and includes freight and instalment
   interest. Phase 2 will reconcile `SUM(price + freight_value)` against `SUM(payment_value)` and save the difference to `outputs/`.
2. **Delay buckets for Phase 3** (built from *Delay*): Early (< 0), On time (= 0), 1–3 days late, 4–7 days late,
   7+ days late (= 8 days or more, so the 4–7 and 7+ buckets do not overlap).
3. **Repeat Customer % and Cohort Retention** rely on `customer_unique_id`; using `customer_id` would show
   almost no repeat customers, because a new `customer_id` is created for each order.
4. **Refresh frequency** is the recommended schedule if this ran on live data. In this project the data is a static
   2016–2018 snapshot, refreshed only when the files are reloaded.
