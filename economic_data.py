"""Economic indicator adapter using Alpha Vantage."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from provider_client import ProviderError, get_json


@dataclass
class EconomicPoint:
    indicator: str
    date: str
    value: float | None
    unit: str
    source: str = "Alpha Vantage"


FUNCTIONS = {
    "REAL_GDP": "REAL_GDP",
    "CPI": "CPI",
    "INFLATION": "INFLATION",
    "UNEMPLOYMENT": "UNEMPLOYMENT",
    "FEDERAL_FUNDS_RATE": "FEDERAL_FUNDS_RATE",
    "TREASURY_YIELD": "TREASURY_YIELD",
}


def latest_indicator(name: str, interval: str = "monthly") -> EconomicPoint:
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        raise ProviderError("ALPHA_VANTAGE_API_KEY is not set.")

    normalized = name.upper().strip()
    function = FUNCTIONS.get(normalized)
    if not function:
        raise ValueError(f"Unsupported indicator: {name}")

    params: dict[str, Any] = {"function": function, "apikey": key}
    if function in {"CPI", "TREASURY_YIELD", "FEDERAL_FUNDS_RATE"}:
        params["interval"] = interval

    payload = get_json("https://www.alphavantage.co/query", params=params)
    if "Note" in payload or "Information" in payload:
        raise ProviderError(str(payload.get("Note") or payload.get("Information")))

    rows = payload.get("data", []) or []
    if not rows:
        raise ProviderError(f"No {normalized} data returned.")

    row = rows[0]
    raw_value = row.get("value")
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        value = None

    return EconomicPoint(
        indicator=str(payload.get("name") or normalized),
        date=str(row.get("date") or ""),
        value=value,
        unit=str(payload.get("unit") or ""),
    )
