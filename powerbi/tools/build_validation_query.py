"""Stage 5: write a DAX query that checks the Power BI measures against the SQL results.
Usage: python build_validation_query.py <expected_values.csv> <output.dax>

Every expected number and the expected top seller are read from SQL outputs in the folder of <expected_values.csv>,
never typed by hand:
  powerbi_expected_values.csv    the 17 measure values
  seller_late_rate_ranking.csv   the seller with excess_late_rank = 1
  seller_scorecard_totals.csv    platform late and delivered order counts (cross-check of Platform Late Rate)

Paste the .dax file into Power BI Desktop > DAX query view > Run, after refreshing the model. Each row shows the
Power BI value, the SQL value, the difference and PASS / FAIL. The script stops without writing a file if any input
is wrong.
"""
import csv
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RANKING_CSV = "seller_late_rate_ranking.csv"
TOTALS_CSV = "seller_scorecard_totals.csv"
EXPECTED_COLUMNS = {"measure", "filter_context", "expected_value"}

# Plain decimal numbers only: no blanks, text, nan, inf or exponents can reach the DAX query.
NUMBER_PATTERN = re.compile(r"-?[0-9]+(\.[0-9]+)?")
SELLER_ID_PATTERN = re.compile(r"[0-9a-f]{32}")

RANKED = "dim_seller[is_ranked_30plus_orders] = 1"
WHOLE_NUMBER = None     # counts are not rounded in SQL, so they must match exactly

LATE_KEY = ("Late %", "all")
DELIVERED_KEY = ("Delivered Orders (in scope)", "all")
TOP_SELLER_KEY = ("Excess Late Orders", "top seller by excess (rank 1)")

# A slicer selection used to prove that Platform Late Rate ignores filters (UAT-30, UAT-48).
SLICER_FILTERS = 'dim_customer[customer_state] = "SP", dim_date[year_month_label] = "2018-03"'

# The ranked seller(s) with the most excess late orders. TOPN returns every seller tied for first place.
TOP_SELLERS_TABLE = ('TOPN ( 1, ADDCOLUMNS ( VALUES ( dim_seller[seller_id] ), "@Excess", [Excess Late Orders] ), '
                     "[@Excess], DESC )")

# (measure, filter_context) in the CSV  ->  (DAX expression, decimals used by ROUND in sql/06_views_for_powerbi.sql).
# The decimals are listed here because the CSV drops trailing zeros: SQL's 51.70 is stored as 51.7.
# "%" measures return a fraction (0.0303) and the CSV stores a percent (3.0348), so they are multiplied by 100.
CHECKS = {
    ("Total Revenue (R$)", "all valid orders 2017-01 to 2018-08"): ("[Total Revenue (R$)]", 2),
    ("Orders", "all"): ("[Orders]", WHOLE_NUMBER),
    ("AOV (R$)", "all"): ("[AOV (R$)]", 4),
    ("Customers", "all (distinct customer_unique_id)"): ("[Customers]", WHOLE_NUMBER),
    ("Repeat Customer %", "all"): ("100 * [Repeat Customer %]", 4),
    DELIVERED_KEY: ("[Delivered Orders]", WHOLE_NUMBER),
    ("On-Time %", "all"): ("100 * [On-Time %]", 4),
    LATE_KEY: ("100 * [Late %]", 4),
    ("Avg Delay (days)", "all (negative = early)"): ("[Avg Delay (days)]", 4),
    ("Avg Delivery Days", "all"): ("[Avg Delivery Days]", 4),
    ("Avg Review", "all valid orders with a review"): ("[Avg Review]", 4),
    ("Avg Review (delivered)", "orders in delivery scope with a review"): ("[Avg Review (delivered)]", 4),
    # dim_date is marked as a date table, so DATEADD inside the measure still reaches the previous month.
    ("Revenue MoM %", "month = 2018-08 (vs 2018-07)"):
        ('100 * CALCULATE ( [Revenue MoM %], dim_date[year_month_label] = "2018-08" )', 4),
    ("Revenue MoM %", "month = 2017-11 (vs 2017-10)"):
        ('100 * CALCULATE ( [Revenue MoM %], dim_date[year_month_label] = "2017-11" )', 4),
    ("Excess Late Orders", "sellers with 30+ delivered orders (is_ranked_30plus_orders = 1)"):
        (f"CALCULATE ( [Excess Late Orders], {RANKED} )", 2),
    # The DAX for this row needs the expected seller, so top_seller_value_dax builds it.
    TOP_SELLER_KEY: (None, 2),
    ("Seller Late %", "sellers with 30+ delivered orders (seller-order pairs)"):
        (f"100 * CALCULATE ( [Seller Late % (pairs)], {RANKED} )", 4),
}


