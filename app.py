"""Interactive analyst workbench. Run: streamlit run app.py"""
from datetime import date
import json
import pandas as pd
import plotly.express as px
import streamlit as st

from retail_ops.metrics import DB, ROOT, dimensions, query

st.set_page_config(page_title="Retail Ops | Sales & customers", page_icon="🛍", layout="wide")
st.markdown("""<style>
.block-container {padding-top:4rem; max-width:1500px}
h1 {letter-spacing:-1.5px; font-weight:750!important}
[data-testid="stMetric"] {background:white;border:1px solid #E5DFD8;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"] {font-size:13px;color:#65656C}
[data-testid="stMetricValue"] {font-size:26px}
[data-testid="stMetricLabel"] p {white-space:normal}
.eyebrow {color:#B51D51;font-size:12px;letter-spacing:2px;font-weight:700}
@media (max-width:1000px) {
  [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
  [data-testid="stColumn"] {min-width:min(100%,240px);flex:1 1 240px!important}
}
</style>""", unsafe_allow_html=True)

if not DB.exists():
    st.title("Sales & customer analytics")
    st.info("Build the local warehouse first: python -m retail_ops.pipeline")
    st.stop()

stamp = DB.stat().st_mtime_ns


@st.cache_data(show_spinner=False)
def load(name, start, end, country, version):
    return query(name, start, end, country)


def chart(fig):
    fig.update_layout(font=dict(family="Arial", color="#21242C"), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=15, t=20, b=0),
                      colorway=["#E62A69", "#253652", "#DB923B", "#69A999"])
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E9E3DD")
    st.plotly_chart(fig, width="stretch")


def export(df, key):
    st.download_button("Download this analysis (CSV)", df.to_csv(index=False), f"{key}.csv", "text/csv", key=key)


with st.sidebar:
    st.markdown("### RETAIL / OPS")
    st.caption("Shikhar · Business operations portfolio")
    st.divider()
    with st.form("filters"):
        country = st.selectbox("Market", ["All markets"] + dimensions())
        window = st.date_input("Order dates", (date(2009, 12, 1), date(2011, 11, 30)),
                               min_value=date(2009, 12, 1), max_value=date(2011, 12, 9))
        st.form_submit_button("Apply filters", width="stretch", type="primary")
    st.caption("Default: 24 complete calendar months. December 2011 has only nine observed days.")
    st.divider()
    st.markdown("**Historical public data**")
    st.caption("UK giftware retailer · GBP\n\nUCI Online Retail II · 2009–2011\n\nNo affiliation with Myntra.")
    st.link_button("Source & attribution", "https://archive.ics.uci.edu/dataset/502/online+retail+ii")

if len(window) != 2:
    st.info("Select both a start and an end date.")
    st.stop()
start, end = window
st.markdown('<div class="eyebrow">PROJECT 01 / SALES & CUSTOMER ANALYTICS</div>', unsafe_allow_html=True)
st.title("Retail sales & customer behaviour")
st.caption(f"{country} · {start:%d %b %Y} – {end:%d %b %Y} · Currency: GBP · Historical findings")
if start.day != 1 or end != (pd.Timestamp(end) + pd.offsets.MonthEnd(0)).date():
    st.warning("This selection contains a partial calendar month. Monthly totals are not comparable without adjusting for coverage.")

with st.spinner("Running SQL against the transaction warehouse..."):
    k = load("kpis", start, end, country, stamp).iloc[0]

if k.orders == 0:
    st.info("No merchandise sales in this market and date selection. Select a broader window or another market.")
    st.stop()

cards = st.columns(5)
cards[0].metric("Gross merchandise sales", f"£{k.gross_sales_gbp:,.0f}")
cards[1].metric("Orders", f"{k.orders:,.0f}")
cards[2].metric("Average order value", f"£{k.aov_gbp:,.2f}")
cards[3].metric("Repeat purchase rate", "n/a" if pd.isna(k.repeat_purchase_rate) else f"{k.repeat_purchase_rate:.1%}")
cards[4].metric("Net recorded value", f"£{k.net_recorded_value_gbp:,.0f}")
st.caption("AOV = gross merchandise sales / positive merchandise orders. Repeat rate = identified buyers with 2+ orders / identified buyers in this window. Net recorded value subtracts recorded reversals in this window; it is not profit.")

