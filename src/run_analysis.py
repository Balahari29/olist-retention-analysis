"""
Run the Phase 3 SQL files in order and save every marked result to outputs/<name>.csv.

Each file is split into statements on ';' at the end of a line.
  - A statement whose comment lines include  "-- @output: some_name"  is a SELECT: its result is saved
    to outputs/some_name.csv.
  - Every other statement (USE, CREATE OR REPLACE VIEW) is just executed.
SQL files must not contain ';' inside comments or strings.

Run from the project root:
  .venv/bin/python src/run_analysis.py                      # all files, in order
  .venv/bin/python src/run_analysis.py 04_analysis_delivery  # one or more files by name
"""
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from load_to_mysql import get_engine   # same .env-based connection as the loader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SQL_FILES = [               # order matters: later files use views created by earlier ones
    "03_clean_layer",
    "03_analysis_retention",
    "04_analysis_delivery",
    "05_analysis_sellers_categories",
    "06_views_for_powerbi",
]
OUTPUT_MARKER = re.compile(r"^\s*--\s*@output:\s*(\w+)\s*$")
STATEMENT_END = re.compile(r";\s*$", re.MULTILINE)


def split_statements(sql_text):
    """Return (output_name or None, statement) for each statement in a SQL file."""
    statements = []
    for raw_statement in STATEMENT_END.split(sql_text):
        output_name = None
        code_lines = []
        for line in raw_statement.splitlines():
            marker = OUTPUT_MARKER.match(line)
            if marker:
                output_name = marker.group(1)
            elif not line.strip().startswith("--"):
                code_lines.append(line)
        statement = "\n".join(code_lines).strip()
        if statement:
            statements.append((output_name, statement))
    return statements


def run_file(connection, file_name):
    print(f"\n######## {file_name}.sql")
    for output_name, statement in split_statements((SQL_DIR / f"{file_name}.sql").read_text(encoding="utf-8")):
        if output_name is None:
            connection.execute(text(statement))
            continue
        # convert_dtypes: MySQL SUM() returns DECIMAL, so whole counts arrive as 96464.0; store them as integers
        result = pd.read_sql(text(statement), connection).convert_dtypes()
        result.to_csv(OUTPUT_DIR / f"{output_name}.csv", index=False)
        print(f"\n=== {output_name}  ->  outputs/{output_name}.csv  ({len(result)} rows)")
        print(result.head(25).to_string(index=False))


def main():
    files_to_run = sys.argv[1:] or SQL_FILES
    OUTPUT_DIR.mkdir(exist_ok=True)
    with get_engine(database="olist").connect() as connection:
        for file_name in files_to_run:
            run_file(connection, file_name)
        connection.commit()


if __name__ == "__main__":
    main()
