"""Shared HTTP client with retries, timeouts, and safe API-key handling."""
from __future__ import annotations

import os
import time
from typing import Any, Mapping

import requests


class ProviderError(RuntimeError):
    pass


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProviderError(f"Missing Railway variable: {name}")
    return value


def get_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: int = 15,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                params=dict(params or {}),
                headers=dict(headers or {}),
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ProviderError("Provider returned an unexpected response.")
            return data
        except (requests.RequestException, ValueError, ProviderError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise ProviderError(str(last_error) if last_error else "Provider request failed.")
