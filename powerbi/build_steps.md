# Build the dashboard in Power BI Desktop (Windows), step by step
For a first-time Power BI user. Follow the steps in order; each one says **what** to click and **why**, so you can
explain it in an interview. Use these files alongside: `model_spec.md` (tables, types, relationships),
`dax_measures.md` (measures + expected values), `page_layout.md` (what goes on each page).

> Menu names are from current Power BI Desktop. If a label differs slightly, look for the same word in the
> **Home**, **Modeling** or **View** ribbon tab.

---

## Step 0: Get the files onto the Windows PC
1. Install **Power BI Desktop** (free) from the Microsoft Store.
2. The star-schema CSVs are **not in git** (too large to version). On the Mac, regenerate them with
   `.venv/bin/python src/export_views.py`, then copy them to the PC. The easiest way is **`powerbi_data.zip`** in
   the project root (command in the README, Power BI section): copy it by USB or cloud drive and unzip it on the PC.
   It contains:
   - `powerbi/data/` (7 CSVs: the star schema), and
   - from `outputs/`: `retention_cohort_long.csv`, `distance_vs_delay_bands.csv`,
     `retention_first_order_late_vs_on_time.csv`, `rfm_segments.csv` (static tables).

*Why:* the .pbix reads CSV snapshots, so the PC needs no MySQL. The CSVs come from the same SQL views as every
number in `outputs/`.

## Step 1: Switch off three automatic features (before loading anything)
1. Open Power BI Desktop → **File → Options and settings → Options**.
2. **GLOBAL → Data Load** → *Type detection*: choose **Never detect column types and headers for unstructured sources**.
3. **CURRENT FILE → Data Load**:
   - untick **Autodetect new relationships after data is loaded**
   - untick **Auto date/time** (under *Time intelligence*)
4. **OK**.

*Why:* automatic type detection guesses from the first 200 rows and can turn zip `06273` into `6273` or an ID into a
number; automatic relationships can link the wrong columns; Auto date/time creates hidden date tables that we replace
with our own `dim_date`.

## Step 2: Load the first CSV (fact_orders) with Power Query
1. **Home → Get data → Text/CSV** → select `powerbi/data/fact_orders.csv` → **Open**.
2. In the preview: *File origin* **65001: Unicode (UTF-8)**, *Delimiter* **Comma**,
   *Data type detection* **Do not detect data types**.
3. Click **Transform Data** (not Load). The **Power Query Editor** opens.
4. Check the header row: if the first row shows `Column1, Column2…`, click **Home → Use First Row as Headers**.
5. Set each column's type (list in `model_spec.md` §3): click the small icon left of the column name
   (ABC / 123 / calendar) and pick **Text**, **Whole Number**, **Decimal Number**, **Date** or **Date/Time**.
   Tip: Ctrl+click several columns, then **Transform → Data Type** to set them at once.
   - If decimals turn into errors (Windows region uses a comma for decimals): right-click the column header →
     **Change Type → Using Locale…** → *Data type* Decimal Number, *Locale* **English (United States)**.
6. Look at the bottom-left status bar: it should say **0 errors**. To check, select a column →
   **View → Column quality** (shows Valid / Error / Empty %). Empty is expected for delivery columns of orders
   outside delivery scope.

*Why:* Power Query is where data enters the model. Setting types by hand once means every refresh uses the same rules.

