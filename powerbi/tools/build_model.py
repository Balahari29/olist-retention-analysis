"""Generate the PBIP semantic model (TMDL) for the Olist dashboard.
Usage: python build_model.py <powerbi_dir>
Writes <powerbi_dir>/Olist Retention.SemanticModel/. No credentials: Power BI asks for them at refresh.
"""
import json
import sys
import uuid
from pathlib import Path

PROJECT = "Olist Retention"
NAMESPACE = uuid.UUID("6f1c2d0e-7a51-4c1b-9a77-0d3f5e2b8c11")


def tag(key):                       # stable lineage tags, so regenerating gives the same IDs
    return str(uuid.uuid5(NAMESPACE, key))


def quote(name):                    # TMDL object names with spaces/symbols need single quotes
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


# ---------------------------------------------------------------------------------------------
# Columns: (name, model dataType, M type, options)
# options: hidden, fmt, sortBy, category, key, summarize
# ---------------------------------------------------------------------------------------------
TEXT, INT, DBL, DEC, DATE, DT = "string", "int64", "double", "decimal", "date", "datetime"
M_TYPES = {TEXT: "type text", INT: "Int64.Type", DBL: "type number", DEC: "Currency.Type",
           DATE: "type date", DT: "type datetime"}

TABLES = {
    "dim_date": [
        ("date_key", DATE, {"key": True, "fmt": "yyyy-mm-dd"}),
        ("year_number", INT, {}), ("quarter_number", INT, {}), ("month_number", INT, {}),
        ("month_name", TEXT, {"sortBy": "month_number"}),
        ("year_month_label", TEXT, {"sortBy": "month_start"}),
        ("month_start", DATE, {"fmt": "yyyy-mm"}),
        ("weekday_number", INT, {}), ("weekday_name", TEXT, {"sortBy": "weekday_number"}),
        ("is_weekend", INT, {}),
    ],
    "dim_customer": [
        ("customer_id", TEXT, {"hidden": True}), ("customer_unique_id", TEXT, {}),
        ("customer_zip_code_prefix", TEXT, {}), ("customer_city", TEXT, {}),
        ("customer_state", TEXT, {"category": "StateOrProvince"}),
        ("customer_latitude", DBL, {"category": "Latitude"}), ("customer_longitude", DBL, {"category": "Longitude"}),
        ("cohort_month", DATE, {"fmt": "yyyy-mm"}), ("person_valid_orders", INT, {}), ("is_repeat_customer", INT, {}),
    ],
    "dim_seller": [
        ("seller_id", TEXT, {}), ("seller_zip_code_prefix", TEXT, {}), ("seller_city", TEXT, {}),
        ("seller_state", TEXT, {"category": "StateOrProvince"}),
        ("seller_latitude", DBL, {"category": "Latitude"}), ("seller_longitude", DBL, {"category": "Longitude"}),
        ("late_rate_rank", INT, {}), ("late_rate_decile", INT, {}), ("is_ranked_30plus_orders", INT, {}),
    ],
    "dim_product": [
        ("product_id", TEXT, {"hidden": True}), ("category_portuguese", TEXT, {}), ("category_english", TEXT, {}),
        ("product_photos_qty", INT, {}), ("product_weight_g", INT, {}), ("product_length_cm", INT, {}),
        ("product_height_cm", INT, {}), ("product_width_cm", INT, {}),
    ],
    "fact_orders": [
        ("order_id", TEXT, {}), ("customer_id", TEXT, {"hidden": True}),
        ("purchase_date", DATE, {"hidden": True, "fmt": "yyyy-mm-dd"}), ("order_status", TEXT, {}),
        ("item_count", INT, {}), ("order_revenue", DEC, {"fmt": "R$ #,0.00"}), ("order_freight", DEC, {"fmt": "R$ #,0.00"}),
        ("payment_total", DEC, {"fmt": "R$ #,0.00"}), ("in_delivery_scope", INT, {"hidden": True}),
        ("delivered_date", DATE, {"fmt": "yyyy-mm-dd"}), ("estimated_date", DATE, {"fmt": "yyyy-mm-dd"}),
        ("delay_days", INT, {"hidden": True}), ("delay_bucket", TEXT, {"sortBy": "delay_bucket_order"}),
        ("delay_bucket_order", INT, {}), ("is_on_time", INT, {"hidden": True}), ("is_late", INT, {"hidden": True}),
        ("delivery_days", INT, {"hidden": True}), ("flag_pickup_before_approval", INT, {}),
        ("approval_to_pickup_days", DBL, {}), ("review_id", TEXT, {"hidden": True}), ("review_score", INT, {"hidden": True}),
    ],
    "fact_order_items": [
        ("order_id", TEXT, {"hidden": True}), ("order_item_id", INT, {"hidden": True}),
        ("product_id", TEXT, {"hidden": True}), ("seller_id", TEXT, {"hidden": True}),
        ("customer_id", TEXT, {"hidden": True}), ("purchase_date", DATE, {"hidden": True, "fmt": "yyyy-mm-dd"}),
        ("price", DEC, {"hidden": True, "fmt": "R$ #,0.00"}), ("freight_value", DEC, {"fmt": "R$ #,0.00"}),
        ("shipping_limit_date", DT, {}), ("in_delivery_scope", INT, {"hidden": True}),
        ("is_late", INT, {"hidden": True}), ("delay_days", INT, {"hidden": True}), ("review_score", INT, {"hidden": True}),
    ],
}

