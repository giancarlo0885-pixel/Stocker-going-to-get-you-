"""Transparent 0-100 research confidence scoring."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    score: int
    label: str
    reasons: list[str]


def calculate_confidence(
    *,
    model_probability: float,
    data_quality: float,
    trend_agreement: float,
    news_agreement: float,
    volatility_penalty: float,
) -> ConfidenceResult:
    values = {
        "model_probability": model_probability,
        "data_quality": data_quality,
        "trend_agreement": trend_agreement,
        "news_agreement": news_agreement,
        "volatility_penalty": volatility_penalty,
    }
    for name, value in values.items():
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1.")

    raw = (
        model_probability * 0.35
        + data_quality * 0.25
        + trend_agreement * 0.20
        + news_agreement * 0.10
        + (1 - volatility_penalty) * 0.10
    )
    score = int(round(raw * 100))

    if score >= 80:
        label = "high"
    elif score >= 65:
        label = "moderate"
    elif score >= 50:
        label = "low"
    else:
        label = "very low"

    reasons = [
        f"Model probability: {model_probability:.0%}",
        f"Data quality: {data_quality:.0%}",
        f"Trend agreement: {trend_agreement:.0%}",
        f"News agreement: {news_agreement:.0%}",
        f"Volatility penalty: {volatility_penalty:.0%}",
    ]
    return ConfidenceResult(score=score, label=label, reasons=reasons)