def dax_text(value):
    return '"' + value.replace('"', '""') + '"'


def decimals_shown(number_text):
    return len(number_text.split(".")[1]) if "." in number_text else 0


def tolerance(decimals):
    """Half of the last decimal place SQL rounded to: 4 decimals -> 0.00005. Whole numbers must match exactly."""
    return Decimal(0) if decimals is WHOLE_NUMBER else Decimal(5) * Decimal(10) ** -(decimals + 1)


def top_seller_value_dax(seller_id):
    """The top seller's excess, or BLANK (which shows FAIL) if the top seller is not the expected one or is tied."""
    return (f"CALCULATE ( VAR TopSellers = {TOP_SELLERS_TABLE} RETURN "
            f'IF ( CONCATENATEX ( TopSellers, dim_seller[seller_id], ", " ) = {dax_text(seller_id)}, '
            f"MAXX ( TopSellers, [@Excess] ) ), {RANKED} )")


def top_seller_detail_dax(seller_id):
    """Text that names the expected seller and the seller Power BI actually found."""
    found = (f"CALCULATE ( VAR TopSellers = {TOP_SELLERS_TABLE} RETURN "
             f'CONCATENATEX ( TopSellers, dim_seller[seller_id], ", " ), {RANKED} )')
    return f'{dax_text(f"Expected seller {seller_id}; Power BI top seller: ")} & {found}'


def read_csv_rows(csv_path, required_columns, errors):
    """Return the rows of a CSV, or an empty list after recording why it cannot be used."""
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                errors.append(f"{Path(csv_path).name}: missing columns {sorted(missing_columns)}")
                return []
            return list(reader)
    except OSError as problem:
        errors.append(f"{Path(csv_path).name}: cannot be read ({problem})")
        return []


def validate_expected_rows(rows, errors):
    """Check the expected-values CSV and return {(measure, filter_context): expected value text}."""
    expected = {}
    for line_number, row in enumerate(rows, start=2):       # line 1 is the header
        key = (row["measure"], row["filter_context"])
        value_text = row["expected_value"]
        if key in expected:
            errors.append(f"line {line_number}: duplicate check {key}")
            continue
        expected[key] = value_text
        if value_text is None or not NUMBER_PATTERN.fullmatch(value_text):
            errors.append(f"line {line_number}: expected value {value_text!r} is not a number for {key}")
        elif key in CHECKS:
            decimals = CHECKS[key][1]
            if decimals is WHOLE_NUMBER and Decimal(value_text) != Decimal(value_text).to_integral_value():
                errors.append(f"line {line_number}: expected value {value_text} must be a whole number for {key}")
            elif decimals is not WHOLE_NUMBER and decimals_shown(value_text) > decimals:
                errors.append(f"line {line_number}: expected value {value_text} has more than {decimals} decimals "
                              f"for {key}")

    for key in expected:
        if key not in CHECKS:
            errors.append(f"unexpected check in CSV (no DAX defined): {key}")
    for key in CHECKS:
        if key not in expected:
            errors.append(f"missing check in CSV: {key}")
    return expected


def find_top_seller(ranking_csv, expected, errors):
    """Return the one seller SQL ranks first by excess late orders, after matching its value to the expected CSV."""
    columns = {"seller_id", "excess_late_orders", "excess_late_rank"}
    top_rows = [row for row in read_csv_rows(ranking_csv, columns, errors) if row["excess_late_rank"] == "1"]
    if len(top_rows) != 1:
        errors.append(f"{RANKING_CSV}: expected exactly 1 seller with excess_late_rank = 1, found {len(top_rows)}")
        return None
    seller_id, excess_text = top_rows[0]["seller_id"], top_rows[0]["excess_late_orders"]
    if not SELLER_ID_PATTERN.fullmatch(seller_id):
        errors.append(f"{RANKING_CSV}: {seller_id!r} is not a valid seller_id")
        return None
    expected_text = expected.get(TOP_SELLER_KEY, "")
    if NUMBER_PATTERN.fullmatch(excess_text) and NUMBER_PATTERN.fullmatch(expected_text):
        if Decimal(excess_text) != Decimal(expected_text):
            errors.append(f"{RANKING_CSV}: top seller excess {excess_text} differs from the expected value "
                          f"{expected_text}")
    elif expected_text:
        errors.append(f"{RANKING_CSV}: top seller excess {excess_text!r} is not a number")
    return seller_id


