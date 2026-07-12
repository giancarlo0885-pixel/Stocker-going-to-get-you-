"""Market regime classifier using trend and volatility."""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def classify_regime(close_prices: Iterable[float]) -> dict[str, float | str]:
    close = pd.Series(list(close_prices), dtype="float64").dropna()
    if len(close) < 30:
        return {"regime": "insufficient_data", "trend_pct": 0.0, "volatility_pct": 0.0}

    short = close.rolling(10).mean().iloc[-1]
    long = close.rolling(30).mean().iloc[-1]
    trend = short / long - 1
    volatility = close.pct_change().tail(20).std(ddof=0)

    if trend > 0.02 and volatility < 0.03:
        regime = "bull_trend"
    elif trend < -0.02 and volatility < 0.03:
        regime = "bear_trend"
    elif volatility >= 0.03:
        regime = "high_volatility"
    else:
        regime = "sideways"

    return {
        "regime": regime,
        "trend_pct": round(float(trend) * 100, 2),
        "volatility_pct": round(float(volatility) * 100, 2),
    }
