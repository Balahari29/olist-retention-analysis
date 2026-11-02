"""
Export MySQL views to CSV files used outside SQL (Excel, Power BI imports).

Run from the project root:  .venv/bin/python src/export_views.py
"""
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_to_mysql import get_engine   # same .env-based connection as the loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POWERBI_DATA = PROJECT_ROOT / "powerbi" / "data"

# view name -> (output file, ORDER BY clause)
EXPORTS = {
    "v_seller_scorecard": (PROJECT_ROOT / "excel" / "seller_scorecard_data.csv", "excess_late_rank, seller_id"),
    # Power BI star schema (sql/06_views_for_powerbi.sql) + RFM segments (written by notebooks/analysis.ipynb)
    "fact_orders": (POWERBI_DATA / "fact_orders.csv", "order_id"),
    "fact_order_items": (POWERBI_DATA / "fact_order_items.csv", "order_id, order_item_id"),
    "dim_customer": (POWERBI_DATA / "dim_customer.csv", "customer_id"),
    "dim_seller": (POWERBI_DATA / "dim_seller.csv", "seller_id"),
    "dim_product": (POWERBI_DATA / "dim_product.csv", "product_id"),
    "dim_date": (POWERBI_DATA / "dim_date.csv", "date_key"),
    "rfm_customer_segments": (POWERBI_DATA / "rfm_customer_segments.csv", "customer_unique_id"),
}


def main():
    engine = get_engine(database="olist")
    for view_name, (output_path, order_by) in EXPORTS.items():
        with engine.connect() as connection:
            frame = pd.read_sql(text(f"SELECT * FROM {view_name} ORDER BY {order_by}"), connection)
        # MySQL DECIMAL arrives as Python Decimal; store as plain numbers
        for column in frame.columns:
            if frame[column].map(lambda value: isinstance(value, Decimal)).any():
                frame[column] = frame[column].astype(float)
        frame = frame.convert_dtypes()   # whole-number columns (e.g. SUM() counts) as integers, not 172.0
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_path, index=False)
        print(f"{view_name}: {len(frame)} rows -> {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