TABLE_DESCRIPTIONS = {
    "dim_date": "Calendar, one row per day 2017-01-01 to 2018-12-31 (MySQL view dim_date). Marked as date table.",
    "dim_customer": "One row per customer_id (1:1 with orders). customer_unique_id = the person.",
    "dim_seller": "Sellers with at least one item in a valid order; ranking columns only for 30+ delivered orders.",
    "dim_product": "Products with English category names.",
    "fact_orders": "One row per valid order (97,905). Order-level revenue, delivery and review.",
    "fact_order_items": "One row per item of a valid order (111,752). Order-level delivery/review values repeat on each item.",
}

# calculated columns on dim_customer (dax_measures.md 9.2)
CALC_COLUMNS = {
    "dim_customer": [
        ("Customer Type", TEXT, 'IF ( dim_customer[is_repeat_customer] = 1, "Repeat", "One-time" )', {}),
        ("Order Count Band", TEXT,
         'SWITCH ( TRUE (), dim_customer[person_valid_orders] = 1, "1 order", dim_customer[person_valid_orders] = 2, '
         '"2 orders", dim_customer[person_valid_orders] = 3, "3 orders", "4+ orders" )', {"sortBy": "Order Count Band Sort"}),
        ("Order Count Band Sort", INT, "MIN ( dim_customer[person_valid_orders], 4 )", {"hidden": True}),
    ]
}

