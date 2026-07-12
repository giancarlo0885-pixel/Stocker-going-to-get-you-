import math

from market_predictor import Forecast


def test_forecast_dataclass():
    item = Forecast(
        symbol="TEST",
        current_price=10,
        horizon_days=5,
        expected_price=11,
        low_range=8,
        high_range=13,
        probability_up=0.6,
        trend="Mixed",
        market_regime="Range-bound",
        confidence=50,
        risk_level="Moderate",
        explanation="test",
        sample_size=100,
    )
    assert item.low_range < item.expected_price < item.high_range
    assert 0 <= item.probability_up <= 1
    assert 0 <= item.confidence <= 100
