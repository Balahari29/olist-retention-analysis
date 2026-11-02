# Insight memo: late deliveries, reviews and repeat customers
**To:** Head of Customer Experience · Logistics Manager · Marketing Manager
**From:** Bala Hariharan B, Business / Data Analyst | **Date:** 2026-11-02
**Data:** Olist orders Jan 2017 - Aug 2018, valid orders only (README "Data rules"). Money in R$ (BRL).

## The finding
**Late orders score about 2 stars lower: 2.27 vs 4.29 out of 5** (−2.02 stars, 95% CI 1.98-2.06, p < 0.001,
`outputs/hypothesis_test_results.csv`). **But 74% of those late-order reviews (4,741 of 6,365) were written before the
parcel arrived.** Customers were asked to rate an order they did not have yet. Counting only reviews written after
delivery, the gap is **0.76 stars**: smaller, but still real (`outputs/hypothesis_test_conclusion.txt`).
6.79% of delivered orders arrive late: **6,531 orders in 20 months** (`outputs/delivery_kpis_overall.csv`).

## Recommendations, in priority order
**1. Send the review survey only after delivery is confirmed, and notify customers before an order runs late.**
*Owner: Head of Customer Experience.*
- *Evidence:* most of the 2-star penalty comes from surveys that reached customers whose parcel was still on its way:
  4,741 of 6,365 late-order reviews (`outputs/hypothesis_test_results.csv`).
- *Impact:* the **6,531 customers per 20 months whose order runs late** hear from Olist first instead of from a survey
  about a missing parcel, and future ratings measure the product and delivery, not the wait.

**2. Add delivery-date buffer to long routes and fix the worst states and sellers, ranked by excess late orders.**
*Owner: Logistics Manager.*
- *Evidence:* late % rises from 4.49% (under 100 km) to **11.64% for routes over 1,500 km** (8,754 orders,
  `outputs/distance_vs_delay_bands.csv`); estimates already grow with distance (Spearman 0.54 with delivery days, only
  0.07 with being late, `outputs/distance_correlation.csv`), so long routes are under-buffered. AL (21.46% late) and
  MA (17.53%) are worst (`outputs/delivery_ontime_by_state.csv`). 244 sellers are worse than an average seller of their
  size; the **top 20 account for 457 excess late orders** (`outputs/seller_excess_summary.csv`).
- *Impact (customers affected; groups overlap, so not additive):* bringing long routes to the platform rate means
  **about 425 fewer late orders**; AL and MA about 58 and 77; the top 20 sellers about 457. Every **20% cut in late
  orders spares about 1,306 customers** a late, poorly reviewed order. The platform-wide average review moves only
  +0.01 to +0.03 stars (`excel/seller_scorecard.xlsx` What-If, from the files above), because only 6.79% of orders are
  late; the gain is concentrated on the customers affected and on seller ratings.

**3. Run a second-purchase campaign for "New - high value" customers, with a random holdout group.**
*Owner: Marketing Manager.*
- *Evidence:* 97% of customers buy once (`outputs/retention_orders_per_customer.csv`); only 1.42-2.28% of a cohort
  returns within 6 months (`outputs/retention_cohort_6m_window.csv`). "New - high value" is **14,737 customers (15.56%)
  holding 29.40% of revenue**, R$ 268.29 average spend (`outputs/rfm_segments.csv`).
- *Impact:* each +1 percentage point of return in this segment is **about 147 more repeat customers, about
  R$ 39,500** at their average spend. Hold out a random 10% who get no campaign; the difference in return rate is the
  campaign's true lift.

## Limitations
- **Correios strike (March 2018):** the timing fits the peak in late deliveries, but the state pattern does not (strike
  states 15.57% late vs 23.23% elsewhere, `outputs/delivery_spike_strike_states.csv`). Consistent with the data, not proof.
- **February 2018 is unexplained:** late % was already 13.71-14.47% in both state groups before the strike
  (`outputs/delivery_spike_strike_states.csv`).
- **Late first order vs repeat purchase is inconclusive:** 1.47% vs 1.79% return, p = 0.161; the test can only detect
  gaps of about 0.63 points or more (`outputs/retention_first_order_late_test.csv`).
- **Old data:** Olist 2016-2018 (analysis window Jan 2017 - Aug 2018, `outputs/dq_orders_per_month.csv`); results may
  not hold today. Distances are straight-line, not road routes.
