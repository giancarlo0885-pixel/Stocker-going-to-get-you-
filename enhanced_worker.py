"""24/7 research worker with crash protection and heartbeat.

Set ORACLE_WORKER_INTERVAL_SECONDS in Railway. This worker does not execute
real-money trades. Replace run_cycle() internals with calls into your existing
engine/oracle modules as needed.
"""
from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone

from health_monitor import write_heartbeat

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("garibaldi-worker")

RUNNING = True


def _stop(signum: int, frame: object) -> None:
    global RUNNING
    RUNNING = False
    log.info("Shutdown signal received: %s", signum)


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def run_cycle() -> dict[str, object]:
    # Safe default: verifies that the worker is alive.
    # Optional integration example:
    # from oracle_worker import run_once
    # return run_once()
    return {
        "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "paper-research-only",
    }


def main() -> None:
    interval = max(60, int(os.getenv("ORACLE_WORKER_INTERVAL_SECONDS", "300")))
    failures = 0
    log.info("Enhanced worker started; interval=%ss", interval)

    while RUNNING:
        started = time.monotonic()
        try:
            details = run_cycle()
            failures = 0
            write_heartbeat("ok", details)
            log.info("Cycle complete: %s", details)
        except Exception as exc:  # keeps service alive while recording the failure
            failures += 1
            write_heartbeat("error", {"error": str(exc), "failures": failures})
            log.exception("Worker cycle failed")
            time.sleep(min(60, 2 ** min(failures, 5)))

        elapsed = time.monotonic() - started
        remaining = max(1, interval - int(elapsed))
        for _ in range(remaining):
            if not RUNNING:
                break
            time.sleep(1)

    write_heartbeat("stopped", {})
    log.info("Enhanced worker stopped")


if __name__ == "__main__":
    main()
