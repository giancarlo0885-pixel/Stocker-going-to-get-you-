"""Economic event calendar with graceful fallback.

Uses Finnhub when FINNHUB_API_KEY is present. Returns normalized events so the
rest of the application does not depend on one provider's response format.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import requests

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
FINNHUB_BASE = "https://finnhub.io/api/v1"


def get_economic_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    start = date.today()
    end = start + timedelta(days=max(1, min(days_ahead, 30)))

    if not FINNHUB_API_KEY:
        return []

    try:
        response = requests.get(
            f"{FINNHUB_BASE}/calendar/economic",
            params={"from": start.isoformat(), "to": end.isoformat(), "token": FINNHUB_API_KEY},
            timeout=15,
        )
        response.raise_for_status()
        raw = response.json().get("economicCalendar", [])
    except (requests.RequestException, ValueError, TypeError):
        return []

    events: list[dict[str, Any]] = []
    for item in raw:
        events.append(
            {
                "date": item.get("time") or item.get("date"),
                "country": item.get("country", ""),
                "event": item.get("event", "Economic event"),
                "impact": item.get("impact", ""),
                "actual": item.get("actual"),
                "estimate": item.get("estimate"),
                "previous": item.get("prev"),
                "unit": item.get("unit", ""),
            }
        )
    return events


def high_impact_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    events = get_economic_events(days_ahead)
    important_words = ("rate", "cpi", "inflation", "payroll", "employment", "gdp", "fomc", "fed")
    return [
        event for event in events
        if str(event.get("impact", "")).lower() in {"high", "3"}
        or any(word in str(event.get("event", "")).lower() for word in important_words)
    ]
