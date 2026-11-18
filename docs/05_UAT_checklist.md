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
| UAT-01 | Row count `fact_orders` | Table view, bottom-left count | 97,905 | `outputs/powerbi_views_checks.csv` | 97,905 (Stage 5 check 2) | PASS |
| UAT-02 | Row count `fact_order_items` | Table view | 111,752 | `outputs/powerbi_views_checks.csv` | Matches Expected (tester-reported) | PASS |
| UAT-03 | Row count `dim_customer` | Table view | 97,905 | `outputs/powerbi_views_checks.csv` | Matches Expected (tester-reported) | PASS |
| UAT-04 | Row count `dim_seller` | Table view | 3,029 | `outputs/powerbi_views_checks.csv` | Matches Expected (tester-reported) | PASS |
| UAT-05 | Row count `dim_product` | Table view | 32,951 | `outputs/powerbi_views_checks.csv` | Matches Expected (tester-reported) | PASS |
| UAT-06 | Row count `dim_date` | Table view | 730 | `outputs/powerbi_views_checks.csv` | Matches Expected (tester-reported) | PASS |
| UAT-07 | Row count `rfm_customer_segments` | Table view | 94,703 | `outputs/rfm_segments.csv` (sum of `customers`) | Table is not in the built model | N/A |
| UAT-08 | No type errors | Power Query → View → Column quality, every table | 0% Error in every column | `powerbi/model_spec.md` §3 | Matches Expected (tester-reported) | PASS |
| UAT-09 | Zip prefixes keep leading zeros | Table view, `dim_customer[customer_zip_code_prefix]`, sort ascending | First value starts with `0` (5 characters) | `powerbi/model_spec.md` §3 | Matches Expected (tester-reported) | PASS |
| UAT-10 | Relationships R1-R6, R8 exist | Model view → Manage relationships | 7 active, all *Many to one*, *Single* | `powerbi/model_spec.md` §4 | 6 active (R1, R2, R4, R5, R6, R8) + 1 inactive (R7); R3 not built | Correction required |
| UAT-11 | R2 is Many to one / Single | Manage relationships → R2 | Many to one (*:1), Single (else R8 must be inactive) | `powerbi/model_spec.md` §4 | Many to one, Single (`relationships.tmdl`) | PASS |
| UAT-12 | Date table marked | Data pane → `dim_date` icon | Marked as date table on `date_key` | `powerbi/model_spec.md` §5 | `dataCategory: Time`, key `date_key` (`dim_date.tmdl`) | PASS |

