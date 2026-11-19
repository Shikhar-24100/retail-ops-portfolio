"""Forecast quality and inventory decisions shown as separate outcomes."""
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from retail_ops.metrics import ROOT

OUT = ROOT / "reports/forecasting"
st.markdown("""<style>
.block-container {padding-top:4rem;max-width:1500px}
h1 {letter-spacing:-1px;font-weight:750!important}
[data-testid="stMetric"] {background:white;border:1px solid #E5DFD8;border-radius:12px;padding:14px}
[data-testid="stMetricLabel"] p {white-space:normal}
[data-testid="stMetricValue"] {font-size:26px}
.eyebrow {color:#B51D51;font-size:12px;letter-spacing:2px;font-weight:700}
@media(max-width:1000px){[data-testid="stHorizontalBlock"]{flex-wrap:wrap}
[data-testid="stColumn"]{min-width:min(100%,240px);flex:1 1 240px!important}}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">FORECASTING & INVENTORY</div>', unsafe_allow_html=True)
st.title("Forecast accuracy meets inventory decisions")
if not (OUT / "metadata.json").exists():
    st.info("Build this project first: python -m retail_ops.build_forecasting")
    st.stop()


@st.cache_data(show_spinner=False)
def load_results(version):
    return {"meta":json.loads((OUT/"metadata.json").read_text()),
        "choice":json.loads((OUT/"model_selection.json").read_text()),
        "scores":pd.read_csv(OUT/"accuracy.csv"), "sku_scores":pd.read_csv(OUT/"sku_accuracy.csv",dtype={"sku":str}),
        "forecasts":pd.read_parquet(OUT/"forecasts.parquet"),
        "summary":pd.read_csv(OUT/"inventory_summary.csv"),
        "ledger":pd.read_parquet(OUT/"inventory_ledger.parquet"),
        "selection":pd.read_csv(OUT/"selected_skus.csv",dtype={"sku":str}),
        "weekly":pd.read_csv(OUT/"weekly_units.csv",dtype={"sku":str},parse_dates=["week"]),
        "calibration":pd.read_csv(OUT/"safety_calibration.csv")}


def chart(fig):
    fig.update_layout(font=dict(family="Arial",color="#21242C"), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=15,t=20,b=0),
        colorway=["#253652","#E62A69","#D69234"])
    fig.update_yaxes(gridcolor="#E9E3DD")
    st.plotly_chart(fig,width="stretch")


def download(frame,name):
    st.download_button("Download CSV",frame.to_csv(index=False),name+".csv","text/csv",key=name)


data = load_results((OUT/"metadata.json").stat().st_mtime_ns)
meta, choice = data["meta"],data["choice"]
labels = meta["labels"]
scores = data["scores"]
test = scores[(scores.origin_phase=="holdout") & (scores.horizon==1)].set_index("method")
baseline,candidate = choice["baseline"],choice["candidate"]
b,c = test.loc[baseline],test.loc[candidate]
st.caption("50 training-selected UK SKUs · 104 complete weeks · Held-out evaluation: 18 July–4 December 2011 · Historical sales replay, simulated inventory")
st.info("The candidate improves one-week WAPE but has substantial underforecast bias. At the default inventory setting it produces more unserved units and higher assumed cost. The baseline remains the better replenishment choice in that scenario.")
a1,a2,a3 = st.columns(3)
a1.metric("Candidate one-week WAPE",f"{c.wape:.1%}",f"{100*(c.wape-b.wape):+.2f} pp vs baseline",delta_color="inverse")
a2.metric("Baseline one-week WAPE",f"{b.wape:.1%}")
a3.metric("Candidate demand bias",f"{c.bias:+.1%}")
st.caption("WAPE = total absolute error / total recorded units across 1,000 held-out SKU-weeks. Bias = (forecast − recorded units) / recorded units. Choices were frozen using validation results, before the holdout run.")

with st.sidebar:
    st.markdown("### Study scope")
    st.caption(f"{meta['population']['selected_skus']} SKUs selected from {meta['population']['eligible_skus']} eligible SKUs using the first 60 weeks only.\n\nTraining unit coverage: {meta['population']['training_unit_coverage']:.1%} of UK paid units.")
    sku = st.selectbox("Inspect a SKU",["All 50 SKUs"]+data["selection"].sku.tolist(),key="forecast_sku")
    st.divider()
    st.markdown("**Model selection**")
    st.caption(f"Baseline: {labels[baseline]}\n\nCandidate: {labels[candidate]}\n\nMetric: one-week validation WAPE.")
    st.caption("The SKU filter changes charts and detail tables. Headline forecasts and inventory comparisons always cover all 50 SKUs.")

forecast_tab,inventory_tab,design_tab = st.tabs(["Forecast evaluation","Inventory scenarios","Study design & evidence"])

with forecast_tab:
    st.subheader("Actual units and weekly forecasts")
    f = data["forecasts"]
    f = f[(f.origin_phase=="holdout") & (f.horizon==1) & f.method.isin([baseline,candidate])]
    if sku != "All 50 SKUs":
        f = f[f.sku==sku]
    timeline = f.groupby(["target_week","method"],as_index=False)[["actual","forecast"]].sum()
    fig = go.Figure()
    actual = timeline[timeline.method==baseline]
    fig.add_scatter(x=actual.target_week,y=actual.actual,name="Recorded paid units",line=dict(color="#253652",width=3))
    for method,color in [(baseline,"#D69234"),(candidate,"#E62A69")]:
        d = timeline[timeline.method==method]
        fig.add_scatter(x=d.target_week,y=d.forecast,name=labels[method],line=dict(color=color,dash="dot"))
    fig.update_layout(yaxis_title="Units / week",legend=dict(orientation="h",y=-.25),height=430)
    chart(fig)
    st.caption("Aggregate curves can hide offsetting SKU errors. The headline WAPE is computed from individual SKU-week errors, not from the aggregated curve.")
    download(f,"held_out_forecasts")
    st.subheader("Same holdout, same forecast origins")
    table = test.reset_index()[["method","points","mae_units","wape","bias"]].copy()
    table["method"] = table.method.map(labels)
    st.dataframe(table,hide_index=True,width="stretch",column_config={
        "mae_units":st.column_config.NumberColumn(format="%.2f"),
        "wape":st.column_config.NumberColumn("WAPE (fraction)",format="%.4f"),
        "bias":st.column_config.NumberColumn("Bias (fraction)",format="%.4f")})
    st.subheader("Forecast horizon matters for replenishment")
    multi = scores[(scores.origin_phase=="holdout") & scores.method.isin([baseline,candidate])].copy()
    multi["model"] = multi.method.map(labels)
    chart(px.line(multi,x="horizon",y="wape",color="model",markers=True,
        labels={"horizon":"Weeks ahead","wape":"SKU-level WAPE","model":""}).update_yaxes(tickformat=".0%"))
    st.caption("Only targets within the holdout are scored. Later horizons have fewer complete forecast origins. Inventory needs the full lead-time-plus-review path, not just the next week.")
    detail = data["sku_scores"].query("origin_phase == 'holdout'")
    if sku != "All 50 SKUs":
        detail = detail[detail.sku==sku]
    with st.expander("SKU results, including failures"):
        st.dataframe(detail,hide_index=True,width="stretch")
        download(detail,"sku_forecast_accuracy")
    with st.expander("Validation search and frozen selection"):
        v = scores.query("origin_phase == 'validation' and horizon == 1")
        st.dataframe(v.sort_values("wape"),hide_index=True,width="stretch")
        st.json(choice)
        download(v,"validation_model_comparison")

with inventory_tab:
    st.subheader("Compare replenishment policies")
    st.caption("Weekly review with order-up-to targets. Recorded paid sales are replayed as assumed demand. These are hypothetical policies and costs, not reconstructed historical stock levels.")
    x,y = st.columns(2)
    lead = x.selectbox("Supplier lead time (weeks)",[1,2,4],index=1,key="inventory_lead")
    quantile = y.selectbox("Validation buffer quantile",[.90,.95,.99],index=1,format_func=lambda q:f"{q:.0%}",key="inventory_quantile")
    h1,h2 = st.columns(2)
    holding = h1.number_input("Assumed holding cost (£/unit/week)",min_value=0.,value=.05,step=.01,key="inventory_holding")
    penalty = h2.number_input("Assumed penalty (£/unserved unit)",min_value=0.,value=1.,step=.25,key="inventory_penalty")
    st.caption("Lead time and buffer quantile select precomputed policy replays. Cost inputs reprice their stock and unserved units; they do not retrain or optimize the ordering rule. A 95% buffer quantile does not guarantee a 95% fill rate.")
    result = data["summary"].query("lead_time_weeks == @lead and buffer_quantile == @quantile").copy()
    result["assumed_cost_gbp"] = result.stock_unit_weeks*holding+result.lost_units*penalty
    ib,ic = result.set_index("policy").loc["baseline"],result.set_index("policy").loc["candidate"]
    j1,j2,j3 = st.columns(3)
    j1.metric("Candidate simulated fill rate",f"{ic.fill_rate:.1%}",f"{100*(ic.fill_rate-ib.fill_rate):+.2f} pp vs baseline")
    j2.metric("Baseline simulated fill rate",f"{ib.fill_rate:.1%}")
    j3.metric("Candidate − baseline cost",f"£{ic.assumed_cost_gbp-ib.assumed_cost_gbp:+,.0f}",delta_color="off")
    show = ["policy","fill_rate","lost_units","stockout_sku_weeks","mean_on_hand_units","assumed_cost_gbp","ending_on_hand_units","ending_pipeline_units"]
    st.dataframe(result[show],hide_index=True,width="stretch",column_config={
        "fill_rate":st.column_config.NumberColumn("Unit fill rate (fraction)",format="%.4f"),
        "mean_on_hand_units":st.column_config.NumberColumn(format="%.1f"),
        "assumed_cost_gbp":st.column_config.NumberColumn(format="£%.2f")})
    download(result,"inventory_scenario")
    st.caption("Fill rate = fulfilled units / replay demand units. A stockout SKU-week has at least one unserved unit. Mean stock is total portfolio on-hand stock averaged over 20 weeks, assuming uniform within-week demand. Open purchase orders at the end are shown separately.")
    frontier = data["summary"].copy()
    frontier["setting"] = frontier.lead_time_weeks.astype(str)+"w / "+(frontier.buffer_quantile*100).astype(int).astype(str)+"%"
    st.subheader("The service–stock trade-off")
    chart(px.scatter(frontier,x="mean_on_hand_units",y="fill_rate",color="policy",symbol="lead_time_weeks",
        hover_data=["buffer_quantile","lost_units","setting"],labels={"mean_on_hand_units":"Mean portfolio on-hand units (simulated)",
            "fill_rate":"Simulated unit fill rate","policy":"Policy","lead_time_weeks":"Lead time"}).update_yaxes(tickformat=".0%"))
    ledger = data["ledger"].query("lead_time_weeks == @lead and buffer_quantile == @quantile and phase == 'holdout'")
    if sku != "All 50 SKUs":
        ledger = ledger[ledger.sku==sku]
    flow = ledger.groupby(["week","policy"],as_index=False)[["demand_units","fulfilled_units","lost_units","average_on_hand_units"]].sum()
    st.subheader("Inventory through the holdout")
    chart(px.line(flow,x="week",y="average_on_hand_units",color="policy",
        labels={"week":"Week starting","average_on_hand_units":"Mean on-hand units (simulated)","policy":""}))
    with st.expander("Audit the receive, order and fulfil ledger"):
        st.dataframe(ledger.head(200),hide_index=True,width="stretch")
        download(ledger,"inventory_decision_ledger")
    st.warning("No live inventory, supplier lead times, costs or lost-sales records are present. This replay assumes unlimited supply, fixed lead times, no backorders, no expiry, no returns to stock and no minimum order quantities. Neither policy is a production recommendation for Myntra.")

with design_tab:
    st.subheader("Time order is preserved")
    split = pd.DataFrame([{"stage":k,"first_week":v[0],"last_week":v[1]} for k,v in meta["splits"].items()])
    st.dataframe(split,hide_index=True,width="stretch")
    st.markdown("""
1. Rank active SKUs using the first 60 weeks only. Zero-fill missing SKU-weeks as **no recorded paid sale**.
2. Evaluate two baselines and six candidate configurations on 16 rolling validation origins. Select each role by one-week pooled WAPE.
3. Freeze model choices and calibrate safety buffers from complete validation protection windows. Overlapping errors are pooled after normalising by training mean demand.
4. Start both inventory policies with identical stock and empty purchase-order pipelines, then run eight warm-up weeks.
5. Evaluate 20 later weeks. Models can refit with data observed before each weekly origin, while settings and buffer calibration remain frozen.
""")
    st.code("target = ceil(sum(forecast over lead_time + 1 weeks) + safety_buffer)\norder = max(0, target - on_hand_after_receipts - outstanding_orders)\narrival_week = order_week + lead_time\nassumed_cost = holding_rate × stock_unit_weeks + penalty × unserved_units",language="text")
    st.caption("A pooled log-ridge uses lagged units, trailing means/variation, known annual calendar features and SKU indicators. Scaling and coefficients are refit on past observations only. Log-scale point forecasts can underpredict large unit spikes; that limitation is visible in the bias metric.")
    st.json(meta,expanded=False)
    audit = OUT/"validation.json"
    if audit.exists():
        st.subheader("Independent reconciliation")
        st.json(json.loads(audit.read_text()),expanded=False)
    st.subheader("Training-only SKU selection")
    st.dataframe(data["selection"],hide_index=True,width="stretch")
    download(data["selection"],"training_selected_skus")
    st.caption("Source: Chen, D. (2012), Online Retail II, UCI, CC BY 4.0. The common data audit and cleaning decisions are documented in Sales & customers.")
