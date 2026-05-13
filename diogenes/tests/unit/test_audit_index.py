"""tests/unit/test_audit_index.py"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from diogenes.models import AUDIT_INDEX_COLUMNS, CycleRecord
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex


def _record(cycle_id: str, module_id: str = "MOD_010", activity: int = 1) -> CycleRecord:
    return CycleRecord(
        cycle_id=cycle_id, module_id=module_id, activity=activity,
        status=CycleState.PREPARADO.value,
        opened_at_utc="2026-05-10T10:00:00Z",
    )


class TestAuditIndex:

    def test_cria_com_cabecalho_correto(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        assert (workspace / "audit_index.csv").exists()
        with open(workspace / "audit_index.csv") as f:
            header = next(csv.reader(f))
        assert header == AUDIT_INDEX_COLUMNS
        assert len(header) == 27  # 27 colunas conforme SDD Bloco 5.5

    def test_idempotente(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        audit.create_if_not_exists()  # sem erro

    def test_add_e_get_cycle(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        r = _record("MOD_010_A1_20260510T100000Z")
        audit.add_cycle(r)
        row = audit.get_cycle("MOD_010_A1_20260510T100000Z")
        assert row is not None
        assert row["module_id"] == "MOD_010"
        assert row["status"] == "PREPARADO"
        assert row["watson_rodadas"] == "0"   # campos específicos do SDD

    def test_duplicado_levanta_erro(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        r = _record("CYC001")
        audit.add_cycle(r)
        with pytest.raises(ValueError, match="já existe"):
            audit.add_cycle(r)

    def test_update_status_atomico(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        audit.add_cycle(_record("CYC001"))
        audit.update_status("CYC001", "EM_EXECUCAO_WATSON", watson_rodadas="1")
        row = audit.get_cycle("CYC001")
        assert row["status"] == "EM_EXECUCAO_WATSON"
        assert row["watson_rodadas"] == "1"

    def test_update_inexistente_levanta_erro(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        with pytest.raises(KeyError):
            audit.update_status("NAO_EXISTE", "PREPARADO")

    def test_list_com_filtros(self, workspace: Path):
        audit = AuditIndex(workspace)
        audit.create_if_not_exists()
        for i in range(3):
            audit.add_cycle(_record(f"MOD_010_A1_CYC{i:03d}", "MOD_010"))
        audit.add_cycle(_record("MOD_001_A1_CYC000", "MOD_001"))
        assert len(audit.list_cycles(module_id="MOD_010")) == 3
        assert len(audit.list_cycles(module_id="MOD_001")) == 1
        assert audit.count_cycles_for_module("MOD_010") == 3
