# Power BI page layout
Four report pages plus one drill-through page. Canvas: **16:9**. Every visual answers a user story
(`docs/03_user_stories.md`) and has an **insight title**: a sentence that states the finding, with each number taken
from the `outputs/` file named in the *Source* column. Measures are defined in `powerbi/dax_measures.md`.

## Colour rule (one highlight colour for "bad")
| Role | Colour | Used for |
|---|---|---|
| **Bad (the only highlight)** | **Orange `#EB6834`** | Worse than the platform or the target: late buckets, states/sellers/categories with Late % above `[Platform Late Rate]`, decile 1, segment "Lost" |
| Default | Blue `#2A78D6` | Every other bar, line and card value |
| Context | Grey `#B5B4AF` | Reference lines (platform average), axis gridlines, "not significant" bars |
| Text | `#0B0B0B` titles, `#52514E` subtitles/labels | Never coloured by series |

- Orange is **never** used for anything except "bad", so a reader learns it once.
- Conditional colours come from the measures `Colour - Late vs Platform` / `Colour - Seller Late vs Platform`
  (*Format → Bars → Colors → fx → Field value*), so the rule is the same on every page.
- Colour is never the only signal: the title, data labels or a reference line say the same thing.

## Slicer plan
| Slicer | Field | Style | Pages | Sync |
|---|---|---|---|---|
| Purchase date | `dim_date[date_key]` | Between (date range) | All four + drill-through | Synced (View → Sync slicers) |
| Customer state | `dim_customer[customer_state]` | Dropdown, multi-select | Executive Overview, Delivery vs Satisfaction | Synced on those two |
| RFM segment | `rfm_customer_segments[segment]` | Vertical list | Customer Segments | – |
| Seller state | `dim_seller[seller_state]` | Dropdown | Seller Performance | – |
| Late-rate decile | `dim_seller[late_rate_decile]` | Tiles (1-10) | Seller Performance | – |
| Category | `dim_product[category_english]` | Dropdown with search | Seller Performance | – |

**Rules readers must know (put them in a small grey note under the slicers):**
- *Customer state* filters `fact_orders` only; it has no effect on the Seller Performance page (by design, see model_spec.md §4).
- Visuals built on **static tables** (cohort matrix, distance bands, first-order test, segment summary) show the whole
  period and ignore slicers. Their subtitles say **"Whole period 2017-01 to 2018-08, not filtered by slicers."**
- RFM segments are scored once over the whole window; the date slicer does not re-score them.

---

## Page 1: Executive Overview
Layout: KPI cards across the top, two trend charts in the middle, two ranking charts at the bottom.

| # | Visual | Fields / measure | User story | Insight title | Source |
|---|---|---|---|---|---|
| 1.1 | Card | `[Total Revenue (R$)]` (format R$ millions) | US-06 | "Revenue: R$ 13.45M from 97,905 orders" | `powerbi_expected_values.csv` |
| 1.2 | Card | `[AOV (R$)]` | US-06 | "Average order: R$ 137.37" | `powerbi_expected_values.csv` |
| 1.3 | Card | `[Repeat Customer %]` | US-01 | "Only 3.03% of customers buy twice" | `retention_repeat_customers.csv` |
| 1.4 | Card | `[On-Time %]` | US-04 | "93.21% of orders arrive on time" | `delivery_kpis_overall.csv` |
| 1.5 | Card | `[Avg Review (delivered)]` | US-02 | "Average review: 4.16 stars" | `delivery_kpis_overall.csv` |
| 1.6 | Clustered column | X `dim_date[year_month_label]`, Y `[Total Revenue (R$)]`; tooltip `[Revenue MoM %]` | US-06 | "Black Friday 2017 lifted revenue 52% in one month" | `revenue_mom.csv` |
| 1.7 | Line | X `dim_date[year_month_label]`, Y `[On-Time %]`; marker for 2018-03 in orange | US-04 | "On-time delivery fell to 81% in March 2018" | `delivery_ontime_by_month.csv` |
| 1.8 | Bar (horizontal), Top N = 10 by revenue | Y `dim_customer[customer_state]`, X `[Total Revenue (R$)]` | US-06 | "São Paulo alone brings 38% of revenue" | `revenue_pareto_state.csv` |
| 1.9 | Bar (horizontal), Top N = 20 | Y `dim_product[category_english]`, X `[Item Revenue (R$)]`; tooltip `[Category Cumulative Revenue %]` | US-06 | "18 of 74 categories make 80% of revenue" | `revenue_pareto_summary.csv` |

