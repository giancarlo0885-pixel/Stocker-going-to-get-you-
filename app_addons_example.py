"""Copy the parts you want into app.py. Do not use this as the Railway start file."""
import streamlit as st

from confidence_engine import calculate_confidence
from economic_data import latest_indicator
from options_flow import scan_options
from paper_journal import list_trades

st.subheader("Oracle Add-ons")

symbol = st.text_input("Options symbol", "AAPL").upper().strip()
if st.button("Scan options"):
    try:
        result = scan_options(symbol)
        st.json(result.__dict__)
    except Exception as exc:
        st.warning(str(exc))

indicator = st.selectbox(
    "Economic indicator",
    ["CPI", "INFLATION", "UNEMPLOYMENT", "FEDERAL_FUNDS_RATE", "REAL_GDP"],
)
if st.button("Load economic data"):
    try:
        st.json(latest_indicator(indicator).__dict__)
    except Exception as exc:
        st.warning(str(exc))

confidence = calculate_confidence(
    model_probability=0.68,
    data_quality=0.85,
    trend_agreement=0.70,
    news_agreement=0.60,
    volatility_penalty=0.35,
)
st.metric("Example confidence", f"{confidence.score}%")
st.caption("Research score, not a guarantee.")

st.dataframe(list_trades(50), width="stretch")
