"""
Load the 9 Olist CSVs from data/raw/ into the MySQL database `olist`.

Steps:
  1. Run sql/01_schema.sql (drops and recreates the database, so the load is re-runnable).
  2. Read each CSV in chunks with pandas and append it to its table with SQLAlchemy.
  3. Reconcile row counts (rows read by pandas vs rows in MySQL) -> outputs/row_counts.csv

Run from the project root:  .venv/bin/python src/load_to_mysql.py
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_FILE = PROJECT_ROOT / "sql" / "01_schema.sql"
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "row_counts.csv"
CHUNK_SIZE = 50_000

# One entry per table, in load order: parents before children, so foreign keys are satisfied.
#   text_columns: read as strings (IDs, zip prefixes keep leading zeros)
#   integer_columns: pandas nullable integers ("Int64"), so missing values stay NULL instead of becoming floats
#   date_columns: parsed to datetime; empty cells become NULL
#   rename: source column -> table column
TABLES = [
    {
        "table": "category_translation",
        "file": "product_category_name_translation.csv",
        "text_columns": ["product_category_name", "product_category_name_english"],
    },
    {
        "table": "customers",
        "file": "olist_customers_dataset.csv",
        "text_columns": ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                         "customer_city", "customer_state"],
    },
    {
        "table": "sellers",
        "file": "olist_sellers_dataset.csv",
        "text_columns": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    },
    {
        "table": "products",
        "file": "olist_products_dataset.csv",
        "text_columns": ["product_id", "product_category_name"],
        "integer_columns": ["product_name_lenght", "product_description_lenght", "product_photos_qty",
                            "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"],
        # Fix the typo in the source column names (documented in README)
        "rename": {"product_name_lenght": "product_name_length",
                   "product_description_lenght": "product_description_length"},
    },
    {
        "table": "orders",
        "file": "olist_orders_dataset.csv",
        "text_columns": ["order_id", "customer_id", "order_status"],
        "date_columns": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
                         "order_delivered_customer_date", "order_estimated_delivery_date"],
    },
    {
        "table": "order_items",
        "file": "olist_order_items_dataset.csv",
        "text_columns": ["order_id", "product_id", "seller_id"],
        "integer_columns": ["order_item_id"],
        "date_columns": ["shipping_limit_date"],
    },
    {
        "table": "order_payments",
        "file": "olist_order_payments_dataset.csv",
        "text_columns": ["order_id", "payment_type"],
        "integer_columns": ["payment_sequential", "payment_installments"],
    },
    {
        "table": "order_reviews",
        "file": "olist_order_reviews_dataset.csv",
        "text_columns": ["review_id", "order_id", "review_comment_title", "review_comment_message"],
        "integer_columns": ["review_score"],
        "date_columns": ["review_creation_date", "review_answer_timestamp"],
    },
    {
        "table": "geolocation",
        "file": "olist_geolocation_dataset.csv",
        "text_columns": ["geolocation_zip_code_prefix", "geolocation_city", "geolocation_state"],
    },
]


def get_engine(database=None):
    """Build a SQLAlchemy engine from the MySQL credentials in .env (never hard-coded)."""
    load_dotenv(PROJECT_ROOT / ".env")
    url = URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        database=database,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url)


def run_schema_file():
    """Run sql/01_schema.sql statement by statement (it creates the database, so connect without one)."""
    sql_text = SCHEMA_FILE.read_text(encoding="utf-8")
    # Drop comment lines, then split on ';' (the schema file has no ';' inside strings or comments)
    code_lines = [line for line in sql_text.splitlines() if not line.strip().startswith("--")]
    statements = [statement.strip() for statement in "\n".join(code_lines).split(";") if statement.strip()]
    with get_engine().begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print(f"Schema created: {len(statements)} statements from {SCHEMA_FILE.name}")


def load_table(engine, table_config):
    """Read one CSV in chunks and append it to its MySQL table. Returns the number of rows read."""
    column_types = {column: "string" for column in table_config.get("text_columns", [])}
    column_types.update({column: "Int64" for column in table_config.get("integer_columns", [])})
    date_columns = table_config.get("date_columns", [])

    chunks = pd.read_csv(
        RAW_DATA_DIR / table_config["file"],
        dtype=column_types,
        encoding="utf-8-sig",     # strips the byte-order mark (BOM) at the start of the translation CSV
        keep_default_na=False,    # do not turn text like "NA" or "null" into missing values...
        na_values=[""],           # ...only truly empty cells become NULL
        chunksize=CHUNK_SIZE,
    )

    rows_read = 0
    for chunk in chunks:
        for column in date_columns:
            # errors="raise": a badly formatted date stops the load instead of silently becoming NULL
            chunk[column] = pd.to_datetime(chunk[column], format="%Y-%m-%d %H:%M:%S", errors="raise")
        chunk = chunk.rename(columns=table_config.get("rename", {}))
        chunk.to_sql(table_config["table"], engine, if_exists="append", index=False)
        rows_read += len(chunk)
    return rows_read


def main():
    run_schema_file()
    engine = get_engine(database="olist")

    reconciliation_rows = []
    for table_config in TABLES:
        rows_read = load_table(engine, table_config)
        with engine.connect() as connection:
            rows_in_mysql = connection.execute(text(f"SELECT COUNT(*) FROM {table_config['table']}")).scalar()
        reconciliation_rows.append({
            "table_name": table_config["table"],
            "source_file": table_config["file"],
            "rows_read_by_pandas": rows_read,
            "rows_in_mysql": rows_in_mysql,
            "difference": rows_read - rows_in_mysql,
            "match": rows_read == rows_in_mysql,
        })
        print(f"{table_config['table']:<22} read {rows_read:>9,}   in MySQL {rows_in_mysql:>9,}")

    row_counts = pd.DataFrame(reconciliation_rows)
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    row_counts.to_csv(OUTPUT_FILE, index=False)
    print(f"\nAll tables match: {row_counts['match'].all()}   Saved: {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
