"""Two substantial projects, one shared retail operations portfolio."""
import streamlit as st

st.set_page_config(page_title="Retail Operations Portfolio", page_icon="🛍", layout="wide")
navigation = st.navigation([
    st.Page("retail_ops/sales_page.py", title="Sales & customers", icon="🛍", default=True),
    st.Page("retail_ops/forecast_page.py", title="Forecast & inventory", icon="📦"),
])
navigation.run()
