"""Periodic weekly review, deterministic lead time, lost-sales inventory replay."""
import numpy as np
import pandas as pd


def safety_calibration(validation, scales, method, protection, quantile):
    d = validation[(validation.method == method) & (validation.horizon <= protection)
                   & (validation.origin_phase == "validation")].copy()
    g = d.groupby(["origin_index", "sku"]).agg(n=("actual", "count"),
          actual=("actual", "sum"), forecast=("forecast", "sum"))
    g = g[g.n == protection].reset_index()
    if g.empty or not 0 < quantile < 1:
        raise ValueError("Calibration requires complete validation protection windows and a valid quantile")
    normalised = (g.actual-g.forecast)/g.sku.map(scales)
    if not np.isfinite(normalised).all():
        raise ValueError("Calibration scales must be positive and finite")
    buffer = max(0., float(np.quantile(normalised, quantile, method="higher")))
    return buffer, len(g)


def simulate(demand, forecasts, safety, initial, lead_time, warmup=8, weeks=None, skus=None):
    """Receive -> review/order -> fulfil -> close. Orders arrive t+lead_time."""
    demand, forecasts = np.asarray(demand), np.asarray(forecasts)
    n, m = demand.shape
    if not isinstance(lead_time, int) or lead_time < 1 or forecasts.shape != (n, 5, m) or lead_time+1 > 5:
        raise ValueError("Need 1–4 week lead time and a five-horizon forecast for every SKU-week")
    if not 0 <= warmup < n:
        raise ValueError("Warm-up must leave at least one evaluation week")
    if any(not np.isfinite(x).all() or (np.asarray(x) < 0).any() for x in [demand, forecasts, safety, initial]):
        raise ValueError("Demand, forecasts, buffers and inventory must be finite and nonnegative")
    if not np.equal(demand, np.floor(demand)).all():
        raise ValueError("Replay requires integer unit demand")
    on_hand = np.ceil(np.asarray(initial)).astype(np.int64)
    scheduled = np.zeros((n+lead_time+1, m), dtype=np.int64)
    records = []
    skus = skus if skus is not None else [str(i) for i in range(m)]
    weeks = weeks if weeks is not None else pd.date_range("2000-01-03", periods=n, freq="W-MON")
    for t in range(n):
        opening = on_hand.copy()
        received = scheduled[t].copy()
        available = opening+received
        pipeline = scheduled[t+1:].sum(axis=0)
        target = np.ceil(forecasts[t, :lead_time+1].sum(axis=0)+safety).astype(np.int64)
        order = np.maximum(0, target-available-pipeline)
        scheduled[t+lead_time] += order
        fulfilled = np.minimum(available, demand[t]).astype(np.int64)
        lost = demand[t]-fulfilled
        on_hand = available-fulfilled
        # Holding stock integral under uniform demand within the week. If stock
        # runs out early, inventory is zero for the rest of that week.
        average_stock = np.where(available >= demand[t], available-demand[t]/2,
            np.divide(available.astype(float)**2, 2*demand[t],
                      out=np.zeros(m, dtype=float), where=demand[t]>0))
        records.append(pd.DataFrame({"week":weeks[t], "sku":skus,
            "phase":"warmup" if t < warmup else "holdout", "opening_units":opening,
            "received_units":received, "available_units":available, "pipeline_before_order":pipeline,
            "order_up_to_units":target, "ordered_units":order, "demand_units":demand[t],
            "fulfilled_units":fulfilled, "lost_units":lost, "closing_units":on_hand,
            "average_on_hand_units":average_stock,
            "ending_pipeline_units":scheduled[t+1:].sum(axis=0)}))
    return pd.concat(records, ignore_index=True)


def summarize(ledger, holding_cost=.05, lost_penalty=1.):
    d = ledger[ledger.phase == "holdout"]
    demand = d.demand_units.sum()
    stock_weeks = d.average_on_hand_units.sum()
    lost = d.lost_units.sum()
    last = d[d.week == d.week.max()]
    return {"demand_units":float(demand), "fulfilled_units":float(d.fulfilled_units.sum()),
        "lost_units":float(lost), "fill_rate":float(d.fulfilled_units.sum()/demand) if demand else np.nan,
        "stockout_sku_weeks":int(d.lost_units.gt(0).sum()), "sku_weeks":len(d),
        "stock_unit_weeks":float(stock_weeks),
        "mean_on_hand_units":float(stock_weeks/d.week.nunique()),
        "ordered_units":float(d.ordered_units.sum()),
        "ending_on_hand_units":int(last.closing_units.sum()),
        "ending_pipeline_units":int(last.ending_pipeline_units.sum()),
        "assumed_holding_cost_gbp":float(stock_weeks*holding_cost),
        "assumed_lost_sale_penalty_gbp":float(lost*lost_penalty),
        "total_assumed_cost_gbp":float(stock_weeks*holding_cost+lost*lost_penalty)}
