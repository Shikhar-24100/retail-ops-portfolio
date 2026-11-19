"""Execute the same reviewable SQL in the dashboard and report pipeline."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/retail.sqlite"


def connect(path=None):
    return sqlite3.connect(f"{Path(path or DB).resolve().as_uri()}?mode=ro", uri=True)


def query(name, start="2009-12-01", end="2011-11-30", country="All markets", path=None):
    sql = (ROOT / "sql" / f"{name}.sql").read_text(encoding="utf-8")
    with connect(path) as con:
        return pd.read_sql_query(sql, con, params={"start": str(start), "end": str(end), "country": country})


def dimensions(path=None):
    with connect(path) as con:
        return pd.read_sql_query("SELECT DISTINCT country FROM sales ORDER BY country", con).country.tolist()