## B. KPI measures (Checks page, no slicers)
| ID | Measure | Filter context | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-13 | Total Revenue (R$) | none | R$ 13,449,529.68 | `outputs/powerbi_expected_values.csv` | R$ 13,449,529.68 (Stage 5 check 1) | PASS |
| UAT-14 | Orders | none | 97,905 | `outputs/powerbi_expected_values.csv` | 97,905 (Stage 5 check 2) | PASS |
| UAT-15 | AOV (R$) | none | R$ 137.37 | `outputs/powerbi_expected_values.csv` | R$ 137.37 (Stage 5 check 3) | PASS |
| UAT-16 | Customers | none | 94,703 | `outputs/powerbi_expected_values.csv` | 94,703 (Stage 5 check 4) | PASS |
| UAT-17 | Repeat Customer % | none | 3.03% | `outputs/powerbi_expected_values.csv` | 3.03% (Stage 5 check 5) | PASS |
| UAT-18 | Delivered Orders | none | 96,201 | `outputs/powerbi_expected_values.csv` | 96,201 (Stage 5 check 6) | PASS |
| UAT-19 | On-Time % | none | 93.21% | `outputs/powerbi_expected_values.csv` | 93.21% (Stage 5 check 7) | PASS |
| UAT-20 | Late % | none | 6.79% | `outputs/powerbi_expected_values.csv` | 6.79% (Stage 5 check 8) | PASS |
| UAT-21 | Avg Delay (days) | none | −11.81 | `outputs/powerbi_expected_values.csv` | −11.81 (Stage 5 check 9) | PASS |
| UAT-22 | Avg Delivery Days | none | 12.48 | `outputs/powerbi_expected_values.csv` | 12.48 (Stage 5 check 10) | PASS |
| UAT-23 | Avg Review | none | 4.12 | `outputs/powerbi_expected_values.csv` | 4.12 (Stage 5 check 11) | PASS |
| UAT-24 | Avg Review (delivered) | none | 4.16 | `outputs/powerbi_expected_values.csv` | 4.16 (Stage 5 check 12) | PASS |
| UAT-25 | Revenue MoM % | `year_month_label` = 2018-08 | −3.32% | `outputs/powerbi_expected_values.csv` | −3.32% (Stage 5 check 13) | PASS |
| UAT-26 | Revenue MoM % | `year_month_label` = 2017-11 | 52.06% | `outputs/powerbi_expected_values.csv` | 52.06% (Stage 5 check 14) | PASS |
| UAT-27 | Excess Late Orders | `dim_seller[is_ranked_30plus_orders]` = 1 | −45.41 | `outputs/powerbi_expected_values.csv` | −45.41 (Stage 5 check 15) | PASS |
| UAT-28 | Excess Late Orders | seller `4a3ca9315b744ce9f8e9374361493884` | 51.70 | `outputs/powerbi_expected_values.csv` | 51.70 (Stage 5 check 16) | PASS |
| UAT-29 | Seller Late % | `is_ranked_30plus_orders` = 1 | 6.73% | `outputs/powerbi_expected_values.csv` | 6.73% (Stage 5 check 17) | PASS |
| UAT-30 | Platform Late Rate | any slicer selection (e.g. one state) | 6.79% (must not change) | `outputs/powerbi_expected_values.csv` | 6.79% with and without filters (Stage 5 checks 18, 19) | PASS |

## C. Visual checks (by page)
| ID | Page / visual | Check | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-31 | 1.6 Revenue by month | Tooltip on 2017-11 | Revenue MoM % 52.06% | `outputs/revenue_mom.csv` | Matches Expected (tester-reported) | PASS |
| UAT-32 | 1.7 On-time % by month | Value for 2018-03 | 81.04% | `outputs/delivery_ontime_by_month.csv` | Matches Expected (tester-reported) | PASS |
| UAT-33 | 1.8 Top 10 states | SP revenue | R$ 5,150,778.70 | `outputs/revenue_pareto_state.csv` | Matches Expected (tester-reported) | PASS |
| UAT-34 | 1.9 Category Pareto | Tooltip `Category Cumulative Revenue %`, health_beauty / pet_shop | 9.30% / 81.27% | `outputs/revenue_pareto_category.csv` | Matches Expected (tester-reported) | PASS |
| UAT-35 | 2.1 Review by delay bucket | Early / 7+ days late | 4.29 / 1.70 | `outputs/delivery_buckets_vs_review.csv` | Matches Expected (tester-reported) | PASS |
| UAT-36 | 2.1 Review by delay bucket | Bucket order on the axis | Early, On time, 1-3, 4-7, 7+ days late | `outputs/delivery_buckets_vs_review.csv` | Matches Expected (tester-reported); axis sorts by `delay_bucket_order` | PASS |
| UAT-37 | 2.3 Late % by state | AL / MA | 21.46% / 17.53% | `outputs/delivery_ontime_by_state.csv` | Matches Expected (tester-reported) | PASS |
| UAT-38 | 2.3 Late % by state | Bars above platform average are amber, others teal | Amber `#E5A642` above `[Platform Late Rate]`, teal `#168C89` at or below it | `powerbi/page_layout.md` colour rule | Rule matches all 27 states in `outputs/delivery_ontime_by_state.csv`; Desktop retest not recorded | Retest required |
| UAT-39 | 2.4 Late % by category | audio (100+ orders filter on) | 11.85% | `outputs/delivery_late_by_category.csv` | Visual is not in the built report | N/A |
| UAT-40 | 2.5 Distance bands | 0-100 / 1,500+ km | 4.49% / 11.64% | `outputs/distance_vs_delay_bands.csv` | Visual is not in the built report | N/A |
| UAT-41 | 3.1 RFM segments | New - high value: % customers / % revenue | 15.56% / 29.40% | `outputs/rfm_segments.csv` | Visual is not in the built report | N/A |
| UAT-42 | 3.3 Cohort matrix | Cohort 2017-10, month 1 | 0.71% | `outputs/retention_cohort_long.csv` | Matches Expected (tester-reported) | PASS |
| UAT-43 | 3.5 First-order test | Late / on time return within 6 months | 1.47% / 1.79% | `outputs/retention_first_order_late_vs_on_time.csv` | Visual is not in the built report | N/A |
| UAT-44 | 4.1 Seller table | Row 1 by Excess Late Orders | seller `4a3ca931…`, 51.70 | `outputs/seller_late_rate_ranking.csv` | Matches Expected (tester-reported) | PASS |
| UAT-45 | 4.3 Late orders by decile | Decile 1 / decile 3 share | 15.56% / 23.60% | `outputs/seller_late_rate_by_decile.csv` | Matches Expected (tester-reported); share is in the chart tooltip | PASS |

