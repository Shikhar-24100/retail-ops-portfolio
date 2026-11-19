"""Run frozen model selection, historical evaluation and inventory simulation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

from retail_ops.metrics import ROOT
from retail_ops.forecasting import (TRAIN_END, VALID_END, TEST_START, HORIZON, BASELINES,
    CANDIDATES, LABELS, make_panel, backtest, accuracy, choose_models)
from retail_ops.inventory import safety_calibration, simulate, summarize

OUT = ROOT / "reports/forecasting"


def build():
    source = ROOT / "data/processed/daily_sku_sales.parquet"
    if not source.exists():
        raise SystemExit("Build the shared warehouse first: python -m retail_ops.pipeline")
    OUT.mkdir(exist_ok=True, parents=True)
    panel = make_panel(pd.read_parquet(source))
    print("Validation: eight methods, 16 weekly origins, 50 training-selected SKUs...", flush=True)
    validation = backtest(panel, range(TRAIN_END, VALID_END), BASELINES+CANDIDATES, actual_end=VALID_END)
    selected = choose_models(validation)
    selection = {**selected, "criterion":"Lowest pooled one-week WAPE on 16 validation origins; ties by method name",
        "candidate_search":list(CANDIDATES), "baseline_search":list(BASELINES),
        "selected_before_holdout":True, "train_through_week":str(panel.weeks[TRAIN_END-1].date()),
        "validation_through_week":str(panel.weeks[VALID_END-1].date())}
    # Freeze the choices to disk before generating the holdout forecasts.
    (OUT / "model_selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print("Frozen choices:", selected, flush=True)
    methods = tuple(dict.fromkeys([*BASELINES, selected["candidate"]]))
    evaluation = backtest(panel, range(VALID_END, len(panel.weeks)), methods, actual_end=len(panel.weeks))
    predictions = pd.concat([validation, evaluation], ignore_index=True)
    predictions.to_parquet(OUT / "forecasts.parquet", index=False)
    accuracy(predictions).to_csv(OUT / "accuracy.csv", index=False)
    accuracy(predictions[predictions.horizon == 1], per_sku=True).to_csv(OUT / "sku_accuracy.csv", index=False)
    panel.selection.to_csv(OUT / "selected_skus.csv", index=False)
    observed = pd.DataFrame(panel.y, index=panel.weeks, columns=panel.skus).rename_axis("week").reset_index()
    observed.melt("week", var_name="sku", value_name="units").to_csv(OUT / "weekly_units.csv", index=False)
    scales = dict(zip(panel.skus, panel.y[:TRAIN_END].mean(axis=0)))
    summaries, ledgers, calibrations = [], [], []
    for lead in [1, 2, 4]:
        # Same warm-up starting stock and empty pipeline for both policies.
        initial = np.ceil(panel.y[VALID_END-8:VALID_END].mean(axis=0)*(lead+1))
        for quantile in [.90, .95, .99]:
            for role, method in selected.items():
                buffer, points = safety_calibration(validation, scales, method, lead+1, quantile)
                safety = np.array([scales[s]*buffer for s in panel.skus])
                f = evaluation[evaluation.method == method]
                cube = np.stack([f[f.horizon == h].pivot(index="origin_index", columns="sku", values="forecast")
                    .reindex(index=range(VALID_END, len(panel.weeks)), columns=panel.skus).to_numpy()
                    for h in range(1, HORIZON+1)], axis=1)
                ledger = simulate(panel.y[VALID_END:], cube, safety, initial, lead,
                    warmup=TEST_START-VALID_END, weeks=panel.weeks[VALID_END:], skus=panel.skus)
                ledger["policy"] = role
                ledger["method"] = method
                ledger["lead_time_weeks"] = lead
                ledger["buffer_quantile"] = quantile
                ledgers.append(ledger)
                summaries.append({"policy":role, "method":method, "lead_time_weeks":lead,
                    "buffer_quantile":quantile, **summarize(ledger)})
                calibrations.append({"policy":role, "method":method, "protection_weeks":lead+1,
                    "buffer_quantile":quantile, "normalised_buffer":buffer,
                    "validation_sku_windows":points, "total_safety_units":float(safety.sum())})
    pd.DataFrame(summaries).to_csv(OUT / "inventory_summary.csv", index=False)
    pd.concat(ledgers, ignore_index=True).to_parquet(OUT / "inventory_ledger.parquet", index=False)
    pd.DataFrame(calibrations).to_csv(OUT / "safety_calibration.csv", index=False)
    audit = json.loads((ROOT / "reports/data_quality.json").read_text())
    metadata = {"source_sha256":audit["source_sha256"],
        "daily_input_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "population":panel.population, "first_week":str(panel.weeks[0].date()),
        "last_week":str(panel.weeks[-1].date()),
        "splits":{"training":[str(panel.weeks[0].date()),str(panel.weeks[59].date())],
                  "validation":[str(panel.weeks[60].date()),str(panel.weeks[75].date())],
                  "warmup":[str(panel.weeks[76].date()),str(panel.weeks[83].date())],
                  "holdout":[str(panel.weeks[84].date()),str(panel.weeks[-1].date())]},
        "labels":LABELS, "default_scenario":{"lead_time_weeks":2,"buffer_quantile":.95,
            "holding_cost_per_unit_week_gbp":.05,"lost_unit_penalty_gbp":1.},
        "review_period_weeks":1, "warmup_weeks":8, "holdout_weeks":20,
        "forecast_horizons":5, "weekly_refit":True,
        "limitations":["Paid recorded sales proxy for demand; historical availability and lost sales unobserved",
            "Missing SKU-weeks zero-filled as no recorded paid sales; not proof of zero demand",
            "Giftware and wholesale retailer; not fashion demand or Myntra data",
            "Validation residual windows overlap and pool normalised errors across SKUs",
            "Buffer quantile is a calibration setting, not a guaranteed fill rate",
            "Inventory has assumed fixed lead times, unlimited supply and no minimum order quantities",
            "Costs are hypothetical uniform rates; procurement, ordering, expiry and return flows excluded",
            "Holdout simulates sequential decisions with weekly observed updates; no hyperparameter retuning"]}
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("Forecast metrics and 18 inventory policy/scenario runs saved.", flush=True)
    print(accuracy(predictions).query("origin_phase == 'holdout' and horizon == 1").to_string(index=False))
    print(pd.DataFrame(summaries).query("lead_time_weeks == 2 and buffer_quantile == .95").to_string(index=False))


if __name__ == "__main__":
    build()
