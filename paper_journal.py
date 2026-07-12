"""SQLite paper-trading journal. It never connects to a brokerage."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


DB_PATH = os.getenv("PAPER_JOURNAL_DB", "paper_trades.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
            quantity REAL NOT NULL CHECK(quantity > 0),
            entry_price REAL NOT NULL CHECK(entry_price > 0),
            exit_price REAL,
            confidence INTEGER,
            thesis TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN'
        )
        """
    )
    conn.commit()
    return conn


def open_trade(
    symbol: str,
    asset_type: str,
    side: str,
    quantity: float,
    entry_price: float,
    confidence: int | None = None,
    thesis: str = "",
) -> int:
    side = side.upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if quantity <= 0 or entry_price <= 0:
        raise ValueError("quantity and entry_price must be positive")
    if confidence is not None and not 0 <= confidence <= 100:
        raise ValueError("confidence must be between 0 and 100")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO paper_trades
            (opened_at, symbol, asset_type, side, quantity, entry_price, confidence, thesis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                symbol.upper().strip(),
                asset_type.lower().strip(),
                side,
                quantity,
                entry_price,
                confidence,
                thesis,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def close_trade(trade_id: int, exit_price: float) -> dict[str, Any]:
    if exit_price <= 0:
        raise ValueError("exit_price must be positive")

    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM paper_trades WHERE id = ? AND status = 'OPEN'",
            (trade_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Open trade not found")

        direction = 1 if row["side"] == "BUY" else -1
        pnl = (exit_price - row["entry_price"]) * row["quantity"] * direction
        conn.execute(
            """
            UPDATE paper_trades
            SET exit_price = ?, closed_at = ?, status = 'CLOSED'
            WHERE id = ?
            """,
            (exit_price, datetime.now(timezone.utc).isoformat(), trade_id),
        )
        conn.commit()
        return {"trade_id": trade_id, "realized_pnl": round(pnl, 2)}


def list_trades(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM paper_trades ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 1000)),),
        ).fetchall()
    return [dict(row) for row in rows]
