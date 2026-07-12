"""Simple worker heartbeat and health report."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEARTBEAT_FILE = Path(os.getenv("HEARTBEAT_FILE", "worker_heartbeat.json"))


def write_heartbeat(status: str = "ok", details: dict[str, Any] | None = None) -> None:
    payload = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_heartbeat() -> dict[str, Any]:
    if not HEARTBEAT_FILE.exists():
        return {"status": "missing", "updated_at": None, "details": {}}
    try:
        return json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "corrupt", "updated_at": None, "details": {}}
