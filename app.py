import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Macro Pulse Dashboard", page_icon="📈", layout="wide")

# 1. API Authentication
if "FRED_API_KEY" in st.secrets:
    fred_key = st.secrets["FRED_API_KEY"]
else:
    st.error("Missing FRED API Key. Add it to .streamlit/secrets.toml or Streamlit Cloud Secrets.")
    st.stop()

fred = Fred(api_key=fred_key)

# 2. Cached Data Fetching (Caches for 6 hours to prevent rate limits)
@st.cache_data(ttl=21600)
def fetch_fred_series(series_id: str, lookback_years: int = 10):
    start = datetime.today() - timedelta(days=lookback_years * 365)
    data = fred.get_series(series_id, observation_start=start)
    df = data.dropna().reset_index()
    df.columns = ["Date", "Value"]
    return df

# Core Macro Indicators
INDICATORS = {
    "Unemployment Rate (%)": {"id": "UNRATE", "format": "{:.1f}%", "is_pct_change": False},
    "Fed Funds Rate (%)": {"id": "FEDFUNDS", "format": "{:.2f}%", "is_pct_change": False},
    "10Y-2Y Yield Spread (%)": {"id": "T10Y2Y", "format": "{:.2f}%", "is_pct_change": False},
    "CPI Inflation (YoY %)": {"id": "CPIAUCSL", "format": "{:.1f}%", "is_pct_change": True},
}

st.title("Macro Economic Pulse")
st.caption("Live macroeconomic time-series powered by Federal Reserve Economic Data (FRED).")

# 3. Top Row Scorecards
cols = st.columns(len(INDICATORS))

for col, (label, meta) in zip(cols, INDICATORS.items()):
    # Fetch 5 years of data for metric computation
    raw_df = fetch_fred_series(meta["id"], lookback_years=5)
    
    if meta["is_pct_change"]:
        # 12-month change for monthly inflation series
        pct_series = raw_df["Value"].pct_change(periods=12) * 100
        valid = pct_series.dropna()
        latest_val = valid.iloc[-1]
        prior_val = valid.iloc[-2]
    else:
        latest_val = raw_df["Value"].iloc[-1]
        prior_val = raw_df["Value"].iloc[-2]
    
    delta = latest_val - prior_val
    formatted_val = meta["format"].format(latest_val)
    formatted_delta = f"{delta:+.2f} pts"

    with col:
        st.metric(label=label, value=formatted_val, delta=formatted_delta)

st.divider()

# 4. Interactive Historical Chart
col_select, col_slider = st.columns([2, 3])
with col_select:
    selected_name = st.selectbox("Select indicator to visualize:", list(INDICATORS.keys()))
with col_slider:
    lookback = st.slider("Timeframe (Years):", min_value=1, max_value=30, value=10)

selected_meta = INDICATORS[selected_name]
chart_df = fetch_fred_series(selected_meta["id"], lookback_years=lookback)

if selected_meta["is_pct_change"]:
    chart_df["Value"] = chart_df["Value"].pct_change(periods=12) * 100
    chart_df = chart_df.dropna()

fig = px.line(
    chart_df,
    x="Date",
    y="Value",
    title=f"{selected_name} — Historical Trend ({lookback} Years)",
    labels={"Value": selected_name, "Date": ""},
)
fig.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, use_container_width=True)
