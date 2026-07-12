from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from config import settings
from db import dataframe, execute, fetch_all, fetch_one, init_db as _init_db
from market_data import latest_snapshot, technical_features
from news_intelligence import aggregate_news_sentiment


DB_PATH = settings.sqlite_path
SCAN_SECONDS = settings.scan_seconds
WATCHLISTS = {
    "cash": list(settings.cash_watchlist),
    "crypto": list(settings.crypto_watchlist),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    _init_db()
    for board in ("cash", "crypto"):
        execute(
            "INSERT INTO settings(board, enabled) VALUES (:board, 1) "
            "ON CONFLICT(board) DO NOTHING",
            {"board": board},
        )
        execute(
            "INSERT INTO accounts(board, cash, starting_cash) VALUES (:board, :cash, :cash) "
            "ON CONFLICT(board) DO NOTHING",
            {"board": board, "cash": settings.starting_paper_cash},
        )
        execute(
            "INSERT INTO bot_status(board, last_run, last_error, scan_count) "
            "VALUES (:board, NULL, NULL, 0) ON CONFLICT(board) DO NOTHING",
            {"board": board},
        )


def enabled(board: str) -> bool:
    init_db()
    row = fetch_one("SELECT enabled FROM settings WHERE board=:board", {"board": board})
    return bool(row["enabled"]) if row else False


def set_enabled(board: str, value: bool) -> None:
    init_db()
    execute(
        "INSERT INTO settings(board, enabled) VALUES (:board, :enabled) "
        "ON CONFLICT(board) DO UPDATE SET enabled=:enabled",
        {"board": board, "enabled": int(value)},
    )


def _cash(board: str) -> float:
    row = fetch_one("SELECT cash FROM accounts WHERE board=:board", {"board": board})
    return float(row["cash"]) if row else 0.0


def _positions(board: str) -> list[dict]:
    return fetch_all("SELECT * FROM positions WHERE board=:board", {"board": board})


def _signal(symbol: str) -> tuple[str, float, int, str, float]:
    snap = latest_snapshot(symbol)
    tech = technical_features(symbol)
    news = aggregate_news_sentiment(symbol, limit=5)

    score = 0.0
    reasons = []

    score += 1.0 if tech["price"] > tech["ma20"] else -1.0
    reasons.append("price above 20-day average" if tech["price"] > tech["ma20"] else "price below 20-day average")

    score += 1.0 if tech["ma20"] > tech["ma50"] else -1.0
    reasons.append("short trend above medium trend" if tech["ma20"] > tech["ma50"] else "short trend below medium trend")

    score += 0.75 if tech["momentum_20"] > 0 else -0.75
    if tech["macd"] > tech["macd_signal"]:
        score += 0.5
        reasons.append("MACD momentum positive")
    else:
        score -= 0.5
        reasons.append("MACD momentum negative")

    if tech["rsi14"] < 30:
        score += 0.5
        reasons.append("RSI oversold")
    elif tech["rsi14"] > 70:
        score -= 0.5
        reasons.append("RSI overbought")

    score += (news["score"] - 50) / 25.0
    reasons.append(f"news sentiment {news['sentiment'].lower()}")

    action = (
        "BUY" if score >= settings.buy_score_threshold
        else "SELL" if score <= settings.sell_score_threshold
        else "HOLD"
    )
    confidence = int(max(25, min(90, 50 + abs(score) * 8)))
    return action, score, confidence, "; ".join(reasons), snap.price


def _record_signal(board: str, symbol: str, action: str, score: float, confidence: int, price: float, reason: str) -> None:
    execute(
        "INSERT INTO signals(board, symbol, action, score, confidence, price, reason, timestamp) "
        "VALUES (:board, :symbol, :action, :score, :confidence, :price, :reason, :timestamp)",
        {
            "board": board, "symbol": symbol, "action": action, "score": score,
            "confidence": confidence, "price": price, "reason": reason, "timestamp": _now(),
        },
    )


def _buy(board: str, symbol: str, price: float, reason: str) -> None:
    if price <= 0:
        return

    cash = _cash(board)
    if cash < 1:
        return

    count = fetch_one(
        "SELECT COUNT(*) AS count FROM positions WHERE board=:board",
        {"board": board},
    )
    existing = fetch_one(
        "SELECT quantity, average_price FROM positions WHERE board=:board AND symbol=:symbol",
        {"board": board, "symbol": symbol},
    )
    if not existing and int(count["count"]) >= settings.max_open_positions:
        return

    spend = min(cash, max(1.0, cash * settings.max_position_pct))
    quantity = spend / price

    if existing:
        old_qty = float(existing["quantity"])
        old_avg = float(existing["average_price"])
        new_qty = old_qty + quantity
        new_avg = ((old_qty * old_avg) + spend) / new_qty
        execute(
            "UPDATE positions SET quantity=:quantity, average_price=:average_price, updated_at=:updated_at "
            "WHERE board=:board AND symbol=:symbol",
            {
                "quantity": new_qty, "average_price": new_avg, "updated_at": _now(),
                "board": board, "symbol": symbol,
            },
        )
    else:
        execute(
            "INSERT INTO positions(board, symbol, quantity, average_price, updated_at) "
            "VALUES (:board, :symbol, :quantity, :average_price, :updated_at)",
            {
                "board": board, "symbol": symbol, "quantity": quantity,
                "average_price": price, "updated_at": _now(),
            },
        )

    execute("UPDATE accounts SET cash=cash-:spend WHERE board=:board", {"spend": spend, "board": board})
    execute(
        "INSERT INTO trades(board, symbol, side, quantity, price, value, reason, timestamp) "
        "VALUES (:board, :symbol, 'BUY', :quantity, :price, :value, :reason, :timestamp)",
        {
            "board": board, "symbol": symbol, "quantity": quantity, "price": price,
            "value": spend, "reason": reason, "timestamp": _now(),
        },
    )


def _sell(board: str, symbol: str, price: float, reason: str) -> None:
    position = fetch_one(
        "SELECT quantity FROM positions WHERE board=:board AND symbol=:symbol",
        {"board": board, "symbol": symbol},
    )
    if not position:
        return

    quantity = float(position["quantity"])
    value = quantity * price
    execute("DELETE FROM positions WHERE board=:board AND symbol=:symbol", {"board": board, "symbol": symbol})
    execute("UPDATE accounts SET cash=cash+:value WHERE board=:board", {"value": value, "board": board})
    execute(
        "INSERT INTO trades(board, symbol, side, quantity, price, value, reason, timestamp) "
        "VALUES (:board, :symbol, 'SELL', :quantity, :price, :value, :reason, :timestamp)",
        {
            "board": board, "symbol": symbol, "quantity": quantity, "price": price,
            "value": value, "reason": reason, "timestamp": _now(),
        },
    )


def _record_equity(board: str) -> None:
    cash = _cash(board)
    positions_value = 0.0
    for row in _positions(board):
        try:
            price = latest_snapshot(row["symbol"]).price
        except Exception:
            price = float(row["average_price"])
        positions_value += float(row["quantity"]) * price

    execute(
        "INSERT INTO equity(board, equity, cash, positions_value, timestamp) "
        "VALUES (:board, :equity, :cash, :positions_value, :timestamp)",
        {
            "board": board, "equity": cash + positions_value, "cash": cash,
            "positions_value": positions_value, "timestamp": _now(),
        },
    )


def _run_board(board: str) -> None:
    if not enabled(board):
        return

    error = None
    try:
        for symbol in WATCHLISTS.get(board, []):
            action, score, confidence, reason, price = _signal(symbol)
            _record_signal(board, symbol, action, score, confidence, price, reason)
            if action == "BUY":
                _buy(board, symbol, price, reason)
            elif action == "SELL":
                _sell(board, symbol, price, reason)
        _record_equity(board)
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        execute(
            "UPDATE bot_status SET last_run=:last_run, last_error=:last_error, scan_count=scan_count+1 "
            "WHERE board=:board",
            {"last_run": _now(), "last_error": error, "board": board},
        )


def run_once() -> None:
    init_db()
    errors = []
    for board in ("cash", "crypto"):
        try:
            _run_board(board)
        except Exception as exc:
            errors.append(f"{board}: {exc}")
    if errors:
        raise RuntimeError(" | ".join(errors))


def account_snapshot(board: str) -> dict:
    init_db()
    cash = _cash(board)
    positions_value = 0.0
    for row in _positions(board):
        try:
            price = latest_snapshot(row["symbol"]).price
        except Exception:
            price = float(row["average_price"])
        positions_value += float(row["quantity"]) * price

    row = fetch_one("SELECT starting_cash FROM accounts WHERE board=:board", {"board": board})
    starting = float(row["starting_cash"]) if row else settings.starting_paper_cash
    equity = cash + positions_value
    pnl = equity - starting
    return {
        "cash": cash,
        "positions_value": positions_value,
        "equity": equity,
        "pnl": pnl,
        "return_pct": (pnl / starting * 100) if starting else 0.0,
    }


def reset_board(board: str) -> None:
    init_db()
    execute("DELETE FROM positions WHERE board=:board", {"board": board})
    execute("DELETE FROM trades WHERE board=:board", {"board": board})
    execute("DELETE FROM signals WHERE board=:board", {"board": board})
    execute("DELETE FROM equity WHERE board=:board", {"board": board})
    execute("UPDATE accounts SET cash=starting_cash WHERE board=:board", {"board": board})


def equity_df(board: str) -> pd.DataFrame:
    return dataframe(
        "SELECT timestamp, equity, cash, positions_value FROM equity WHERE board=:board ORDER BY id",
        {"board": board},
    )


def positions_df(board: str) -> pd.DataFrame:
    frame = dataframe(
        "SELECT symbol, quantity, average_price, updated_at FROM positions WHERE board=:board ORDER BY symbol",
        {"board": board},
    )
    if frame.empty:
        return frame

    current_prices, market_values, pnls = [], [], []
    for _, row in frame.iterrows():
        try:
            price = latest_snapshot(row["symbol"]).price
        except Exception:
            price = float(row["average_price"])
        value = float(row["quantity"]) * price
        cost = float(row["quantity"]) * float(row["average_price"])
        current_prices.append(price)
        market_values.append(value)
        pnls.append(value - cost)

    frame["current_price"] = current_prices
    frame["market_value"] = market_values
    frame["unrealized_pnl"] = pnls
    return frame


def trades_df(board: str) -> pd.DataFrame:
    return dataframe(
        "SELECT timestamp, symbol, side, quantity, price, value, reason "
        "FROM trades WHERE board=:board ORDER BY id DESC LIMIT 200",
        {"board": board},
    )


def signals_df(board: str) -> pd.DataFrame:
    return dataframe(
        "SELECT timestamp, symbol, action, score, confidence, price, reason "
        "FROM signals WHERE board=:board ORDER BY id DESC LIMIT 200",
        {"board": board},
    )


def status_df() -> pd.DataFrame:
    return dataframe("SELECT board, last_run, last_error, scan_count FROM bot_status ORDER BY board")
