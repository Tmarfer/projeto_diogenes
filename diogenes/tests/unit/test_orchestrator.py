"""
tests/unit/test_orchestrator.py — DVA-CBS | Projeto Diógenes
Testes unitários do Orquestrador: contador de IDs de alerta, fail-fast
contra corrupção de estado e cache de tasks_watson.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from diogenes.config import get_config
from diogenes.models import WatsonOutput
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.exceptions import CorruptedStateError
from diogenes.orchestrator.orchestrator import (
    Orchestrator,
    _avancar_id_alerta,
    _carregar_tasks_cache,
    _incrementar_id_alerta,
    _salvar_tasks_cache,
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


# ── cache tasks_watson ────────────────────────────────────────────────────────

from diogenes.models import DefinirTasksResult


def _escrever_cache(tmp_path: Path, module_id: str = "MOD_010",
                    idade_dias: int = 0, module_id_campo: str | None = None) -> Path:
    cache_dir = tmp_path / module_id
    cache_dir.mkdir(parents=True)
    criado_em = datetime.now(timezone.utc) - timedelta(days=idade_dias)
    dados = {
        "module_id": module_id_campo or module_id,
        "tasks_text": "## Tasks para Watson\nTask 1: análise",
        "planilha_verificacao_no_pacote": False,
        "criado_em": criado_em.isoformat(),
    }
    cache_path = cache_dir / "mycroft_tasks_watson.json"
    cache_path.write_text(json.dumps(dados), encoding="utf-8")
    return cache_path


def test_carregar_tasks_cache_retorna_resultado(tmp_path: Path):
    """Cache válido é carregado corretamente."""
    _escrever_cache(tmp_path)
    result = _carregar_tasks_cache("MOD_010", tmp_path)
    assert result is not None
    assert "Task 1" in result.tasks_text
    assert result.planilha_verificacao_no_pacote is False


def test_carregar_tasks_cache_ausente_retorna_none(tmp_path: Path):
    """Sem arquivo de cache, retorna None."""
    (tmp_path / "MOD_010").mkdir()
    assert _carregar_tasks_cache("MOD_010", tmp_path) is None


def test_carregar_tasks_cache_expirado_retorna_none(tmp_path: Path):
    """Cache com idade > 30 dias é descartado."""
    _escrever_cache(tmp_path, idade_dias=31)
    assert _carregar_tasks_cache("MOD_010", tmp_path) is None


def test_carregar_tasks_cache_module_id_errado_retorna_none(tmp_path: Path):
    """Cache com module_id divergente é rejeitado."""
    _escrever_cache(tmp_path, module_id_campo="MOD_999")
    assert _carregar_tasks_cache("MOD_010", tmp_path) is None


def test_salvar_e_recarregar_tasks_cache(tmp_path: Path):
    """Salvar e recarregar preserva tasks_text e flag planilha."""
    result = DefinirTasksResult(tasks_text="Task A\nTask B", planilha_verificacao_no_pacote=True)
    _salvar_tasks_cache(result, "MOD_TEST", tmp_path)
    loaded = _carregar_tasks_cache("MOD_TEST", tmp_path)
    assert loaded is not None
    assert loaded.tasks_text == "Task A\nTask B"
    assert loaded.planilha_verificacao_no_pacote is True
