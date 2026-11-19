import numpy as np
import pandas as pd
import pytest
from retail_ops.forecasting import (BASELINES, CANDIDATES, Panel, accuracy, backtest,
    choose_models, make_panel, predict)
from retail_ops.inventory import safety_calibration, simulate, summarize


def small_panel():
    weeks = pd.date_range("2009-12-07", periods=104, freq="W-MON")
    y = np.column_stack([np.arange(104)%9+10, np.arange(104)%7+20]).astype(float)
    return Panel(weeks, ["12345", "23456"], y, pd.DataFrame(), {})


@pytest.mark.parametrize("method", BASELINES+CANDIDATES)
def test_forecasts_cannot_see_future_targets(method):
    p = small_panel()
    expected = predict(p.y, p.weeks, 60, method)
    changed = p.y.copy()
    changed[60:] = 999999
    assert np.allclose(expected, predict(changed, p.weeks, 60, method))
    assert expected.shape == (5, 2)
    assert np.isfinite(expected).all() and (expected >= 0).all()


def test_simple_baselines_are_hand_verifiable():
    p = small_panel()
    assert np.allclose(predict(p.y, p.weeks, 60, "moving_average_4"), np.tile(p.y[56:60].mean(axis=0), (5,1)))
    assert np.array_equal(predict(p.y, p.weeks, 60, "seasonal_naive_52"), p.y[8:13])


def test_selection_and_calendar_never_use_future_units():
    p = small_panel()
    rows = [{"date":w.strftime("%Y-%m-%d"),"sku":s,"country":"United Kingdom","units":p.y[t,j]}
            for t,w in enumerate(p.weeks) for j,s in enumerate(p.skus)]
    # Supply the true source boundaries without creating eligible new products.
    rows += [{"date":"2009-12-01","sku":"99999","country":"United Kingdom","units":1},
             {"date":"2011-12-09","sku":"99999","country":"United Kingdom","units":1}]
    d = pd.DataFrame(rows)
    a = make_panel(d, top_n=1)
    d.loc[d.date >= "2011-01-31", "units"] = 1000000
    b = make_panel(d, top_n=1)
    assert a.skus == b.skus == ["23456"]
    assert a.weeks[0] == p.weeks[0] and a.weeks[-1] == p.weeks[-1]
    assert np.array_equal(a.y[:60], b.y[:60])


def test_validation_hides_targets_beyond_its_cutoff():
    p = small_panel()
    f = backtest(p, [75], BASELINES, actual_end=76)
    assert f[f.horizon > 1].actual.isna().all()
    assert (f.train_through_week < f.origin_week).all()
    assert (f.target_week >= f.origin_week).all()


def test_model_choice_ignores_holdout_scores():
    p = small_panel()
    validation = backtest(p, [60,61], BASELINES+CANDIDATES, actual_end=76)
    choice = choose_models(validation)
    holdout = backtest(p, [84], BASELINES+CANDIDATES, actual_end=104)
    holdout["forecast"] = 999999999
    assert choose_models(pd.concat([validation,holdout])) == choice


def test_wape_uses_total_demand_not_mean_sku_percentages():
    d = pd.DataFrame({"origin_phase":["holdout"]*2,"target_phase":["holdout"]*2,
        "method":["test"]*2,"horizon":[1,1],"sku":["a","b"],"actual":[0.,10.],"forecast":[5.,12.]})
    m = accuracy(d).iloc[0]
    assert m.wape == .7 and m.bias == .7 and m.mae_units == 3.5
    d.actual = 0
    assert pd.isna(accuracy(d).wape.iloc[0])


def test_lead_time_pipeline_and_conservation():
    demand = np.full((5,1), 2.)
    forecasts = np.full((5,5,1), 2.)
    x = simulate(demand, forecasts, np.array([0]), np.array([4]), 1, warmup=1)
    assert x.received_units.tolist() == [0,0,2,2,2]
    assert x.ordered_units.tolist() == [0,2,2,2,2]
    assert (x.opening_units+x.received_units-x.fulfilled_units == x.closing_units).all()
    assert (x.fulfilled_units+x.lost_units == x.demand_units).all()
    assert (x.closing_units >= 0).all()
    assert summarize(x)["fill_rate"] == 1


def test_orders_do_not_arrive_in_the_same_week_and_warmup_is_excluded():
    x = simulate(np.full((4,1),3.), np.full((4,5,1),3.), [0], [0], 2, warmup=2)
    assert x.received_units.tolist()[:3] == [0,0,9]
    assert x.lost_units.tolist()[:2] == [3,3]
    assert summarize(x)["lost_units"] == 0
    assert summarize(x)["demand_units"] == 6


def test_uniform_within_week_holding_integral():
    x = simulate(np.array([[2.],[0.]]), np.zeros((2,5,1)), [0], [1], 1, warmup=0)
    assert x.average_on_hand_units.tolist() == [.25,0]
    assert summarize(x, holding_cost=2, lost_penalty=3)["total_assumed_cost_gbp"] == 3.5


def test_safety_buffer_uses_complete_validation_windows_only():
    v = pd.DataFrame({"method":["m"]*6,"horizon":[1,2,1,2,1,2],
        "origin_phase":["validation"]*4+["holdout"]*2,"origin_index":[60,60,75,75,84,84],
        "sku":["a"]*6,"actual":[12,12,12,np.nan,9999,9999],"forecast":[10]*6})
    buffer, n = safety_calibration(v,{"a":10},"m",2,.95)
    assert buffer == .4 and n == 1


def test_invalid_inventory_inputs_fail():
    with pytest.raises(ValueError, match="lead time"):
        simulate(np.ones((2,1)),np.ones((2,5,1)),[0],[0],0,warmup=0)
    with pytest.raises(ValueError, match="nonnegative"):
        simulate(-np.ones((2,1)),np.ones((2,5,1)),[0],[0],1,warmup=0)
