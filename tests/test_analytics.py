import pandas as pd
import pytest
from retail_ops.metrics import query
from retail_ops.pipeline import classify, remove_sheet_overlap


def test_hand_calculated_kpis_include_anonymous_sales(warehouse):
    k = query("kpis", "2010-01-01", "2010-12-31", path=warehouse).iloc[0]
    assert k.gross_sales_gbp == 80
    assert k.orders == 4
    assert k.aov_gbp == 20
    assert k.identified_customers == 2
    assert k.repeat_purchase_rate == .5
    assert k.identified_revenue_share == .625
    assert k.reversed_gbp == 24
    assert k.net_recorded_value_gbp == 56


def test_returns_only_sku_does_not_disappear(warehouse):
    p = query("products", "2010-01-01", "2010-12-31", path=warehouse)
    assert p.net_recorded_value_gbp.sum() == 56
    assert p.loc[p.sku == "55555", "net_recorded_value_gbp"].iloc[0] == -4


def test_fixed_follow_up_and_history_before_filter(warehouse):
    c = query("cohorts", "2010-01-01", "2010-04-01", path=warehouse)
    assert c.eligible_customers.sum() == 1
    assert c.repeat_rate_90d.iloc[0] == 1
    # Jan 1 has only 89 follow-up days by March 31, so exclude it.
    assert query("cohorts", "2010-01-01", "2010-03-31", path=warehouse).empty
    # Filtering to Jan 5 must not relabel an established buyer as newly acquired.
    assert query("cohorts", "2010-01-05", "2010-12-31", path=warehouse).cohort.tolist() == ["2010-04"]


def test_segments_partition_identified_revenue(warehouse):
    s = query("segments", "2010-01-01", "2010-12-31", path=warehouse)
    assert s.customers.sum() == 2
    assert s.gross_sales_gbp.sum() == 50


def test_empty_market_and_parameterized_country(warehouse):
    k = query("kpis", country="UK' OR 1=1 --", path=warehouse).iloc[0]
    assert k.orders == 0
    assert pd.isna(k.repeat_purchase_rate)
    assert k.gross_sales_gbp == 0


def test_cross_sheet_overlap_preserves_within_sheet_duplicates(source):
    original = source.iloc[[0, 0]].copy()
    original.source_row = [2, 3]
    later = original.copy()
    later.source_sheet = "Sheet 2"
    cleaned, removed = remove_sheet_overlap(pd.concat([original, later], ignore_index=True))
    assert len(cleaned) == 2
    assert removed == 2
    assert classify(cleaned).duplicate_candidate.sum() == 1
    later.loc[later.index[0], "quantity"] = 99
    with pytest.raises(ValueError, match="Conflicting cross-sheet"):
        remove_sheet_overlap(pd.concat([original, later], ignore_index=True))


def test_merchandise_and_cancellation_rules(source):
    d = classify(source)
    assert d.disposition.value_counts().to_dict() == {"sale":4, "return_or_cancellation":2, "non_merchandise":1, "nonpositive_price":1, "other_adjustment":1}


def test_three_decimal_currency_is_preserved(source):
    d = source.iloc[[0]].copy()
    d.price = 1.235
    result = classify(d)
    assert result.unit_price_mills.iloc[0] == 1235
    assert result.value_mills.iloc[0] == 2470
    d.price = 1.2345
    with pytest.raises(ValueError, match="precise"):
        classify(d)


def test_invoice_customer_conflicts_fail_before_reporting(source, tmp_path):
    from retail_ops.pipeline import write_database
    d = source.iloc[[0, 1]].copy()
    d.invoice = "1"
    d.timestamp = "2010-01-01"
    d.customer_id = [101, 202]
    with pytest.raises(ValueError, match="inconsistent customer_id"):
        write_database(classify(d), tmp_path / "conflict.sqlite")
