"""Upcoming earnings calendar using Finnhub when configured."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import requests

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()


def upcoming_earnings(days_ahead: int = 14, symbol: str | None = None) -> list[dict[str, Any]]:
    if not FINNHUB_API_KEY:
        return []

    start = date.today()
    end = start + timedelta(days=max(1, min(days_ahead, 60)))
    params = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "token": FINNHUB_API_KEY,
    }
    if symbol:
        params["symbol"] = symbol.upper().strip()

    try:
        response = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        raw = response.json().get("earningsCalendar", [])
    except (requests.RequestException, ValueError, TypeError):
        return []

    return [
        {
            "date": row.get("date"),
            "symbol": row.get("symbol"),
            "hour": row.get("hour"),
            "eps_estimate": row.get("epsEstimate"),
            "revenue_estimate": row.get("revenueEstimate"),
            "quarter": row.get("quarter"),
            "year": row.get("year"),
        }
        for row in raw
    ]
