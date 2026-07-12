from __future__ import annotations

from market_data import technical_features


def risk_report(symbol: str, asset_type: str = "Stock / ETF") -> dict:
    tech = technical_features(symbol, asset_type)

    score = 0
    reasons = []

    if tech["volatility"] > 0.60:
        score += 35
        reasons.append("Very high historical volatility")
    elif tech["volatility"] > 0.30:
        score += 20
        reasons.append("Moderate-to-high historical volatility")
    else:
        score += 10
        reasons.append("Lower historical volatility")

    if tech["max_drawdown"] < -0.50:
        score += 30
        reasons.append("History includes a drawdown greater than 50%")
    elif tech["max_drawdown"] < -0.25:
        score += 20
        reasons.append("History includes a drawdown greater than 25%")
    else:
        score += 10

    if tech["rsi14"] > 75 or tech["rsi14"] < 25:
        score += 15
        reasons.append("Momentum is at an extreme")

    if abs(tech["momentum_20"]) > 0.15:
        score += 15
        reasons.append("Price moved rapidly during the last 20 sessions")

    score = min(100, score)
    label = "High" if score >= 65 else "Moderate" if score >= 40 else "Lower"

    return {
        "symbol": tech["symbol"],
        "score": score,
        "label": label,
        "reasons": reasons,
        "volatility": tech["volatility"],
        "max_drawdown": tech["max_drawdown"],
        "rsi14": tech["rsi14"],
    }
