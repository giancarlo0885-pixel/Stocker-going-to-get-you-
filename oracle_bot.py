from __future__ import annotations

from typing import Optional

import streamlit as st

from config import settings
from market_data import latest_snapshot, technical_features
from news_intelligence import aggregate_news_sentiment
from risk_engine import risk_report

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def _market_context(symbol: str) -> str:
    snapshot = latest_snapshot(symbol)
    tech = technical_features(symbol)
    news = aggregate_news_sentiment(symbol, limit=6)
    risk = risk_report(symbol)

    trend = (
        "bullish" if tech["price"] > tech["ma20"] > tech["ma50"]
        else "bearish" if tech["price"] < tech["ma20"] < tech["ma50"]
        else "mixed"
    )

    return (
        f"{snapshot.symbol} price: {snapshot.price:,.4f}. Daily change: {snapshot.change_pct:.2f}%. "
        f"Trend: {trend}. RSI: {tech['rsi14']:.1f}. "
        f"20-day momentum: {tech['momentum_20'] * 100:.2f}%. "
        f"Annualized volatility: {tech['volatility'] * 100:.1f}%. "
        f"News sentiment: {news['sentiment']} ({news['score']}/100). "
        f"Risk: {risk['label']} ({risk['score']}/100)."
    )


def _ai_answer(question: str, context: str) -> Optional[str]:
    if not settings.openai_api_key or OpenAI is None:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are GARIBALDI MARKET ORACLE. Explain stocks, crypto, ETFs and fiat currency "
                    "in plain language. Clearly label uncertainty. Never guarantee profit. Never tell users "
                    "to risk rent, food, transportation, emergency money, or borrowed money."
                ),
            },
            {
                "role": "user",
                "content": f"Market context:\n{context}\n\nQuestion:\n{question}",
            },
        ],
    )
    return response.output_text.strip()


def render_oracle_bot() -> None:
    symbol = st.text_input("Asset symbol", value="BTC")
    question = st.text_area(
        "Your question",
        value="What is the trend, what could go wrong, and what should a beginner understand?",
    )
    if st.button("Ask Oracle", type="primary"):
        try:
            context = _market_context(symbol)
            answer = _ai_answer(question, context)
            st.markdown("### Oracle response")
            st.write(answer or context)
            if not answer:
                st.caption("Add OPENAI_API_KEY in Railway to enable expanded AI explanations.")
        except Exception as exc:
            st.error(f"Oracle analysis unavailable: {exc}")
