# UAT checklist: Power BI dashboard vs SQL
**Project:** Olist Customer Retention & Delivery Experience Analysis
**Version:** 1.0 | **Date:** 2026-11-02 | **Tester:** Bala Hariharan B | **Build:** `powerbi/olist_dashboard.pbix`

**How to test:** build the report with `powerbi/build_steps.md`. Unless a row says otherwise, **clear all slicers**.
Read the value from a card or tooltip and write it in **Actual**. **Pass** = equal to **Expected** at the precision
shown (percentages to 2 decimals, money to the cent, averages to 2 decimals). Every expected value comes from the
file in **Source** (computed in SQL from the same views Power BI loads). Investigate any **Fail** before sign-off:
check the column's data type, then the relationship, then the DAX against `powerbi/dax_measures.md`.

## A. Model checks
| ID | Check | How to test | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-01 | Row count `fact_orders` | Table view, bottom-left count | 97,905 | `outputs/powerbi_views_checks.csv` | | |
| UAT-02 | Row count `fact_order_items` | Table view | 111,752 | `outputs/powerbi_views_checks.csv` | | |
| UAT-03 | Row count `dim_customer` | Table view | 97,905 | `outputs/powerbi_views_checks.csv` | | |
| UAT-04 | Row count `dim_seller` | Table view | 3,029 | `outputs/powerbi_views_checks.csv` | | |
| UAT-05 | Row count `dim_product` | Table view | 32,951 | `outputs/powerbi_views_checks.csv` | | |
| UAT-06 | Row count `dim_date` | Table view | 730 | `outputs/powerbi_views_checks.csv` | | |
| UAT-07 | Row count `rfm_customer_segments` | Table view | 94,703 | `outputs/rfm_segments.csv` (sum of `customers`) | | |
| UAT-08 | No type errors | Power Query → View → Column quality, every table | 0% Error in every column | `powerbi/model_spec.md` §3 | | |
| UAT-09 | Zip prefixes keep leading zeros | Table view, `dim_customer[customer_zip_code_prefix]`, sort ascending | First value starts with `0` (5 characters) | `powerbi/model_spec.md` §3 | | |
| UAT-10 | Relationships R1-R6, R8 exist | Model view → Manage relationships | 7 active, all *Many to one*, *Single* | `powerbi/model_spec.md` §4 | | |
| UAT-11 | R2 is Many to one / Single | Manage relationships → R2 | Many to one (*:1), Single (else R8 must be inactive) | `powerbi/model_spec.md` §4 | | |
| UAT-12 | Date table marked | Data pane → `dim_date` icon | Marked as date table on `date_key` | `powerbi/model_spec.md` §5 | | |

## B. KPI measures (Checks page, no slicers)
| ID | Measure | Filter context | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-13 | Total Revenue (R$) | none | R$ 13,449,529.68 | `outputs/powerbi_expected_values.csv` | | |
| UAT-14 | Orders | none | 97,905 | `outputs/powerbi_expected_values.csv` | | |
| UAT-15 | AOV (R$) | none | R$ 137.37 | `outputs/powerbi_expected_values.csv` | | |
| UAT-16 | Customers | none | 94,703 | `outputs/powerbi_expected_values.csv` | | |
| UAT-17 | Repeat Customer % | none | 3.03% | `outputs/powerbi_expected_values.csv` | | |
| UAT-18 | Delivered Orders | none | 96,201 | `outputs/powerbi_expected_values.csv` | | |
| UAT-19 | On-Time % | none | 93.21% | `outputs/powerbi_expected_values.csv` | | |
| UAT-20 | Late % | none | 6.79% | `outputs/powerbi_expected_values.csv` | | |
| UAT-21 | Avg Delay (days) | none | −11.81 | `outputs/powerbi_expected_values.csv` | | |
| UAT-22 | Avg Delivery Days | none | 12.48 | `outputs/powerbi_expected_values.csv` | | |
| UAT-23 | Avg Review | none | 4.12 | `outputs/powerbi_expected_values.csv` | | |
| UAT-24 | Avg Review (delivered) | none | 4.16 | `outputs/powerbi_expected_values.csv` | | |
| UAT-25 | Revenue MoM % | `year_month_label` = 2018-08 | −3.32% | `outputs/powerbi_expected_values.csv` | | |
| UAT-26 | Revenue MoM % | `year_month_label` = 2017-11 | 52.06% | `outputs/powerbi_expected_values.csv` | | |
| UAT-27 | Excess Late Orders | `dim_seller[is_ranked_30plus_orders]` = 1 | −45.41 | `outputs/powerbi_expected_values.csv` | | |
| UAT-28 | Excess Late Orders | seller `4a3ca9315b744ce9f8e9374361493884` | 51.70 | `outputs/powerbi_expected_values.csv` | | |
| UAT-29 | Seller Late % | `is_ranked_30plus_orders` = 1 | 6.73% | `outputs/powerbi_expected_values.csv` | | |
| UAT-30 | Platform Late Rate | any slicer selection (e.g. one state) | 6.79% (must not change) | `outputs/powerbi_expected_values.csv` | | |

