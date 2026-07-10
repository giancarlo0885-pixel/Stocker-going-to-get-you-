from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from engine import *
from news_intelligence import combined_regime

st.set_page_config(page_title="Garibaldi Market Oracle — $10 Challenge", page_icon="💹", layout="wide")
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 20% 10%,rgba(40,120,70,.15),transparent 30%),radial-gradient(circle at 80% 10%,rgba(120,70,160,.16),transparent 30%)}
.title{text-align:center;font-weight:900;letter-spacing:.08em;font-size:clamp(1.6rem,4vw,3.2rem)}
.sub{text-align:center;opacity:.8;margin-bottom:1rem}.board{border:1px solid rgba(255,255,255,.18);border-radius:18px;padding:1rem;background:rgba(20,20,25,.55);min-height:280px}
.cash{box-shadow:-10px 0 40px rgba(40,170,90,.12)}.crypto{box-shadow:10px 0 40px rgba(155,90,220,.14)}.vs{text-align:center;font-size:2rem;font-weight:900;padding-top:5rem}
@media(max-width:800px){.vs{padding-top:.5rem}}
</style>
""", unsafe_allow_html=True)

init_db(); start_background_bot()
st.markdown('<div class="title">GARIBALDI MARKET ORACLE™</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">$10 CHALLENGE · CASH MARKET vs CRYPTO · SIMULATED TRADING PIT</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Control room")
    if st.button("Run both scans now", width="stretch"):
        run_once(); st.success("Both boards scanned."); st.rerun()
    cv=st.toggle("Cash board bot", value=enabled("cash")); kv=st.toggle("Crypto board bot", value=enabled("crypto"))
    if cv != enabled("cash"): set_enabled("cash",cv); st.rerun()
    if kv != enabled("crypto"): set_enabled("crypto",kv); st.rerun()
    st.caption(f"Scan interval: about {SCAN_SECONDS//60} minute(s)")
    with st.expander("Reset the challenge"):
        rc=st.checkbox("Reset cash board"); rk=st.checkbox("Reset crypto board")
        if st.button("Reset selected boards", width="stretch"):
            if rc: reset_board("cash")
            if rk: reset_board("crypto")
            st.success("Selected boards reset to $10."); st.rerun()

cs=account_snapshot("cash"); ks=account_snapshot("crypto")
l,m,r=st.columns([1,.18,1])
with l:
    st.markdown('<div class="board cash">', unsafe_allow_html=True); st.markdown("## 💵 CASH MARKET PIT"); st.caption("Stocks · ETFs · gold · bonds · dollar · FX")
    a,b=st.columns(2); a.metric("Equity",f"${cs['equity']:.2f}",f"${cs['pnl']:+.2f}"); b.metric("Return",f"{cs['return_pct']:.2f}%",f"DD {cs['drawdown_pct']:.2f}%")
    a,b=st.columns(2); a.metric("Cash",f"${cs['cash']:.2f}"); b.metric("Positions",f"${cs['positions_value']:.2f}")
    rg=combined_regime("cash"); st.write(f"**News regime:** {rg.label} ({rg.score:+.2f})"); st.caption(rg.explanation); st.markdown("</div>",unsafe_allow_html=True)
with m: st.markdown('<div class="vs">VS</div>',unsafe_allow_html=True)
with r:
    st.markdown('<div class="board crypto">', unsafe_allow_html=True); st.markdown("## 🪙 CRYPTO PIT"); st.caption("Bitcoin · Ethereum · Solana · XRP · Dogecoin")
    a,b=st.columns(2); a.metric("Equity",f"${ks['equity']:.2f}",f"${ks['pnl']:+.2f}"); b.metric("Return",f"{ks['return_pct']:.2f}%",f"DD {ks['drawdown_pct']:.2f}%")
    a,b=st.columns(2); a.metric("Cash",f"${ks['cash']:.2f}"); b.metric("Positions",f"${ks['positions_value']:.2f}")
    rg=combined_regime("crypto"); st.write(f"**News regime:** {rg.label} ({rg.score:+.2f})"); st.caption(rg.explanation); st.markdown("</div>",unsafe_allow_html=True)

st.info("Each side begins with $10 in fake money. Fractional shares and crypto are allowed. Cash-market fills occur only during regular U.S. market hours; crypto can trade 24/7.")
board=st.radio("Inspect a board",["Cash","Crypto"],horizontal=True).lower()
tabs=st.tabs(["Equity curve","Open positions","Paper trades","Live decisions","Market intelligence","Literacy lab","Bot health"])
with tabs[0]:
    x=equity_df(board)
    if x.empty: st.write("No equity-history points yet. Run a scan or wait for the bot.")
    else:
        x["timestamp"]=pd.to_datetime(x["timestamp"],errors="coerce")
        st.line_chart(x.dropna(subset=["timestamp"]).set_index("timestamp")[["equity","cash","positions_value"]],width="stretch")
with tabs[1]:
    x=positions_df(board); st.write("No open simulated positions." if x.empty else "")
    if not x.empty: st.dataframe(x,width="stretch",hide_index=True)
with tabs[2]:
    x=trades_df(board); st.write("No simulated fills yet." if x.empty else "")
    if not x.empty:
        st.dataframe(x,width="stretch",hide_index=True)
        st.download_button("Download trade history CSV",x.to_csv(index=False).encode(),file_name=f"{board}_10_dollar_trades.csv",mime="text/csv")
with tabs[3]:
    x=signals_df(board); st.write("No decisions logged yet." if x.empty else "")
    if not x.empty: st.dataframe(x,width="stretch",hide_index=True)
with tabs[4]:
    rg=combined_regime(board); st.metric("Current headline regime",rg.label,f"{rg.score:+.2f}"); st.write(rg.explanation)
    if rg.headlines.empty: st.write("Current headlines could not be retrieved.")
    else:
        for _,row in rg.headlines.head(12).iterrows():
            st.markdown(f"**{row['title']}**"); st.caption(f"{row['source']} · {row['published']}")
            if row["link"]: st.link_button("Open source",row["link"])
with tabs[5]:
    st.subheader("Financial literacy before prediction")
    st.markdown("""**Five principles:** liquidity first; fractional sizing; regime awareness; central-bank literacy; and evidence over mythology.

*The Creature from Jekyll Island* raises influential criticisms of central banking and concentrated financial power. Some historical events it discusses are real, while several broader claims are disputed. This app uses the useful questions—who supplies liquidity, who bears risk, and how policy changes incentives—without treating disputed conclusions as facts.

The algorithm combines trend, momentum, RSI, volatility, headline regime, stop loss, take profit, trailing stop, slippage, position limits, and fractional sizing. It does not know the future.""")
with tabs[6]:
    st.dataframe(status_df(),width="stretch",hide_index=True)
    st.caption("Refreshed "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

st.divider(); st.caption("Educational paper trading only. No real broker orders. No guarantee of profit or of turning $10 into wealth. Public market data and RSS feeds can be delayed or unavailable.")
