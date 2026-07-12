from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import engine
from api_manager import api_statuses
from market_data import history, latest_snapshot, technical_features
from market_predictor import convert_currency, forecast_market
from news_intelligence import get_market_news
from oracle_bot import render_oracle_bot
from risk_engine import risk_report


st.set_page_config(
    page_title="Garibaldi Market Oracle",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 1.2rem;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(120,120,120,.22);
    border-radius: 14px;
    padding: 14px;
}
.hero {font-size: clamp(2.2rem, 6vw, 4.8rem); font-weight: 900; line-height: .98;}
.sub {font-size: 1.05rem; opacity: .78; margin: .8rem 0 1rem;}
.card {border:1px solid rgba(120,120,120,.2); border-radius:16px; padding:18px; min-height:160px;}
</style>
""", unsafe_allow_html=True)

engine.init_db()

st.markdown('<div class="hero">GARIBALDI MARKET ORACLE™</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub">Plain-language market intelligence for stocks, crypto, ETFs and world currencies.</div>',
    unsafe_allow_html=True,
)
st.warning(
    "Educational analysis and simulated paper trading only. Forecasts are estimates, not guarantees."
)

tabs = st.tabs([
    "🏠 Home", "📈 Markets", "🔮 Forecast", "💱 Currency",
    "📰 News", "🧪 Paper Trading", "🤖 Ask Oracle", "📚 Learn", "⚙️ Health"
])

with tabs[0]:
    st.subheader("Choose what you need")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="card"><h3>Stocks & ETFs</h3><p>See price, trend, risk, technical indicators and forecasts.</p><b>Examples:</b> AAPL, NVDA, SPY</div>', unsafe_allow_html=True)
    c2.markdown('<div class="card"><h3>Crypto</h3><p>Study 24/7 digital-asset markets and volatility.</p><b>Examples:</b> BTC, ETH, SOL</div>', unsafe_allow_html=True)
    c3.markdown('<div class="card"><h3>Fiat Currency</h3><p>Convert government-issued currencies and study FX pairs.</p><b>Examples:</b> USD/EUR, USD/MXN</div>', unsafe_allow_html=True)

    st.subheader("Built-in protections")
    st.write(
        "The app uses position limits, maximum allocation per trade, confidence labels, risk reports, "
        "paper trading only, and probability ranges instead of guaranteed targets."
    )

with tabs[1]:
    st.subheader("Market snapshot")
    c1, c2 = st.columns([1, 2])
    with c1:
        asset_type = st.selectbox("Asset type", ["Stock / ETF", "Crypto", "Fiat / FX"], key="market_type")
        default = {"Stock / ETF": "AAPL", "Crypto": "BTC", "Fiat / FX": "USD/EUR"}[asset_type]
        symbol = st.text_input("Symbol", value=default, key="market_symbol")
        analyze = st.button("Analyze market", type="primary", use_container_width=True)

    if analyze:
        try:
            snap = latest_snapshot(symbol, asset_type)
            tech = technical_features(symbol, asset_type)
            risk = risk_report(symbol, asset_type)

            with c2:
                a, b, c, d = st.columns(4)
                a.metric("Price", f"{snap.price:,.4f}")
                b.metric("Daily change", f"{snap.change_pct:+.2f}%")
                c.metric("RSI", f"{tech['rsi14']:.1f}")
                d.metric("Risk", f"{risk['label']} · {risk['score']}/100")

            frame = history(symbol, period="1y", asset_type=asset_type)
            st.line_chart(frame[["Close"]])

            x1, x2, x3, x4 = st.columns(4)
            x1.metric("20-day average", f"{tech['ma20']:,.4f}")
            x2.metric("50-day average", f"{tech['ma50']:,.4f}")
            x3.metric("Volatility", f"{tech['volatility'] * 100:.1f}%")
            x4.metric("Max drawdown", f"{tech['max_drawdown'] * 100:.1f}%")
            st.write("**Risk reasons:** " + "; ".join(risk["reasons"]))
        except Exception as exc:
            st.error(f"Analysis unavailable: {exc}")

with tabs[2]:
    st.subheader("Probability-based forecast")
    c1, c2, c3 = st.columns(3)
    forecast_type = c1.selectbox("Asset type", ["Stock / ETF", "Crypto", "Fiat / FX"], key="forecast_type")
    forecast_symbol = c2.text_input("Symbol or pair", value="BTC" if forecast_type == "Crypto" else "AAPL")
    horizon = c3.slider("Days ahead", 1, 30, 5)

    if st.button("Calculate forecast", type="primary"):
        try:
            result = forecast_market(forecast_symbol, horizon, forecast_type)
            a, b, c, d = st.columns(4)
            a.metric("Current", f"{result.current_price:,.4f}")
            b.metric("Center estimate", f"{result.expected_price:,.4f}")
            c.metric("Probability up", f"{result.probability_up * 100:.1f}%")
            d.metric("Confidence", f"{result.confidence}/100")

            st.markdown(f"### {result.symbol} · {result.trend}")
            st.write(f"**Regime:** {result.market_regime} · **Risk:** {result.risk_level}")
            r1, r2 = st.columns(2)
            r1.metric("Lower range", f"{result.low_range:,.4f}")
            r2.metric("Upper range", f"{result.high_range:,.4f}")
            st.progress(result.confidence / 100)
            st.write(result.explanation)
            st.caption(f"Based on {result.sample_size} daily prices. Markets can move outside this range.")
        except Exception as exc:
            st.error(f"Forecast unavailable: {exc}")

with tabs[3]:
    st.subheader("Fiat currency converter")
    c1, c2, c3 = st.columns(3)
    amount = c1.number_input("Amount", min_value=0.01, value=100.0)
    source = c2.text_input("From", value="USD", max_chars=3).upper()
    target = c3.text_input("To", value="EUR", max_chars=3).upper()

    if st.button("Convert", type="primary"):
        try:
            converted, rate, pair = convert_currency(amount, source, target)
            st.success(f"{amount:,.2f} {source} ≈ {converted:,.2f} {target}")
            st.caption(f"Approximate market rate: 1 {source} = {rate:,.6f} {target} · Pair: {pair}")
        except Exception as exc:
            st.error(f"Conversion unavailable: {exc}")

with tabs[4]:
    st.subheader("Market news and sentiment")
    news_symbol = st.text_input("News search", value="Bitcoin")
    if st.button("Load news"):
        items = get_market_news(news_symbol, 10)
        if not items:
            st.info("No current articles were returned.")
        for item in items:
            st.markdown(f"**{item.headline}**")
            st.caption(f"{item.source} · {item.sentiment} {item.score}/100 · {item.published_at}")
            if item.summary:
                st.write(item.summary[:400])
            if item.url:
                st.markdown(f"[Open article]({item.url})")
            st.divider()

with tabs[5]:
    st.subheader("$10 paper-trading challenge")
    board = st.radio("Board", ["cash", "crypto"], horizontal=True)
    snap = engine.account_snapshot(board)
    a, b, c, d = st.columns(4)
    a.metric("Total value", f"${snap['equity']:.2f}")
    b.metric("Profit / loss", f"${snap['pnl']:+.2f}")
    c.metric("Cash", f"${snap['cash']:.2f}")
    d.metric("Return", f"{snap['return_pct']:.2f}%")

    c1, c2, c3 = st.columns(3)
    if c1.button("Run scan now", use_container_width=True):
        try:
            engine.run_once()
            st.success("Scan complete.")
        except Exception as exc:
            st.error(str(exc))
    enabled_now = engine.enabled(board)
    new_enabled = c2.toggle("Bot enabled", value=enabled_now)
    if new_enabled != enabled_now:
        engine.set_enabled(board, new_enabled)
    if c3.button("Reset this board", use_container_width=True):
        engine.reset_board(board)
        st.success("Board reset.")

    t1, t2, t3, t4, t5 = st.tabs(["Growth", "Positions", "Trades", "Signals", "Health"])
    with t1:
        frame = engine.equity_df(board)
        st.info("No equity history yet.") if frame.empty else st.line_chart(frame.set_index("timestamp")[["equity", "cash", "positions_value"]])
    with t2:
        frame = engine.positions_df(board)
        st.info("No open positions.") if frame.empty else st.dataframe(frame, use_container_width=True, hide_index=True)
    with t3:
        frame = engine.trades_df(board)
        st.info("No trades yet.") if frame.empty else st.dataframe(frame, use_container_width=True, hide_index=True)
    with t4:
        frame = engine.signals_df(board)
        st.info("No signals yet.") if frame.empty else st.dataframe(frame, use_container_width=True, hide_index=True)
    with t5:
        st.dataframe(engine.status_df(), use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Ask the Oracle")
    render_oracle_bot()

with tabs[7]:
    st.subheader("Money basics")
    st.markdown("""
**Crypto:** Digital assets that trade around the clock and can be extremely volatile.

**Fiat currency:** Government-issued money such as USD, EUR, GBP, JPY and MXN.

**ETF:** A basket of assets traded like a stock.

**Volatility:** How sharply price moves. Higher volatility means greater upside and downside.

**Drawdown:** The decline from a prior peak.

**Diversification:** Spreading risk across different assets rather than relying on one outcome.

**Liquidity:** How easily an asset can be bought or sold without heavily moving its price.

**Probability range:** A band of plausible outcomes. It is more honest than claiming one exact future price.

**Safety rule:** Never risk rent, food, transportation, emergency savings or borrowed money.
""")

with tabs[8]:
    st.subheader("System health")
    for item in api_statuses():
        st.write(f"{'✅' if item.configured else '⚠️'} **{item.name}:** {item.purpose}")
    st.dataframe(engine.status_df(), use_container_width=True, hide_index=True)
    st.caption("Checked " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

st.divider()
st.caption(
    "GARIBALDI MARKET ORACLE™ provides educational market analysis and simulated trades only. "
    "No real orders and no guaranteed returns."
)