# ---------------------------------------------------------------------------------------------
# Measures: (name, folder, format, description, DAX). DAX copied from powerbi/dax_measures.md.
# ---------------------------------------------------------------------------------------------
RS, PCT, CNT, DEC2, DEC4 = "R$ #,0.00", "0.00%", "#,0", "0.00", "0.0000"
MEASURES = [
    # 1. Revenue
    ("Total Revenue (R$)", "Revenue", RS, "Product revenue of valid orders, excluding freight.",
     "SUM ( fact_orders[order_revenue] )"),
    ("Orders", "Revenue", CNT, "Number of valid orders.", "COUNTROWS ( fact_orders )"),
    ("AOV (R$)", "Revenue", RS, "Average product value per valid order.", "DIVIDE ( [Total Revenue (R$)], [Orders] )"),
    ("Previous Month Revenue (R$)", "Revenue", RS, "Revenue of the previous calendar month.",
     "CALCULATE ( [Total Revenue (R$)], DATEADD ( dim_date[date_key], -1, MONTH ) )"),
    ("Revenue MoM %", "Revenue", PCT, "Change vs the previous calendar month; needs a month in context.", """
VAR CurrentRevenue  = [Total Revenue (R$)]
VAR PreviousRevenue = [Previous Month Revenue (R$)]
RETURN
    IF ( NOT ISBLANK ( PreviousRevenue ), DIVIDE ( CurrentRevenue - PreviousRevenue, PreviousRevenue ) )"""),
    ("Revenue Change vs Previous Month (R$)", "Revenue", RS, "Revenue minus previous month revenue.", """
VAR PreviousRevenue = [Previous Month Revenue (R$)]
RETURN
    IF ( NOT ISBLANK ( PreviousRevenue ), [Total Revenue (R$)] - PreviousRevenue )"""),
    ("Item Revenue (R$)", "Revenue", RS, "Revenue at item level, for product and seller analysis.",
     "SUM ( fact_order_items[price] )"),
    ("Item Orders", "Revenue", CNT, "Distinct orders with at least one item in context.",
     "DISTINCTCOUNT ( fact_order_items[order_id] )"),
    # Revenue \ Pareto
    ("Category Cumulative Revenue %", "Revenue\\Pareto", PCT, "Running share of revenue, highest category first.", """
VAR CurrentRevenue = [Item Revenue (R$)]
VAR AllCategories  = ALLSELECTED ( dim_product[category_english] )
VAR CategoriesAtOrAbove =
    FILTER ( AllCategories, [Item Revenue (R$)] >= CurrentRevenue )
RETURN
    DIVIDE ( SUMX ( CategoriesAtOrAbove, [Item Revenue (R$)] ),
             SUMX ( AllCategories, [Item Revenue (R$)] ) )"""),
    ("Category Revenue Share %", "Revenue\\Pareto", PCT, "Category share of item revenue.",
     "DIVIDE ( [Item Revenue (R$)], CALCULATE ( [Item Revenue (R$)], ALLSELECTED ( dim_product[category_english] ) ) )"),
    ("Category Revenue Rank", "Revenue\\Pareto", CNT, "Rank of the category by item revenue.", """
IF (
    ISINSCOPE ( dim_product[category_english] ),
    RANKX ( ALLSELECTED ( dim_product[category_english] ), [Item Revenue (R$)], , DESC )
)"""),
    ("Categories for 80% Revenue", "Revenue\\Pareto", CNT, "Number of categories needed to reach 80% of revenue.", """
COUNTROWS (
    FILTER ( ALLSELECTED ( dim_product[category_english] ), [Category Cumulative Revenue %] < 0.8 )
) + 1"""),
    ("State Revenue Share %", "Revenue\\Pareto", PCT, "Customer-state share of revenue.",
     "DIVIDE ( [Total Revenue (R$)], CALCULATE ( [Total Revenue (R$)], ALLSELECTED ( dim_customer[customer_state] ) ) )"),
    ("State Cumulative Revenue %", "Revenue\\Pareto", PCT, "Running share of revenue, highest state first.", """
VAR CurrentRevenue = [Total Revenue (R$)]
VAR AllStates      = ALLSELECTED ( dim_customer[customer_state] )
VAR StatesAtOrAbove = FILTER ( AllStates, [Total Revenue (R$)] >= CurrentRevenue )
RETURN
    DIVIDE ( SUMX ( StatesAtOrAbove, [Total Revenue (R$)] ), SUMX ( AllStates, [Total Revenue (R$)] ) )"""),
    ("States for 80% Revenue", "Revenue\\Pareto", CNT, "Number of customer states needed to reach 80% of revenue.",
     "COUNTROWS ( FILTER ( ALLSELECTED ( dim_customer[customer_state] ), [State Cumulative Revenue %] < 0.8 ) ) + 1"),
    # 2. Customers
    ("Customers", "Customers", CNT, "Distinct people (customer_unique_id) with a valid order in context.",
     "CALCULATE ( DISTINCTCOUNT ( dim_customer[customer_unique_id] ), fact_orders )"),
    ("Repeat Customer %", "Customers", PCT, "Share of people with 2+ valid orders inside the selected period.", """
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
VAR CustomersWithOrders = COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 1 ) )
VAR RepeatCustomers     = COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 2 ) )
RETURN
    DIVIDE ( RepeatCustomers, CustomersWithOrders )"""),
    ("Repeat Customers", "Customers", CNT, "People with 2+ valid orders inside the selected period.", """
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
RETURN
    COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] >= 2 ) )"""),
    ("One-time Customers", "Customers", CNT, "People with exactly 1 valid order inside the selected period.", """
VAR OrdersPerCustomer =
    ADDCOLUMNS (
        VALUES ( dim_customer[customer_unique_id] ),
        "@Orders", CALCULATE ( COUNTROWS ( fact_orders ) )
    )
RETURN
    COUNTROWS ( FILTER ( OrdersPerCustomer, [@Orders] = 1 ) )"""),
    ("Orders per Customer", "Customers", DEC4, "Valid orders per person.", "DIVIDE ( [Orders], [Customers] )"),
    # Customers \ Cohort
    ("Cohort Customers", "Customers\\Cohort", CNT, "People in the cohort (month of first valid order).",
     "DISTINCTCOUNT ( dim_customer[customer_unique_id] )"),
    ("Cohort Active Customers", "Customers\\Cohort", CNT,
     "Cohort members with a valid order N months after their first month; blank when not yet observable.", """
VAR CohortStart    = SELECTEDVALUE ( dim_customer[cohort_month] )
VAR MonthOffset    = SELECTEDVALUE ( 'Cohort Month Offset'[month_offset] )
VAR TargetMonth    = EDATE ( CohortStart, MonthOffset )
VAR LastOrderDate  = CALCULATE ( MAX ( fact_orders[purchase_date] ), REMOVEFILTERS () )
VAR LastDataMonth  = DATE ( YEAR ( LastOrderDate ), MONTH ( LastOrderDate ), 1 )
RETURN
    IF (
        NOT ISBLANK ( CohortStart ) && NOT ISBLANK ( MonthOffset ) && TargetMonth <= LastDataMonth,
        CALCULATE ( [Customers], REMOVEFILTERS ( dim_date ), dim_date[month_start] = TargetMonth ) + 0
    )"""),
    ("Cohort Retention % (live)", "Customers\\Cohort", PCT, "Cohort Active Customers / Cohort Customers.", """
VAR ActiveCustomers = [Cohort Active Customers]
RETURN
    IF ( NOT ISBLANK ( ActiveCustomers ), DIVIDE ( ActiveCustomers, [Cohort Customers] ) )"""),
    # 3. Delivery
    ("Delivered Orders", "Delivery", CNT, "Orders in delivery scope.",
     "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[in_delivery_scope] = 1 )"),
    ("On-Time Orders", "Delivery", CNT, "Delivered on or before the estimated date.",
     "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_on_time] = 1 )"),
    ("Late Orders", "Delivery", CNT, "Delivered after the estimated date.",
     "CALCULATE ( COUNTROWS ( fact_orders ), fact_orders[is_late] = 1 )"),
    ("On-Time %", "Delivery", PCT, "Share of delivered orders on or before the estimated date.",
     "DIVIDE ( [On-Time Orders], [Delivered Orders] )"),
    ("Late %", "Delivery", PCT, "Share of delivered orders after the estimated date.",
     "DIVIDE ( [Late Orders], [Delivered Orders] )"),
    ("Avg Delay (days)", "Delivery", DEC2, "Days delivered after (+) or before (-) the estimate.",
     "AVERAGE ( fact_orders[delay_days] )"),
    ("Avg Delivery Days", "Delivery", DEC2, "Purchase to delivery, in days.", "AVERAGE ( fact_orders[delivery_days] )"),
    ("Platform Late Rate", "Delivery", PCT, "Late % of the whole platform, ignoring all filters.",
     "CALCULATE ( [Late %], REMOVEFILTERS () )"),
    ("Late % vs Platform (pp)", "Delivery", "+0.00%;-0.00%;0.00%", "Late % minus the platform late rate.",
     "[Late %] - [Platform Late Rate]"),
    # 4. Satisfaction
    ("Avg Review", "Satisfaction", DEC2, "Average review score (1-5) of valid orders with a review.",
     "AVERAGE ( fact_orders[review_score] )"),
    ("Avg Review (delivered)", "Satisfaction", DEC2, "Average review score of delivered orders.",
     "CALCULATE ( AVERAGE ( fact_orders[review_score] ), fact_orders[in_delivery_scope] = 1 )"),
    # 5. Sellers
    ("Seller Delivered Orders", "Sellers", CNT, "Distinct delivered orders of the sellers in context (use for one seller).",
     "CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[in_delivery_scope] = 1 )"),
    ("Seller Late Orders", "Sellers", CNT, "Distinct late orders of the sellers in context (use for one seller).",
     "CALCULATE ( DISTINCTCOUNT ( fact_order_items[order_id] ), fact_order_items[is_late] = 1 )"),
    ("Seller Late %", "Sellers", PCT, "Late rate on distinct orders (identical to the pair version for one seller).",
     "DIVIDE ( [Seller Late Orders], [Seller Delivered Orders] )"),
    ("Seller Late % (pairs)", "Sellers", PCT, "Late rate on seller-order pairs: the SQL definition for groups of sellers.",
     "DIVIDE ( [Late Orders (seller sum)], [Delivered Orders (seller sum)] )"),
    ("Excess Late Orders", "Sellers", "#,0.00", "Late orders above what an average seller of the same size would have.", """
SUMX (
    VALUES ( dim_seller[seller_id] ),
    [Seller Late Orders] - [Seller Delivered Orders] * [Platform Late Rate]
)"""),
    ("Seller Avg Review", "Sellers", DEC2, "One review score per order, delivered orders only.", """
AVERAGEX (
    SUMMARIZE (
        FILTER ( fact_order_items, fact_order_items[in_delivery_scope] = 1 ),
        fact_order_items[order_id], fact_order_items[review_score]
    ),
    fact_order_items[review_score]
)"""),
    ("Seller Avg Delay (days)", "Sellers", DEC2, "One delay value per order, delivered orders only.", """
AVERAGEX (
    SUMMARIZE (
        FILTER ( fact_order_items, fact_order_items[in_delivery_scope] = 1 ),
        fact_order_items[order_id], fact_order_items[delay_days]
    ),
    fact_order_items[delay_days]
)"""),
    ("Seller Revenue (R$)", "Sellers", RS, "Item revenue of the sellers in context.", "SUM ( fact_order_items[price] )"),
    ("Total Sellers", "Sellers", CNT, "Sellers with at least one item in context.",
     "DISTINCTCOUNT ( fact_order_items[seller_id] )"),
    ("Ranked Sellers", "Sellers", CNT, "Sellers with 30+ delivered orders (SQL threshold).",
     "CALCULATE ( [Total Sellers], dim_seller[is_ranked_30plus_orders] = 1 )"),
    ("Seller Late Rate Rank", "Sellers", CNT, "SQL late-rate rank (ranked sellers only).",
     "SELECTEDVALUE ( dim_seller[late_rate_rank] )"),
    ("Excess Late Rank", "Sellers", CNT, "Rank of the seller by Excess Late Orders among the sellers shown.", """
IF (
    ISINSCOPE ( dim_seller[seller_id] ),
    RANKX ( ALLSELECTED ( dim_seller[seller_id] ), [Excess Late Orders], , DESC )
)"""),
    ("Share of Seller Late Orders", "Sellers", PCT, "Share of seller late orders (pairs) in the selected deciles.", """
DIVIDE ( [Late Orders (seller sum)],
         CALCULATE ( [Late Orders (seller sum)], REMOVEFILTERS ( dim_seller[late_rate_decile] ) ) )"""),
    ("Seller Detail Title", "Sellers", None, "Dynamic title for the drill-through page.", """
"Seller " & SELECTEDVALUE ( dim_seller[seller_id], "(select one seller)" )
    & "  |  " & SELECTEDVALUE ( dim_seller[seller_city] ) & " - " & SELECTEDVALUE ( dim_seller[seller_state] )"""),
    # Sellers \ Helpers
    ("Late Orders (seller sum)", "Sellers\\Helpers", CNT, "Late seller-order pairs, summed seller by seller.",
     "SUMX ( VALUES ( dim_seller[seller_id] ), [Seller Late Orders] )"),
    ("Delivered Orders (seller sum)", "Sellers\\Helpers", CNT, "Delivered seller-order pairs, summed seller by seller.",
     "SUMX ( VALUES ( dim_seller[seller_id] ), [Seller Delivered Orders] )"),
    # 7. Formatting
    ("Colour - Late vs Platform", "Formatting", None, "Orange when Late % is above the platform, else blue.",
     'IF ( [Late %] > [Platform Late Rate], "#EB6834", "#2A78D6" )'),
    ("Colour - Seller Late vs Platform", "Formatting", None, "Orange when Seller Late % is above the platform, else blue.",
     'IF ( [Seller Late %] > [Platform Late Rate], "#EB6834", "#2A78D6" )'),
    ("Colour - Seller Late (pairs) vs Platform", "Formatting", None,
     "Orange when Seller Late % (pairs) is above the platform, else blue (for groups of sellers).",
     'IF ( [Seller Late % (pairs)] > [Platform Late Rate], "#EB6834", "#2A78D6" )'),
    ("Colour - Late Bucket", "Formatting", None, "Orange for late delay buckets (1-3, 4-7, 7+ days late), else blue.",
     'IF ( MAX ( fact_orders[delay_bucket_order] ) >= 3, "#EB6834", "#2A78D6" )'),
]

