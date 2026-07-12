"""Validation helpers that prevent bad market data from reaching predictions."""
from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_OHLCV = ("Open", "High", "Low", "Close", "Volume")


def validate_ohlcv(frame: pd.DataFrame) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if frame is None or frame.empty:
        return False, ["No market data was returned."]

    missing = [column for column in REQUIRED_OHLCV if column not in frame.columns]
    if missing:
        errors.append("Missing columns: " + ", ".join(missing))
        return False, errors

    if frame[list(REQUIRED_OHLCV)].isna().all().any():
        errors.append("One or more required columns contain only missing values.")

    if (frame["Close"].dropna() <= 0).any():
        errors.append("Close prices must be positive.")

    invalid_range = (frame["High"] < frame["Low"]).fillna(False)
    if invalid_range.any():
        errors.append("Some rows have High below Low.")

    duplicates = frame.index.duplicated().sum()
    if duplicates:
        errors.append(f"Found {duplicates} duplicate timestamps.")

    return len(errors) == 0, errors


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except (TypeError, ValueError):
        return default
