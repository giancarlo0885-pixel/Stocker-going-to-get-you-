"""Options-chain scanner.

Uses POLYGON_API_KEY when available. This produces research signals only and
does not place trades. Some options endpoints require a paid data plan.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from provider_client import ProviderError, get_json


@dataclass
class OptionsSignal:
    symbol: str
    call_volume: float
    put_volume: float
    call_open_interest: float
    put_open_interest: float
    put_call_volume_ratio: float | None
    bias: str
    contracts_scanned: int
    source: str = "Polygon/Massive options snapshot"


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def scan_options(symbol: str, limit: int = 250) -> OptionsSignal:
    key = os.getenv("POLYGON_API_KEY", "").strip()
    if not key:
        raise ProviderError("POLYGON_API_KEY is not set.")

    symbol = symbol.upper().strip()
    url = f"https://api.polygon.io/v3/snapshot/options/{symbol}"
    params: dict[str, Any] = {"apiKey": key, "limit": min(max(limit, 10), 250)}

    call_volume = put_volume = 0.0
    call_oi = put_oi = 0.0
    scanned = 0

    while url and scanned < limit:
        payload = get_json(url, params=params)
        params = {}  # next_url already carries pagination details
        for item in payload.get("results", []) or []:
            details = item.get("details", {}) or {}
            day = item.get("day", {}) or {}
            contract_type = str(details.get("contract_type", "")).lower()
            volume = _number(day.get("volume"))
            open_interest = _number(item.get("open_interest"))

            if contract_type == "call":
                call_volume += volume
                call_oi += open_interest
            elif contract_type == "put":
                put_volume += volume
                put_oi += open_interest
            scanned += 1
            if scanned >= limit:
                break

        next_url = payload.get("next_url")
        url = str(next_url) if next_url else ""
        if url and "apiKey=" not in url:
            params = {"apiKey": key}

    ratio = (put_volume / call_volume) if call_volume > 0 else None
    if ratio is None:
        bias = "insufficient data"
    elif ratio < 0.7:
        bias = "bullish options activity"
    elif ratio > 1.3:
        bias = "bearish options activity"
    else:
        bias = "balanced options activity"

    return OptionsSignal(
        symbol=symbol,
        call_volume=round(call_volume, 2),
        put_volume=round(put_volume, 2),
        call_open_interest=round(call_oi, 2),
        put_open_interest=round(put_oi, 2),
        put_call_volume_ratio=round(ratio, 3) if ratio is not None else None,
        bias=bias,
        contracts_scanned=scanned,
    )
