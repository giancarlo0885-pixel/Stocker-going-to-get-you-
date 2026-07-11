from __future__ import annotations

"""
GARIBALDI MARKET ORACLE - Ask the Oracle bot

Drop this file in the same GitHub repository folder as:
    app.py, engine.py, market_data.py, news_intelligence.py

This module analyzes one stock/ETF/forex/crypto symbol at a time.
It does NOT place real or paper trades.
"""

import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from engine import compute_signal
from market_data import load_history
from news_intelligence import combined_regime


CRYPTO_ALIASES = {
    "BTC": "BTC-USD",
    "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD",
    "ETHEREUM": "ETH-USD",
    "SOL": "SOL-USD",
    "SOLANA": "SOL-USD",
    "XRP": "XRP-USD",
    "DOGE": "DOGE-USD",
    "DOGECOIN": "DOGE-USD",
    "ADA": "ADA-USD",
    "CARDANO": "ADA-USD",
    "AVAX": "AVAX-USD",
}


@dataclass
class OracleReport:
    symbol: str
    board: str
    source: str
    price: float
    action: str
    rating: str
    confidence: float
    risk: str
    score: float
    rsi: float
    momentum_8d: float
    volatility_30d: float
    ema8: float
    ema21: float
    ema55: float
    entry_low: float
    entry_high: float
    stop: float
    target_1: float
    target_2: float
    news_label: str
    news_score: float
    explanation: str
    history: pd.DataFrame
    headlines: pd.DataFrame


def normalize_symbol(raw: str) -> tuple[str, str]:
    """Clean a user-entered ticker and determine cash or crypto board."""
    cleaned = re.sub(r"[^A-Za-z0-9=.\-^]", "", (raw or "").strip().upper())
    if not cleaned:
        raise ValueError("Enter a ticker such as AAPL, NVDA, RKLB, BTC, or ETH.")

    symbol = CRYPTO_ALIASES.get(cleaned, cleaned)
    board = "crypto" if symbol.endswith("-USD") else "cash"
    return symbol, board


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def _indicators(frame: pd.DataFrame) -> dict[str, float]:
    close = frame["Close"].dropna().astype(float)
    if len(close) < 35:
        raise ValueError("Not enough price history was returned for this symbol.")

    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = _safe_float((100 - 100 / (1 + rs)).iloc[-1], 50.0)

    daily_returns = close.pct_change()
    return {
        "price": _safe_float(close.iloc[-1]),
        "ema8": _safe_float(close.ewm(span=8, adjust=False).mean().iloc[-1]),
        "ema21": _safe_float(close.ewm(span=21, adjust=False).mean().iloc[-1]),
        "ema55": _safe_float(close.ewm(span=55, adjust=False).mean().iloc[-1]),
        "rsi": rsi,
        "momentum": _safe_float(close.pct_change(8).iloc[-1]),
        "volatility": max(0.0, _safe_float(daily_returns.rolling(30).std().iloc[-1])),
    }


def _rating(action: str, score: float, confidence: float, rsi: float) -> str:
    if action == "BUY":
        if confidence >= 65 and score >= 0.42 and rsi < 70:
            return "STRONG WATCH / POSSIBLE BUY"
        return "CAUTIOUS BUY"
    if action == "SELL":
        return "AVOID / EXIT SIGNAL"
    if score >= 0.12:
        return "WATCH FOR A BETTER ENTRY"
    if score <= -0.12:
        return "WEAK / WAIT"
    return "NEUTRAL / WAIT"


def _risk_label(volatility: float, rsi: float, board: str) -> str:
    annualized = volatility * math.sqrt(365 if board == "crypto" else 252)
    if annualized >= 0.65 or rsi >= 78:
        return "VERY HIGH"
    if annualized >= 0.42 or rsi >= 72:
        return "HIGH"
    if annualized >= 0.24:
        return "MODERATE"
    return "LOWER"


