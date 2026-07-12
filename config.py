from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _csv(name: str, default: str) -> list[str]:
    return [x.strip().upper() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    sqlite_path: str = os.getenv("PAPER_DB_PATH", "paper_trading.db").strip()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "").strip()

    scan_seconds: int = max(60, _int("BOT_SCAN_SECONDS", 300))
    worker_error_retry_seconds: int = max(15, _int("WORKER_ERROR_RETRY_SECONDS", 60))
    worker_heartbeat_seconds: int = max(60, _int("WORKER_HEARTBEAT_SECONDS", 900))

    starting_paper_cash: float = max(1.0, _float("STARTING_PAPER_CASH", 10.0))
    max_position_pct: float = min(1.0, max(0.05, _float("MAX_POSITION_PCT", 0.25)))
    max_open_positions: int = max(1, _int("MAX_OPEN_POSITIONS", 4))
    buy_score_threshold: float = _float("BUY_SCORE_THRESHOLD", 2.0)
    sell_score_threshold: float = _float("SELL_SCORE_THRESHOLD", -2.0)

    cash_watchlist: tuple[str, ...] = tuple(_csv("CASH_WATCHLIST", "AAPL,NVDA,SPY,QQQ"))
    crypto_watchlist: tuple[str, ...] = tuple(_csv("CRYPTO_WATCHLIST", "BTC,ETH,SOL,XRP"))


settings = Settings()
