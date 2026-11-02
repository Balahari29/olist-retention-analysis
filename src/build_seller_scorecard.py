"""
Build excel/seller_scorecard.xlsx from excel/seller_scorecard_data.csv with openpyxl.

Sheets: KPI, Scorecard, What-If, Targets, Data.
Only INPUTS are typed in (each labelled with its source in outputs/); every RESULT is an Excel formula.
Functions added after Excel 2007 need the _xlfn. prefix in the file (XLOOKUP, RANK.EQ, PERCENTILE.INC).

Run from the project root:  .venv/bin/python src/build_seller_scorecard.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_CSV = PROJECT_ROOT / "excel" / "seller_scorecard_data.csv"
WORKBOOK_PATH = PROJECT_ROOT / "excel" / "seller_scorecard.xlsx"
OUTPUTS = PROJECT_ROOT / "outputs"

# Formats and colours
BRL_FORMAT = '"R$" #,##0.00'
BRL_FORMAT_NO_DECIMALS = '"R$" #,##0'
PERCENT_FORMAT = "0.00%"
TITLE_FONT = Font(size=14, bold=True)
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="2A78D6")
INPUT_FILL = PatternFill("solid", fgColor="DDEBFB")        # blue = an input / assumption you may change
INPUT_FONT = Font(color="1C5CAB", bold=True)
NOTE_FONT = Font(italic=True, color="52514E")
THIN_BORDER = Border(*(Side(style="thin", color="C9C8C3"),) * 4)


def style_header_row(sheet, row, first_column, last_column):
    for column in range(first_column, last_column + 1):
        cell = sheet.cell(row=row, column=column)
        cell.font, cell.fill = HEADER_FONT, HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def mark_input(cell):
    cell.fill, cell.font, cell.border = INPUT_FILL, INPUT_FONT, THIN_BORDER


def main():
    sellers = pd.read_csv(DATA_CSV)
    totals = pd.read_csv(OUTPUTS / "seller_scorecard_totals.csv").iloc[0]
    delivery_kpis = pd.read_csv(OUTPUTS / "delivery_kpis_overall.csv").iloc[0]
    test_results = pd.read_csv(OUTPUTS / "hypothesis_test_results.csv")
    stars_per_late_order_low = abs(test_results.loc[test_results["analysis"].str.startswith("sensitivity"),
                                                    "mean_difference_late_minus_on_time"].iloc[0])
    stars_per_late_order_high = abs(test_results.loc[test_results["analysis"].str.startswith("main"),
                                                     "mean_difference_late_minus_on_time"].iloc[0])

    seller_count = len(sellers)
    data_last_row = seller_count + 1                       # row 1 = headers
    workbook = Workbook()

    # ------------------------------------------------------------------ Data sheet (formatted Excel Table)
    data_sheet = workbook.active
    data_sheet.title = "Data"
    data_sheet.append(list(sellers.columns))
    for row in sellers.itertuples(index=False):
        data_sheet.append(list(row))
    last_column_letter = get_column_letter(len(sellers.columns))
    seller_table = Table(displayName="SellerData", ref=f"A1:{last_column_letter}{data_last_row}")
    seller_table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    data_sheet.add_table(seller_table)
    data_sheet.freeze_panes = "B2"
    column_of = {name: get_column_letter(index + 1) for index, name in enumerate(sellers.columns)}
    for row in range(2, data_last_row + 1):
        data_sheet[f"{column_of['revenue_brl']}{row}"].number_format = BRL_FORMAT
    for name, width in {"seller_id": 36, "seller_city": 22, "revenue_brl": 16}.items():
        data_sheet.column_dimensions[column_of[name]].width = width

    def data_range(column_name):
        """Absolute range of one Data column, e.g. Data!$D$2:$D$626."""
        letter = column_of[column_name]
        return f"Data!${letter}$2:${letter}${data_last_row}"

    # ------------------------------------------------------------------ Targets sheet (assumptions)
    targets = workbook.create_sheet("Targets")
    targets["A1"] = "Targets and assumptions"
    targets["A1"].font = TITLE_FONT
    targets["A2"] = "Blue cells are inputs. Change an ASSUMPTION to see how the Scorecard and What-If sheets respond."
    targets["A2"].font = NOTE_FONT
    target_headers = ["Item", "Value", "Unit", "Type", "Source / note"]
    for column, header in enumerate(target_headers, start=1):
        targets.cell(row=4, column=column, value=header)
    style_header_row(targets, 4, 1, len(target_headers))
    target_rows = [
        ("Platform late orders", int(totals["platform_late_orders"]), "orders", "Input (from data)",
         "outputs/seller_scorecard_totals.csv (= late_orders in outputs/delivery_kpis_overall.csv)"),
        ("Platform delivered orders", int(totals["platform_delivered_orders"]), "orders", "Input (from data)",
         "outputs/seller_scorecard_totals.csv (= delivered_orders_in_scope in outputs/delivery_kpis_overall.csv)"),
        ("Late-rate target", "=B5/B6", "% of orders", "ASSUMPTION",
         "Target = platform average late rate (calculated from the two rows above)"),
        ("Review target", 4.0, "stars", "ASSUMPTION", "A seller should average at least 4.0 stars"),
        ("Action: late-rate multiple", 2, "x target", "ASSUMPTION", "Action if late rate is at least 2x the target"),
        ("Action: review below", 3.5, "stars", "ASSUMPTION", "Action if average review is below 3.5 stars"),
    ]
    for row_number, (item, value, unit, kind, note) in enumerate(target_rows, start=5):
        targets.cell(row=row_number, column=1, value=item)
        value_cell = targets.cell(row=row_number, column=2, value=value)
        targets.cell(row=row_number, column=3, value=unit)
        type_cell = targets.cell(row=row_number, column=4, value=kind)
        targets.cell(row=row_number, column=5, value=note).font = NOTE_FONT
        if kind == "ASSUMPTION":
            type_cell.font = Font(bold=True, color="D03B3B")
        if not str(value).startswith("="):
            mark_input(value_cell)
    targets["B7"].number_format = PERCENT_FORMAT
    targets["B8"].number_format = "0.00"
    targets["B10"].number_format = "0.00"
    for letter, width in {"A": 30, "B": 12, "C": 13, "D": 20, "E": 90}.items():
        targets.column_dimensions[letter].width = width
    target_keys, target_values = "Targets!$A$5:$A$10", "Targets!$B$5:$B$10"

    def lookup_target(name):
        return f'_xlfn.XLOOKUP("{name}",{target_keys},{target_values})'

    # ------------------------------------------------------------------ Scorecard sheet
    scorecard = workbook.create_sheet("Scorecard", 0)
    scorecard["A1"] = "Seller delivery scorecard (sellers with 30+ delivered orders)"
    scorecard["A1"].font = TITLE_FONT
    scorecard["A2"] = ("Status: Action = late rate >= 2x target OR review < 3.5;  On target = late rate <= target AND "
                       "review >= 4.0;  otherwise Watch (thresholds on the Targets sheet). Orange rows = bottom 10% "
                       "of sellers by late rate.")
    scorecard["A2"].font = NOTE_FONT
    first_row, last_row = 6, 6 + seller_count - 1
    scorecard["A3"] = "Bottom-10% cut-off (90th percentile of late rate)"
    scorecard["E3"] = f"=_xlfn.PERCENTILE.INC($E${first_row}:$E${last_row},0.9)"
    scorecard["E3"].number_format = PERCENT_FORMAT
    scorecard["A4"] = "Sellers highlighted (late rate at or above the cut-off)"
    scorecard["E4"] = f'=COUNTIF($E${first_row}:$E${last_row},">="&$E$3)'
    for cell in ("E3", "E4"):
        scorecard[cell].font = Font(bold=True)

    scorecard_headers = ["Seller ID", "State", "Delivered orders", "Late orders", "Late rate", "Avg review",
                         "Revenue (R$)", "Excess late orders", "Excess-late rank", "Late-rate target",
                         "Review target", "Status", "Late-rate decile (SQL NTILE)", "Bottom 10%"]
    for column, header in enumerate(scorecard_headers, start=1):
        scorecard.cell(row=5, column=column, value=header)
    style_header_row(scorecard, 5, 1, len(scorecard_headers))
    scorecard.row_dimensions[5].height = 32

    seller_ids = data_range("seller_id")
    for offset, seller_id in enumerate(sellers["seller_id"]):
        row = first_row + offset
        key = f"$A{row}"
        scorecard[f"A{row}"] = seller_id                                       # row label (data, not a result)
        scorecard[f"B{row}"] = f"=_xlfn.XLOOKUP({key},{seller_ids},{data_range('seller_state')})"
        scorecard[f"C{row}"] = f"=_xlfn.XLOOKUP({key},{seller_ids},{data_range('delivered_orders')})"
        scorecard[f"D{row}"] = f"=_xlfn.XLOOKUP({key},{seller_ids},{data_range('late_orders')})"
        scorecard[f"E{row}"] = f"=IF(C{row}=0,\"\",D{row}/C{row})"
        scorecard[f"F{row}"] = (f"=IFERROR(_xlfn.XLOOKUP({key},{seller_ids},{data_range('review_score_sum')})"
                                f"/_xlfn.XLOOKUP({key},{seller_ids},{data_range('reviewed_orders')}),\"\")")
        scorecard[f"G{row}"] = f"=_xlfn.XLOOKUP({key},{seller_ids},{data_range('revenue_brl')})"
        scorecard[f"H{row}"] = f"=D{row}-C{row}*J{row}"                       # late orders above the target rate
        scorecard[f"I{row}"] = f"=_xlfn.RANK.EQ(H{row},$H${first_row}:$H${last_row},0)"
        scorecard[f"J{row}"] = f"={lookup_target('Late-rate target')}"
        scorecard[f"K{row}"] = f"={lookup_target('Review target')}"
        scorecard[f"L{row}"] = (f"=IF(OR(E{row}>=J{row}*{lookup_target('Action: late-rate multiple')},"
                                f"F{row}<{lookup_target('Action: review below')}),\"Action\","
                                f"IF(AND(E{row}<=J{row},F{row}>=K{row}),\"On target\",\"Watch\"))")
        scorecard[f"M{row}"] = f"=_xlfn.XLOOKUP({key},{seller_ids},{data_range('late_rate_decile')})"
        scorecard[f"N{row}"] = f"=IF(E{row}>=$E$3,\"Yes\",\"No\")"
        scorecard[f"E{row}"].number_format = PERCENT_FORMAT
        scorecard[f"F{row}"].number_format = "0.00"
        scorecard[f"G{row}"].number_format = BRL_FORMAT
        scorecard[f"H{row}"].number_format = "0.00"
        scorecard[f"J{row}"].number_format = PERCENT_FORMAT
        scorecard[f"K{row}"].number_format = "0.00"

    full_rows = f"A{first_row}:N{last_row}"
    # Bottom 10% of sellers (highest late rate): light orange row
    scorecard.conditional_formatting.add(
        full_rows, FormulaRule(formula=[f"$E{first_row}>=$E$3"], fill=PatternFill("solid", fgColor="FDE3D8")))
    # Status colours (the label is always shown, so colour is never the only signal)
    status_cells = f"L{first_row}:L{last_row}"
    for status, colour, font_colour in [("Action", "F8D7D7", "9B1C1C"), ("Watch", "FFF1CC", "7A5200"),
                                        ("On target", "D9F2D9", "0B6B0B")]:
        scorecard.conditional_formatting.add(status_cells, FormulaRule(
            formula=[f'$L{first_row}="{status}"'], fill=PatternFill("solid", fgColor=colour),
            font=Font(bold=True, color=font_colour)))
    scorecard.auto_filter.ref = f"A5:N{last_row}"
    scorecard.freeze_panes = "B6"
    for letter, width in {"A": 36, "B": 7, "C": 11, "D": 9, "E": 10, "F": 9, "G": 15, "H": 11, "I": 10,
                          "J": 11, "K": 9, "L": 11, "M": 13, "N": 9}.items():
        scorecard.column_dimensions[letter].width = width

    # ------------------------------------------------------------------ What-If sheet
    what_if = workbook.create_sheet("What-If", 1)
    what_if["A1"] = "What if late deliveries fall? Expected rise in the average review score"
    what_if["A1"].font = TITLE_FONT
    what_if["A3"] = "% reduction in late orders (input)"
    what_if["B3"] = 0.2
    what_if["B3"].number_format = "0%"
    mark_input(what_if["B3"])
    what_if["A5"] = "Inputs"
    what_if["A5"].font = Font(bold=True)
    what_if_inputs = [
        ("Delivered orders (platform)", "=Targets!B6", "#,##0", "Targets sheet"),
        ("Late orders (platform)", "=Targets!B5", "#,##0", "Targets sheet"),
        ("Current average review score", float(delivery_kpis["avg_review_score"]), "0.00",
         "outputs/delivery_kpis_overall.csv (avg_review_score)"),
        ("Stars lost per late order - LOW", float(stars_per_late_order_low), "0.00",
         "outputs/hypothesis_test_results.csv (sensitivity: reviews written after delivery)"),
        ("Stars lost per late order - HIGH", float(stars_per_late_order_high), "0.00",
         "outputs/hypothesis_test_results.csv (main: all reviews)"),
    ]
    for row, (label, value, number_format, source) in enumerate(what_if_inputs, start=6):
        what_if[f"A{row}"] = label
        what_if[f"B{row}"] = value
        what_if[f"B{row}"].number_format = number_format
        what_if[f"C{row}"] = source
        what_if[f"C{row}"].font = NOTE_FONT
        if not str(value).startswith("="):
            mark_input(what_if[f"B{row}"])

    what_if["A12"] = "Results (formulas)"
    what_if["A12"].font = Font(bold=True)
    what_if_results = [
        ("Late orders avoided", "=B7*B3", "#,##0"),
        ("Current late %", "=B7/B6", PERCENT_FORMAT),
        ("New late %", "=(B7-B13)/B6", PERCENT_FORMAT),
        ("Rise in average review - LOW", "=B13/B6*B9", "0.000"),
        ("Rise in average review - HIGH", "=B13/B6*B10", "0.000"),
        ("New average review - LOW", "=B8+B16", "0.00"),
        ("New average review - HIGH", "=B8+B17", "0.00"),
    ]
    for row, (label, formula, number_format) in enumerate(what_if_results, start=13):
        what_if[f"A{row}"] = label
        what_if[f"B{row}"] = formula
        what_if[f"B{row}"].number_format = number_format
    what_if["A21"] = ('="A "&TEXT(B3,"0%")&" cut in late orders should lift the average review by "'
                      '&TEXT(B16,"0.00")&" to "&TEXT(B17,"0.00")&" stars (from "&TEXT(B8,"0.00")&" to "'
                      '&TEXT(B18,"0.00")&"-"&TEXT(B19,"0.00")&")."')
    what_if["A21"].font = Font(bold=True)
    what_if["A22"] = ("Method: rise = (late orders avoided / delivered orders) x stars lost per late order. Assumes reviewed "
                      "orders behave like all delivered orders, and that a late order turned on-time scores like an "
                      "on-time order.")
    what_if["A22"].font = NOTE_FONT

    # Frame for Excel's Data Table (What-If Analysis > Data Table, column input cell = B3); see manual_steps.md
    what_if["A24"] = "Sensitivity table: build with Data > What-If Analysis > Data Table (column input cell: B3)"
    what_if["A24"].font = Font(bold=True)
    for column, header in enumerate(["% reduction", "Rise LOW", "Rise HIGH", "New avg LOW", "New avg HIGH"], start=1):
        what_if.cell(row=25, column=column, value=header)
    style_header_row(what_if, 25, 1, 5)
    for column, formula in zip("BCDE", ["=B16", "=B17", "=B18", "=B19"]):
        what_if[f"{column}26"] = formula                                     # formulas the Data Table recalculates
        what_if[f"{column}26"].number_format = "0.000"
    what_if["A26"] = "(current)"
    for row, reduction in zip(range(27, 32), [0.1, 0.2, 0.3, 0.4, 0.5]):
        what_if[f"A{row}"] = reduction
        what_if[f"A{row}"].number_format = "0%"
    what_if["A32"] = "Cells B27:E31 are filled by Excel's Data Table (excel/manual_steps.md, step 3)."
    what_if["A32"].font = NOTE_FONT
    for letter, width in {"A": 36, "B": 14, "C": 14, "D": 14, "E": 14}.items():
        what_if.column_dimensions[letter].width = width

    # ------------------------------------------------------------------ KPI sheet (tiles)
    kpi = workbook.create_sheet("KPI", 0)
    kpi["B1"] = "Seller scorecard: headline KPIs"
    kpi["B1"].font = TITLE_FONT
    kpi["B2"] = ("Sellers with 30+ delivered orders. Late % and review are over seller-order pairs "
                 "(an order with 2 sellers counts for each).")
    kpi["B2"].font = NOTE_FONT
    tiles = [
        ("B", "Sellers", f"=COUNTA({data_range('seller_id')})", "#,##0"),
        ("E", "Late %", f"=SUM({data_range('late_orders')})/SUM({data_range('delivered_orders')})", PERCENT_FORMAT),
        ("H", "Avg review (stars)", f"=SUM({data_range('review_score_sum')})/SUM({data_range('reviewed_orders')})", "0.00"),
        ("K", "Revenue (R$)", f"=SUM({data_range('revenue_brl')})", BRL_FORMAT_NO_DECIMALS),
    ]
    tile_fill = PatternFill("solid", fgColor="F0EFEC")
    for first_letter, label, formula, number_format in tiles:
        first_index = ord(first_letter) - ord("A") + 1
        last_letter = get_column_letter(first_index + 1)
        kpi.merge_cells(f"{first_letter}4:{last_letter}4")
        kpi.merge_cells(f"{first_letter}5:{last_letter}6")
        kpi[f"{first_letter}4"] = label
        kpi[f"{first_letter}4"].font = Font(bold=True, color="52514E")
        kpi[f"{first_letter}5"] = formula
        kpi[f"{first_letter}5"].font = Font(size=22, bold=True, color="0B0B0B")
        kpi[f"{first_letter}5"].number_format = number_format
        for row in (4, 5, 6):
            for column in (first_index, first_index + 1):
                cell = kpi.cell(row=row, column=column)
                cell.fill = tile_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
        kpi.column_dimensions[first_letter].width = 13
        kpi.column_dimensions[last_letter].width = 13
    for spacer in ("A", "D", "G", "J"):
        kpi.column_dimensions[spacer].width = 3
    kpi["B8"] = "Source: Data sheet (excel/seller_scorecard_data.csv, from MySQL view v_seller_scorecard)."
    kpi["B8"].font = NOTE_FONT

    workbook.calculation.fullCalcOnLoad = True        # Excel recalculates every formula when the file opens
    workbook.save(WORKBOOK_PATH)
    print(f"saved {WORKBOOK_PATH.relative_to(PROJECT_ROOT)}: sheets {workbook.sheetnames}, {seller_count} sellers")


if __name__ == "__main__":
    main()
