from streamlit.testing.v1 import AppTest
from retail_ops import metrics


def test_dashboard_filters_search_and_empty_selection(warehouse, monkeypatch):
    monkeypatch.setattr(metrics, "DB", warehouse)
    app = AppTest.from_file(str(metrics.ROOT / "app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.metric[0].value == "£80"
    app.text_input[0].set_value("does not exist").run()
    assert not app.exception
    # Search changes the product table without changing headline KPIs.
    product_table = next(x.value for x in app.dataframe if "cumulative_sales_share" in x.value.columns)
    assert product_table.empty
    assert app.metric[0].value == "£80"
    app.date_input[0].set_value(("2011-01-01", "2011-02-01"))
    app.button[0].click().run()
    assert not app.exception
    assert any("No merchandise sales" in item.value for item in app.info)


def test_anonymous_only_market_has_no_invented_customer_metrics(warehouse, monkeypatch):
    import sqlite3
    with sqlite3.connect(warehouse) as con:
        con.execute("UPDATE orders SET customer_id=NULL")
        con.execute("UPDATE sales SET customer_id=NULL")
    monkeypatch.setattr(metrics, "DB", warehouse)
    app = AppTest.from_file(str(metrics.ROOT / "app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.metric[0].value == "£80"
    assert next(m.value for m in app.metric if m.label == "Repeat purchase rate") == "n/a"
    assert next(m.value for m in app.metric if m.label == "Identified customers") == "0"
    assert any("No first-observed customers" in item.value for item in app.info)
