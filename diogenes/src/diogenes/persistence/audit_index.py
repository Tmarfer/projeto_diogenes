"""
persistence/audit_index.py — DVA-CBS | Projeto Diógenes
Leitura e escrita do audit_index.csv.

Schema: 25 colunas conforme SDD Bloco 5.5.
Escrita atômica: arquivo temporário + rename (RF-PE-04).

Referência normativa: RF-PE-04, RNF-RAST-05 (PRD v0.1), Bloco 5.5 (SDD v0.1)
"""

from __future__ import annotations

import csv
import dataclasses
import tempfile
from pathlib import Path

from diogenes.models import AUDIT_INDEX_COLUMNS, CycleRecord


class AuditIndex:
    """Encapsula todas as operações sobre o audit_index.csv."""

    def __init__(self, workspace_path: Path) -> None:
        self.path = workspace_path / "audit_index.csv"

    def create_if_not_exists(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=AUDIT_INDEX_COLUMNS).writeheader()

    def add_cycle(self, record: CycleRecord) -> None:
        if self.get_cycle(record.cycle_id) is not None:
            raise ValueError(
                f"cycle_id '{record.cycle_id}' já existe em audit_index.csv."
            )
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=AUDIT_INDEX_COLUMNS).writerow(
                dataclasses.asdict(record)
            )

    def update_status(self, cycle_id: str, status: str, **extra: str) -> None:
        """Atualização atômica via arquivo temporário + rename (RF-PE-04)."""
        rows = self._read_all()
        updated = False
        for row in rows:
            if row["cycle_id"] == cycle_id:
                row["status"] = status
                for k, v in extra.items():
                    if k in AUDIT_INDEX_COLUMNS:
                        row[k] = v
                updated = True
                break
        if not updated:
            raise KeyError(f"cycle_id '{cycle_id}' não encontrado em audit_index.csv")
        self._write_atomic(rows)

    def get_cycle(self, cycle_id: str) -> dict | None:
        for row in self._read_all():
            if row["cycle_id"] == cycle_id:
                return row
        return None

    def list_cycles(
        self,
        module_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        rows = self._read_all()
        if module_id:
            rows = [r for r in rows if r["module_id"] == module_id]
        if status:
            rows = [r for r in rows if r["status"] == status]
        return rows

    def count_cycles_for_module(self, module_id: str) -> int:
        return sum(1 for r in self._read_all() if r["module_id"] == module_id)

    def update_motor_saida(self, cycle_id: str, invocado_at_utc: str,
                            occurrences: int, output_hash: str) -> None:
        self.update_status(
            cycle_id, self.get_cycle(cycle_id)["status"],
            motor_saida_invocado_at_utc=invocado_at_utc,
            motor_saida_occurrences=str(occurrences),
            output_hash=output_hash,
        )

    def seal_cycle(self, cycle_id: str, decision: str,
                   seal_at_utc: str, notes: str = "") -> None:
        from diogenes.orchestrator.states import CycleState
        extra: dict = {
            "motor_saida_decision": decision,
            "lestrade_seal_at_utc": seal_at_utc,
            "ended_at_utc": seal_at_utc,
        }
        if notes:
            extra["notes"] = notes[:200]
        self.update_status(cycle_id, CycleState.ENCERRADO_CHANCELADO.value, **extra)

    def update_watson_metadata(self, cycle_id: str, rodadas: int,
                               overruled: bool, critical_alerts: int) -> None:
        self.update_status(
            cycle_id, self.get_cycle(cycle_id)["status"],
            watson_rodadas=str(rodadas),
            mycroft_overruled_watson=str(overruled).lower(),
            watson_critical_alerts_count=str(critical_alerts),
        )

    def update_sherlock_metadata(self, cycle_id: str, rodadas: int,
                                  overruled: bool, dilemmas: int) -> None:
        self.update_status(
            cycle_id, self.get_cycle(cycle_id)["status"],
            sherlock_rodadas=str(rodadas),
            mycroft_overruled_sherlock=str(overruled).lower(),
            sherlock_dilemmas_count=str(dilemmas),
        )

    def update_output_info(self, cycle_id: str, output_filename: str) -> None:
        self.update_status(
            cycle_id, self.get_cycle(cycle_id)["status"],
            output_filename=output_filename,
        )

    def _read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write_atomic(self, rows: list[dict]) -> None:
        parent = self.path.parent
        tmp_fd, tmp_str = tempfile.mkstemp(dir=parent, suffix=".tmp", prefix="audit_")
        tmp_path = Path(tmp_str)
        try:
            with open(tmp_fd, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=AUDIT_INDEX_COLUMNS)
                w.writeheader()
                w.writerows(rows)
            tmp_path.replace(self.path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