## Page 2: Delivery vs Satisfaction
Layout: the review-by-delay chart large on the left with the test result under it; state, category and distance on the right.

| # | Visual | Fields / measure | User story | Insight title | Source |
|---|---|---|---|---|---|
| 2.1 | Clustered column | X `fact_orders[delay_bucket]` (sorted by `delay_bucket_order`), Y `[Avg Review (delivered)]`; colour: late buckets orange; data labels on | US-02 | "Orders 7+ days late average 1.7 stars vs 4.3 when early" | `delivery_buckets_vs_review.csv` |
| 2.2 | Text box (or multi-row card) | Copy the two lines of the test conclusion | US-02 | "Late orders score 2.02 stars lower (0.76 when the review is written after delivery)" | `hypothesis_test_conclusion.txt` |
| 2.3 | Bar (horizontal), sorted by Late % | Y `dim_customer[customer_state]`, X `[Late %]`; colour `Colour - Late vs Platform`; constant line at `[Platform Late Rate]` (grey) | US-04 | "AL and MA: 21% and 18% of orders late vs 6.8% overall" | `delivery_ontime_by_state.csv` |
| 2.4 | Bar (horizontal), Top N = 15 by `[Seller Late %]`; visual filter `[Seller Delivered Orders]` ≥ 100 | Y `dim_product[category_english]`, X `[Seller Late %]`; colour `Colour - Seller Late vs Platform` | US-04 | "Audio is the most-delayed category: 11.9% late" | `delivery_late_by_category.csv` |
| 2.5 | Clustered column (static table) | X `distance_vs_delay_bands[distance_band]`, Y `late_pct` (Don't summarize / Sum); subtitle "Whole period, not filtered" | US-04 | "Late % rises from 4.5% under 100 km to 11.6% beyond 1,500 km" | `distance_vs_delay_bands.csv` |

Note for 2.4: an order with items in two categories counts once in each, as in the SQL output.

## Page 3: Customer Segments
Layout: segment chart and segment table on top; cohort heatmap across the bottom; two small visuals at the right.

| # | Visual | Fields / measure | User story | Insight title | Source |
|---|---|---|---|---|---|
| 3.1 | Clustered bar | Y `rfm_customer_segments[segment]`, X `[% of Customers]` (blue) and `[% of Revenue]` (grey); legend on | US-05 | "New – high value: 16% of customers, 29% of revenue" | `rfm_segments.csv` |
| 3.2 | Table (static) | `rfm_segment_summary`: segment, customers, pct_of_customers, revenue_brl, revenue_share_pct, suggested_action | US-05 | "Eight segments, one action each: start with New – high value" | `rfm_segments.csv` |
| 3.3 | Matrix (static) | Rows `retention_cohort_long[cohort_month]`, Columns `month_offset` (filter: `month_offset` 1 to 12), Values `[Cohort Retention %]`; background colour scale white → blue | US-01 | "No cohort tops 0.71% repeat buyers in any month" | `retention_cohort_long.csv` |
| 3.4 | Card | `[Repeat Customer %]` | US-01 | "Only 3.03% of customers bought twice in 20 months" | `retention_repeat_customers.csv` |
| 3.5 | Clustered column (static) | X `retention_first_order_late_vs_on_time[first_order_delivery]` (exclude "not in delivery scope"), Y `return_within_6m_pct`; both bars grey (not significant) | US-01, US-02 | "Late first order: 1.47% vs 1.79% return within 6 months, not significant (p = 0.16)" | `retention_first_order_late_test.csv` |

## Page 4: Seller Performance (with drill-through)
Layout: slicers in a row at the top; seller table on the left; scatter and decile chart on the right.
Every visual on this page has the **visual-level filter `dim_seller[is_ranked_30plus_orders]` = 1** (sellers with 30+ delivered orders).

| # | Visual | Fields / measure | User story | Insight title | Source |
|---|---|---|---|---|---|
| 4.1 | Table, Top N = 20 by `[Excess Late Orders]` | `dim_seller[seller_id]`, `dim_seller[seller_state]`, `[Seller Delivered Orders]`, `[Seller Late %]`, `[Excess Late Orders]`, `[Seller Avg Review]`, `[Seller Revenue (R$)]`; `[Seller Late %]` font colour via `Colour - Seller Late vs Platform` | US-03 | "By excess late orders, the #1 seller ranks only #135 on late rate" | `seller_late_rate_ranking.csv` |
| 4.2 | Scatter | X `[Seller Delivered Orders]`, Y `[Seller Late %]`, Values `dim_seller[seller_id]`; constant Y line at `[Platform Late Rate]` | US-03 | "The seller with the most excess late orders has 1,772 orders and a 9.7% late rate" | `seller_late_rate_ranking.csv` |
| 4.3 | Clustered column | X `dim_seller[late_rate_decile]`, Y `[Share of Seller Late Orders]`; decile 1 orange | US-03 | "Worst 10% of sellers cause 16% of late orders; decile 3 causes 24%" | `seller_late_rate_by_decile.csv` |

**Drill-through:** right-click any seller in 4.1 or 4.2 → *Drill through* → **Seller Detail**.

## Page 5 (drill-through, hidden from navigation): Seller Detail
Drill-through field: **`dim_seller[seller_id]`** (Visualizations pane → *Drill through* well). Power BI adds a Back button automatically.

| # | Visual | Fields / measure | User story | Title |
|---|---|---|---|---|
| 5.1 | Card (title) | `[Seller Detail Title]` | US-03 | (dynamic: seller ID, city, state) |
| 5.2 | Cards ×5 | `[Seller Delivered Orders]`, `[Seller Late %]`, `[Seller Avg Delay (days)]`, `[Seller Avg Review]`, `[Seller Revenue (R$)]` | US-03 (AC-3) | "Delivered orders", "Late %", "Avg delay (days)", "Avg review", "Revenue (R$)" |
| 5.3 | Card | `[Excess Late Orders]` | US-03 | "Late orders above the platform average" |
| 5.4 | Line | X `dim_date[year_month_label]`, Y `[Seller Late %]`; constant line `[Platform Late Rate]` | US-03 | "Late % by month vs the platform average" |
| 5.5 | Bar | Y `dim_product[category_english]`, X `[Seller Delivered Orders]` | US-03 | "What this seller ships" |

**Check value:** drill into seller `4a3ca9315b744ce9f8e9374361493884` (ibitinga, SP) → 1,772 delivered orders, 9.71%
late, −9.53 days average delay, 3.85 average review, R$ 200,326.12 revenue, 51.70 excess late orders
(`outputs/seller_late_rate_ranking.csv`, `excel/seller_scorecard_data.csv`).

## User-story coverage
| Story | Visuals |
|---|---|
| US-01 Repeat customers & cohorts | 1.3, 3.3, 3.4, 3.5 |
| US-02 Late delivery vs review | 1.5, 2.1, 2.2, 3.5 |
| US-03 Seller ranking & drill-through | 4.1, 4.2, 4.3, 5.1-5.5 |
| US-04 Delays by category & state | 1.4, 1.7, 2.3, 2.4, 2.5 |
| US-05 RFM segments | 3.1, 3.2 |
| US-06 Revenue concentration | 1.1, 1.2, 1.6, 1.8, 1.9 |
