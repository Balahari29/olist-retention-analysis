
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE")
required = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE"
]

for key in required:
    if not os.getenv(key):
        raise ValueError(f"Missing environment variable: {key}")

print("Host:", host)
print("Port:", port)
print("Database:", database)


engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
)



try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE(), VERSION()"))
        print("Connection successful!")
        print(result.fetchone())
except Exception as e:
    print("Connection failed:", e)