overview, customers, products, pricing, methods = st.tabs(["Sales overview", "Customers & cohorts", "Product performance", "Pricing & promotion evidence", "Definitions & SQL"])

with overview:
    monthly = load("monthly", start, end, country, stamp)
    markets = load("countries", start, end, country, stamp)
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Monthly gross sales")
        fig = px.area(monthly, x="month", y="gross_sales_gbp", labels={"month":"Month", "gross_sales_gbp":"Gross sales (GBP)"})
        chart(fig)
    with c2:
        st.subheader("Market contribution")
        chart(px.bar(markets.head(8).sort_values("gross_sales_gbp"), x="gross_sales_gbp", y="country", orientation="h",
                     labels={"gross_sales_gbp":"Gross sales (GBP)", "country":""}))
    st.subheader("Sales reconciliation")
    a, b, c = st.columns(3)
    a.metric("Gross sales", f"£{k.gross_sales_gbp:,.2f}")
    b.metric("Recorded reversals", f"£{k.reversed_gbp:,.2f}")
    c.metric("Net recorded value", f"£{k.net_recorded_value_gbp:,.2f}")
    st.caption("Reversals include negative-quantity merchandise cancellations and returns. Original sales are not linked, so this is not a matched return rate. Shipping, fees, manual adjustments, and nonpositive-price lines are excluded.")
    st.dataframe(monthly, hide_index=True, width="stretch")
    export(monthly, "monthly")

with customers:
    segments = load("segments", start, end, country, stamp)
    cohorts = load("cohorts", start, end, country, stamp)
    a, b = st.columns(2)
    a.metric("Identified customers", f"{k.identified_customers:,.0f}")
    b.metric("Sales linked to a customer", f"{k.identified_revenue_share:.1%}")
    st.caption("Anonymous purchases count toward sales and AOV, but cannot be assigned a repeat history. Customer-level results cover identified buyers only.")
    st.subheader("Behavioural customer segments")
    chart(px.bar(segments.sort_values("gross_sales_gbp"), x="gross_sales_gbp", y="segment", orientation="h",
                 hover_data=["customers", "avg_frequency"], labels={"gross_sales_gbp":"Gross sales (GBP)", "segment":""}))
    st.dataframe(segments, hide_index=True, width="stretch")
    st.caption("Recency is measured at the selected end date. Recent = last purchase within 90 days. Frequent = 3+ orders; repeat = 2; one-time = 1, within the selected period. Lapsed = over 90 days. These are descriptive rules, not churn predictions.")
    st.subheader("90-day repeat purchase by first-observed cohort")
    if len(cohorts):
        mature = cohorts.repeat_customers_90d.sum() / cohorts.eligible_customers.sum()
        st.metric("Weighted 90-day repeat rate", f"{mature:.1%}")
        chart(px.line(cohorts, x="cohort", y="repeat_rate_90d", markers=True,
                      hover_data=["eligible_customers"], labels={"cohort":"First observed purchase month", "repeat_rate_90d":"90-day repeat rate"}).update_yaxes(tickformat=".0%"))
        st.dataframe(cohorts, hide_index=True, width="stretch")
        export(cohorts, "cohorts")
    else:
        st.info("No first-observed customers have a full 90-day follow-up in this selection.")
    st.caption("First purchase looks back to the start of the source in the selected market. Customers enter only if 90 days are observable after their first order. The latest eligible cohort may contain only part of its acquisition month. Purchases before December 2009 are unknown.")
    export(segments, "segments")

