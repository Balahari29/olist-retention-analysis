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

# view name -> (output file, ORDER BY clause)
EXPORTS = {
    "v_seller_scorecard": (PROJECT_ROOT / "excel" / "seller_scorecard_data.csv", "excess_late_rank, seller_id"),
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
        output_path.parent.mkdir(exist_ok=True)
        frame.to_csv(output_path, index=False)
        print(f"{view_name}: {len(frame)} rows -> {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
