"""
orchestrator/events.py — Logger de eventos do ciclo em events.jsonl.
Append-only. Um objeto JSON por linha (SDD Bloco 5.6).
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EventLogger:
    def __init__(self, runtime_dir: Path, cycle_id: str) -> None:
        self._path = runtime_dir / "events.jsonl"
        self._cycle_id = cycle_id

    def log(self, event_type: str, phase: str | None = None,
            agent: str | None = None, details: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cycle_id": self._cycle_id,
            "event_type": event_type,
            "phase": phase,
            "agent": agent,
            "details": details or {},
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
