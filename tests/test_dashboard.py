from streamlit.testing.v1 import AppTest
from retail_ops import metrics


def test_dashboard_filters_search_and_empty_selection(warehouse, monkeypatch):
    monkeypatch.setattr(metrics, "DB", warehouse)
    app = AppTest.from_file(str(metrics.ROOT / "app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.metric[0].value == "£80"
    app.text_input[0].set_value("does not exist").run()
    assert not app.exception
    # The product table reflects the search without changing headline KPIs.
    assert app.metric[0].value == "£80"
    app.date_input[0].set_value(("2011-01-01", "2011-02-01"))
    app.button[0].click().run()
    assert not app.exception
    assert any("No merchandise sales" in item.value for item in app.info)
