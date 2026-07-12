"""Optional supervised 24/7 intelligence worker.

Run as a separate Railway service:
    python upgrade_worker.py

This worker does not place real trades. It refreshes calendars, records alerts,
and writes a heartbeat so you can confirm it is alive.
"""
from __future__ import annotations

import logging
import os
import time

from alert_manager import create_alert
from earnings_calendar import upcoming_earnings
from economic_calendar import high_impact_events
from worker_health import write_heartbeat

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("oracle-upgrade-worker")

INTERVAL_SECONDS = max(300, int(os.getenv("ORACLE_SCAN_INTERVAL_SECONDS", "900")))


def scan_once() -> dict[str, int]:
    economic = high_impact_events(7)
    earnings = upcoming_earnings(7)

    new_alerts = 0
    for event in economic:
        title = str(event.get("event") or "Economic event")
        if create_alert(
            category="economic",
            title=title,
            message=f"{event.get('country', '')} {event.get('date', '')}".strip(),
            severity="high",
        ):
            new_alerts += 1

    for event in earnings:
        symbol = str(event.get("symbol") or "")
        if create_alert(
            category="earnings",
            symbol=symbol,
            title=f"{symbol} earnings".strip(),
            message=f"Scheduled {event.get('date', '')} {event.get('hour', '')}".strip(),
            severity="medium",
        ):
            new_alerts += 1

    result = {
        "economic_events": len(economic),
        "earnings_events": len(earnings),
        "new_alerts": new_alerts,
    }
    write_heartbeat("running", result)
    return result


def main() -> None:
    LOGGER.info("GARIBALDI MARKET ORACLE upgrade worker started.")
    while True:
        try:
            result = scan_once()
            LOGGER.info("Scan complete: %s", result)
        except Exception:
            LOGGER.exception("Worker scan failed.")
            write_heartbeat("error", {"message": "See Railway logs."})
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
