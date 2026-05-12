"""llm/call_id.py — gerador de call_id único por chamada"""
from __future__ import annotations
from datetime import datetime, timezone


def gerar_call_id(agent: str, call_type: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{agent}_{call_type}"
