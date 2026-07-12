from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import requests

from config import settings


@dataclass(frozen=True)
class APIStatus:
    name: str
    configured: bool
    purpose: str


def request_json(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 15,
) -> dict | list:
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_statuses() -> list[APIStatus]:
    return [
        APIStatus("Finnhub", bool(settings.finnhub_api_key), "Optional company news"),
        APIStatus("OpenAI", bool(settings.openai_api_key), "Optional plain-language AI answers"),
        APIStatus("Database", True, "PostgreSQL when DATABASE_URL exists; SQLite otherwise"),
    ]
