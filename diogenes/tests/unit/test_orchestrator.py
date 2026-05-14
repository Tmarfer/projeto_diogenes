"""
tests/unit/test_orchestrator.py — DVA-CBS | Projeto Diógenes
Testes unitários do Orquestrador: contador de IDs de alerta e fail-fast
contra corrupção de estado no audit_index.
"""
from __future__ import annotations

import pytest

from diogenes.config import get_config
from diogenes.models import WatsonOutput
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.exceptions import CorruptedStateError
from diogenes.orchestrator.orchestrator import (
    Orchestrator,
    _avancar_id_alerta,
    _incrementar_id_alerta,
)
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex


def _watson_output(ultimo_id: str, count: int = 0) -> WatsonOutput:
    return WatsonOutput(
        texto="", critical_alerts_count=count,
        has_unanalyzable_files=False, secoes={}, ultimo_id_alerta=ultimo_id,
    )


# ── _avancar_id_alerta ────────────────────────────────────────────────────────

def test_avancar_id_usa_maior_id_parseado_nao_a_contagem():
    """O próximo ID deriva do `ultimo_id_alerta` parseado, ignorando o count
    bruto do LLM — imune a Watson re-emitir a tabela inteira."""
    out = _watson_output("W001-006", count=99)
    assert _avancar_id_alerta("W001-002", out) == "W001-007"


def test_avancar_id_sem_alertas_mantem_contador():
    """Output sem nenhum ID não consome ID novo — contador inalterado."""
    out = _watson_output("", count=0)
    assert _avancar_id_alerta("W001-007", out) == "W001-007"


def test_avancar_id_contiguo_entre_rodadas():
    """Rodadas sucessivas de revisão produzem IDs contíguos mesmo quando
    Watson re-emite a tabela completa (count cresce, IDs não)."""
    proximo = "W001-001"
    proximo = _avancar_id_alerta(proximo, _watson_output("W001-003", count=3))
    assert proximo == "W001-004"
    # Watson re-emite as 3 antigas + 1 nova → count=4, último ID W001-004
    proximo = _avancar_id_alerta(proximo, _watson_output("W001-004", count=4))
    assert proximo == "W001-005"


def test_incrementar_id_formato_invalido_retorna_original():
    assert _incrementar_id_alerta("nao-e-id") == "nao-e-id"


# ── _transicionar: fail-fast contra estado corrompido ─────────────────────────

def test_transicionar_status_invalido_levanta_corrupted_state(
    env_vars, module_input, workspace
):
    cfg = get_config()
    manifest = MotorStart(cfg).run("MOD_SINT_001", 1)
    # Corromper o status no audit_index com um valor que não é CycleState
    AuditIndex(workspace).update_status(manifest.cycle_id, "STATUS_LIXO")

    orq = Orchestrator(manifest.cycle_id)
    with pytest.raises(CorruptedStateError):
        orq._transicionar(CycleState.EM_EXECUCAO_WATSON)
