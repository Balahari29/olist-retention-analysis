# Build the dashboard in Tableau Public (Mac), step by step
For a first-time Tableau user. Each step says **what** to click and **why**, so you can explain it in an interview.
Use alongside: `data_model.md` (tables, relationships, types), `calculated_fields.md` (formulas + expected values),
`../powerbi/page_layout.md` (insight titles, colour rule, slicer plan: the same design, built here in Tableau).

> **Important: saving to Tableau Public makes the workbook public.** Anyone with the link can see the dashboard
> (and, if you allow it, download the workbook and its data). The data here is the public Kaggle Olist dataset, so this
> is fine; never publish private data this way. Tableau Public can only save to your public profile.

---

## Step 0: Install and get the data
1. Download **Tableau Public** (free desktop app) from public.tableau.com → *Create* → *Download the app*. Install,
   open it, and create / sign in to a free Tableau Public account when asked.
2. Regenerate the data on the Mac: `.venv/bin/python src/export_views.py` (writes `tableau/data/`), or unzip
   `tableau_data.zip` in the project folder.

## Step 1: Connect the main data source with relationships
1. On the start page, under **Connect → To a File**, click **Text file** → open `tableau/data/fact_orders.csv`.
   The **Data Source** tab opens with `fact_orders` on the canvas: this is the root table.
2. In the left panel (*Files*), drag **`dim_date.csv`** onto the canvas next to `fact_orders`. A line (the "noodle")
   appears and the *Edit Relationship* box opens. Set **`purchase_date` = `date_key`**. Close the box.
3. Repeat, dragging each file next to the table named below and setting the fields (`data_model.md` §2):

   | Drag | Next to | Fields |
   |---|---|---|
   | `dim_customer.csv` | `fact_orders` | `customer_id` = `customer_id` |
   | `rfm_customer_segments.csv` | `dim_customer` | `customer_unique_id` = `customer_unique_id` |
   | `fact_order_items.csv` | `fact_orders` | `order_id` = `order_id` |
   | `dim_seller.csv` | `fact_order_items` | `seller_id` = `seller_id` |
   | `dim_product.csv` | `fact_order_items` | `product_id` = `product_id` |

   Tip: drop the file **on** the table you want it related to (it highlights), not on empty canvas.
4. Leave *Performance Options* at the defaults.
5. Rename the data source: double-click its name at the top-left of the Data Source tab → **`Olist`**.

*Why:* relationships (not joins) keep each table at its own level of detail, so order revenue is never multiplied by
the number of items. Tableau only allows a tree of relationships, which is why `fact_order_items` hangs off `fact_orders`.

