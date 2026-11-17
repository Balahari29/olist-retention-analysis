"""Generate the PBIR report (5 pages + hidden seller drill-through) and the .pbip file.
Usage: python build_report.py <powerbi_dir> <base_theme_json>
"""
import json
import shutil
import sys
import uuid
from pathlib import Path

PROJECT = "Olist Retention"
NS = uuid.UUID("0b8f3c52-2d4e-4f7a-8f0e-5a6c7d8e9f10")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
BASE_THEME = "Fluent2-CY26SU10"
VERSIONS = {"visual": "2.14.0", "report": "3.3.0", "page": "2.1.0"}
BLUE, GREY, ORANGE, INK, MUTED = "#2A78D6", "#B5B4AF", "#EB6834", "#0B0B0B", "#52514E"
M = "_Measures"


def uid(key):
    return uuid.uuid5(NS, key).hex[:20]


# ------------------------------------------------------------------ field and formatting helpers
def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": prop}}


def ref(field):
    inner = field.get("Column") or field.get("Measure")
    return f'{inner["Expression"]["SourceRef"]["Entity"]}.{inner["Property"]}', inner["Property"]


def proj(field, display=None):
    query_ref, native = ref(field)
    out = {"field": field, "queryRef": query_ref, "nativeQueryRef": native}
    if display:
        out["displayName"] = display
    return out


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(value):
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_code):
    return {"solid": {"color": text(hex_code)}}


def measure_color(measure_name):
    return {"solid": {"color": {"expr": meas(measure_name)}}}


ALL_POINTS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}


def title_objects(title, subtitle=None, font_size=None):
    properties = {"show": lit("true"), "text": text(title)}
    if font_size:
        properties["fontSize"] = lit(f"{font_size}D")
    objects = {"title": [{"properties": properties}]}
    if subtitle:
        objects["subTitle"] = [{"properties": {"show": lit("true"), "text": text(subtitle)}}]
    return objects


def padding_objects(vertical, horizontal):
    return {"padding": [{"properties": {"top": lit(f"{vertical}D"), "bottom": lit(f"{vertical}D"),
                                        "left": lit(f"{horizontal}D"), "right": lit(f"{horizontal}D")}}]}


# ------------------------------------------------------------------ layout grid (page 1280 x 720 px)
# Every page uses the same rows, so the report looks consistent. Gaps between rows are 8-14 px.
# Cards and slicers turn their container title off / shrink padding: the Fluent2 base theme gives every visual
# 14-16 px padding and the custom theme shows a 12 pt title on every visual, which clipped KPI values and slicers.
PAGE_WIDTH, PAGE_HEIGHT = 1280, 720
MARGIN, GAP = 16, 12                        # outer page margin, gap between visuals in a row
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN     # 1248
HEADER_Y, HEADER_HEIGHT = 8, 56             # page title + subtitle text box (y 8-64)
NAV_Y, NAV_HEIGHT = 16, 40                  # page navigator / back button, vertically centred on the header
SLICER_Y, SLICER_HEIGHT, SLICER_WIDTH = 72, 76, 300        # slicer row (y 72-148)
SLICER_STEP = SLICER_WIDTH + GAP            # slicer slot n starts at x = 16 + n * 312
SLICER_TITLE_PT = 10
CARD_Y, CARD_HEIGHT = 162, 92               # KPI card row (y 162-254)
CARD_PADDING = (8, 12)                      # (top/bottom, left/right) px
ROW2, ROW3 = 266, 493                       # first and second chart rows
HALF, FULL = 215, 442                       # one-row chart height; two-row chart height (ROW3 + HALF - ROW2)
DETAIL_CARD_Y = 76                          # Seller Detail has no slicers: cards sit right under the header
DETAIL_CHART_Y = DETAIL_CARD_Y + CARD_HEIGHT + GAP           # 180
DETAIL_CHART_HEIGHT = ROW3 + HALF - DETAIL_CHART_Y           # 528: ends at y 708 like the other pages' charts