# (name, from table.column, to table.column, active)
RELATIONSHIPS = [
    ("R1 fact_orders purchase_date", "fact_orders.purchase_date", "dim_date.date_key", True),
    ("R2 fact_orders customer_id", "fact_orders.customer_id", "dim_customer.customer_id", True),
    ("R4 fact_order_items purchase_date", "fact_order_items.purchase_date", "dim_date.date_key", True),
    ("R5 fact_order_items seller_id", "fact_order_items.seller_id", "dim_seller.seller_id", True),
    ("R6 fact_order_items product_id", "fact_order_items.product_id", "dim_product.product_id", True),
    ("R7 fact_orders delivered_date (inactive)", "fact_orders.delivered_date", "dim_date.date_key", False),
    ("R8 fact_order_items customer_id", "fact_order_items.customer_id", "dim_customer.customer_id", True),
]


def expression_lines(dax, indent):
    lines = dax.strip("\n").split("\n")
    return "\n".join(indent + line if line.strip() else "" for line in lines)


def column_block(table, name, dtype, opts, calc_expression=None):
    model_type = "dateTime" if dtype in (DATE, DT) else dtype
    head = f"\tcolumn {quote(name)}"
    if calc_expression:
        head += f" = {calc_expression}"
    out = [head, f"\t\tdataType: {model_type}"]
    if opts.get("fmt"):
        out.append(f"\t\tformatString: {opts['fmt']}")
    elif dtype == DATE:
        out.append("\t\tformatString: yyyy-mm-dd")
    elif dtype == DT:
        out.append("\t\tformatString: General Date")
    if opts.get("key"):
        out.append("\t\tisKey")
    if opts.get("hidden"):
        out.append("\t\tisHidden")
    if opts.get("category"):
        out.append(f"\t\tdataCategory: {opts['category']}")
    out.append(f"\t\tlineageTag: {tag(table + '.' + name)}")
    out.append("\t\tsummarizeBy: none")
    if not calc_expression:
        out.append(f"\t\tsourceColumn: {name}")
    if opts.get("sortBy"):
        out.append(f"\t\tsortByColumn: {quote(opts['sortBy'])}")
    out.append("")
    if dtype == DATE:
        out.append("\t\tannotation UnderlyingDateTimeDataType = Date")
        out.append("")
    return "\n".join(out)