def analyze_asset(raw_symbol: str, question: str = "") -> OracleReport:
    """Run the existing Oracle engine against a user-selected asset."""
    symbol, board = normalize_symbol(raw_symbol)
    frame, source = load_history(symbol, board)

    if frame is None or frame.empty or "Close" not in frame.columns:
        raise ValueError(
            f"No usable market data was returned for {symbol}. "
            "Check the ticker and try again."
        )

    indicators = _indicators(frame)

    # Symbol-specific Google News RSS analysis.
    news = combined_regime(symbol)
    engine_result = compute_signal(frame, news.score)

    price = indicators["price"]
    volatility = indicators["volatility"]
    # Practical zones based on recent daily volatility, with sensible floors/caps.
    move = price * min(0.12, max(0.012, volatility * 1.6))
    entry_low = max(0.0, price - move * 0.45)
    entry_high = price + move * 0.15
    stop = max(0.0, price - move * 1.35)
    target_1 = price + move * 1.20
    target_2 = price + move * 2.20

    action = str(engine_result.get("action", "HOLD")).upper()
    score = _safe_float(engine_result.get("score"))
    confidence = _safe_float(engine_result.get("confidence"))
    rating = _rating(action, score, confidence, indicators["rsi"])
    risk = _risk_label(volatility, indicators["rsi"], board)

    trend_text = (
        "bullish"
        if indicators["ema8"] > indicators["ema21"] > indicators["ema55"]
        else "bearish"
        if indicators["ema8"] < indicators["ema21"] < indicators["ema55"]
        else "mixed"
    )

    explanation = (
        f"{symbol} has a {trend_text} moving-average structure. "
        f"RSI is {indicators['rsi']:.1f}, 8-period momentum is "
        f"{indicators['momentum']:+.2%}, and recent daily volatility is "
        f"{volatility:.2%}. The headline regime is {news.label.lower()} "
        f"({news.score:+.2f}). The engine currently returns {action} with "
        f"{confidence:.0f}% signal confidence. Price zones are estimates, "
        f"not guarantees."
    )

    return OracleReport(
        symbol=symbol,
        board=board,
        source=str(source),
        price=price,
        action=action,
        rating=rating,
        confidence=confidence,
        risk=risk,
        score=score,
        rsi=indicators["rsi"],
        momentum_8d=indicators["momentum"],
        volatility_30d=volatility,
        ema8=indicators["ema8"],
        ema21=indicators["ema21"],
        ema55=indicators["ema55"],
        entry_low=entry_low,
        entry_high=entry_high,
        stop=stop,
        target_1=target_1,
        target_2=target_2,
        news_label=news.label,
        news_score=news.score,
        explanation=explanation,
        history=frame.copy(),
        headlines=news.headlines.copy(),
    )


def render_oracle_bot() -> None:
    """Streamlit interface. Call this inside an app.py tab."""
    st.subheader("Ask the Oracle")
    st.caption(
        "Research a stock, ETF, forex pair, or cryptocurrency using the "
        "existing trend, momentum, RSI, volatility, and headline engine."
    )

    symbol = st.text_input(
        "Ticker or crypto",
        placeholder="Examples: AAPL, NVDA, RKLB, SPY, BTC, ETH",
        key="oracle_symbol",
    )
    question = st.text_area(
        "What do you want to know?",
        value="Is this a good buy right now?",
        key="oracle_question",
    )

    if not st.button("Analyze investment", type="primary", width="stretch"):
        return

    try:
        with st.spinner("Oracle is checking price action and headlines..."):
            report = analyze_asset(symbol, question)
    except Exception as exc:
        st.error(str(exc))
        return

    st.markdown(f"## {report.symbol}: {report.rating}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current price", f"${report.price:,.4f}")
    c2.metric("Engine action", report.action)
    c3.metric("Confidence", f"{report.confidence:.0f}%")
    c4.metric("Risk", report.risk)

    st.progress(min(100, max(0, int(round(report.confidence)))))
    st.write(report.explanation)

    z1, z2, z3 = st.columns(3)
    z1.metric("Possible entry zone", f"${report.entry_low:,.4f}–${report.entry_high:,.4f}")
    z2.metric("Risk limit", f"${report.stop:,.4f}")
    z3.metric("Targets", f"${report.target_1:,.4f} / ${report.target_2:,.4f}")

    with st.expander("Technical evidence", expanded=True):
        evidence = pd.DataFrame(
            {
                "Indicator": [
                    "EMA 8",
                    "EMA 21",
                    "EMA 55",
                    "RSI 14",
                    "8-period momentum",
                    "30-period daily volatility",
                    "News score",
                    "Engine score",
                ],
                "Value": [
                    f"{report.ema8:,.4f}",
                    f"{report.ema21:,.4f}",
                    f"{report.ema55:,.4f}",
                    f"{report.rsi:.1f}",
                    f"{report.momentum_8d:+.2%}",
                    f"{report.volatility_30d:.2%}",
                    f"{report.news_score:+.2f} ({report.news_label})",
                    f"{report.score:+.3f}",
                ],
            }
        )
        st.dataframe(evidence, width="stretch", hide_index=True)

    history = report.history.copy()
    if not history.empty:
        if isinstance(history.index, pd.DatetimeIndex):
            chart = history[["Close"]].dropna().tail(180)
        else:
            chart = history[["Close"]].dropna().tail(180)
        st.line_chart(chart, width="stretch")

    st.markdown("### Recent headlines")
    if report.headlines.empty:
        st.info("No current symbol-specific headlines were available.")
    else:
        for _, row in report.headlines.head(8).iterrows():
            st.markdown(f"**{row.get('title', '')}**")
            st.caption(
                f"{row.get('source', 'Google News')} · "
                f"{row.get('published', '')}"
            )
            link = str(row.get("link", "") or "")
            if link:
                st.link_button("Open source", link)

    st.warning(
        "Educational research and simulated trading only. This rating is not "
        "personalized financial advice and does not guarantee a profit."
    )
