"""Deduplicated market alerts stored in SQLite."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = os.getenv("PAPER_DB_PATH", "paper_trading.db")


def _connect() -> sqlite3.Connection:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=20)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS oracle_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL,
            category TEXT NOT NULL,
            symbol TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL
        )
        """
    )
    return connection


def create_alert(
    category: str,
    title: str,
    message: str,
    symbol: str = "",
    severity: str = "info",
    dedupe_hours: int = 12,
) -> bool:
    normalized = f"{category}|{symbol.upper()}|{title}|{message}".encode("utf-8")
    fingerprint = hashlib.sha256(normalized).hexdigest()
    now = int(time.time())
    cutoff = now - max(1, dedupe_hours) * 3600

    with _connect() as connection:
        connection.execute("DELETE FROM oracle_alerts WHERE created_at < ?", (cutoff - 7 * 86400,))
        existing = connection.execute(
            "SELECT created_at FROM oracle_alerts WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if existing and existing[0] >= cutoff:
            return False

        connection.execute(
            """
            INSERT OR REPLACE INTO oracle_alerts
            (fingerprint, created_at, category, symbol, title, message, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fingerprint, now, category, symbol.upper(), title, message, severity),
        )
    return True


def recent_alerts(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT created_at, category, symbol, title, message, severity
            FROM oracle_alerts ORDER BY created_at DESC LIMIT ?
            """,
            (max(1, min(limit, 500)),),
        ).fetchall()

    keys = ("created_at", "category", "symbol", "title", "message", "severity")
    return [dict(zip(keys, row)) for row in rows]