## D. Interaction checks
| ID | Check | How to test | Expected | Source | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| UAT-46 | Date slicer filters all pages | Set 2018-01-01 to 2018-08-31 on page 1, open pages 2 and 4 | Same range shown, visuals change | `powerbi/page_layout.md` slicer plan | Matches Expected (tester-reported) | PASS |
| UAT-47 | Static visuals ignore slicers | Change the date slicer, watch 2.5, 3.2, 3.3, 3.5 | Values unchanged; subtitle says "not filtered" | `powerbi/page_layout.md` slicer plan | Not run: only the cohort matrix (3.3) exists | Correction required |
| UAT-48 | Customer state slicer | Select SP on page 1 | Cards change; Platform Late Rate stays 6.79% | `outputs/powerbi_expected_values.csv` | Matches Expected (tester-reported) | PASS |
| UAT-49 | Drill-through | Right-click seller `4a3ca931…` → Drill through → Seller Detail | 1,772 orders, 9.71% late, −9.53 days, 3.85 stars, R$ 200,326.12, 51.70 excess | `outputs/seller_late_rate_ranking.csv`, `excel/seller_scorecard_data.csv` | Matches Expected (tester-reported) | PASS |
| UAT-50 | Drill-through Back button | Ctrl+click Back | Returns to Seller Performance | `powerbi/build_steps.md` Step 11 | Matches Expected (tester-reported) | PASS |
| UAT-51 | Insight titles | Read every title | Each states a finding and matches `page_layout.md` | `powerbi/page_layout.md` | 1 of 20 titles matches `page_layout.md`; 6 subtitles state a finding | Correction required |

## Sign-off
| Total checks | Passed | Failed | Tester | Date |
|---|---|---|---|---|
| 51 | 42 | 0 | | |

## Execution notes (recorded 2026-11-18)
**Result:** 42 PASS, 0 Fail, 5 N/A, 3 Correction required, 1 Retest required. Only PASS rows are counted as passed.
The Tester and Date cells in the sign-off stay blank for the tester to complete.

**Build tested:** `powerbi/Olist Retention.pbip` (5 pages plus the hidden Seller Detail drill-through). The header
still names the original `.pbix`, and this checklist was written for the earlier 4-page design in `powerbi/page_layout.md`.

### Evidence used
| Evidence | Checks | What it proves |
|---|---|---|
| Power BI query results in `outputs/stage5_validation_results.csv` (19 of 19 PASS) | UAT-01, UAT-13 to UAT-30 | The value returned by the model; **Actual** shows that value at the checklist's precision |
| Model definition files in `powerbi/Olist Retention.SemanticModel/definition/` | UAT-11, UAT-12 | The saved relationship and date table settings |
| Manual test in Power BI Desktop, reported as passed by the tester | UAT-02 to UAT-06, UAT-08, UAT-09, UAT-31 to UAT-37, UAT-42, UAT-44 to UAT-46, UAT-48 to UAT-50 | The tester's confirmation. The on-screen values and screenshots were not saved, so **Actual** does not repeat a number |

