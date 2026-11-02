"""
Run every data-quality check in sql/02_data_quality_checks.sql and save each result to outputs/<name>.csv.

A check is one SELECT statement preceded by a marker line:   -- @check: dq_some_name
Run from the project root:  .venv/bin/python src/run_dq_checks.py
"""
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_to_mysql import get_engine   # same .env-based connection as the loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKS_FILE = PROJECT_ROOT / "sql" / "02_data_quality_checks.sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MARKER = re.compile(r"^--\s*@check:\s*(\w+)\s*$", re.MULTILINE)


def read_checks(sql_text):
    """Split the SQL file into (check_name, select_statement) pairs using the @check markers."""
    parts = MARKER.split(sql_text)          # [text before first marker, name1, sql1, name2, sql2, ...]
    checks = []
    for check_name, block in zip(parts[1::2], parts[2::2]):
        # Keep only code lines: drop comment lines that belong to the next check's header
        code_lines = [line for line in block.splitlines() if not line.strip().startswith("--")]
        statement = "\n".join(code_lines).strip().rstrip(";")
        checks.append((check_name, statement))
    return checks


def main():
    engine = get_engine(database="olist")
    checks = read_checks(CHECKS_FILE.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(exist_ok=True)

    with engine.connect() as connection:
        for check_name, statement in checks:
            # convert_dtypes: MySQL SUM() returns DECIMAL, so whole counts arrive as 96464.0; store them as integers
            result = pd.read_sql(text(statement), connection).convert_dtypes()
            output_path = OUTPUT_DIR / f"{check_name}.csv"
            result.to_csv(output_path, index=False)
            print(f"\n=== {check_name}  ->  outputs/{output_path.name}")
            print(result.to_string(index=False))
    print(f"\n{len(checks)} checks saved to outputs/")


if __name__ == "__main__":
    main()
