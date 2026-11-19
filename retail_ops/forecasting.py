"""Leakage-aware weekly forecasting with frozen validation-selected models."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

TRAIN_END, VALID_END, TEST_START = 60, 76, 84
HORIZON = 5
BASELINES = ("moving_average_4", "seasonal_naive_52")
CANDIDATES = ("seasonal_blend_25", "seasonal_blend_50", "seasonal_blend_75",
              "ridge_alpha_1", "ridge_alpha_10", "ridge_alpha_100")
LABELS = {
    "moving_average_4":"4-week moving average", "seasonal_naive_52":"52-week seasonal naive",
    "seasonal_blend_25":"Seasonal blend (25% seasonal)",
    "seasonal_blend_50":"Seasonal blend (50% seasonal)",
    "seasonal_blend_75":"Seasonal blend (75% seasonal)",
    "ridge_alpha_1":"Pooled log-ridge (alpha 1)",
    "ridge_alpha_10":"Pooled log-ridge (alpha 10)",
    "ridge_alpha_100":"Pooled log-ridge (alpha 100)",
}


@dataclass
class Panel:
    weeks: pd.DatetimeIndex
    skus: list
    y: np.ndarray
    selection: pd.DataFrame
    population: dict


def phase(index):
    if index < TRAIN_END:
        return "training"
    if index < VALID_END:
        return "validation"
    if index < TEST_START:
        return "warmup"
    return "holdout"


def make_panel(daily, top_n=50):
    """Zero means no recorded paid sale, not proof of zero unconstrained demand."""
    d = daily[daily.country == "United Kingdom"].copy()
    d["date"] = pd.to_datetime(d.date)
    first = d.date.min() + pd.Timedelta(days=(-d.date.min().dayofweek) % 7)
    last_sunday = d.date.max() - pd.Timedelta(days=(d.date.max().dayofweek-6) % 7)
    weeks = pd.date_range(first, last_sunday-pd.Timedelta(days=6), freq="W-MON")
    if len(weeks) != 104:
        raise ValueError("This study's frozen splits require the original 104 complete weeks")
    d["week"] = d.date - pd.to_timedelta(d.date.dt.dayofweek, unit="d")
    wide = d.groupby(["week", "sku"]).units.sum().unstack(fill_value=0).reindex(weeks, fill_value=0)
    train = wide.iloc[:TRAIN_END]
    active = train.gt(0).sum()
    recent = train.iloc[-8:].gt(0).sum()
    eligible = (active >= 40) & (recent >= 6)
    ranked = train.loc[:, eligible].sum().rename("training_units").reset_index()
    ranked = ranked.sort_values(["training_units", "sku"], ascending=[False, True]).head(top_n)
    if ranked.empty:
        raise ValueError("No SKUs satisfy the training-only eligibility rules")
    skus = ranked.sku.tolist()
    ranked["training_active_weeks"] = ranked.sku.map(active)
    ranked["training_last8_active_weeks"] = ranked.sku.map(recent)
    ranked["training_mean_units"] = ranked.training_units / TRAIN_END
    ranked["rank"] = range(1, len(ranked)+1)
    population = {"market":"United Kingdom", "complete_weeks":len(weeks),
                  "observed_skus_complete_calendar":len(wide.columns), "eligible_skus":int(eligible.sum()),
                  "selected_skus":len(skus), "training_uk_units":int(train.sum().sum()),
                  "selected_training_units":int(ranked.training_units.sum()),
                  "training_unit_coverage":float(ranked.training_units.sum()/train.sum().sum()),
                  "selection_rule":"Top 50 by training units among SKUs with sales in >=40 of 60 training weeks and >=6 of the last 8 training weeks"}
    return Panel(weeks, skus, wide[skus].to_numpy(dtype=float), ranked, population)


def features(history, week):
    """Features at t use only quantities before t plus the known calendar."""
    n = history.shape[1]
    lags = [np.log1p(history[-lag]) for lag in [1, 2, 4, 8]]
    rolling = [np.log1p(history[-4:].mean(axis=0)), np.log1p(history[-8:].mean(axis=0)),
               np.log1p(history[-4:].std(axis=0))]
    angle = 2*np.pi*(pd.Timestamp(week)-pd.Timestamp("2000-01-01")).days/365.25
    calendar = [np.full(n, np.sin(angle)), np.full(n, np.cos(angle))]
    return np.column_stack(lags + rolling + calendar + [np.eye(n)])


def fit_ridge(history, weeks, alpha):
    if len(history) < 16:
        raise ValueError("Ridge needs at least 16 observed weeks")
    x = np.vstack([features(history[:t], weeks[t]) for t in range(8, len(history))])
    target = np.log1p(history[8:]).reshape(-1)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-12] = 1
    x = (x-mean)/scale
    intercept = target.mean()
    weights = np.linalg.solve(x.T @ x + alpha*np.eye(x.shape[1]), x.T @ (target-intercept))
    return mean, scale, weights, intercept


def predict(history, weeks, origin, method, horizon=HORIZON):
    if method not in BASELINES+CANDIDATES:
        raise ValueError(f"Unknown method: {method}")
    if origin < 52 or origin > len(history):
        raise ValueError("Forecast origin requires at least 52 observed weeks")
    past = np.asarray(history[:origin], dtype=float).copy()
    if not np.isfinite(past).all() or (past < 0).any():
        raise ValueError("Observed paid units must be finite and nonnegative")
    mean4 = past[-4:].mean(axis=0)
    if method in BASELINES or method.startswith("seasonal_blend_"):
        seasonal = np.array([past[origin+h-52] for h in range(horizon)])
        if method == "moving_average_4":
            return np.tile(mean4, (horizon, 1))
        if method == "seasonal_naive_52":
            return seasonal
        weight = int(method.rsplit("_", 1)[-1])/100
        return weight*seasonal + (1-weight)*mean4
    fit = fit_ridge(past, weeks, float(method.rsplit("_", 1)[-1]))
    mean, scale, weights, intercept = fit
    forecasts = []
    for h in range(horizon):
        week = weeks[0]+pd.Timedelta(weeks=origin+h)
        log_units = ((features(past, week)-mean)/scale) @ weights + intercept
        # Numerical guard only: exp(20) is far above this dataset's unit scale.
        yhat = np.expm1(np.clip(log_units, 0, 20))
        forecasts.append(yhat)
        past = np.vstack([past, yhat])
    return np.asarray(forecasts)


def backtest(panel, origins, methods, actual_end):
    rows = []
    for origin in origins:
        for method in methods:
            f = predict(panel.y, panel.weeks, origin, method)
            for h in range(HORIZON):
                t = origin+h
                actual = panel.y[t] if t < actual_end else np.full(len(panel.skus), np.nan)
                rows.append(pd.DataFrame({"origin_index":origin, "origin_week":panel.weeks[origin],
                    "train_through_week":panel.weeks[origin-1],
                    "target_week":panel.weeks[0]+pd.Timedelta(weeks=t), "target_index":t,
                    "horizon":h+1, "sku":panel.skus, "method":method,
                    "forecast":f[h], "actual":actual, "origin_phase":phase(origin),
                    "target_phase":phase(t) if t < len(panel.weeks) else "future"}))
    return pd.concat(rows, ignore_index=True)


def accuracy(frame, per_sku=False):
    d = frame[frame.actual.notna() & frame.origin_phase.eq(frame.target_phase)].copy()
    d["error"] = d.forecast-d.actual
    d["abs_error"] = d.error.abs()
    keys = ["origin_phase", "method", "horizon"] + (["sku"] if per_sku else [])
    g = d.groupby(keys, as_index=False).agg(points=("actual", "size"), actual_units=("actual", "sum"),
          forecast_units=("forecast", "sum"), absolute_error_units=("abs_error", "sum"),
          mae_units=("abs_error", "mean"), signed_error_units=("error", "sum"))
    g["wape"] = g.absolute_error_units / g.actual_units.replace(0, np.nan)
    g["bias"] = g.signed_error_units / g.actual_units.replace(0, np.nan)
    return g


def choose_models(validation):
    scores = accuracy(validation)
    scores = scores[(scores.origin_phase == "validation") & (scores.horizon == 1)]
    winners = {}
    for role, names in [("baseline", BASELINES), ("candidate", CANDIDATES)]:
        eligible = scores[scores.method.isin(names)].sort_values(["wape", "method"])
        if eligible.empty or not np.isfinite(eligible.wape.iloc[0]):
            raise ValueError("Cannot select models without finite validation WAPE")
        winners[role] = eligible.method.iloc[0]
    return winners