def view_table(table):
    columns = TABLES[table]
    parts = [f"/// {TABLE_DESCRIPTIONS[table]}", f"table {table}"]
    if table == "dim_date":
        parts.append("\tdataCategory: Time")
    parts += [f"\tlineageTag: {tag(table)}", ""]
    for name, dtype, opts in columns:
        parts.append(column_block(table, name, dtype, opts))
    for name, dtype, dax, opts in CALC_COLUMNS.get(table, []):
        parts.append(column_block(table, name, dtype, opts, calc_expression=dax))
    type_pairs = ", ".join(f'{{"{name}", {M_TYPES[dtype]}}}' for name, dtype, _ in columns)
    m_query = f"""let
    Source = MySQL.Database(#"MySQL Server", #"MySQL Database", [ReturnSingleDatabase = true]),
    View = Source{{[Schema = #"MySQL Database", Item = "{table}"]}}[Data],
    Typed = Table.TransformColumnTypes(View, {{{type_pairs}}})
in
    Typed"""
    parts += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource =", expression_lines(m_query, "\t\t\t\t"), "",
              "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(parts)


def measures_table():
    parts = ["/// All report measures, grouped in display folders (see powerbi/dax_measures.md).",
             "table _Measures", f"\tlineageTag: {tag('_Measures')}", ""]
    for name, folder, fmt, description, dax in MEASURES:
        parts.append(f"\t/// {description}")
        if "\n" in dax.strip():
            parts.append(f"\tmeasure {quote(name)} =")
            parts.append(expression_lines(dax, "\t\t\t"))
        else:
            parts.append(f"\tmeasure {quote(name)} = {dax.strip()}")
        if fmt:
            parts.append(f"\t\tformatString: {fmt}")
        parts.append(f"\t\tdisplayFolder: {folder}")
        parts.append(f"\t\tlineageTag: {tag('measure.' + name)}")
        parts.append("")
    parts += ["\tcolumn Value", "\t\tdataType: int64", "\t\tisHidden", "\t\tisNameInferred",
              f"\t\tlineageTag: {tag('_Measures.Value')}", "\t\tsummarizeBy: none", "\t\tsourceColumn: [Value]", "",
              "\tpartition _Measures = calculated", "\t\tmode: import", "\t\tsource = { 0 }", "",
              "\tannotation PBI_Id = measures-table", ""]
    return "\n".join(parts)


