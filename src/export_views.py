"""
Export MySQL views to CSV files used outside SQL: the Excel scorecard, the Power BI design (powerbi/data/)
and the Tableau Public dashboard (tableau/data/). Both data folders are git-ignored; regenerate with this script.

Run from the project root:  .venv/bin/python src/export_views.py
"""
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_to_mysql import get_engine   # same .env-based connection as the loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWERBI_DATA = PROJECT_ROOT / "powerbi" / "data"
TABLEAU_DATA = PROJECT_ROOT / "tableau" / "data"
OUTPUTS = PROJECT_ROOT / "outputs"

# view name -> (list of output files, ORDER BY clause). Each view is read once and written to every file listed.
EXPORTS = {
    "v_seller_scorecard": ([PROJECT_ROOT / "excel" / "seller_scorecard_data.csv"], "excess_late_rank, seller_id"),
}
# Star schema (sql/06_views_for_powerbi.sql) + RFM segments (written by notebooks/analysis.ipynb):
# the same files feed the Power BI design and the Tableau build.
STAR_SCHEMA = {
    "fact_orders": "order_id",
    "fact_order_items": "order_id, order_item_id",
    "dim_customer": "customer_id",
    "dim_seller": "seller_id",
    "dim_product": "product_id",
    "dim_date": "date_key",
    "rfm_customer_segments": "customer_unique_id",
}
for view_name, order_by in STAR_SCHEMA.items():
    EXPORTS[view_name] = ([POWERBI_DATA / f"{view_name}.csv", TABLEAU_DATA / f"{view_name}.csv"], order_by)

# Results computed in SQL/Python over the whole period, used by Tableau as separate (static) data sources
TABLEAU_STATIC_OUTPUTS = [
    "retention_cohort_long.csv",
    "distance_vs_delay_bands.csv",
    "retention_first_order_late_vs_on_time.csv",
    "rfm_segments.csv",
]


def main():
    engine = get_engine(database="olist")
    for view_name, (output_paths, order_by) in EXPORTS.items():
        with engine.connect() as connection:
            frame = pd.read_sql(text(f"SELECT * FROM {view_name} ORDER BY {order_by}"), connection)
        # MySQL DECIMAL arrives as Python Decimal; store as plain numbers
        for column in frame.columns:
            if frame[column].map(lambda value: isinstance(value, Decimal)).any():
                frame[column] = frame[column].astype(float)
        frame = frame.convert_dtypes()   # whole-number columns (e.g. SUM() counts) as integers, not 172.0
        for output_path in output_paths:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(output_path, index=False)
            print(f"{view_name}: {len(frame)} rows -> {output_path.relative_to(PROJECT_ROOT)}")

    TABLEAU_DATA.mkdir(parents=True, exist_ok=True)
    for file_name in TABLEAU_STATIC_OUTPUTS:
        shutil.copy2(OUTPUTS / file_name, TABLEAU_DATA / file_name)
        print(f"outputs/{file_name} -> {(TABLEAU_DATA / file_name).relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
