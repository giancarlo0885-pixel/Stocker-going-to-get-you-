from __future__ import annotations

"""
GARIBALDI MARKET ORACLE™ — 24/7 Background Worker

This worker uses the exact same algorithm and database as engine.py.
It does not create a second trading strategy. It continuously calls
engine.run_once(), which uses the existing:

- compute_signal()
- combined news regime
- EMA / RSI / momentum / volatility scoring
- stop loss / take profit / trailing stop
- position sizing and risk limits
- paper-trading database

Railway start command:
    python oracle_worker.py
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

import engine


LOG_LEVEL = os.getenv("WORKER_LOG_LEVEL", "INFO").upper()
SCAN_SECONDS = max(60, int(os.getenv("BOT_SCAN_SECONDS", "300")))
ERROR_RETRY_SECONDS = max(15, int(os.getenv("WORKER_ERROR_RETRY_SECONDS", "60")))
HEARTBEAT_SECONDS = max(60, int(os.getenv("WORKER_HEARTBEAT_SECONDS", "900")))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("garibaldi-oracle-worker")

_running = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stop_worker(signum: int, _frame) -> None:
    global _running
    logger.info("Shutdown signal received: %s", signum)
    _running = False


def sleep_interruptibly(seconds: float) -> None:
    """Sleep in short steps so Railway can stop the worker cleanly."""
    deadline = time.monotonic() + max(0.0, seconds)

    while _running and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


def main() -> None:
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)

    logger.info("Starting GARIBALDI MARKET ORACLE 24/7 worker")
    logger.info("Database: %s", engine.DB_PATH)
    logger.info("Scan interval: %s seconds", SCAN_SECONDS)
    logger.info("Cash symbols: %s", ", ".join(engine.CASH_SYMBOLS))
    logger.info("Crypto symbols: %s", ", ".join(engine.CRYPTO_SYMBOLS))

    engine.init_db()

    last_heartbeat = 0.0

    while _running:
        cycle_started = time.monotonic()

        try:
            logger.info("Beginning market scan at %s", utc_now())

            # This calls the same engine used by the Streamlit application.
            engine.run_once()

            elapsed = time.monotonic() - cycle_started
            logger.info("Market scan completed in %.1f seconds", elapsed)

            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                try:
                    status = engine.status_df()
                    logger.info("Worker heartbeat at %s\n%s", utc_now(), status.to_string(index=False))
                except Exception:
                    logger.exception("Could not print worker heartbeat")
                last_heartbeat = now

            sleep_interruptibly(max(5.0, SCAN_SECONDS - elapsed))

        except Exception:
            logger.exception(
                "Worker cycle crashed. Retrying in %s seconds.",
                ERROR_RETRY_SECONDS,
            )
            sleep_interruptibly(ERROR_RETRY_SECONDS)

    logger.info("GARIBALDI MARKET ORACLE worker stopped cleanly")


if __name__ == "__main__":
    main()
