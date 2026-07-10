from __future__ import annotations
import numpy as np
import pandas as pd
import requests
try:
    import yfinance as yf
except Exception:
    yf = None

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 GaribaldiMarketOracle/2.0"})
BINANCE = {"BTC-USD":"BTCUSDT","ETH-USD":"ETHUSDT","SOL-USD":"SOLUSDT","XRP-USD":"XRPUSDT","DOGE-USD":"DOGEUSDT"}
COINGECKO = {"BTC-USD":"bitcoin","ETH-USD":"ethereum","SOL-USD":"solana","XRP-USD":"ripple","DOGE-USD":"dogecoin"}

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = x.columns.get_level_values(0)
    x = x.rename(columns={"Adj Close":"Close"})
    for c in ("Open","High","Low","Close","Volume"):
        if c not in x.columns:
            x[c] = np.nan
        x[c] = pd.to_numeric(x[c], errors="coerce")
    return x.dropna(subset=["Close"])[["Open","High","Low","Close","Volume"]]

def yahoo_chart(symbol: str) -> pd.DataFrame:
    r = SESSION.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", params={"range":"5d","interval":"15m","includePrePost":"true"}, timeout=15)
    r.raise_for_status()
    result = r.json().get("chart",{}).get("result") or []
    if not result:
        return pd.DataFrame()
    item = result[0]
    ts = item.get("timestamp") or []
    q = (item.get("indicators",{}).get("quote") or [{}])[0]
    if not ts:
        return pd.DataFrame()
    n = len(ts)
    def pad(v):
        v = v or []
        return (list(v) + [None]*n)[:n]
    return normalize(pd.DataFrame({
        "Datetime":pd.to_datetime(ts, unit="s", utc=True),
        "Open":pad(q.get("open")),"High":pad(q.get("high")),"Low":pad(q.get("low")),"Close":pad(q.get("close")),"Volume":pad(q.get("volume"))
    }).set_index("Datetime"))

def binance(symbol: str) -> pd.DataFrame:
    pair = BINANCE.get(symbol)
    if not pair:
        return pd.DataFrame()
    r = SESSION.get("https://api.binance.us/api/v3/klines", params={"symbol":pair,"interval":"15m","limit":500}, timeout=15)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return pd.DataFrame()
    cols = ["open_time","Open","High","Low","Close","Volume","close_time","quote_volume","trades","taker_base","taker_quote","ignore"]
    x = pd.DataFrame(rows, columns=cols)
    x["Datetime"] = pd.to_datetime(x["open_time"], unit="ms", utc=True)
    return normalize(x.set_index("Datetime"))

def coingecko(symbol: str) -> pd.DataFrame:
    coin = COINGECKO.get(symbol)
    if not coin:
        return pd.DataFrame()
    r = SESSION.get(f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart", params={"vs_currency":"usd","days":5}, timeout=15)
    r.raise_for_status()
    prices = r.json().get("prices") or []
    if not prices:
        return pd.DataFrame()
    x = pd.DataFrame(prices, columns=["ms","Close"])
    x["Datetime"] = pd.to_datetime(x["ms"], unit="ms", utc=True)
    x["Open"] = x["High"] = x["Low"] = x["Close"]
    x["Volume"] = np.nan
    return normalize(x.set_index("Datetime"))

def load_history(symbol: str, market: str):
    providers = []
    if yf is not None:
        providers.append(("Yahoo Finance", lambda: yf.download(symbol, period="5d", interval="15m", auto_adjust=True, progress=False, threads=False, prepost=True)))
    providers.append(("Yahoo Chart API", lambda: yahoo_chart(symbol)))
    if market == "crypto":
        providers += [("Binance.US", lambda: binance(symbol)), ("CoinGecko", lambda: coingecko(symbol))]
    errors = []
    for name, fn in providers:
        try:
            x = normalize(fn())
            if len(x) >= 30:
                return x, name
            errors.append(f"{name}: insufficient data")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
    return pd.DataFrame(), " | ".join(errors)
