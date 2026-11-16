"""Stage 3 logic check: emulate each DAX measure (same filter semantics) in pandas on the six Power BI views,
and compare with the SQL benchmarks in outputs/. Read-only (SELECTs only).
Run from the project root (Windows):  .venv/Scripts/python.exe src/validate_dax_logic.py .
Writes outputs/dax_logic_validation.csv.
Credentials come from <project_root>/.env and are never printed.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

root = Path(sys.argv[1])
outputs = root / "outputs"
load_dotenv(root / ".env")
engine = create_engine(URL.create(
    "mysql+pymysql", username=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
    host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT") or 3306), database=os.getenv("MYSQL_DATABASE") or "olist"))

with engine.connect() as connection:
    def load(view):
        frame = pd.read_sql(text(f"SELECT * FROM {view}"), connection)
        for column in frame.columns:      # DECIMAL -> float
            if frame[column].dtype == object and frame[column].map(lambda v: type(v).__name__ == "Decimal").any():
                frame[column] = frame[column].astype(float)
        return frame
    orders, items = load("fact_orders"), load("fact_order_items")
    customers, sellers, products = load("dim_customer"), load("dim_seller"), load("dim_product")

expected = pd.read_csv(outputs / "powerbi_expected_values.csv")
results = []                                   # (folder, measure, context, dax_value, expected, tolerance)


def check(folder, measure, context, value, benchmark, tolerance):
    results.append((folder, measure, context, value, benchmark, abs(value - benchmark) <= tolerance))


def benchmark(measure, context_prefix="all"):
    row = expected[(expected.measure == measure) & expected.filter_context.str.startswith(context_prefix)]
    return float(row.expected_value.iloc[0])


# expanded fact_orders (R2): customer columns available on each order
orders = orders.merge(customers[["customer_id", "customer_unique_id", "customer_state", "cohort_month"]], on="customer_id")
orders["purchase_date"] = pd.to_datetime(orders.purchase_date)
orders["month_start"] = orders.purchase_date.dt.to_period("M").dt.to_timestamp()
items = items.merge(sellers[["seller_id", "is_ranked_30plus_orders", "late_rate_decile"]], on="seller_id") \
             .merge(products[["product_id", "category_english"]], on="product_id")

# ---------------- Revenue ----------------
total_revenue = orders.order_revenue.sum()
order_count = len(orders)
check("Revenue", "Total Revenue (R$)", "no filter", total_revenue, benchmark("Total Revenue (R$)", "all valid"), 0.005)
check("Revenue", "Orders", "no filter", order_count, benchmark("Orders"), 0)
check("Revenue", "AOV (R$)", "no filter", total_revenue / order_count, benchmark("AOV (R$)"), 0.00005)
check("Revenue", "Item Revenue (R$)", "no filter", items.price.sum(), total_revenue, 0.005)

monthly = orders.groupby("month_start").agg(revenue=("order_revenue", "sum"), orders=("order_id", "count"))
monthly["prev"] = monthly.revenue.shift(1)                     # DATEADD(-1, MONTH) on a contiguous calendar
monthly["mom_pct"] = (monthly.revenue - monthly.prev) / monthly.prev * 100
for month, context in [("2017-11-01", "month = 2017-11"), ("2018-08-01", "month = 2018-08")]:
    check("Revenue", "Revenue MoM %", context, monthly.loc[month, "mom_pct"], benchmark("Revenue MoM %", context), 0.00005)
mom_file = pd.read_csv(outputs / "revenue_mom.csv", parse_dates=["purchase_month"]).set_index("purchase_month")
check("Revenue", "Revenue MoM % (every month)", "max abs diff vs revenue_mom.csv (2 dp)",
      (monthly.mom_pct.round(2) - mom_file.mom_pct).abs().max(skipna=True), 0, 0.0)
check("Revenue", "AOV (R$) by month", "max abs diff vs revenue_mom.csv (2 dp)",
      ((monthly.revenue / monthly.orders).round(2) - mom_file.aov_brl).abs().max(), 0, 0.0)

category = items.groupby("category_english").agg(revenue=("price", "sum"), orders=("order_id", "nunique")) \
                .sort_values("revenue", ascending=False)
category["cumulative_pct"] = category.revenue.cumsum() / category.revenue.sum() * 100   # >= current, as in DAX
pareto_category = pd.read_csv(outputs / "revenue_pareto_category.csv").set_index("category_english")
check("Revenue", "Item Revenue (R$) by category", "max abs diff vs revenue_pareto_category.csv",
      (category.revenue.round(2) - pareto_category.revenue_brl).abs().max(), 0, 0.005)
check("Revenue", "Item Orders (distinct order_id) by category", "max abs diff vs revenue_pareto_category.csv",
      (category.orders - pareto_category.orders).abs().max(), 0, 0)
check("Revenue", "Category Cumulative Revenue %", "max abs diff vs revenue_pareto_category.csv (2 dp)",
      (category.cumulative_pct.round(2) - pareto_category.cumulative_pct).abs().max(), 0, 0.0)
check("Revenue", "Categories for 80% revenue", "revenue_pareto_summary.csv",
      (category.cumulative_pct < 80).sum() + 1, 18, 0)

state = orders.groupby("customer_state").order_revenue.sum().sort_values(ascending=False)
state_cumulative = state.cumsum() / state.sum() * 100
pareto_state = pd.read_csv(outputs / "revenue_pareto_state.csv").set_index("customer_state")
check("Revenue", "Total Revenue (R$) by customer state", "max abs diff vs revenue_pareto_state.csv",
      (state.round(2) - pareto_state.revenue_brl).abs().max(), 0, 0.005)
check("Revenue", "State Cumulative Revenue %", "max abs diff vs revenue_pareto_state.csv (2 dp)",
      (state_cumulative.round(2) - pareto_state.cumulative_pct).abs().max(), 0, 0.0)
check("Revenue", "States for 80% revenue", "revenue_pareto_summary.csv", (state_cumulative < 80).sum() + 1, 7, 0)

# ---------------- Customers / retention ----------------
orders_per_person = orders.groupby("customer_unique_id").size()
check("Customers", "Customers", "no filter", orders_per_person.size, benchmark("Customers"), 0)
check("Customers", "Repeat Customers", "no filter (retention_repeat_customers.csv)", (orders_per_person >= 2).sum(), 2874, 0)
check("Customers", "One-time Customers", "no filter (retention_orders_per_customer.csv)", (orders_per_person == 1).sum(), 91829, 0)
check("Customers", "Repeat Customer %", "no filter", 100 * (orders_per_person >= 2).mean(), benchmark("Repeat Customer %"), 0.00005)
check("Customers", "Orders per Customer", "no filter (= 97,905 / 94,703)", order_count / orders_per_person.size, 97905 / 94703, 1e-9)
distribution = pd.read_csv(outputs / "retention_orders_per_customer.csv").set_index("valid_orders").customers
check("Customers", "Customers by person_valid_orders", "max abs diff vs retention_orders_per_customer.csv",
      (orders_per_person.value_counts().sort_index() - distribution).abs().max(), 0, 0)
person_column = customers.drop_duplicates("customer_unique_id").set_index("customer_unique_id").person_valid_orders
check("Customers", "dim_customer[person_valid_orders] = orders per person", "rows that differ",
      (person_column.reindex(orders_per_person.index) != orders_per_person).sum(), 0, 0)

last_month = orders.month_start.max()
cohort_size = orders.groupby("cohort_month").customer_unique_id.nunique()
cohort_rows = []
orders["cohort_month"] = pd.to_datetime(orders.cohort_month)
for cohort_month, cohort_orders in orders.groupby("cohort_month"):
    for offset in range(0, 20):
        target = cohort_month + pd.DateOffset(months=offset)
        if target > last_month:                           # beyond the observed window -> BLANK
            break
        active = cohort_orders.loc[cohort_orders.month_start == target, "customer_unique_id"].nunique()
        cohort_rows.append((cohort_month, offset, active, round(100 * active / cohort_orders.customer_unique_id.nunique(), 2)))
cohort = pd.DataFrame(cohort_rows, columns=["cohort_month", "month_offset", "active", "pct"])
cohort_file = pd.read_csv(outputs / "retention_cohort_long.csv", parse_dates=["cohort_month"])
merged = cohort.merge(cohort_file, on=["cohort_month", "month_offset"], how="outer", indicator=True)
check("Customers", "Cohort cells (cohort x offset)", "rows vs retention_cohort_long.csv", len(cohort), len(cohort_file), 0)
check("Customers", "Cohort cells missing on either side", "outer join", (merged._merge != "both").sum(), 0, 0)
check("Customers", "Cohort Active Customers", "max abs diff vs retention_cohort_long.csv",
      (merged.active - merged.active_customers).abs().max(), 0, 0)
check("Customers", "Cohort Retention %", "max abs diff vs retention_cohort_long.csv (2 dp)",
      (merged.pct - merged.retention_pct).abs().max(), 0, 0.0)

# ---------------- Delivery ----------------
in_scope = orders[orders.in_delivery_scope == 1]
check("Delivery", "Delivered Orders", "no filter", len(in_scope), benchmark("Delivered Orders (in scope)"), 0)
check("Delivery", "Late Orders", "no filter (delivery_kpis_overall.csv)", orders.is_late.eq(1).sum(), 6531, 0)
check("Delivery", "On-Time %", "no filter", 100 * orders.is_on_time.eq(1).sum() / len(in_scope), benchmark("On-Time %"), 0.00005)
check("Delivery", "Late %", "no filter", 100 * orders.is_late.eq(1).sum() / len(in_scope), benchmark("Late %"), 0.00005)
check("Delivery", "Avg Delay (days)", "no filter", orders.delay_days.mean(), benchmark("Avg Delay (days)"), 0.00005)
check("Delivery", "Avg Delivery Days", "no filter", orders.delivery_days.mean(), benchmark("Avg Delivery Days"), 0.00005)
by_month = in_scope.groupby("month_start").agg(delivered=("order_id", "count"), late=("is_late", "sum"))
month_file = pd.read_csv(outputs / "delivery_ontime_by_month.csv", parse_dates=["purchase_month"]).set_index("purchase_month")
check("Delivery", "On-Time % by month", "max abs diff vs delivery_ontime_by_month.csv (2 dp)",
      ((100 * (1 - by_month.late / by_month.delivered)).round(2) - month_file.on_time_pct).abs().max(), 0, 0.0)
by_state = in_scope.groupby("customer_state").agg(delivered=("order_id", "count"), late=("is_late", "sum"))
state_file = pd.read_csv(outputs / "delivery_ontime_by_state.csv").set_index("customer_state")
check("Delivery", "Late % by customer state", "max abs diff vs delivery_ontime_by_state.csv (2 dp)",
      ((100 * by_state.late / by_state.delivered).round(2) - state_file.late_pct).abs().max(), 0, 0.0)
by_bucket = in_scope.groupby("delay_bucket").agg(orders=("order_id", "count"), review=("review_score", "mean"))
bucket_file = pd.read_csv(outputs / "delivery_buckets_vs_review.csv").set_index("delay_bucket")
check("Delivery", "Delivered Orders by delay bucket", "max abs diff vs delivery_buckets_vs_review.csv",
      (by_bucket.orders - bucket_file.orders).abs().max(), 0, 0)
check("Delivery", "Avg Review (delivered) by delay bucket", "max abs diff vs delivery_buckets_vs_review.csv (2 dp)",
      (by_bucket.review.round(2) - bucket_file.avg_review_score).abs().max(), 0, 0.0)

# ---------------- Satisfaction ----------------
check("Satisfaction", "Avg Review", "no filter", orders.review_score.mean(), benchmark("Avg Review"), 0.00005)
check("Satisfaction", "Avg Review (delivered)", "no filter", in_scope.review_score.mean(), benchmark("Avg Review (delivered)", "orders"), 0.00005)

# ---------------- Sellers (fact_order_items: order-level values repeat per item) ----------------
platform_late_rate = orders.is_late.eq(1).sum() / len(in_scope)
scope_items = items[items.in_delivery_scope == 1]
pairs = scope_items.drop_duplicates(["seller_id", "order_id"])          # one row per seller-order pair
per_seller = pairs.groupby("seller_id").agg(delivered=("order_id", "count"), late=("is_late", "sum"))
per_seller["excess"] = per_seller.late - per_seller.delivered * platform_late_rate
ranked_ids = set(sellers.loc[sellers.is_ranked_30plus_orders == 1, "seller_id"])
ranked = per_seller[per_seller.index.isin(ranked_ids)]

check("Sellers", "Total Sellers", "no filter (dim_seller rows with items)", items.seller_id.nunique(), 3029, 0)
check("Sellers", "Ranked Sellers", "is_ranked_30plus_orders = 1 (seller_scorecard_totals.csv)", len(ranked_ids), 625, 0)
# Existing [Seller Late %] = DISTINCTCOUNT(order_id): a multi-seller order counts ONCE across the selection
ranked_scope_items = scope_items[scope_items.seller_id.isin(ranked_ids)]
distinct_delivered = ranked_scope_items.order_id.nunique()
distinct_late = ranked_scope_items.loc[ranked_scope_items.is_late == 1, "order_id"].nunique()
check("Sellers", "Seller Late % (existing, DISTINCTCOUNT across selection)", "ranked sellers",
      100 * distinct_late / distinct_delivered, benchmark("Seller Late %", "sellers"), 0.00005)
check("Sellers", "Seller Late % (pairs, SUMX per seller)", "ranked sellers",
      100 * ranked.late.sum() / ranked.delivered.sum(), benchmark("Seller Late %", "sellers"), 0.00005)
check("Sellers", "Seller Delivered Orders (existing DISTINCTCOUNT)", "ranked sellers vs 81,433 pairs", distinct_delivered, 81433, 0)
check("Sellers", "Delivered Orders (seller sum)", "ranked sellers vs 81,433 pairs", ranked.delivered.sum(), 81433, 0)
check("Sellers", "Excess Late Orders", "ranked sellers", ranked.excess.sum(), benchmark("Excess Late Orders", "sellers"), 0.005)
check("Sellers", "Excess Late Orders", "top seller (max)", per_seller.excess.max(), benchmark("Excess Late Orders", "top"), 0.005)

top = "4a3ca9315b744ce9f8e9374361493884"
top_items = scope_items[scope_items.seller_id == top].drop_duplicates(["order_id", "review_score"])
check("Sellers", "Seller Delivered Orders", "top seller", per_seller.loc[top, "delivered"], 1772, 0)
check("Sellers", "Seller Late %", "top seller (2 dp)", round(100 * per_seller.loc[top, "late"] / per_seller.loc[top, "delivered"], 2), 9.71, 0.0)
check("Sellers", "Seller Avg Review", "top seller (2 dp)", round(top_items.review_score.mean(), 2), 3.85, 0.0)
top_delay = scope_items[scope_items.seller_id == top].drop_duplicates(["order_id", "delay_days"])
check("Sellers", "Seller Avg Delay (days)", "top seller (2 dp)", round(top_delay.delay_days.mean(), 2), -9.53, 0.0)
check("Sellers", "Seller Revenue (R$)", "top seller", items.loc[items.seller_id == top, "price"].sum(), 200326.12, 0.005)

ranked_pairs = pairs[pairs.seller_id.isin(ranked_ids)]
decile = ranked_pairs.groupby("late_rate_decile").is_late.sum()
decile_file = pd.read_csv(outputs / "seller_late_rate_by_decile.csv").set_index("late_rate_decile")
check("Sellers", "Late Orders (seller sum) by decile", "max abs diff vs seller_late_rate_by_decile.csv",
      (decile - decile_file.late_orders).abs().max(), 0, 0)
check("Sellers", "Share of Seller Late Orders by decile", "max abs diff vs seller_late_rate_by_decile.csv (2 dp)",
      ((100 * decile / decile.sum()).round(2) - decile_file.share_of_all_late_orders_pct).abs().max(), 0, 0.0)
decile_excess = ranked.join(sellers.set_index("seller_id").late_rate_decile).groupby("late_rate_decile").excess.sum()
check("Sellers", "Excess Late Orders by decile", "max abs diff vs seller_late_rate_by_decile.csv (2 dp)",
      (decile_excess.round(2) - decile_file.excess_late_orders).abs().max(), 0, 0.005)

# ---------------- report ----------------
report = pd.DataFrame(results, columns=["folder", "measure", "context", "dax_logic_value", "benchmark", "pass"])
pd.set_option("display.width", 250, "display.max_colwidth", 70, "display.max_rows", 200)
print(report.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
report.to_csv(outputs / "dax_logic_validation.csv", index=False)
print(f"\nPASS {report['pass'].sum()} / {len(report)}  -> outputs/dax_logic_validation.csv")