def offset_table():
    return "\n".join([
        "/// Month offsets 0-19 for the cohort matrix columns (disconnected table).",
        "table 'Cohort Month Offset'", f"\tlineageTag: {tag('Cohort Month Offset')}", "",
        "\tcolumn month_offset", "\t\tdataType: int64", "\t\tformatString: 0", "\t\tisNameInferred",
        f"\t\tlineageTag: {tag('Cohort Month Offset.month_offset')}", "\t\tsummarizeBy: none",
        "\t\tsourceColumn: [month_offset]", "",
        "\tpartition 'Cohort Month Offset' = calculated", "\t\tmode: import",
        '\t\tsource = SELECTCOLUMNS ( GENERATESERIES ( 0, 19, 1 ), "month_offset", [Value] )', ""])


def main(powerbi_dir):
    model_dir = Path(powerbi_dir) / f"{PROJECT}.SemanticModel"
    definition = model_dir / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    table_names = list(TABLES) + ["_Measures", "Cohort Month Offset"]

    (model_dir / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": PROJECT},
        "config": {"version": "2.0", "logicalId": tag("semantic-model")}}, indent=2), encoding="utf-8")
    (model_dir / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}}, indent=2), encoding="utf-8")

    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n\n", encoding="utf-8")
    model_lines = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
                   "\tdiscourageImplicitMeasures", "\tsourceQueryCulture: en-US", "\tdataAccessOptions",
                   "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
                   "annotation __PBI_TimeIntelligenceEnabled = 0", "",
                   'annotation PBI_QueryOrder = ["MySQL Server","MySQL Database",' +
                   ",".join(f'"{name}"' for name in TABLES) + "]", ""]
    model_lines += [f"ref table {quote(name)}" for name in table_names] + [""]
    (definition / "model.tmdl").write_text("\n".join(model_lines), encoding="utf-8")

    (definition / "expressions.tmdl").write_text("\n".join([
        "/// MySQL host (and :port if not 3306). Change in Transform data > Edit parameters.",
        'expression \'MySQL Server\' = "localhost" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('param.server')}", "", "\tannotation PBI_ResultType = Text", "",
        "/// MySQL database that holds the Power BI views (sql/06_views_for_powerbi.sql).",
        'expression \'MySQL Database\' = "olist" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]',
        f"\tlineageTag: {tag('param.database')}", "", "\tannotation PBI_ResultType = Text", ""]), encoding="utf-8")

    rel_lines = []
    for name, from_column, to_column, active in RELATIONSHIPS:
        rel_lines += [f"relationship {tag('rel.' + name)}"]      # relationships cannot carry /// descriptions
        if not active:
            rel_lines.append("\tisActive: false")
        rel_lines += [f"\tfromColumn: {from_column}", f"\ttoColumn: {to_column}", ""]
    (definition / "relationships.tmdl").write_text("\n".join(rel_lines), encoding="utf-8")

    for table in TABLES:
        (definition / "tables" / f"{table}.tmdl").write_text(view_table(table), encoding="utf-8")
    (definition / "tables" / "_Measures.tmdl").write_text(measures_table(), encoding="utf-8")
    (definition / "tables" / "Cohort Month Offset.tmdl").write_text(offset_table(), encoding="utf-8")
    print(f"semantic model written: {model_dir} ({len(MEASURES)} measures, {len(RELATIONSHIPS)} relationships)")


if __name__ == "__main__":
    main(sys.argv[1])
