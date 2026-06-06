"""
orchestrator/events.py — Logger de eventos do ciclo em events.jsonl.
Append-only. Um objeto JSON por linha (SDD Bloco 5.6).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventLogger:
    def __init__(self, runtime_dir: Path, cycle_id: str) -> None:
        self._path = runtime_dir / "events.jsonl"
        self._cycle_id = cycle_id
        # workspace root = _runtime/../../../..  (events.jsonl→_runtime→cycle→cycles→workspace)
        self._workspace = self._path.parent.parent.parent.parent

    def log(self, event_type: str, phase: str | None = None,
            agent: str | None = None, details: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cycle_id": self._cycle_id,
            "event_type": event_type,
            "phase": phase,
            "agent": agent,
            "details": details or {},
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        # Atualiza painel HTML em background — nunca interrompe a execução principal.
        try:
            self._atualizar_painel_html()
        except Exception:  # noqa: BLE001
            pass

    def _atualizar_painel_html(self) -> None:
        from diogenes.reports.cycle_report import build_report
        from diogenes.reports.render_html import render_html

        data = build_report(self._cycle_id, self._workspace)
        html = render_html(data)
        html_path = self._workspace / "cycles" / self._cycle_id / "report.html"
        html_path.write_text(html, encoding="utf-8")