## C. Visual checks (by page)
| ID | Page / visual | Check | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-31 | 1.6 Revenue by month | Tooltip on 2017-11 | Revenue MoM % 52.06% | `outputs/revenue_mom.csv` | | |
| UAT-32 | 1.7 On-time % by month | Value for 2018-03 | 81.04% | `outputs/delivery_ontime_by_month.csv` | | |
| UAT-33 | 1.8 Top 10 states | SP revenue | R$ 5,150,778.70 | `outputs/revenue_pareto_state.csv` | | |
| UAT-34 | 1.9 Category Pareto | Tooltip `Category Cumulative Revenue %`, health_beauty / pet_shop | 9.30% / 81.27% | `outputs/revenue_pareto_category.csv` | | |
| UAT-35 | 2.1 Review by delay bucket | Early / 7+ days late | 4.29 / 1.70 | `outputs/delivery_buckets_vs_review.csv` | | |
| UAT-36 | 2.1 Review by delay bucket | Bucket order on the axis | Early, On time, 1-3, 4-7, 7+ days late | `outputs/delivery_buckets_vs_review.csv` | | |
| UAT-37 | 2.3 Late % by state | AL / MA | 21.46% / 17.53% | `outputs/delivery_ontime_by_state.csv` | | |
| UAT-38 | 2.3 Late % by state | Bars above platform average are orange, others blue | Rule applied | `powerbi/page_layout.md` colour rule | | |
| UAT-39 | 2.4 Late % by category | audio (100+ orders filter on) | 11.85% | `outputs/delivery_late_by_category.csv` | | |
| UAT-40 | 2.5 Distance bands | 0-100 / 1,500+ km | 4.49% / 11.64% | `outputs/distance_vs_delay_bands.csv` | | |
| UAT-41 | 3.1 RFM segments | New - high value: % customers / % revenue | 15.56% / 29.40% | `outputs/rfm_segments.csv` | | |
| UAT-42 | 3.3 Cohort matrix | Cohort 2017-10, month 1 | 0.71% | `outputs/retention_cohort_long.csv` | | |
| UAT-43 | 3.5 First-order test | Late / on time return within 6 months | 1.47% / 1.79% | `outputs/retention_first_order_late_vs_on_time.csv` | | |
| UAT-44 | 4.1 Seller table | Row 1 by Excess Late Orders | seller `4a3ca931…`, 51.70 | `outputs/seller_late_rate_ranking.csv` | | |
| UAT-45 | 4.3 Late orders by decile | Decile 1 / decile 3 share | 15.56% / 23.60% | `outputs/seller_late_rate_by_decile.csv` | | |

## D. Interaction checks
| ID | Check | How to test | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-46 | Date slicer filters all pages | Set 2018-01-01 to 2018-08-31 on page 1, open pages 2 and 4 | Same range shown, visuals change | `powerbi/page_layout.md` slicer plan | | |
| UAT-47 | Static visuals ignore slicers | Change the date slicer, watch 2.5, 3.2, 3.3, 3.5 | Values unchanged; subtitle says "not filtered" | `powerbi/page_layout.md` slicer plan | | |
| UAT-48 | Customer state slicer | Select SP on page 1 | Cards change; Platform Late Rate stays 6.79% | `outputs/powerbi_expected_values.csv` | | |
| UAT-49 | Drill-through | Right-click seller `4a3ca931…` → Drill through → Seller Detail | 1,772 orders, 9.71% late, −9.53 days, 3.85 stars, R$ 200,326.12, 51.70 excess | `outputs/seller_late_rate_ranking.csv`, `excel/seller_scorecard_data.csv` | | |
| UAT-50 | Drill-through Back button | Ctrl+click Back | Returns to Seller Performance | `powerbi/build_steps.md` Step 11 | | |
| UAT-51 | Insight titles | Read every title | Each states a finding and matches `page_layout.md` | `powerbi/page_layout.md` | | |

## Sign-off
| Total checks | Passed | Failed | Tester | Date |
|---|---|---|---|---|
| 51 | | | | |