## Step 3: Load the other tables
In the Power Query Editor: **Home → New Source → Text/CSV** and repeat Step 2 for:
`fact_order_items`, `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `rfm_customer_segments`
(from `powerbi/data/`), then the static tables from `outputs/`: `retention_cohort_long`, `distance_vs_delay_bands`,
`retention_first_order_late_vs_on_time`, and `rfm_segments` (rename this query to **`rfm_segment_summary`**:
double-click its name in the *Queries* list on the left).

When all 11 queries are listed: **Home → Close & Apply**. Power BI loads the data (a minute).

**Check:** in **Table view** (grid icon, left edge) click each table: the row count in the bottom-left must match
`model_spec.md` §2 (e.g. fact_orders **97,905**, fact_order_items **111,752**, dim_date **730**).

## Step 4: Create the relationships
1. Click **Model view** (the third icon on the left edge).
2. **Home → Manage relationships → New relationship**. For each row R1-R6 and R8 in `model_spec.md` §4:
   - top drop-down: the **many** table (e.g. `fact_orders`) and click the key column (`purchase_date`)
   - bottom drop-down: the **one** table (`dim_date`) and click its key (`date_key`)
   - *Cardinality*: **Many to one (*:1)**; *Cross filter direction*: **Single**; tick **Make this relationship active**
   - **Save**.
3. **Create R2 before R8.** For R2 (`fact_orders[customer_id]` → `dim_customer[customer_id]`) Power BI may pick
   **One to one**, which always filters in **both** directions. Change it to **Many to one** and **Single**.
4. Then create R8 (`fact_order_items[customer_id]` → `dim_customer[customer_id]`, Many to one, Single, active).
   If R2 had to stay One to one, create R8 **inactive** (untick *Make this relationship active*): a both-directions R2
   plus an active R8 would give `dim_date` two routes to `fact_order_items` (see `model_spec.md` §4).
5. Do not connect the static tables, and do not connect `fact_orders` to `fact_order_items` directly.

*Why:* relationships let a filter on a dimension (a date, a state, a seller) flow to the facts. "Single" direction
means filters flow one way only (dimension → fact), which keeps results predictable.

## Step 5: Set up the date table
1. In the **Data** pane (right), click the table **`dim_date`**.
2. **Table tools → Mark as date table** → *Date column*: **date_key** → **OK** (Power BI checks the dates are unique and
   continuous; ours are: 730 days, 2017-01-01 to 2018-12-31).
3. Sort month labels in calendar order: click column `month_name` → **Column tools → Sort by column → month_number**.
   Repeat: `year_month_label` by `month_start`; `weekday_name` by `weekday_number`.

*Why:* "mark as date table" lets `DATEADD` (used by Revenue MoM %) work; "sort by column" stops months from sorting
alphabetically (April, August, December…).

## Step 6: Create the measures
1. **Home → Enter data** → *Name*: `_Measures` → **Load** (an empty table to hold all measures in one place).
2. Click `_Measures` in the Data pane → **Home → New measure**. The formula bar opens.
3. Copy one measure from `dax_measures.md` (everything inside the grey code box, e.g.
   `Total Revenue (R$) = SUM ( fact_orders[order_revenue] )`), paste it, press **Enter**.
4. With the measure selected, **Measure tools → Format**: choose **Percentage** (2 decimals) for % measures, or type the
   custom format from the *Format strings* table (e.g. `"R$" #,0.00`).
5. Optional: in **Model view**, select the measure → *Properties* pane → **Display folder** (e.g. `Delivery`).
6. Repeat for every measure. Once all exist, delete the default column `Column1` from `_Measures`; the table icon
   changes to a calculator.

## Step 7: Check every measure against its expected value (before building pages)
1. Add a new page (**+** at the bottom), name it **Checks**.
2. For each measure: **Visualizations → Card**, drag the measure onto it.
3. Compare each card with the **Expected** value in `dax_measures.md` (no slicers on this page). Examples:
   Total Revenue **R$ 13,449,529.68**, Orders **97,905**, Repeat Customer % **3.03%**, On-Time % **93.21%**,
   Late % **6.79%**, Avg Delay **−11.81**, Avg Review (delivered) **4.16**.
4. If one differs: check that column's data type (Step 2) and its relationship (Step 4). Fix before moving on.
5. When all match, right-click the page tab → **Hide page** (keep it for the Phase 7 UAT checklist).

*Why:* building visuals on a wrong measure hides the error. Checking against SQL first is a mini-UAT.

## Step 8: Apply the colour theme
**View → Themes → Customize current theme → Name and colors**:
- *Theme colors*: **Color 1 `#2A78D6`** (blue, default), **Color 2 `#B5B4AF`** (grey, context)
- *Sentiment colors*: **Bad `#EB6834`** (orange), the only highlight colour (see `page_layout.md`)
- **Apply**.

## Step 9: Build page 1, Executive Overview (in full detail)
1. Double-click the tab **Page 1** → rename to **Executive Overview**.
2. **Date slicer:** **Visualizations → Slicer** → drag `dim_date[date_key]` into *Field* → in **Format visual →
   Slicer settings → Style** choose **Between**. Place it top-right.
3. **State slicer:** another Slicer with `dim_customer[customer_state]` → Style **Dropdown**.
4. **KPI cards (1.1-1.5):** **Visualizations → Card** → drag `[Total Revenue (R$)]` into *Fields*. In **Format visual
   → General → Title**: switch **On**, type the title from `page_layout.md` ("Revenue: R$ 13.45M from 97,905 orders").
   Repeat for AOV, Repeat Customer %, On-Time %, Avg Review (delivered). Line them up across the top
   (select all → **Format → Align → Align top**, **Distribute horizontally**).