with products:
    p = load("products", start, end, country, stamp)
    st.subheader("Products driving sales")
    top = st.slider("Products to display", 5, 30, 12)
    p["label"] = p.sku + " · " + p.description.fillna("").str.slice(0, 34)
    chart(px.bar(p.head(top).sort_values("gross_sales_gbp"), x="gross_sales_gbp", y="label", orientation="h",
                 hover_data=["units", "orders", "reversed_gbp"], labels={"label":"", "gross_sales_gbp":"Gross sales (GBP)"}).update_layout(height=470))
    a, b = st.columns(2)
    a.metric("SKUs with sales", f"{(p.gross_sales_gbp > 0).sum():,}")
    b.metric("Top 20 SKU sales share", f"{p.head(20).gross_sales_gbp.sum()/k.gross_sales_gbp:.1%}")
    st.caption("Descriptions use a representative source label, not a curated category taxonomy. SKU codes are the product key. Returns-only SKUs remain in the reconciliation.")
    search = st.text_input("Search SKU or product description")
    visible = p[p.label.str.contains(search, case=False, regex=False, na=False)] if search else p
    st.dataframe(visible.drop(columns="label"), hide_index=True, width="stretch", column_config={"cumulative_sales_share":st.column_config.NumberColumn(format="%.3f")})
    export(visible.drop(columns="label"), "products")
    st.subheader("Decisions to investigate")
    st.markdown(f"""
- **Availability:** review the top 20 SKUs, which account for **{p.head(20).gross_sales_gbp.sum()/k.gross_sales_gbp:.1%}** of this selection's gross sales. Test replenishment rules in project 2 before claiming stockout reduction.
- **Retention:** compare recent one-time buyers with repeat buyers, then test a follow-up offer using a control group. Historical segment differences do not prove campaign uplift.
- **Reversal exceptions:** investigate SKUs with high recorded reversals and check invoice-level context before changing assortment.
- **Trading calendar:** use complete-month history to plan peak capacity. Validate any future plan with time-based forecast backtests.
""")

with pricing:
    st.subheader("What the data can establish")
    st.info("Promotion effectiveness is unavailable: this source has no campaign exposure, promotion flag, list price, discount depth, or product costs.")
    st.markdown("The table shows observed price dispersion for SKUs with at least 30 orders. Different prices can reflect wholesale quantities, customer mix, seasonality, or data errors. Treat these as investigation candidates.")
    price = load("price_variation", start, end, country, stamp)
    st.dataframe(price.head(100), hide_index=True, width="stretch")
    export(price, "price_variation")
    st.subheader("How to measure a promotion properly")
    st.markdown("Randomly assign eligible customers to offer and control groups. Record exposure, eligibility, net revenue, returns, and margin over the same follow-up window. Compare incremental contribution margin per eligible customer, with uncertainty and sample-size checks. Log opt-outs and delivery costs before scaling.")

with methods:
    st.subheader("Source, scope & quality")
    audit_path = ROOT / "reports/data_quality.json"
    if audit_path.exists():
        st.json(json.loads(audit_path.read_text()), expanded=False)
    st.markdown("""
- **Population:** UK online giftware retailer with substantial wholesale activity. This is a methods demonstration for business operations, not evidence about Myntra customers.
- **Merchandise rule:** a five-digit SKU with up to two trailing letters. This is a documented heuristic; fees and manual adjustments are excluded.
- **Duplicates:** remove identical invoice copies across source sheets. Retain repeated lines within an invoice because they may represent genuine order entries. The audit reports the sales sensitivity if duplicate candidates are dropped.
- **Money:** integer thousandths of GBP preserve the source's three-decimal prices. No exchange-rate conversion, margin, or causal impact is claimed.
- **Forecast handoff:** daily observed sales by SKU and market are built separately. Project 2 will evaluate forecasts against a seasonal naive baseline, then simulate explicit inventory policies. It is not implemented in project 1.
""")
    st.subheader("Review the SQL behind each result")
    name = st.selectbox("Query", ["kpis", "monthly", "products", "segments", "cohorts", "countries", "price_variation"])
    st.code((ROOT / "sql" / f"{name}.sql").read_text(), language="sql")
    st.json({"start":str(start), "end":str(end), "country":country})
    st.caption("Attribution: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. CC BY 4.0. Data transformed as described above.")
