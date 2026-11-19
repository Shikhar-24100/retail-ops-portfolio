"""Independent checks of saved forecasts, SQL source units and inventory ledgers."""
import hashlib
import json
import numpy as np
import pandas as pd
from retail_ops.metrics import ROOT, connect

OUT = ROOT/"reports/forecasting"


def close(a,b,label):
    assert np.allclose(a,b,rtol=1e-9,atol=1e-6,equal_nan=True), label


def validate():
    meta = json.loads((OUT/"metadata.json").read_text())
    choice = json.loads((OUT/"model_selection.json").read_text())
    daily = ROOT/"data/processed/daily_sku_sales.parquet"
    assert hashlib.sha256(daily.read_bytes()).hexdigest() == meta["daily_input_sha256"]
    assert meta["source_sha256"] == json.loads((ROOT/"reports/data_quality.json").read_text())["source_sha256"]
    selection = pd.read_csv(OUT/"selected_skus.csv",dtype={"sku":str})
    weekly = pd.read_csv(OUT/"weekly_units.csv",dtype={"sku":str},parse_dates=["week"])
    truth = weekly.pivot(index="week",columns="sku",values="units").sort_index()
    placeholders = ",".join("?" for _ in selection.sku)
    with connect() as con:
        source = pd.read_sql_query(f"""SELECT date(date,'-' || ((CAST(strftime('%w',date) AS INTEGER)+6)%7) || ' days') AS week,
            sku, SUM(quantity) AS units FROM sales WHERE country='United Kingdom'
            AND date BETWEEN '2009-12-07' AND '2011-12-04' AND sku IN ({placeholders})
            GROUP BY week,sku""", con, params=selection.sku.tolist(),parse_dates=["week"])
    source = source.pivot(index="week",columns="sku",values="units").reindex(index=truth.index,columns=truth.columns).fillna(0)
    close(source,truth,"Weekly panel must match source SQL exactly")
    f = pd.read_parquet(OUT/"forecasts.parquet")
    assert not f.duplicated(["origin_week","method","horizon","sku"]).any()
    assert (f.train_through_week < f.origin_week).all()
    assert (f.target_week >= f.origin_week).all()
    assert (f.forecast >= 0).all() and np.isfinite(f.forecast).all()
    assert f[(f.origin_phase=="validation") & (f.target_index>=76)].actual.isna().all()
    observed = f[f.actual.notna()].merge(weekly,left_on=["target_week","sku"],right_on=["week","sku"],validate="many_to_one")
    close(observed.actual,observed.units,"Forecast actuals must equal independent weekly source units")
    scores = pd.read_csv(OUT/"accuracy.csv")
    scored = f[f.actual.notna() & f.origin_phase.eq(f.target_phase)]
    for row in scores.itertuples():
        g = scored[(scored.origin_phase==row.origin_phase)&(scored.method==row.method)&(scored.horizon==row.horizon)]
        error = g.forecast.to_numpy()-g.actual.to_numpy()
        assert len(g)==row.points
        close(np.mean(np.abs(error)),row.mae_units,"MAE")
        close(np.abs(error).sum()/g.actual.sum(),row.wape,"Pooled WAPE")
        close(error.sum()/g.actual.sum(),row.bias,"Signed demand bias")
    for role,names in [("baseline",choice["baseline_search"]),("candidate",choice["candidate_search"])]:
        v = scores.query("origin_phase == 'validation' and horizon == 1")
        assert v[v.method.isin(names)].sort_values(["wape","method"]).iloc[0].method == choice[role]
    # Independent closed-form baseline checks at every saved origin/horizon.
    for method in choice["baseline_search"]:
        for origin,g in f[f.method==method].groupby("origin_index"):
            for h,rows in g.groupby("horizon"):
                expected = truth.iloc[origin-4:origin].mean() if method=="moving_average_4" else truth.iloc[origin+h-1-52]
                ordered = rows.set_index("sku").reindex(truth.columns)
                close(ordered.forecast,expected,"Simple baseline arithmetic")
    ledger = pd.read_parquet(OUT/"inventory_ledger.parquet")
    close(ledger.opening_units+ledger.received_units-ledger.fulfilled_units,ledger.closing_units,"Physical stock conservation")
    close(ledger.fulfilled_units+ledger.lost_units,ledger.demand_units,"Demand served plus unserved")
    close(ledger.opening_units+ledger.received_units,ledger.available_units,"Receipts before demand")
    assert (ledger.select_dtypes("number") >= 0).all().all()
    ledger_truth = ledger.merge(weekly,on=["week","sku"],validate="many_to_one")
    close(ledger_truth.demand_units,ledger_truth.units,"Replay demand must equal source units")
    calibration = pd.read_csv(OUT/"safety_calibration.csv")
    scales = selection.set_index("sku").training_mean_units
    summaries = pd.read_csv(OUT/"inventory_summary.csv")
    scenario_checks = 0
    for (role,lead,q),g in ledger.groupby(["policy","lead_time_weeks","buffer_quantile"]):
        ordered = g.sort_values(["sku","week"]).copy()
        group = ordered.groupby("sku",sort=False)
        close(ordered.received_units,group.ordered_units.shift(int(lead)).fillna(0),"Lead-time arrival schedule")
        later = ordered.week > ordered.week.min()
        close(ordered.loc[later,"opening_units"],group.closing_units.shift(1)[later],"Week-to-week carry")
        close(ordered.ending_pipeline_units,group.ordered_units.cumsum()-group.received_units.cumsum(),"Outstanding order balance")
        close(ordered.ordered_units,np.maximum(0,ordered.order_up_to_units-ordered.available_units-ordered.pipeline_before_order),"Order-up-to equation")
        method = choice[role]
        v = f[(f.method==method)&(f.origin_phase=="validation")&(f.horizon<=lead+1)]
        protect = v.groupby(["origin_index","sku"]).agg(n=("actual","count"),actual=("actual","sum"),forecast=("forecast","sum"))
        protect = protect[protect.n==lead+1].reset_index()
        residual = (protect.actual-protect.forecast)/protect.sku.map(scales)
        buffer = max(0,np.quantile(residual,q,method="higher"))
        saved = calibration[(calibration.policy==role)&(calibration.protection_weeks==lead+1)&(calibration.buffer_quantile==q)].iloc[0]
        close(buffer,saved.normalised_buffer,"Validation-only buffer calibration")
        assert saved.validation_sku_windows==len(protect)
        future = f[(f.method==method)&(f.origin_index>=76)&(f.horizon<=lead+1)].groupby(["origin_week","sku"]).forecast.sum()
        targets = ordered.merge(future.rename("protection_forecast"),left_on=["week","sku"],right_index=True,validate="one_to_one")
        close(targets.order_up_to_units,np.ceil(targets.protection_forecast+targets.sku.map(scales)*buffer),"Forecast-to-stock target")
        initial = ordered[ordered.week==ordered.week.min()].set_index("sku").reindex(truth.columns)
        close(initial.opening_units,np.ceil(truth.iloc[68:76].mean()*(lead+1)),"Common initial stock")
        hold = g[g.phase=="holdout"]
        assert hold.week.nunique()==20 and len(hold)==1000
        record = summaries[(summaries.policy==role)&(summaries.lead_time_weeks==lead)&(summaries.buffer_quantile==q)].iloc[0]
        close(record.fill_rate,hold.fulfilled_units.sum()/hold.demand_units.sum(),"Simulated unit fill rate")
        close(record.lost_units,hold.lost_units.sum(),"Unserved units")
        close(record.stock_unit_weeks,hold.average_on_hand_units.sum(),"Holding stock integral")
        close(record.total_assumed_cost_gbp,.05*hold.average_on_hand_units.sum()+hold.lost_units.sum(),"Assumed cost accounting")
        assert record.stockout_sku_weeks==hold.lost_units.gt(0).sum()
        scenario_checks += 1
    result = {"status":"passed","forecast_rows_checked":len(f),"forecast_score_rows_checked":len(scores),
        "weekly_source_cells_checked":int(truth.size),"inventory_ledger_rows_checked":len(ledger),
        "inventory_policy_scenarios_checked":scenario_checks,
        "checks":["SQL source to weekly panel","Forecast truth alignment and unique keys",
            "Chronological forecast origins","Independent baseline arithmetic and error metrics",
            "Validation-only model selection and buffer calibration","Common warm-up initial stock",
            "Demand and stock conservation","Lead-time receipts and purchase-order balances",
            "Forecast-to-inventory order-up-to equations","Holdout service and assumed-cost accounting"]}
    (OUT/"validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    validate()
