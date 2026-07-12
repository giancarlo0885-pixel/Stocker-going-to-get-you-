from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone

import engine
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("garibaldi-oracle-worker")
running = True


def stop_worker(signum: int, _frame) -> None:
    global running
    logger.info("Shutdown signal received: %s", signum)
    running = False


def sleep_interruptibly(seconds: float) -> None:
    deadline = time.monotonic() + max(0.0, seconds)
    while running and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


def main() -> None:
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)

    engine.init_db()
    logger.info("Worker started. Scan interval: %s seconds", settings.scan_seconds)

    last_heartbeat = 0.0
    while running:
        started = time.monotonic()
        try:
            logger.info("Beginning scan at %s", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            engine.run_once()
            logger.info("Scan completed in %.1f seconds", time.monotonic() - started)

            now = time.monotonic()
            if now - last_heartbeat >= settings.worker_heartbeat_seconds:
                logger.info("Heartbeat:\n%s", engine.status_df().to_string(index=False))
                last_heartbeat = now

            sleep_interruptibly(max(5, settings.scan_seconds - (time.monotonic() - started)))
        except Exception:
            logger.exception("Worker cycle failed")
            sleep_interruptibly(settings.worker_error_retry_seconds)

    logger.info("Worker stopped cleanly")


if __name__ == "__main__":
    main()
