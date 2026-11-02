# UAT checklist: Tableau Public dashboard vs SQL
**Project:** Olist Customer Retention & Delivery Experience Analysis
**Version:** 2.0 | **Date:** 2026-11-02 | **Tester:** Bala Hariharan B
**Build:** Tableau Public workbook "Olist Customer Retention & Delivery" (built with `tableau/build_steps.md`).
The Power BI design in `powerbi/` uses the same expected values and can be tested with the same rows.

**How to test:** unless a row says otherwise, **clear all filters**. Read the value from the Checks sheet, a label or a
tooltip and write it in **Actual**. **Pass** = equal to **Expected** at the precision shown (percentages to 2 decimals,
money to the cent, averages to 2 decimals). Every expected value comes from the file in **Source** (computed in SQL from
the same views Tableau loads). On a **Fail**: check the field's data type, then which table the field came from
(`tableau/data_model.md` §4), then the formula in `tableau/calculated_fields.md`.

## A. Data model checks
| ID | Check | How to test in Tableau | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-01 | Rows in `fact_orders` | `fact_orders (Count)` on Text | 97,905 | `outputs/powerbi_views_checks.csv` | | |
| UAT-02 | Rows in `fact_order_items` | `fact_order_items (Count)` | 111,752 | `outputs/powerbi_views_checks.csv` | | |
| UAT-03 | Rows in `dim_customer` | `dim_customer (Count)` | 97,905 | `outputs/powerbi_views_checks.csv` | | |
| UAT-04 | Rows in `dim_seller` | `dim_seller (Count)` | 3,029 | `outputs/powerbi_views_checks.csv` | | |
| UAT-05 | Rows in `dim_product` | `dim_product (Count)` | 32,951 | `outputs/powerbi_views_checks.csv` | | |
| UAT-06 | Rows in `dim_date` | `dim_date (Count)` | 730 | `outputs/powerbi_views_checks.csv` | | |
| UAT-07 | Rows in `rfm_customer_segments` | `rfm_customer_segments (Count)` | 94,703 | `outputs/rfm_segments.csv` (sum of `customers`) | | |
| UAT-08 | IDs and zips are String | Data Source tab: type icon above each ID/zip column | Abc (String) for every field listed in `data_model.md` §3 | `tableau/data_model.md` §3 | | |
| UAT-09 | Zip prefixes keep leading zeros | `customer_zip_code_prefix` on Rows, sort ascending | First value starts with `0` (5 characters) | `tableau/data_model.md` §3 | | |
| UAT-10 | Relationships T1-T6 | Data Source tab: click each noodle | 6 relationships, fields as in `data_model.md` §2, tree with `fact_orders` as root | `tableau/data_model.md` §2 | | |
| UAT-11 | Static sources separate | Data pane: data source list | `retention_cohort_long`, `distance_vs_delay_bands`, `retention_first_order_late_vs_on_time`, `rfm_segments` are their own sources | `tableau/data_model.md` §1 | | |
| UAT-12 | Dates typed as Date | Data pane icons for `date_key`, `purchase_date` | Calendar icon (Date) | `tableau/data_model.md` §3 | | |

## B. KPI calculated fields (Checks sheet, no filters)
| ID | Field | Filter / context | Expected | Source | Actual | Pass/Fail |
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
| UAT-25 | Revenue MoM % | sheet E2 tooltip, month = Aug 2018 | −3.32% | `outputs/powerbi_expected_values.csv` | | |
| UAT-26 | Revenue MoM % | sheet E2 tooltip, month = Nov 2017 | 52.06% | `outputs/powerbi_expected_values.csv` | | |
| UAT-27 | Excess Late Orders | filter `is_ranked_30plus_orders` = 1 | −45.41 | `outputs/powerbi_expected_values.csv` | | |
| UAT-28 | Excess Late Orders | seller `4a3ca9315b744ce9f8e9374361493884` | 51.70 | `outputs/powerbi_expected_values.csv` | | |
| UAT-29 | Seller Late % | filter `is_ranked_30plus_orders` = 1 | 6.73% | `outputs/powerbi_expected_values.csv` | | |
| UAT-30 | Platform Late Rate | with any filter (e.g. state = SP) | 6.79% (must not change) | `outputs/powerbi_expected_values.csv` | | |

