from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

import numpy as np

from market_data import history, normalize_symbol, technical_features


@dataclass(frozen=True)
class Forecast:
    symbol: str
    current_price: float
    horizon_days: int
    expected_price: float
    low_range: float
    high_range: float
    probability_up: float
    trend: str
    market_regime: str
    confidence: int
    risk_level: str
    explanation: str
    sample_size: int

    def as_dict(self) -> dict:
        return asdict(self)


def forecast_market(symbol: str, horizon_days: int = 5, asset_type: str = "Stock / ETF") -> Forecast:
    normalized = normalize_symbol(symbol, asset_type)
    close = history(normalized, period="5y", interval="1d")["Close"].dropna()
    if len(close) < 60:
        raise ValueError("At least 60 daily prices are needed for this forecast.")

    horizon_days = max(1, min(int(horizon_days), 90))
    current = float(close.iloc[-1])
    returns = np.log(close / close.shift(1)).dropna()

    recent = returns.tail(min(90, len(returns)))
    weights = np.linspace(0.4, 1.6, len(recent))
    recency_drift = float(np.average(recent.to_numpy(), weights=weights))
    long_drift = float(returns.mean())
    daily_vol = max(float(returns.tail(min(252, len(returns))).std(ddof=1)), 1e-6)

    tech = technical_features(normalized)
    trend_adjustment = 0.0
    if tech["price"] > tech["ma20"] > tech["ma50"]:
        trend_adjustment += 0.0012
    elif tech["price"] < tech["ma20"] < tech["ma50"]:
        trend_adjustment -= 0.0012

    if tech["macd"] > tech["macd_signal"]:
        trend_adjustment += 0.0005
    else:
        trend_adjustment -= 0.0005

    if tech["rsi14"] > 75:
        trend_adjustment -= 0.0007
    elif tech["rsi14"] < 25:
        trend_adjustment += 0.0007

    adjusted_drift = 0.65 * recency_drift + 0.35 * long_drift + trend_adjustment
    expected = current * math.exp(adjusted_drift * horizon_days)

    # 80% statistical interval
    z = 1.2816
    horizon_vol = daily_vol * math.sqrt(horizon_days)
    low = expected * math.exp(-z * horizon_vol)
    high = expected * math.exp(z * horizon_vol)

    score = (adjusted_drift * horizon_days) / horizon_vol if horizon_vol else 0.0
    probability_up = 0.5 * (1 + math.erf(score / math.sqrt(2)))

    trend = (
        "Bullish trend" if tech["price"] > tech["ma20"] > tech["ma50"]
        else "Bearish trend" if tech["price"] < tech["ma20"] < tech["ma50"]
        else "Mixed / sideways trend"
    )
    market_regime = (
        "High-volatility" if tech["volatility"] > 0.60
        else "Trending" if abs(tech["momentum_20"]) > 0.08
        else "Range-bound"
    )
    risk_level = "High" if tech["volatility"] > 0.60 else "Moderate" if tech["volatility"] > 0.30 else "Lower"

    signal_strength = min(
        1.0,
        abs(probability_up - 0.5) * 2
        + min(abs(tech["momentum_20"]), 0.20)
        + min(abs(tech["macd"] - tech["macd_signal"]) / max(current, 1e-9), 0.10),
    )
    data_strength = min(1.0, len(close) / 750)
    confidence = int(max(25, min(90, round(35 + 35 * signal_strength + 20 * data_strength))))

    direction = "upward" if expected >= current else "downward"
    explanation = (
        f"The model estimates a {direction} bias over {horizon_days} day(s). "
        f"It blends recency-weighted and long-term returns, volatility, RSI, MACD, "
        f"20/50-day trend alignment, and market regime. The range is more important "
        f"than the exact target because unexpected events can overwhelm historical patterns."
    )

    return Forecast(
        symbol=normalized,
        current_price=current,
        horizon_days=horizon_days,
        expected_price=expected,
        low_range=low,
        high_range=high,
        probability_up=probability_up,
        trend=trend,
        market_regime=market_regime,
        confidence=confidence,
        risk_level=risk_level,
        explanation=explanation,
        sample_size=len(close),
    )


def convert_currency(amount: float, from_currency: str, to_currency: str) -> tuple[float, float, str]:
    source = from_currency.strip().upper()
    target = to_currency.strip().upper()
    if len(source) != 3 or len(target) != 3:
        raise ValueError("Use three-letter currency codes, such as USD and EUR.")
    if source == target:
        return float(amount), 1.0, f"{source}/{target}"

    direct = f"{source}{target}=X"
    try:
        rate = float(history(direct, period="1mo")["Close"].iloc[-1])
        return float(amount) * rate, rate, direct
    except Exception:
        inverse = f"{target}{source}=X"
        inverse_rate = float(history(inverse, period="1mo")["Close"].iloc[-1])
        if inverse_rate <= 0:
            raise ValueError("Currency rate unavailable.")
        rate = 1.0 / inverse_rate
        return float(amount) * rate, rate, inverse
