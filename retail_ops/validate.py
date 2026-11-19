"""Independent pandas reconciliation against SQL; requires a completed full build."""
import hashlib
import json
import numpy as np
import pandas as pd
from retail_ops.metrics import ROOT, query


def validate():
    audit = json.loads((ROOT / "reports/data_quality.json").read_text())
    digest = hashlib.sha256((ROOT / "data/raw/online_retail_II.xlsx").read_bytes()).hexdigest()
    assert digest == audit["source_sha256"], "Source changed since build"
    assert digest == json.loads((ROOT / "data/raw/cache.json").read_text())["sha256"]
    raw = pd.read_parquet(ROOT / "data/raw/source.parquet")
    # Independently keep the last sheet containing an invoice, retaining its repeated lines.
    last_sheet = raw.groupby("invoice").source_sheet.transform("last")
    source = raw[raw.source_sheet == last_sheet].copy()
    source["day"] = pd.to_datetime(source.timestamp).dt.strftime("%Y-%m-%d")
    merchandise = source.sku.str.match(r"^\d{5}[A-Za-z]{0,2}$", na=False)
    valid = source.timestamp.notna() & source.country.notna() & (source.price > 0)
    window = source.day.between("2009-12-01", "2011-11-30")
    positive = source.quantity.gt(0) & ~source.invoice.str.upper().str.startswith("C", na=False)
    sales = source[merchandise & valid & window & positive].copy()
    sales["amount"] = (sales.price * 1000).round().astype("int64") * sales.quantity
    returns = source[merchandise & valid & window & source.quantity.lt(0)].copy()
    reversed_gbp = -((returns.price * 1000).round().astype("int64") * returns.quantity).sum()/1000
    orders = sales.groupby(["invoice", "day", "customer_id", "country"], dropna=False).amount.sum().reset_index()
    known = orders.dropna(subset=["customer_id"])
    counts = known.groupby("customer_id").size()
    expected = {
        "gross_sales_gbp": sales.amount.sum()/1000,
        "orders": orders.invoice.nunique(), "units": sales.quantity.sum(),
        "aov_gbp": sales.amount.sum()/1000/len(orders),
        "identified_customers": len(counts), "repeat_purchase_rate": counts.ge(2).mean(),
        "identified_revenue_share": known.amount.sum()/sales.amount.sum(),
        "reversed_gbp": reversed_gbp,
        "net_recorded_value_gbp": sales.amount.sum()/1000-reversed_gbp,
    }
    k = query("kpis").iloc[0]
    for name, value in expected.items():
        assert np.isclose(k[name], value, atol=1e-7, rtol=1e-10), (name, k[name], value)
    for name in ["monthly", "products", "countries"]:
        assert np.isclose(query(name).gross_sales_gbp.sum(), expected["gross_sales_gbp"])
    products = query("products").set_index("sku")
    direct_sku = sales.groupby("sku").amount.sum()/1000
    assert np.allclose(products.loc[direct_sku.index].gross_sales_gbp, direct_sku, atol=1e-7, rtol=1e-10)
    assert np.isclose(products.net_recorded_value_gbp.sum(), expected["net_recorded_value_gbp"])
    assert np.isclose(query("segments").gross_sales_gbp.sum(), known.amount.sum()/1000)
    # Count first and second observed invoice dates independently of the SQL CTE.
    first_two = known.sort_values(["customer_id", "day", "invoice"]).groupby("customer_id").day.agg(list)
    outcomes = []
    for days in first_two:
        first = pd.Timestamp(days[0])
        if (pd.Timestamp("2011-11-30")-first).days >= 90:
            outcomes.append((days[0][:7], len(days) > 1 and (pd.Timestamp(days[1])-first).days <= 90))
    c = pd.DataFrame(outcomes, columns=["cohort", "repeat"])
    direct_cohort = c.groupby("cohort").repeat.agg(["size", "sum"]).sort_index()
    sql_cohort = query("cohorts").set_index("cohort").sort_index()
    assert direct_cohort.index.equals(sql_cohort.index)
    assert (direct_cohort["size"].to_numpy() == sql_cohort.eligible_customers.to_numpy()).all()
    assert (direct_cohort["sum"].to_numpy() == sql_cohort.repeat_customers_90d.to_numpy()).all()
    assert sum(audit["dispositions"].values()) == audit["rows_after_overlap_resolution"]
    assert audit["raw_rows"]-audit["cross_sheet_repeated_rows_removed"] == len(source)
    result = {"status":"passed", "source_sha256":digest, "report_start":"2009-12-01",
              "report_end":"2011-11-30", "headline_metrics_checked":list(expected),
              "sku_sales_totals_checked":len(direct_sku), "cohort_months_checked":len(direct_cohort),
              "reconciliations":["month to sales", "market to sales", "SKU to sales", "SKU net to headline net", "segments to identified sales", "source row dispositions"],
              "method":"Independent pandas aggregation of normalized source, compared with SQLite query results"}
    (ROOT / "reports/validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    validate()
