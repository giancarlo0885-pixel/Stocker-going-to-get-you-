from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import time
from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf


CRYPTO_ALIASES = {
    "BTC": "BTC-USD", "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD", "ETHEREUM": "ETH-USD",
    "SOL": "SOL-USD", "SOLANA": "SOL-USD",
    "XRP": "XRP-USD", "DOGE": "DOGE-USD", "ADA": "ADA-USD",
}

_CACHE: dict[tuple[str, str, str], tuple[float, pd.DataFrame]] = {}
CACHE_SECONDS = 60


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    previous_close: float
    change: float
    change_pct: float
    volume: float
    timestamp: str


def normalize_symbol(symbol: str, asset_type: str | None = None) -> str:
    raw = symbol.strip().upper().replace(" ", "")
    if not raw:
        raise ValueError("Enter a symbol.")

    if asset_type == "Crypto":
        return CRYPTO_ALIASES.get(raw, raw if "-" in raw else f"{raw}-USD")
    if asset_type == "Fiat / FX":
        if raw.endswith("=X"):
            return raw
        if "/" in raw:
            left, right = raw.split("/", 1)
            return f"{left}{right}=X"
        return f"{raw}=X" if len(raw) == 6 else raw
    return CRYPTO_ALIASES.get(raw, raw)


def history(symbol: str, period: str = "1y", interval: str = "1d", asset_type: str | None = None) -> pd.DataFrame:
    normalized = normalize_symbol(symbol, asset_type)
    key = (normalized, period, interval)
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1].copy()

    frame = yf.download(
        normalized,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if frame.empty:
        raise ValueError(f"No market history was returned for {normalized}.")

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [c[0] for c in frame.columns]

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in frame.columns:
            frame[col] = np.nan

    frame = frame[["Open", "High", "Low", "Close", "Volume"]].copy()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame = frame.dropna(subset=["Close"])
    if len(frame) < 2:
        raise ValueError(f"Not enough usable data for {normalized}.")

    _CACHE[key] = (time.time(), frame.copy())
    return frame


def latest_snapshot(symbol: str, asset_type: str | None = None) -> MarketSnapshot:
    normalized = normalize_symbol(symbol, asset_type)
    frame = history(normalized, period="10d", interval="1d")
    close = frame["Close"].dropna()
    price = float(close.iloc[-1])
    previous = float(close.iloc[-2]) if len(close) > 1 else price
    change = price - previous
    volume_series = pd.to_numeric(frame["Volume"], errors="coerce").dropna()

    return MarketSnapshot(
        symbol=normalized,
        price=price,
        previous_close=previous,
        change=change,
        change_pct=(change / previous * 100.0) if previous else 0.0,
        volume=float(volume_series.iloc[-1]) if len(volume_series) else 0.0,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def technical_features(symbol: str, asset_type: str | None = None) -> dict:
    frame = history(symbol, period="2y", interval="1d", asset_type=asset_type)
    close = frame["Close"].dropna()
    returns = np.log(close / close.shift(1)).dropna()
    current = float(close.iloc[-1])

    ma20 = float(close.tail(20).mean())
    ma50 = float(close.tail(50).mean())
    ma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())

    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = -delta.clip(upper=0).rolling(14).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi14 = float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else 50.0

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    rolling_std = close.rolling(20).std()
    bb_upper = ma20 + 2 * float(rolling_std.iloc[-1])
    bb_lower = ma20 - 2 * float(rolling_std.iloc[-1])

    volatility = float(returns.tail(min(252, len(returns))).std(ddof=1) * math.sqrt(252))
    momentum_20 = float(current / close.iloc[-21] - 1) if len(close) > 21 else 0.0
    max_drawdown = float((close / close.cummax() - 1).min())

    return {
        "symbol": normalize_symbol(symbol, asset_type),
        "price": current,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "rsi14": rsi14,
        "macd": float(macd.iloc[-1]),
        "macd_signal": float(macd_signal.iloc[-1]),
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "volatility": volatility,
        "momentum_20": momentum_20,
        "max_drawdown": max_drawdown,
        "history_rows": len(close),
    }


def batch_snapshots(symbols: Iterable[str]) -> list[MarketSnapshot]:
    items = []
    for symbol in symbols:
        try:
            items.append(latest_snapshot(symbol))
        except Exception:
            continue
    return items
