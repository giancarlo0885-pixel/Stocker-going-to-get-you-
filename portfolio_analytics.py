"""Portfolio performance metrics for simulated trades."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd


def equity_metrics(equity_values: Iterable[float], periods_per_year: int = 252) -> dict[str, float]:
    values = pd.Series(list(equity_values), dtype="float64").dropna()
    if len(values) < 2 or (values <= 0).any():
        return {
            "total_return_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
        }

    returns = values.pct_change().dropna()
    total_return = values.iloc[-1] / values.iloc[0] - 1
    volatility = float(returns.std(ddof=0) * math.sqrt(periods_per_year))
    running_peak = values.cummax()
    drawdown = values / running_peak - 1
    max_drawdown = float(drawdown.min())

    std = float(returns.std(ddof=0))
    sharpe = float((returns.mean() / std) * math.sqrt(periods_per_year)) if std > 0 else 0.0

    return {
        "total_return_pct": round(total_return * 100, 2),
        "annualized_volatility_pct": round(volatility * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
    }


def trade_metrics(profits: Iterable[float]) -> dict[str, float]:
    pnl = np.asarray(list(profits), dtype=float)
    if pnl.size == 0:
        return {
            "trades": 0,
            "win_rate_pct": 0.0,
            "average_profit": 0.0,
            "profit_factor": 0.0,
        }

    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = abs(float(losses.sum())) if losses.size else 0.0

    return {
        "trades": int(pnl.size),
        "win_rate_pct": round(float((pnl > 0).mean() * 100), 2),
        "average_profit": round(float(pnl.mean()), 4),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
    }