def in_filter(name, field, values):
    inner = field["Column"]
    return {"name": name, "field": field, "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": inner["Expression"]["SourceRef"]["Entity"], "Type": 0}],
                       "Where": [{"Condition": {"In": {
                           "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": inner["Property"]}}],
                           "Values": [[{"Literal": {"Value": v}}] for v in values]}}}]}}


# ------------------------------------------------------------------ visual builder
class Page:
    def __init__(self, key, display_name, subtitle):
        self.key, self.name, self.display_name, self.subtitle = key, uid("page." + key), display_name, subtitle
        self.visuals, self.z = [], 0

    def add(self, key, visual_type, x, y, w, h, roles=None, objects=None, container=None, sort=None,
            filters=None, sync=None):
        self.z += 1
        visual = {"visualType": visual_type}
        if roles:
            visual["query"] = {"queryState": {role: {"projections": [proj(f) if not isinstance(f, tuple) else proj(*f)
                                                                     for f in fields]}
                                              for role, fields in roles.items()}}
            if sort:
                visual["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": d} for f, d in sort],
                                                     "isDefaultSort": False}
        if objects:
            visual["objects"] = objects
        if container:
            visual["visualContainerObjects"] = container
        if sync:
            visual["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
        container_json = {"$schema": f"{SCHEMA}/visualContainer/2.14.0/schema.json", "name": uid(self.key + "." + key),
                          "position": {"x": x, "y": y, "z": self.z * 1000, "height": h, "width": w, "tabOrder": self.z * 1000},
                          "visual": visual}
        if filters:
            container_json["filterConfig"] = {"filters": filters}
        self.visuals.append(container_json)

    # -- reusable pieces
    def header(self, navigator=True):
        paragraphs = [{"textRuns": [{"value": self.display_name,
                                     "textStyle": {"fontWeight": "bold", "fontSize": "18pt", "color": INK}}]},
                      {"textRuns": [{"value": self.subtitle, "textStyle": {"fontSize": "10pt", "color": MUTED}}]}]
        self.add("header", "textbox", MARGIN, HEADER_Y, 600, HEADER_HEIGHT,
                 objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                 container={"background": [{"properties": {"show": lit("false")}}],
                            "border": [{"properties": {"show": lit("false")}}]})
        if navigator:
            self.add("nav", "pageNavigator", 628, NAV_Y, PAGE_WIDTH - MARGIN - 628, NAV_HEIGHT)

    def slicer(self, key, field, slot, mode, sync=None, title=None):
        """Slicer in slot 0, 1, 2... of the slicer row. The default slicer header is hidden (the container title
        names the slicer instead), which leaves room for the date range inputs and the slider."""
        self.add(key, "slicer", MARGIN + slot * SLICER_STEP, SLICER_Y, SLICER_WIDTH, SLICER_HEIGHT,
                 roles={"Values": [field]},
                 objects={"data": [{"properties": {"mode": text(mode)}}],
                          "header": [{"properties": {"show": lit("false")}}]},
                 container=title_objects(title, font_size=SLICER_TITLE_PT) if title else None, sync=sync)

    def cards(self, measures, y=CARD_Y, filters_for=None):
        """One row of KPI cards across the page. The card's own category label names the measure, so the
        container title is turned off and the padding reduced: this stops the value being clipped."""
        width, remainder = divmod(CONTENT_WIDTH - GAP * (len(measures) - 1), len(measures))
        assert remainder == 0, f"{len(measures)} cards do not fit the {CONTENT_WIDTH} px row in whole pixels"
        container = {"title": [{"properties": {"show": lit("false")}}], **padding_objects(*CARD_PADDING)}
        for index, measure in enumerate(measures):
            self.add(f"card{index}", "card", MARGIN + index * (width + GAP), y, width, CARD_HEIGHT,
                     roles={"Values": [meas(measure)]},
                     objects={"labels": [{"properties": {"color": color(BLUE), "fontSize": lit("22D")}}],
                              "categoryLabels": [{"properties": {"show": lit("true"), "color": color(MUTED),
                                                                 "fontSize": lit("10D")}}]},
                     container=container, filters=(filters_for or {}).get(measure))

    def bar_colors(self, measure_name):
        return {"dataPoint": [{"properties": {"fill": measure_color(measure_name)}, "selector": ALL_POINTS}]}


RANKED = lambda name: [in_filter(name, col("dim_seller", "is_ranked_30plus_orders"), ["1L"])]
LABELS_ON = {"labels": [{"properties": {"show": lit("true")}}]}
DATE = col("dim_date", "date_key")
MONTH = col("dim_date", "year_month_label")
CUST_STATE = col("dim_customer", "customer_state")
CATEGORY = col("dim_product", "category_english")
DECILE = col("dim_seller", "late_rate_decile")


def build_pages():
    pages = []

    # ---------------------------------------------------------------- 1. Executive Overview
    p = Page("executive", "Executive Overview", "Olist marketplace, Brazil | valid orders 2017-01 to 2018-08 | R$ (BRL)")
    p.header()
    p.slicer("date", DATE, 0, "Between", sync="PurchaseDate", title="Purchase date")
    p.slicer("state", CUST_STATE, 1, "Dropdown", sync="CustomerState", title="Customer state")
    p.cards(["Total Revenue (R$)", "Orders", "Customers", "AOV (R$)", "Repeat Customer %"])
    p.add("revenue_month", "clusteredColumnChart", 16, ROW2, 816, HALF,
          roles={"Category": [MONTH], "Y": [meas("Total Revenue (R$)")], "Tooltips": [meas("Revenue MoM %"), meas("Orders")]},
          sort=[(MONTH, "Ascending")],
          container=title_objects("Monthly revenue trend", "Black Friday: Nov 2017 revenue +52.06% vs Oct 2017"))
    p.add("revenue_state", "clusteredBarChart", 844, ROW2, 420, FULL,
          roles={"Category": [CUST_STATE], "Y": [meas("Total Revenue (R$)")],
                 "Tooltips": [meas("State Revenue Share %"), meas("State Cumulative Revenue %")]},
          sort=[(meas("Total Revenue (R$)"), "Descending")], objects=LABELS_ON,
          container=title_objects("Revenue by customer state", "SP alone brings 38.30% of revenue"))
    p.add("revenue_category", "clusteredBarChart", 16, ROW3, 816, HALF,
          roles={"Category": [CATEGORY], "Y": [meas("Item Revenue (R$)")],
                 "Tooltips": [meas("Category Revenue Share %"), meas("Category Cumulative Revenue %")]},
          sort=[(meas("Item Revenue (R$)"), "Descending")], objects=LABELS_ON,
          container=title_objects("Revenue by product category", "Highest first; scroll for all 74 categories"))
    pages.append(p)

    # ---------------------------------------------------------------- 2. Customer Retention
    p = Page("retention", "Customer Retention", "Repeat purchase is rare: people counted by customer_unique_id")
    p.header()
    p.slicer("date", DATE, 0, "Between", sync="PurchaseDate", title="Purchase date")
    p.slicer("state", CUST_STATE, 1, "Dropdown", sync="CustomerState", title="Customer state")
    p.cards(["Customers", "Repeat Customers", "One-time Customers", "Repeat Customer %", "Orders per Customer"])
    offset = col("Cohort Month Offset", "month_offset")
    p.add("cohort", "pivotTable", 16, ROW2, 816, FULL,
          roles={"Rows": [(col("dim_customer", "cohort_month"), "Cohort (first order month)")],
                 "Columns": [(offset, "Months since first order")],
                 "Values": [(meas("Cohort Retention % (live)"), "Retention %")]},
          objects={"values": [{"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
              "Input": meas("Cohort Retention % (live)"),
              "FillRule": {"linearGradient2": {"min": {"color": {"Literal": {"Value": "'#FFFFFF'"}}},
                                               "max": {"color": {"Literal": {"Value": f"'{BLUE}'"}}},
                                               "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                           "metadata": f"{M}.Cohort Retention % (live)"}}]},
          filters=[in_filter("cohortMonths1to12", offset, [f"{n}L" for n in range(1, 13)])],
          container=title_objects("Cohort retention: % of each cohort buying again",
                                  "Months 1-12 after the first order. Cohorts use the whole window; the date slicer does not apply."))
    p.add("customer_type", "clusteredBarChart", 844, ROW2, 420, HALF,
          roles={"Category": [col("dim_customer", "Customer Type")], "Y": [meas("Customers")],
                 "Tooltips": [meas("Orders per Customer")]}, objects=LABELS_ON,
          sort=[(meas("Customers"), "Descending")],
          container=title_objects("Customer segmentation", "Repeat = 2+ valid orders over the whole window"))
    band = col("dim_customer", "Order Count Band")
    p.add("orders_band", "clusteredColumnChart", 844, ROW3, 420, HALF,
          roles={"Category": [band], "Y": [meas("Customers")]}, objects=LABELS_ON, sort=[(band, "Ascending")],
          container=title_objects("Orders per customer", "Valid orders per person, whole window"))
    pages.append(p)

    # ---------------------------------------------------------------- 3. Delivery Performance
    p = Page("delivery", "Delivery Performance", "Delivered orders in scope; late = delivered after the estimated date")
    p.header()
    p.slicer("date", DATE, 0, "Between", sync="PurchaseDate", title="Purchase date")
    p.slicer("state", CUST_STATE, 1, "Dropdown", sync="CustomerState", title="Customer state")
    p.cards(["Delivered Orders", "On-Time %", "Late %", "Avg Delivery Days", "Avg Delay (days)"])
    p.add("ontime_month", "lineChart", 16, ROW2, 616, HALF,
          roles={"Category": [MONTH], "Y": [meas("On-Time %")],
                 "Tooltips": [meas("Late %"), meas("Delivered Orders"), meas("Avg Delivery Days")]},
          sort=[(MONTH, "Ascending")], objects={"lineStyles": [{"properties": {"showMarker": lit("true")}}]},
          container=title_objects("Delivery performance by purchase month", "On-time % dipped to 81% in March 2018"))
    bucket = col("fact_orders", "delay_bucket")
    p.add("buckets", "clusteredColumnChart", 644, ROW2, 620, HALF,
          roles={"Category": [bucket], "Y": [meas("Delivered Orders")], "Tooltips": [meas("Avg Review (delivered)")]},
          sort=[(bucket, "Ascending")], objects={**p.bar_colors("Colour - Late Bucket"), **LABELS_ON},
          container=title_objects("Delay bucket analysis", "Delivered date vs estimated date; orange = late"))
    p.add("late_state", "clusteredBarChart", 16, ROW3, 616, HALF,
          roles={"Category": [CUST_STATE], "Y": [meas("Late %")],
                 "Tooltips": [meas("Late % vs Platform (pp)"), meas("Delivered Orders"), meas("Platform Late Rate")]},
          sort=[(meas("Late %"), "Descending")], objects={**p.bar_colors("Colour - Late vs Platform"), **LABELS_ON},
          container=title_objects("Late % by customer state", "Orange = above the platform late rate (6.79%)"))
    p.add("review_delay", "clusteredColumnChart", 644, ROW3, 620, HALF,
          roles={"Category": [bucket], "Y": [meas("Avg Review (delivered)")], "Tooltips": [meas("Delivered Orders")]},
          sort=[(bucket, "Ascending")], objects={**p.bar_colors("Colour - Late Bucket"), **LABELS_ON},
          container=title_objects("Review score vs delivery delay", "7+ days late: 1.70 stars vs 4.29 when early"))
    pages.append(p)

    # ---------------------------------------------------------------- 4. Seller Performance
    p = Page("sellers", "Seller Performance", "Ranked sellers = 30+ delivered orders; rates use seller-order pairs")
    p.header()
    p.slicer("date", DATE, 0, "Between", sync="PurchaseDate", title="Purchase date")
    p.slicer("seller_state", col("dim_seller", "seller_state"), 1, "Dropdown", title="Seller state")
    p.slicer("decile", DECILE, 2, "Dropdown", title="Late-rate decile (1 = worst)")
    p.cards(["Total Sellers", "Ranked Sellers", "Seller Late % (pairs)", "Delivered Orders (seller sum)", "Excess Late Orders"],
            filters_for={m: RANKED(f"rankedCard{i}") for i, m in enumerate(
                ["Seller Late % (pairs)", "Delivered Orders (seller sum)", "Excess Late Orders"])})
    seller = col("dim_seller", "seller_id")
    p.add("worst_sellers", "tableEx", 16, ROW2, 760, FULL,
          roles={"Values": [seller, col("dim_seller", "seller_state"), (meas("Seller Delivered Orders"), "Delivered orders"),
                            (meas("Seller Late %"), "Late %"), (meas("Excess Late Orders"), "Excess late orders"),
                            (meas("Excess Late Rank"), "Excess rank"), (meas("Seller Late Rate Rank"), "Late-rate rank"),
                            (meas("Seller Avg Review"), "Avg review")]},
          sort=[(meas("Excess Late Orders"), "Descending")], filters=RANKED("rankedTable"),
          objects={"values": [{"properties": {"fontColor": measure_color("Colour - Seller Late vs Platform")},
                               "selector": {"metadata": f"{M}.Seller Late %"}}]},
          container=title_objects("Seller ranking: worst performing sellers first",
                                  "Sorted by excess late orders. Right-click a seller > Drill through > Seller Detail"))
    p.add("decile_rate", "clusteredColumnChart", 788, ROW2, 476, HALF,
          roles={"Category": [DECILE], "Y": [meas("Seller Late % (pairs)")], "Tooltips": [meas("Ranked Sellers")]},
          sort=[(DECILE, "Ascending")], filters=RANKED("rankedDecileRate"),
          objects={**p.bar_colors("Colour - Seller Late (pairs) vs Platform"), **LABELS_ON},
          container=title_objects("Seller late rate by decile", "Orange = above the platform late rate"))
    p.add("decile_excess", "clusteredColumnChart", 788, ROW3, 476, HALF,
          roles={"Category": [DECILE], "Y": [meas("Excess Late Orders")],
                 "Tooltips": [meas("Share of Seller Late Orders"), meas("Late Orders (seller sum)")]},
          sort=[(DECILE, "Ascending")], filters=RANKED("rankedDecileExcess"), objects=LABELS_ON,
          container=title_objects("Excess late orders by decile", "Late orders above the platform rate, per decile"))
    pages.append(p)

    # ---------------------------------------------------------------- 5. Product & Revenue
    p = Page("revenue", "Product & Revenue Analysis", "Category revenue = item prices; state revenue = order revenue")
    p.header()
    p.slicer("date", DATE, 0, "Between", sync="PurchaseDate", title="Purchase date")
    p.slicer("state", CUST_STATE, 1, "Dropdown", sync="CustomerState", title="Customer state")
    p.cards(["Total Revenue (R$)", "Orders", "AOV (R$)", "Categories for 80% Revenue", "States for 80% Revenue"])
    p.add("growth", "lineClusteredColumnComboChart", 16, ROW2, 408, HALF,
          roles={"Category": [MONTH], "Y": [meas("Total Revenue (R$)")], "Y2": [meas("Revenue MoM %")],
                 "Tooltips": [meas("Revenue Change vs Previous Month (R$)")]},
          sort=[(MONTH, "Ascending")], container=title_objects("Monthly revenue growth", "Columns = revenue, line = MoM %"))
    p.add("aov", "lineChart", 436, ROW2, 408, HALF,
          roles={"Category": [MONTH], "Y": [meas("AOV (R$)")], "Tooltips": [meas("Orders")]},
          sort=[(MONTH, "Ascending")], objects={"lineStyles": [{"properties": {"showMarker": lit("true")}}]},
          container=title_objects("AOV trend", "Average order value by purchase month"))
    p.add("state_pareto", "lineClusteredColumnComboChart", 856, ROW2, 408, HALF,
          roles={"Category": [CUST_STATE], "Y": [meas("Total Revenue (R$)")], "Y2": [meas("State Cumulative Revenue %")]},
          sort=[(meas("Total Revenue (R$)"), "Descending")],
          container=title_objects("Revenue by state (Pareto)", "7 of 27 states make 80% of revenue"))
    p.add("category_pareto", "lineClusteredColumnComboChart", 16, ROW3, 616, HALF,
          roles={"Category": [CATEGORY], "Y": [meas("Item Revenue (R$)")], "Y2": [meas("Category Cumulative Revenue %")]},
          sort=[(meas("Item Revenue (R$)"), "Descending")],
          container=title_objects("Pareto 80/20: revenue by category", "18 of 74 categories make 80% of revenue"))
    p.add("top_categories", "tableEx", 644, ROW3, 620, HALF,
          roles={"Values": [(meas("Category Revenue Rank"), "Rank"), (CATEGORY, "Category"),
                            (meas("Item Revenue (R$)"), "Revenue (R$)"), (meas("Category Revenue Share %"), "Share"),
                            (meas("Category Cumulative Revenue %"), "Cumulative"), (meas("Item Orders"), "Orders")]},
          sort=[(meas("Item Revenue (R$)"), "Descending")],
          container=title_objects("Top performing categories", "Ranked by item revenue"))
    pages.append(p)

    # ---------------------------------------------------------------- 6. Seller Detail (hidden drill-through)
    p = Page("seller_detail", "Seller Detail", "Drill-through from Seller Performance")
    p.add("back", "actionButton", MARGIN, NAV_Y, 44, NAV_HEIGHT,
          objects={"icon": [{"properties": {"shapeType": text("back")}}]},
          container={"visualLink": [{"properties": {"show": lit("true"), "type": text("Back")}}]})
    # Page heading = a card showing the selected seller (a text box cannot show a measure). It sits right of the back
    # button, centred on the same line (y 36). Container title off: it would only repeat the measure name and,
    # with the theme padding, leave ~4 px for the 16 pt heading.
    title_x = MARGIN + 44 + GAP
    p.add("detail_title", "card", title_x, HEADER_Y, PAGE_WIDTH - MARGIN - title_x, HEADER_HEIGHT,
          roles={"Values": [meas("Seller Detail Title")]},
          objects={"labels": [{"properties": {"color": color(INK), "fontSize": lit("16D")}}],
                   "categoryLabels": [{"properties": {"show": lit("false")}}]},
          container={"title": [{"properties": {"show": lit("false")}}], **padding_objects(*CARD_PADDING)})
    p.cards(["Seller Delivered Orders", "Seller Late %", "Seller Avg Delay (days)", "Seller Avg Review",
             "Seller Revenue (R$)", "Excess Late Orders"], y=DETAIL_CARD_Y)
    p.add("detail_month", "lineChart", 16, DETAIL_CHART_Y, 616, DETAIL_CHART_HEIGHT,
          roles={"Category": [MONTH], "Y": [meas("Seller Late %")],
                 "Tooltips": [meas("Platform Late Rate"), meas("Seller Delivered Orders")]},
          sort=[(MONTH, "Ascending")], objects={"lineStyles": [{"properties": {"showMarker": lit("true")}}]},
          container=title_objects("Late % by month", "Compare with the platform late rate (tooltip)"))
    p.add("detail_categories", "clusteredBarChart", 644, DETAIL_CHART_Y, 620, DETAIL_CHART_HEIGHT,
          roles={"Category": [CATEGORY], "Y": [meas("Seller Delivered Orders")], "Tooltips": [meas("Seller Revenue (R$)")]},
          sort=[(meas("Seller Delivered Orders"), "Descending")], objects=LABELS_ON,
          container=title_objects("What this seller ships", "Delivered orders by category"))
    p.drillthrough = True
    pages.append(p)
    return pages


THEME = {
    "name": "Olist Retention",
    "dataColors": [BLUE, GREY, ORANGE, "#1B4F8C", "#7FB2EB", MUTED, "#F2A27F", "#3F8F6B"],
    "background": "#FFFFFF", "foreground": INK, "tableAccent": BLUE,
    "good": BLUE, "neutral": GREY, "bad": ORANGE, "maximum": BLUE, "center": "#9CC3EE", "minimum": "#FFFFFF",
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": INK},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": INK},
        "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": MUTED},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 24, "color": BLUE}},
    "visualStyles": {
        "*": {"*": {
            "border": [{"show": True, "color": {"solid": {"color": "#E3E2DE"}}, "radius": 8}],
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "dropShadow": [{"show": False}],
            "title": [{"show": True, "fontColor": {"solid": {"color": INK}}, "fontSize": 12}],
            "subTitle": [{"fontColor": {"solid": {"color": MUTED}}, "fontSize": 9}]}},
        "page": {"*": {"background": [{"color": {"solid": {"color": "#F4F4F2"}}, "transparency": 0}],
                       "outspace": [{"color": {"solid": {"color": "#F4F4F2"}}}]}},
        "textbox": {"*": {"border": [{"show": False}], "background": [{"show": False}]}},
        "pageNavigator": {"*": {"border": [{"show": False}], "background": [{"show": False}]}},
        "actionButton": {"*": {"border": [{"show": False}], "background": [{"show": False}]}},
    },
}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main(powerbi_dir, base_theme_file):
    root = Path(powerbi_dir)
    report = root / f"{PROJECT}.Report"
    if report.exists():
        shutil.rmtree(report)                         # generated folder only; rebuilt from scratch each run
    definition = report / "definition"

    write_json(root / f"{PROJECT}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
        "settings": {"enableAutoRecovery": True}})
    write_json(report / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": PROJECT},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NS, "report"))}})
    write_json(report / "definition.pbir", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}}})

    write_json(definition / "version.json", {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write_json(definition / "report.json", {
        "$schema": f"{SCHEMA}/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": VERSIONS, "type": "SharedResources"},
            "customTheme": {"name": "OlistTheme.json", "reportVersionAtImport": VERSIONS, "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "OlistTheme.json", "path": "OlistTheme.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                     "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                     "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    static = report / "StaticResources"
    (static / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base_theme_file, static / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json")
    write_json(static / "RegisteredResources" / "OlistTheme.json", THEME)

    pages = build_pages()
    write_json(definition / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    for p in pages:
        page_json = {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": p.name, "displayName": p.display_name,
                     "displayOption": "FitToPage", "height": 720, "width": 1280}
        if getattr(p, "drillthrough", False):
            seller = col("dim_seller", "seller_id")
            page_json.update({
                "filterConfig": {"filters": [{"name": "drillSeller", "field": seller, "type": "Categorical",
                                              "howCreated": "Drillthrough"}]},
                "pageBinding": {"name": "sellerDetailBinding", "type": "Drillthrough", "referenceScope": "Default",
                                "parameters": [{"name": "sellerDetailParam", "boundFilter": "drillSeller",
                                                "fieldExpr": seller}]},
                "type": "Drillthrough", "visibility": "HiddenInViewMode"})
        write_json(definition / "pages" / p.name / "page.json", page_json)
        for visual in p.visuals:
            write_json(definition / "pages" / p.name / "visuals" / visual["name"] / "visual.json", visual)
    print(f"report written: {report} ({len(pages)} pages, {sum(len(p.visuals) for p in pages)} visuals)")
    for p in pages:
        print(f"  {p.name}  {p.display_name:<28} {len(p.visuals)} visuals")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