## C. Sheet checks
| ID | Sheet | Check | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-31 | E2 Revenue by Month | Tooltip on Nov 2017 | Revenue MoM % 52.06% | `outputs/revenue_mom.csv` | | |
| UAT-32 | E3 On-Time % by Month | Value for Mar 2018 | 81.04% | `outputs/delivery_ontime_by_month.csv` | | |
| UAT-33 | E4 Top 10 States | SP revenue | R$ 5,150,778.70 | `outputs/revenue_pareto_state.csv` | | |
| UAT-34 | E5 Category Pareto | Tooltip `Category Cumulative Revenue %`, health_beauty / pet_shop | 9.30% / 81.27% | `outputs/revenue_pareto_category.csv` | | |
| UAT-35 | D1 Review by Delay Bucket | Early / 7+ days late | 4.29 / 1.70 | `outputs/delivery_buckets_vs_review.csv` | | |
| UAT-36 | D1 Review by Delay Bucket | Bucket order on the axis | Early, On time, 1-3, 4-7, 7+ days late | `outputs/delivery_buckets_vs_review.csv` | | |
| UAT-37 | D2 Late % by State | AL / MA | 21.46% / 17.53% | `outputs/delivery_ontime_by_state.csv` | | |
| UAT-38 | D2 Late % by State | States above the platform average are orange (#EB6834), others blue (#2A78D6) | Colour rule applied | `powerbi/page_layout.md` colour rule | | |
| UAT-39 | D3 Late % by Category | audio (100+ orders filter on) | 11.85% | `outputs/delivery_late_by_category.csv` | | |
| UAT-40 | D4 Late % by Distance | 0-100 / 1,500+ km | 4.49% / 11.64% | `outputs/distance_vs_delay_bands.csv` | | |
| UAT-41 | C1 Segment Share | New - high value: % customers / % revenue | 15.56% / 29.40% | `outputs/rfm_segments.csv` | | |
| UAT-42 | C3 Cohort Heatmap | Cohort 2017-10, month 1 | 0.71% | `outputs/retention_cohort_long.csv` | | |
| UAT-43 | C5 First-Order Test | Late / on time return within 6 months | 1.47% / 1.79% | `outputs/retention_first_order_late_vs_on_time.csv` | | |
| UAT-44 | S1 Seller Table | Row 1 by Excess Late Orders | seller `4a3ca931…`, 51.70 | `outputs/seller_late_rate_ranking.csv` | | |
| UAT-45 | S3 Late Share by Decile | Decile 1 / decile 3 | 15.56% / 23.60% | `outputs/seller_late_rate_by_decile.csv` | | |

## D. Interaction and publishing checks
| ID | Check | How to test | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-46 | Date filter reaches every Olist sheet | Set 2018-01-01 to 2018-08-31 on Executive Overview, open the other dashboards | Same range applied; Olist sheets change | `tableau/build_steps.md` Step 6 | | |
| UAT-47 | Static sheets ignore filters | Change the date filter, watch D4, C2, C3, C5 | Values unchanged; subtitle says "not filtered" | `tableau/build_steps.md` Step 6 | | |
| UAT-48 | Repeat Customer % follows the date filter | Note C4 with no filter (3.03%), then set the date filter to 2018 only | Value changes (INCLUDE LOD respects filters) | `tableau/calculated_fields.md` §2 | | |
| UAT-49 | Customer state filter | Select SP on Executive Overview | KPIs change; `Platform Late Rate` stays 6.79% | `outputs/powerbi_expected_values.csv` | | |
| UAT-50 | Filter action (drill-through stand-in) | Click seller `4a3ca931…` in S1 | Jumps to Seller Detail: 1,772 orders, 9.71% late, −9.53 days, 3.85 stars, R$ 200,326.12, 51.70 excess | `outputs/seller_late_rate_ranking.csv`, `excel/seller_scorecard_data.csv` | | |
| UAT-51 | Back navigation | Click the navigation button on Seller Detail | Returns to Seller Performance | `tableau/build_steps.md` Step 7 | | |
| UAT-52 | Insight titles | Read every sheet and dashboard title | Each states a finding and matches `powerbi/page_layout.md` | `powerbi/page_layout.md` | | |
| UAT-53 | Published link | Open the Tableau Public link in a private browser window (signed out) | Dashboard loads without sign-in (it is public) | `tableau/build_steps.md` Step 9 | | |

## Sign-off
| Total checks | Passed | Failed | Tester | Date |
|---|---|---|---|---|
| 53 | | | | |
