from streamlit.testing.v1 import AppTest
from retail_ops.metrics import ROOT
from retail_ops import metrics


def test_forecast_navigation_sku_and_cost_controls(monkeypatch,tmp_path):
    # Committed results must be explorable on a fresh clone without the raw DB.
    monkeypatch.setattr(metrics,"DB",tmp_path/"not_downloaded.sqlite")
    app = AppTest.from_file(str(ROOT/"app.py"),default_timeout=45).run()
    app.switch_page("retail_ops/forecast_page.py").run()
    assert not app.exception
    assert app.title[0].value=="Forecast accuracy meets inventory decisions"
    app.selectbox(key="forecast_sku").set_value("85123A").run()
    assert not app.exception
    app.selectbox(key="inventory_lead").set_value(4)
    app.selectbox(key="inventory_quantile").set_value(.99).run()
    assert not app.exception
    app.number_input(key="inventory_holding").set_value(0.)
    app.number_input(key="inventory_penalty").set_value(0.).run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label=="Candidate − baseline cost")=="£+0"
