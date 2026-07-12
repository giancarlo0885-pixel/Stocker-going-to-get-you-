"""Heartbeat file for confirming the Railway worker is alive."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

HEARTBEAT_PATH = Path(os.getenv("WORKER_HEARTBEAT_PATH", "/tmp/oracle_worker_heartbeat.json"))


def write_heartbeat(status: str = "running", details: dict[str, Any] | None = None) -> None:
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "unix_time": int(time.time()),
        "details": details or {},
    }
    temporary = HEARTBEAT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(HEARTBEAT_PATH)


def read_heartbeat(max_age_seconds: int = 300) -> dict[str, Any]:
    if not HEARTBEAT_PATH.exists():
        return {"healthy": False, "reason": "No heartbeat found."}

    try:
        payload = json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
        age = int(time.time()) - int(payload.get("unix_time", 0))
        payload["age_seconds"] = age
        payload["healthy"] = age <= max_age_seconds and payload.get("status") == "running"
        return payload
    except (OSError, ValueError, TypeError):
        return {"healthy": False, "reason": "Heartbeat could not be read."}