5. **Revenue by month (1.6):** **Clustered column chart** → *X-axis* `dim_date[year_month_label]`, *Y-axis*
   `[Total Revenue (R$)]`, *Tooltips* `[Revenue MoM %]`. Hover over Nov 2017: the tooltip shows **52.06%**.
   Title: "Black Friday 2017 lifted revenue 52% in one month".
6. **On-time by month (1.7):** **Line chart** → *X-axis* `year_month_label`, *Y-axis* `[On-Time %]`. Format → Markers
   **On**. To highlight March 2018: click its marker → **Format → Markers → Apply settings to: Series / Categories**
   → pick 2018-03 → colour **#EB6834**. Title: "On-time delivery fell to 81% in March 2018".
7. **Top 10 states by revenue (1.8):** **Clustered bar chart** → *Y-axis* `dim_customer[customer_state]`, *X-axis*
   `[Total Revenue (R$)]`. In the **Filters** pane, expand `customer_state` on *this visual* → *Filter type* **Top N**
   → *Show items* **Top 10** → *By value*: drag `[Total Revenue (R$)]` → **Apply filter**. Data labels **On**.
   Title: "São Paulo alone brings 38% of revenue".
8. **Category Pareto (1.9):** **Clustered bar chart** → *Y-axis* `dim_product[category_english]`, *X-axis*
   `[Item Revenue (R$)]`, *Tooltips* `[Category Cumulative Revenue %]`; Top N = 20 as in step 7.
   Title: "18 of 74 categories make 80% of revenue".
9. **Sync the date slicer to all pages:** select it → **View → Sync slicers** → tick *Sync* and *Visible* for every
   page. Do the same for the state slicer, but only for Executive Overview and Delivery vs Satisfaction.

**Page 1 is done** when: the cards match Step 7, changing the date slicer changes every visual, and each title reads
as a sentence with a finding.

## Step 10: Build pages 2-4
Use `page_layout.md` (one row per visual: type, fields, title). Two techniques you will need:

**Colour bars by "worse than platform" (2.3, 2.4, 4.1):** select the visual → **Format visual → Bars → Colors → fx**
→ *Format style* **Field value** → *What field should we base this on?* `Colour - Late vs Platform`
(or `Colour - Seller Late vs Platform`) → **OK**. Bars above the platform late rate turn orange.

**Reference line at the platform average (2.3, 4.2):** select the visual → **Analytics** pane (magnifying-glass icon)
→ **Constant line** (*X-axis constant line* on bar charts) → **Add** → *Value* **fx** → `[Platform Late Rate]` →
colour grey, *Data label* **On**.

**Visual-level filter for sellers (page 4):** select each visual → **Filters** pane → *Filters on this visual* → drag
`dim_seller[is_ranked_30plus_orders]` → tick **1**.

**Static tables (2.5, 3.2, 3.3, 3.5):** set the value field to **Don't summarize** or **Sum** (one row per bar), and
add the subtitle **"Whole period 2017-01 to 2018-08, not filtered by slicers"** (Format → General → Title → Subtitle).

## Step 11: Drill-through page (Seller Detail)
1. Add a page, name it **Seller Detail**.
2. With nothing selected, in the **Visualizations** pane find **Drill through** → drag `dim_seller[seller_id]` into
   *Add drill-through fields here*. A **Back** button appears top-left.
3. Add the visuals 5.1-5.5 from `page_layout.md`.
4. Right-click the page tab → **Hide page** (users reach it only by drilling).
5. Test: on Seller Performance, right-click the first row of the seller table → **Drill through → Seller Detail**.
   For seller `4a3ca9315b744ce9f8e9374361493884` you must see **1,772** orders, **9.71%** late, **−9.53** days,
   **3.85** stars, **R$ 200,326.12**, **51.70** excess late orders. **Ctrl+click** the Back button to return
   (in Desktop, buttons need Ctrl+click).

## Step 12: Save and capture screenshots
1. **File → Save as** → `powerbi/olist_dashboard.pbix`.
2. For the README: open each page, press **Win + Shift + S** (Snipping Tool) → drag over the canvas → save as
   `images/dashboard_1_executive.png`, `dashboard_2_delivery.png`, `dashboard_3_segments.png`,
   `dashboard_4_sellers.png`.
3. Copy the .pbix and PNGs back to the project folder on the Mac and commit them.

**Done when:** all measures match the Checks page, every visual has an insight title, the slicers behave as in
`page_layout.md`'s slicer plan, and drill-through returns the check values above.