### Where a passed check differs from its written location
| ID | Written as | Tested in the built report |
|---|---|---|
| UAT-13 to UAT-30 | Checks page | No Checks page exists; values come from `powerbi/stage5_validation.dax` |
| UAT-31 | 1.6 Revenue by month | Executive Overview, "Monthly revenue trend" |
| UAT-32 | 1.7 On-time % by month | Delivery Performance, "Delivery performance by purchase month" |
| UAT-33 | 1.8 Top 10 states | Executive Overview, "Revenue by customer state" (all states) |
| UAT-34 | 1.9 Category Pareto | Executive Overview, "Revenue by product category" |
| UAT-35, UAT-36 | 2.1 Review by delay bucket | Delivery Performance, "Review score vs delivery delay" |
| UAT-37, UAT-38 | 2.3 Late % by state | Delivery Performance, "Late % by customer state" |
| UAT-42 | 3.3 Cohort matrix | Customer Retention, "Cohort retention: % of each cohort buying again" |
| UAT-44 | 4.1 Seller table | Seller Performance, "Seller ranking: worst performing sellers first" |
| UAT-45 | 4.3 Late orders by decile | Seller Performance, "Excess late orders by decile" (share in the tooltip) |
| UAT-48 | Platform Late Rate on page 1 | Tooltip on Delivery Performance, "Late % by customer state" |

### Checks not passed
| ID | Status | Finding in the built report | Action |
|---|---|---|---|
| UAT-07 | N/A | `rfm_customer_segments` is not one of the model's tables | RFM stays outside the dashboard; results remain in `outputs/rfm_segments.csv` |
| UAT-10 | Correction required | Relationships R1, R2, R4, R5, R6 and R8 are active, R7 is inactive, and R3 is not built because it joins the RFM table | Change Expected to "6 active + R7 inactive, all Many to one, Single", then retest |
| UAT-38 | Retest required | The colour rule changed to amber and teal after the manual test | Confirm the bars in Power BI Desktop and record the result |
| UAT-39 | N/A | No Late % by category visual | Results remain in `outputs/delivery_late_by_category.csv` |
| UAT-40 | N/A | No distance band visual or table | Results remain in `outputs/distance_vs_delay_bands.csv` |
| UAT-41 | N/A | No RFM visual | Results remain in `outputs/rfm_segments.csv` |
| UAT-43 | N/A | No first-order test visual | Results remain in `outputs/retention_first_order_late_vs_on_time.csv` |
| UAT-47 | Correction required | Visuals 2.5, 3.2 and 3.5 are not built. The cohort matrix uses a live measure that ignores the date slicer but not the customer state slicer, and its subtitle reads "the date slicer does not apply" | Rewrite the check for the cohort matrix and the date slicer only, then retest |
| UAT-51 | Correction required | Only "What this seller ships" matches `page_layout.md`. Most built titles describe the visual, and 6 subtitles state a finding | Compare titles with the built report instead of `page_layout.md`, then retest |

### Visual retest after Navy Atlas styling (recorded 2026-11-18)
The Navy Atlas backgrounds, visual styling, Back button and KPI icon layers were applied after the manual UAT above.
**No post-styling Power BI Desktop retest results or screenshots have been saved**, so no check below is recorded as
retested. The tester reported that the backgrounds looked good and that Seller Detail looked good apart from the Back
button, which was restyled afterwards. PASS results above describe the build tested before this styling.

| Checks | What changed | File-based evidence | Desktop retest |
|---|---|---|---|
| UAT-31 to UAT-37, UAT-42, UAT-44, UAT-45 | Colours and formatting only | Fields, filters, sort order and positions match commit `194d2b5` | Not recorded |
| UAT-38 | Rule shown as amber and teal instead of orange and blue | Colour rule matches all 27 states in `outputs/delivery_ontime_by_state.csv` | **Required** |
| UAT-46, UAT-48 | Slicers restyled | Slicer fields and modes match commit `194d2b5` | Not recorded |
| UAT-49, UAT-50 | Seller Detail cards and Back button restyled | Drill-through binding and Back action are unchanged | Not recorded |
| 31 KPI cards | Decorative layers added behind transparent cards | Report validator verifies all 31 layers | Not recorded |
