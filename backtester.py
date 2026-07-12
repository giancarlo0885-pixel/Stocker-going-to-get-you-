"""Simple long-only signal backtester for education and paper trading."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass
class BacktestResult:
    starting_cash: float
    ending_value: float
    total_return_pct: float
    trades: int
    max_drawdown_pct: float
    equity_curve: list[float]


def run_backtest(
    close_prices: Iterable[float],
    signals: Iterable[int],
    starting_cash: float = 10.0,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> BacktestResult:
    prices = pd.Series(list(close_prices), dtype="float64")
    signal_series = pd.Series(list(signals), dtype="int64").reindex(prices.index).fillna(0)

    if prices.empty or (prices <= 0).any():
        raise ValueError("close_prices must contain positive values")

    cash = float(starting_cash)
    units = 0.0
    trades = 0
    curve: list[float] = []

    for price, signal in zip(prices, signal_series):
        if signal > 0 and units == 0 and cash > 0:
            fill = price * (1 + slippage_rate)
            units = (cash * (1 - fee_rate)) / fill
            cash = 0.0
            trades += 1
        elif signal < 0 and units > 0:
            fill = price * (1 - slippage_rate)
            cash = units * fill * (1 - fee_rate)
            units = 0.0
            trades += 1
        curve.append(cash + units * price)

    ending = cash + units * float(prices.iloc[-1])
    equity = pd.Series(curve, dtype="float64")
    drawdown = equity / equity.cummax() - 1

    return BacktestResult(
        starting_cash=round(starting_cash, 2),
        ending_value=round(ending, 4),
        total_return_pct=round((ending / starting_cash - 1) * 100, 2),
        trades=trades,
        max_drawdown_pct=round(float(drawdown.min()) * 100, 2),
        equity_curve=[round(float(v), 4) for v in curve],
    )