def check_platform_rate(totals_csv, expected, errors):
    """Confirm that SQL's platform order counts reproduce the Late % and Delivered Orders values in the expected CSV."""
    columns = {"platform_late_orders", "platform_delivered_orders"}
    rows = read_csv_rows(totals_csv, columns, errors)
    if len(rows) != 1:
        if not errors:
            errors.append(f"{TOTALS_CSV}: expected exactly 1 row, found {len(rows)}")
        return
    late_text, delivered_text = rows[0]["platform_late_orders"], rows[0]["platform_delivered_orders"]
    expected_late, expected_delivered = expected.get(LATE_KEY, ""), expected.get(DELIVERED_KEY, "")
    numbers = (late_text, delivered_text, expected_late, expected_delivered)
    if not all(NUMBER_PATTERN.fullmatch(number) for number in numbers) or Decimal(delivered_text) == 0:
        errors.append(f"{TOTALS_CSV}: platform counts cannot be compared with the expected values")
        return
    late_percent = (100 * Decimal(late_text) / Decimal(delivered_text)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    if late_percent != Decimal(expected_late):
        errors.append(f"{TOTALS_CSV}: platform late rate {late_percent} differs from Late % {expected_late}")
    if Decimal(delivered_text) != Decimal(expected_delivered):
        errors.append(f"{TOTALS_CSV}: platform delivered orders {delivered_text} differs from {expected_delivered}")


def build_checks(rows, expected, seller_id):
    """Return every check as (measure, context, DAX value, expected text, decimals, DAX detail text)."""
    checks = []
    for row in rows:
        key = (row["measure"], row["filter_context"])
        dax_value, decimals = CHECKS[key]
        detail = '""'
        if key == TOP_SELLER_KEY:
            dax_value, detail = top_seller_value_dax(seller_id), top_seller_detail_dax(seller_id)
        checks.append((row["measure"], row["filter_context"], dax_value, row["expected_value"], decimals, detail))

    # Platform Late Rate has no row of its own in the CSV: with no filters it must equal the overall Late %.
    late_text = expected[LATE_KEY]
    late_decimals = CHECKS[LATE_KEY][1]
    checks.append(("Platform Late Rate", "no filters (equals overall Late %)",
                   "100 * [Platform Late Rate]", late_text, late_decimals, '""'))
    filtered_late = f'FORMAT ( 100 * CALCULATE ( [Late %], {SLICER_FILTERS} ), "0.0000" )'
    checks.append(("Platform Late Rate", "customer state SP and month 2018-03 (must not change)",
                   f"100 * CALCULATE ( [Platform Late Rate], {SLICER_FILTERS} )", late_text, late_decimals,
                   f'"Late % with these filters: " & {filtered_late}'))
    return checks


def build_query(expected_csv_name, checks):
    lines = []
    for number, (measure, context, dax_value, expected_text, decimals, detail) in enumerate(checks, start=1):
        lines.append(f'    ROW ( "Check", {number}, "Measure", {dax_text(measure)}, "Context", {dax_text(context)},\n'
                     f'          "Power BI", 1.0 * ( {dax_value} ),\n'
                     f'          "SQL expected", {expected_text}, "Tolerance", {tolerance(decimals):.10f},\n'
                     f'          "Detail", {detail} )')
    return (
        f"// Stage 5 check: Power BI measures vs SQL ({expected_csv_name}, {RANKING_CSV}, {TOTALS_CSV}).\n"
        "// Generated by powerbi/tools/build_validation_query.py - do not edit by hand.\n"
        "// Refresh the model first, then run this in DAX query view.\n"
        "EVALUATE\n"
        "VAR Checks =\n"
        "    UNION (\n" + ",\n".join(lines) + "\n    )\n"
        "RETURN\n"
        "    ADDCOLUMNS (\n"
        "        Checks,\n"
        '        "Difference", [Power BI] - [SQL expected],\n'
        '        "Result", IF ( NOT ISBLANK ( [Power BI] ) && ABS ( [Power BI] - [SQL expected] ) <= [Tolerance], "PASS", "FAIL" )\n'
        "    )\n"
        "ORDER BY [Check]\n")


def main(expected_csv, output_dax):
    outputs_folder = Path(expected_csv).parent
    errors = []
    rows = read_csv_rows(expected_csv, EXPECTED_COLUMNS, errors)
    expected = validate_expected_rows(rows, errors) if rows or not errors else {}
    seller_id = find_top_seller(outputs_folder / RANKING_CSV, expected, errors)
    check_platform_rate(outputs_folder / TOTALS_CSV, expected, errors)
    if errors:
        sys.exit("Validation query not written. Fix these problems:\n  " + "\n  ".join(errors))

    checks = build_checks(rows, expected, seller_id)
    Path(output_dax).write_text(build_query(Path(expected_csv).name, checks), encoding="utf-8")
    print(f"wrote {output_dax}: {len(checks)} checks")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python build_validation_query.py <expected_values.csv> <output.dax>")
    main(sys.argv[1], sys.argv[2])
