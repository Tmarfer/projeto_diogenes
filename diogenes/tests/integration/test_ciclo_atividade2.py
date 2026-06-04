"""
tests/integration/test_ciclo_atividade2.py
Ciclo de Atividade 2 (revalidação): herança do histórico do ciclo de Atividade 1
e confronto na consolidação. Cobre RF-MS-05, RF-MY-08 e CA-FUN-02.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from diogenes.config import get_config
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

from .test_ciclo_sherlock import (
    ANALISE_ARQUIVO,
    AVALIACAO_OK,
    CONSOLIDADO_WATSON,
    DECISAO_SHERLOCK,
    DECISAO_WATSON,
    TASKS,
    VALIDACAO_SHERLOCK,
    _mock,
)

RELATORIO_FINAL = """# Relatório Final de Análise
**Processo:** TC 015.848/2025-6
**Módulo:** MOD_SINT_001

## Histórico da Revalidação

A inconsistência identificada na Atividade 1 foi classificada como Resolvida.

## Posição do Departamento

Módulo apto após revalidação.
"""


@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


def _fabricar_a1_encerrado(cfg, workspace: Path) -> str:
    """Cria um ciclo de Atividade 1 encerrado com os artefatos que a Atividade 2
    herda: relatório consolidado e decisões finais de Watson e Sherlock."""
    motor = MotorStart(cfg)
    manifest_a1 = motor.run("MOD_SINT_001", 1)
    cycle_dir = workspace / "cycles" / manifest_a1.cycle_id

    output_dir = cycle_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"relatorio_preliminar_{manifest_a1.cycle_id}.md").write_text(
        "# Relatório Preliminar\n\nInconsistência X identificada na planilha.\n",
        encoding="utf-8",
    )
    for fase, texto in (
        ("watson_integridade", "### Posição Adotada\nInconsistência X mantida.\n"),
        ("sherlock_validacao", "### Encaminhamento\nContraditório sobre X.\n"),
    ):
        fase_dir = cycle_dir / "stranger_room" / fase
        fase_dir.mkdir(parents=True, exist_ok=True)
        (fase_dir / "99_decisao_final.md").write_text(texto, encoding="utf-8")

    AuditIndex(workspace).seal_cycle(
        manifest_a1.cycle_id, decision="LIMPO",
        seal_at_utc="2026-06-01T10:00:00Z",
    )
    return manifest_a1.cycle_id


def test_motor_start_a2_herda_historico(cfg, module_input, workspace):
    """Motor de Start (A2) grava previous_cycle_id e copia os artefatos do A1."""
    cycle_a1 = _fabricar_a1_encerrado(cfg, workspace)

    manifest_a2 = MotorStart(cfg).run("MOD_SINT_001", 2)

    assert manifest_a2.activity == 2
    assert manifest_a2.previous_cycle_id == cycle_a1

    record = AuditIndex(workspace).get_cycle(manifest_a2.cycle_id)
    assert record["previous_cycle_id"] == cycle_a1  # CA-FUN-02

    historico = workspace / "cycles" / manifest_a2.cycle_id / "_historico"
    assert (historico / "relatorio_anterior.md").exists()
    assert (historico / "watson_decisao_anterior.md").exists()
    assert (historico / "sherlock_decisao_anterior.md").exists()
    assert cycle_a1 in (historico / "PROVENIENCIA.md").read_text(encoding="utf-8")


def test_ciclo_a2_confronta_historico(httpx_mock: HTTPXMock, cfg, module_input, workspace):
    """Ciclo A2 completo: histórico injetado em Watson e relatório final gerado."""
    _fabricar_a1_encerrado(cfg, workspace)

    motor = MotorStart(cfg)
    manifest_a2 = motor.run("MOD_SINT_001", 2)
    AuditIndex(workspace).update_status(
        manifest_a2.cycle_id, CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value
    )

    PACOTE_SH = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS,
        ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO,
        CONSOLIDADO_WATSON,
        AVALIACAO_OK, DECISAO_WATSON,
        PACOTE_SH,
        VALIDACAO_SHERLOCK, VALIDACAO_SHERLOCK,
        AVALIACAO_OK, DECISAO_SHERLOCK,
        RELATORIO_FINAL,
    ]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions", json=_mock(content)
        )

    orq = Orchestrator(manifest_a2.cycle_id)
    resultado = orq.executar(manifest_a2)

    # Output deve ser o relatório final (não preliminar)
    assert resultado != ""
    output_path = Path(resultado)
    assert output_path.name.startswith("relatorio_final_")
    assert output_path.exists()

    record = AuditIndex(workspace).get_cycle(manifest_a2.cycle_id)
    assert record["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
    assert record["output_filename"].startswith("relatorio_final_")

    # O histórico do A1 deve ter sido injetado nas tasks de Watson (evento)
    cycle_dir = workspace / "cycles" / manifest_a2.cycle_id
    eventos = [
        json.loads(ln)
        for ln in (cycle_dir / "_runtime" / "events.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    tipos = [e["event_type"] for e in eventos]
    assert "REVALIDACAO_HISTORICO_INJETADO" in tipos
