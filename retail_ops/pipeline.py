"""Download the attributed source, retain an audit trail, and build SQLite marts."""
import argparse
import hashlib
import io
import json
import re
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from retail_ops.metrics import ROOT, DB, query

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
SOURCE = ROOT / "data/raw/online_retail_II.xlsx"
FIELDS = ["invoice", "sku", "description", "quantity", "timestamp", "price", "customer_id", "country"]


def download():
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if SOURCE.exists():
        return
    print("Downloading the UCI archive...", flush=True)
    with urllib.request.urlopen(URL, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    member = next(n for n in archive.namelist() if n.lower().endswith(".xlsx"))
    SOURCE.write_bytes(archive.read(member))


def load_source():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    cache = ROOT / "data/raw/source.parquet"
    meta = ROOT / "data/raw/cache.json"
    if cache.exists() and meta.exists() and json.loads(meta.read_text())["sha256"] == digest:
        return pd.read_parquet(cache), digest
    book = pd.ExcelFile(SOURCE)
    frames = []
    for sheet in book.sheet_names:
        print(f"Reading {sheet}...", flush=True)
        d = pd.read_excel(book, sheet_name=sheet, dtype={"Invoice": str, "StockCode": str})
        d.columns = FIELDS
        d["source_sheet"] = sheet
        d["source_row"] = np.arange(2, len(d) + 2)
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    # Normalize mixed source identifiers before portable caching.
    for col in ["invoice", "sku", "description", "country"]:
        d[col] = d[col].astype("string").str.strip()
    d.to_parquet(cache, index=False)
    meta.write_text(json.dumps({"sha256": digest}), encoding="utf-8")
    return d, digest


def remove_sheet_overlap(d):
    """Remove only proven repeat invoice copies across sheets; retain within-sheet lines."""
    copies = d.groupby("invoice", dropna=False).source_sheet.nunique()
    overlap = copies[copies > 1].index
    drop_indices = []
    for invoice, g in d[d.invoice.isin(overlap)].groupby("invoice", sort=False):
        sheets = list(g.source_sheet.unique())
        reference = pd.util.hash_pandas_object(g[g.source_sheet == sheets[-1]][FIELDS], index=False)
        for sheet in sheets[:-1]:
            candidate = pd.util.hash_pandas_object(g[g.source_sheet == sheet][FIELDS], index=False)
            if sorted(reference.tolist()) != sorted(candidate.tolist()):
                raise ValueError(f"Conflicting cross-sheet copies for invoice {invoice}; investigate source")
            drop_indices.extend(g[g.source_sheet == sheet].index.tolist())
    return d.drop(index=drop_indices).copy(), len(drop_indices)


def classify(d):
    """Mutually exclusive row disposition. Money is stored in 1/1000 GBP units."""
    d = d.copy()
    for col in ["invoice", "sku", "description", "country"]:
        d[col] = d[col].astype("string").str.strip()
    d["timestamp"] = pd.to_datetime(d.timestamp, errors="coerce")
    d["quantity"] = pd.to_numeric(d.quantity, errors="coerce")
    d["price"] = pd.to_numeric(d.price, errors="coerce")
    d["customer_id"] = pd.to_numeric(d.customer_id, errors="coerce").astype("Int64").astype("string")
    d["duplicate_candidate"] = d.duplicated(FIELDS, keep="first").astype(int)
    valid = (d.timestamp.notna() & d.invoice.notna() & d.country.notna()
             & np.isfinite(d.quantity) & np.isfinite(d.price) & (d.quantity % 1 == 0))
    merchandise = d.sku.str.fullmatch(r"\d{5}[A-Za-z]{0,2}", na=False)
    cancelled = d.invoice.str.upper().str.startswith("C", na=False)
    d["disposition"] = np.select(
        [~valid, ~merchandise, d.price <= 0, (d.quantity > 0) & ~cancelled, d.quantity < 0],
        ["invalid", "non_merchandise", "nonpositive_price", "sale", "return_or_cancellation"],
        default="other_adjustment",
    )
    scaled = d.price.fillna(0) * 1000
    if not np.allclose(scaled[valid], np.rint(scaled[valid]), atol=1e-6, rtol=0):
        raise ValueError("Source has prices more precise than 0.001 GBP")
    d["unit_price_mills"] = np.rint(scaled).astype("int64")
    d["value_mills"] = (d.quantity.fillna(0) * d.unit_price_mills).astype("int64")
    d["date"] = d.timestamp.dt.strftime("%Y-%m-%d")
    return d


def write_database(d, path=DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["invoice", "sku", "description", "quantity", "date", "customer_id", "country",
            "unit_price_mills", "value_mills", "duplicate_candidate", "source_sheet", "source_row"]
    sales = d[d.disposition == "sale"][cols].copy()
    returns = d[d.disposition == "return_or_cancellation"][cols].copy()
    sales.quantity = sales.quantity.astype(int)
    returns.quantity = returns.quantity.astype(int)
    for col in ["date", "customer_id", "country"]:
        if sales.groupby("invoice")[col].nunique(dropna=False).gt(1).any():
            raise ValueError(f"Invoice has inconsistent {col}")
    with sqlite3.connect(path) as con:
        sales.to_sql("sales", con, if_exists="replace", index=False, chunksize=10000)
        returns.to_sql("returns", con, if_exists="replace", index=False, chunksize=10000)
        con.executescript("""
          DROP TABLE IF EXISTS orders;
          CREATE TABLE orders AS
          SELECT invoice, date, customer_id, country, SUM(value_mills) AS value_mills,
                 SUM(quantity) AS units, COUNT(*) AS lines
          FROM sales GROUP BY invoice, date, customer_id, country;
          CREATE UNIQUE INDEX orders_invoice ON orders(invoice);
          CREATE INDEX orders_date_market ON orders(date, country);
          CREATE INDEX orders_customer_date ON orders(customer_id, date);
          CREATE INDEX sales_date_market ON sales(date, country);
          CREATE INDEX sales_sku_date ON sales(sku, date);
          CREATE INDEX returns_date_market ON returns(date, country);
        """)
        d.groupby("disposition", dropna=False).agg(rows=("invoice", "size"), value_mills=("value_mills", "sum")).reset_index().to_sql("audit", con, if_exists="replace", index=False)
    return sales, returns


def build():
    download()
    raw, digest = load_source()
    d, overlap = remove_sheet_overlap(raw)
    d = classify(d)
    sales, returns = write_database(d)
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    audit = {
        "source_url": URL, "source_sha256": digest, "raw_rows": len(raw),
        "cross_sheet_repeated_rows_removed": overlap,
        "rows_after_overlap_resolution": len(d),
        "duplicate_candidate_rows_retained": int(d.duplicate_candidate.sum()),
        "dispositions": d.disposition.value_counts().to_dict(),
        "sales_gbp": float(sales.value_mills.sum() / 1000),
        "signed_returns_cancellations_gbp": float(returns.value_mills.sum() / 1000),
        "sales_gbp_without_duplicate_candidates": float(sales.loc[sales.duplicate_candidate == 0, "value_mills"].sum() / 1000),
        "sales_rows_missing_customer": int(sales.customer_id.isna().sum()),
        "sales_gbp_missing_customer": float(sales.loc[sales.customer_id.isna(), "value_mills"].sum() / 1000),
        "observed_start": str(sales.date.min()), "observed_end": str(sales.date.max()),
        "default_reporting_end": "2011-11-30",
        "scope": "All source dates; report CSVs use complete months through 2011-11-30",
    }
    (report_dir / "data_quality.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    for name in ["kpis", "monthly", "products", "segments", "cohorts", "countries", "price_variation"]:
        result = query(name)
        result.to_csv(report_dir / f"{name}.csv", index=False)
    # Shared input for project 2. Missing dates are absent, not presumed zero demand.
    with sqlite3.connect(DB) as con:
        pd.read_sql_query("""SELECT date, sku, country, SUM(quantity) AS units,
            SUM(value_mills)/1000.0 AS gross_sales_gbp
            FROM sales GROUP BY date, sku, country""", con).to_parquet(ROOT / "data/processed/daily_sku_sales.parquet", index=False)
    print(json.dumps(audit, indent=2), flush=True)
    print("Warehouse and historical reports built.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build()