## Step 2: Set the data types
1. Click each table on the canvas; its columns appear in the grid below.
2. Click the small type icon above a column header (Abc, #, calendar) and choose the type from `data_model.md` §3.
   **Every ID and zip must be String (Abc)**: `customer_zip_code_prefix` as a number would turn `06273` into `6273`.
3. Dates: `purchase_date`, `date_key`, `delivered_date`, `estimated_date`, `month_start`, `cohort_month` → **Date**.

## Step 3: Add the static data sources
**Data → New Data Source → Text file**, once for each of these files in `tableau/data/`:
`retention_cohort_long.csv`, `distance_vs_delay_bands.csv`, `retention_first_order_late_vs_on_time.csv`,
`rfm_segments.csv`. Set their types the same way. They are separate sources on purpose: their numbers cover the whole
period and must not change with filters.

## Step 4: Create the calculated fields and check them
1. Go to a sheet (**Sheet 1** tab at the bottom). With the `Olist` source selected in the Data pane:
   **Analysis → Create Calculated Field…**, type the name and formula from `calculated_fields.md`, click **OK**.
   Create all of them (the RFM, delay and decile fields too); create `Cohort Retention %` in `retention_cohort_long`.
2. Set number formats: right-click a field → **Default Properties → Number Format…** (R$: *Currency (Custom)*,
   prefix `R$ `; %: *Percentage*, 2 decimals).
3. **Check sheet:** rename Sheet 1 to **Checks**. Drag **Measure Names** to *Rows* and **Measure Values** to *Text*;
   in the *Measure Values* card keep only the KPI fields. Compare each number with **Expected** in
   `calculated_fields.md` (e.g. Total Revenue **R$ 13,449,529.68**, Repeat Customer % **3.03%**, On-Time %
   **93.21%**, Late % **6.79%**). Fix any difference before building charts (usually a data type or a field picked from
   the wrong table). Keep this sheet hidden later; it is your UAT evidence.

*Why:* charts built on a wrong number hide the mistake. Checking against the SQL results first is a mini-UAT.

## Step 5: Build the sheets
Create a new sheet for each row (bottom tabs → **New Worksheet** icon, or **⌘ + T**). Double-click the tab to rename it.
Double-click the sheet title to type the **insight title** from `powerbi/page_layout.md`.

**Common techniques**
- *Orange "bad" colour:* drag the colour field (e.g. `Late vs Platform`) onto **Color** on the Marks card → click
  **Color → Edit Colors…** → click each value and set it: worse/late = **#EB6834**, other = **#2A78D6**.
  For a single-colour chart: **Color → More colors** → **#2A78D6**.
- *Reference line at the platform average:* drag `Platform Late Rate` onto **Detail** (as MIN) → open the
  **Analytics** pane (tab next to *Data*) → drag **Reference Line** onto the chart → *Table* → *Value*:
  **MIN(Platform Late Rate)**, *Label*: Custom "Platform average <Value>", line colour grey **#B5B4AF**.
- *Top N that respects other filters:* create a calculated field `Row Number` = `INDEX()`. Sort the chart descending by
  the measure, drag `Row Number` to **Filters** → range **1 to N** → right-click it on the Filters shelf →
  *Compute Using* → the dimension on the chart. (A table-calculation filter runs after all other filters.)
- *Static-table sheets:* add the subtitle **"Whole period 2017-01 to 2018-08, not filtered"** in the title.

**Executive Overview sheets**
| Sheet | Build | Insight title |
|---|---|---|
| E1 KPI Cards | Measure Names → *Columns*; Measure Values → *Text*; keep `Total Revenue (R$)`, `AOV (R$)`, `Repeat Customer %`, `On-Time %`, `Avg Review (delivered)`; Format text size 20 | "Revenue: R$ 13.45M from 97,905 orders" |
| E2 Revenue by Month | `date_key` → *Columns*, right-click → **Month** (the "May 2015" style); `Total Revenue (R$)` → *Rows*; Mark type **Bar**; `Revenue MoM %` → *Tooltip* | "Black Friday 2017 lifted revenue 52% in one month" |
| E3 On-Time % by Month | `date_key` as Month → *Columns*; `On-Time %` → *Rows*; Mark type **Line**; right-click the March 2018 point → **Annotate → Mark** | "On-time delivery fell to 81% in March 2018" |
| E4 Top 10 States by Revenue | `customer_state` → *Rows*; `Total Revenue (R$)` → *Columns*; sort descending; `Row Number` filter 1-10 | "São Paulo alone brings 38% of revenue" |
| E5 Category Pareto | `category_english` → *Rows*; `Item Revenue (R$)` → *Columns*; sort descending; `Category Cumulative Revenue %` → *Tooltip*; `Row Number` filter 1-20 | "18 of 74 categories make 80% of revenue" |

**Delivery vs Satisfaction sheets**
| Sheet | Build | Insight title |
|---|---|---|
| D1 Review by Delay Bucket | `delay_bucket` → *Columns* (sort: right-click → *Sort* → by field `delay_bucket_order`, ascending; exclude Null); `Avg Review (delivered)` → *Rows*; `Delay Bucket Group` → *Color*; Label on | "Orders 7+ days late average 1.7 stars vs 4.3 when early" |
| D2 Late % by State | `customer_state` → *Rows*; `Late %` → *Columns*; sort descending; `Late vs Platform` → *Color*; reference line at platform average | "AL and MA: 21% and 18% of orders late vs 6.8% overall" |
| D3 Late % by Category | `category_english` → *Rows*; `Late %` → *Columns*; `Delivered Orders` → *Filters* → *At least* **100**; sort descending; `Row Number` filter 1-15; `Late vs Platform` → *Color* | "Audio is the most-delayed category: 11.9% late" |
| D4 Late % by Distance *(source `distance_vs_delay_bands`)* | `distance_band` → *Columns* (sort manually 0-100 … 1,500+); `late_pct` → *Rows* | "Late % rises from 4.5% under 100 km to 11.6% beyond 1,500 km" |

**Customer Segments sheets**
| Sheet | Build | Insight title |
|---|---|---|
| C1 Segment Share | `segment` → *Rows*; Measure Names → *Color*; Measure Values → *Columns*, keep `% of Customers` (blue) and `% of Revenue` (grey **#B5B4AF**) | "New – high value: 16% of customers, 29% of revenue" |
| C2 Segment Table *(source `rfm_segments`)* | `segment`, `suggested_action` → *Rows*; Measure Names → *Columns*; Measure Values → *Text*: `customers`, `pct_of_customers`, `revenue_brl`, `revenue_share_pct` | "Eight segments, one action each: start with New – high value" |
| C3 Cohort Heatmap *(source `retention_cohort_long`)* | `cohort_month` (as exact month, discrete) → *Rows*; `month_offset` (Dimension) → *Columns*, filter 1-12; Mark type **Square**; `Cohort Retention %` → *Color* (sequential blue) and *Label* | "No cohort tops 0.71% repeat buyers in any month" |
| C4 Repeat Customer % | `Repeat Customer %` → *Text* (large) | "Only 3.03% of customers bought twice in 20 months" |
| C5 First-Order Test *(source `retention_first_order_late_vs_on_time`)* | `first_order_delivery` → *Columns* (exclude "not in delivery scope"); `return_within_6m_pct` → *Rows*; colour grey | "Late first order: 1.47% vs 1.79% return within 6 months, not significant (p = 0.16)" |

**Seller Performance sheets** (on each: `is_ranked_30plus_orders` → *Filters* → **1**)
| Sheet | Build | Insight title |
|---|---|---|
| S1 Seller Table | `seller_id`, `seller_state` → *Rows*; Measure Values → *Text*: `Seller Delivered Orders`, `Seller Late %`, `Excess Late Orders`, `Seller Avg Review`, `Seller Revenue (R$)`; sort by `Excess Late Orders` descending; `Row Number` filter 1-20 | "By excess late orders, the #1 seller ranks only #135 on late rate" |
| S2 Seller Scatter | `Seller Delivered Orders` → *Columns*; `Seller Late %` → *Rows*; `seller_id` → *Detail*; `Seller Late vs Platform` → *Color*; reference line at platform average | "The seller with the most excess late orders has 1,772 orders and a 9.7% late rate" |
| S3 Late Share by Decile | `late_rate_decile` (Dimension) → *Columns*; `Share of Seller Late Orders` → *Rows* (*Compute Using* → `late_rate_decile`); `Decile Group` → *Color* | "Worst 10% of sellers cause 16% of late orders; decile 3 causes 24%" |

**Seller Detail sheets** (stand-in for drill-through)
| Sheet | Build |
|---|---|
| SD1 Seller KPIs | Measure Names → *Columns*; Measure Values → *Text*: `Seller Delivered Orders`, `Seller Late %`, `Seller Avg Delay (days)`, `Seller Avg Review`, `Seller Revenue (R$)`, `Excess Late Orders`; `seller_id`, `seller_city`, `seller_state` → *Detail*; title: `Seller <seller_id>, <seller_city> - <seller_state>` (Insert → field names in the title editor) |
| SD2 Seller Late % by Month | `date_key` as Month → *Columns*; `Seller Late %` → *Rows*; reference line at platform average |
| SD3 What the Seller Ships | `category_english` → *Rows*; `Seller Delivered Orders` → *Columns*; sort descending |

## Step 6: Add the filters
1. **Purchase date** (all pages): on E2, drag `date_key` → *Filters* → **Range of Dates** → OK. Right-click the
   filter → **Show Filter**. Then right-click it on the Filters shelf → **Apply to Worksheets → All Using This Data
   Source**. Do **not** "Add to Context": that would change `Platform Late Rate`.
2. **Customer state:** drag `customer_state` → *Filters* → All → OK → *Show Filter*, style **Multiple Values
   (dropdown)** → **Apply to Worksheets → Selected Worksheets…** → tick the E and D sheets.
3. **Segment:** `segment` filter on C1 (*Show Filter*, single list).
4. **Seller page:** show filters for `seller_state`, `late_rate_decile` and `category_english`, applied to S1-S3.
5. Static sheets (D4, C2, C3, C5) use other data sources, so these filters never reach them (as intended).

## Step 7: Build the 4 dashboards
For each: **Dashboard → New Dashboard** (or the dashboard icon at the bottom), rename the tab, and set
**Size → Fixed size → 1200 × 800** (left panel). Drag sheets from the left list onto the canvas: Tableau places them in
*tiled* containers. Double-click the dashboard title (**Dashboard → Show Title**) to type it.

| Dashboard | Sheets (top → bottom) |
|---|---|
| **Executive Overview** | E1 across the top · E2 and E3 side by side · E4 and E5 side by side · date and state filters on the right |
| **Delivery vs Satisfaction** | D1 large on the left with a **Text** object below it (drag *Text* from *Objects*) containing the two lines of `outputs/hypothesis_test_conclusion.txt` · D2, D3, D4 on the right |
| **Customer Segments** | C1 and C2 on top · C3 across the bottom · C4 and C5 on the right |
| **Seller Performance** | filters across the top · S1 on the left · S2 and S3 on the right |
| **Seller Detail** | SD1 on top · SD2 and SD3 below · a **Navigation** button (*Objects → Navigation*) back to Seller Performance |

## Step 8: Filter action instead of drill-through
1. Open the **Seller Performance** dashboard → **Dashboard → Actions… → Add Action → Filter…**
2. *Name:* `Go to seller detail`. *Source sheets:* **S1 Seller Table** and **S2 Seller Scatter**.
   *Run action on:* **Select**.
3. *Target sheets:* choose the **Seller Detail** dashboard → tick SD1, SD2, SD3.
4. *Clearing the selection will:* **Exclude all values** (the detail stays empty until a seller is picked).
5. *Filter:* **Selected Fields** → Source field `seller_id` → Target field `seller_id`. **OK**.
6. Test: click the first row of S1 → Tableau jumps to Seller Detail. For seller `4a3ca9315b744ce9f8e9374361493884`
   expect **1,772** orders, **9.71%** late, **−9.53** days, **3.85** stars, **R$ 200,326.12**, **51.70** excess
   late orders. Click the navigation button to return.

*Why:* Tableau has no "drill-through" page type; a filter action that targets another dashboard does the same job:
pick a seller, see only that seller's detail.

## Step 9: Final checks, then publish
1. Run `docs/05_UAT_checklist.md` and fill in Actual / Pass/Fail. Fix failures before publishing.
2. Hide working sheets: right-click a dashboard tab → **Hide All Sheets** (the Checks sheet stays in the workbook).
3. **File → Save to Tableau Public As…** → sign in → name it `Olist Customer Retention & Delivery` → **Save**.
   Tableau creates an extract and uploads it; the browser opens the published workbook. **It is now public.**
4. On the web page: click the settings (gear) icon to choose whether others may download the workbook, and set the
   dashboard **Executive Overview** as the first view.
5. Copy the link into the README ("Dashboard" section) and `docs/linkedin_post.md`.
6. Screenshots for the README: open each dashboard, press **⌘ + Shift + 4**, drag over it, and save as
   `images/dashboard_1_executive.png`, `dashboard_2_delivery.png`, `dashboard_3_segments.png`,
   `dashboard_4_sellers.png` (Mac saves to the Desktop; move them into `images/`).
