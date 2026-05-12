"""
tests/integration/test_ciclo_sherlock.py
Ciclo end-to-end completo (Watson + Sherlock + consolidação) com mocks.
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


def _mock(content: str) -> dict:
    return {
        "id": "test", "object": "chat.completion",
        "model": "google/gemini-2.0-flash-exp:free",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        "system_fingerprint": None,
    }


TASKS = "## Tasks para Watson\n\n1. Analisar planilha\n2. Traduzir SQL\n"

ANALISE_WATSON = """## Resumo Executivo\nAnálise concluída.\n
## Tabela de Alertas\n| Severidade | Localização | Descrição |\n|---|---|---|\n
## Arquivos Não Analisáveis\n"""

AVALIACAO_OK = "## Avaliação\n\nAPROVADO. Output completo.\n"

DECISAO_WATSON = """## Decisão Final — Watson\n### Síntese\nBoa análise.\n
### Posição Adotada\nAcatada.\n### Overrule\nNÃO\n
### Alertas Críticos\nCONTAGEM: 0\n### Notas para Sherlock\nDados bem estruturados.\n"""

VALIDACAO_SHERLOCK = """## Resumo Executivo\nMódulo verificado.\n
## Classificação Ponto a Ponto\n### Item 1\n**Status:** ATENDIDO\n
## Inconsistências para Contraditório\n\n## Limitações e Pontos Não Verificáveis\n"""

DECISAO_SHERLOCK = """## Decisão Final — Sherlock\n### Síntese\nValidação completa.\n
### Posição Adotada\nAcatada.\n### Overrule\nNÃO\n
### Dilemas\nCONTAGEM: 0\n### Encaminhamento\nNenhum.\n"""

RELATORIO = """# Relatório Preliminar de Análise
**Processo:** TC 015.848/2025-6
**Módulo:** MOD_SINT_001

## Contexto

Módulo analisado conforme metodologia homologada.

## Achados de Integridade

Nenhuma inconsistência crítica identificada.

## Achados de Aderência Metodológica

Módulo atende aos requisitos metodológicos.

## Posição do Departamento

Módulo apto para validação pelo GT Reforma Tributária.
"""


@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


@pytest.fixture
def ciclo(cfg, module_input, workspace):
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    AuditIndex(workspace).update_status(
        manifest.cycle_id,
        CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value,
    )
    return manifest


def test_ciclo_completo_sem_revisoes(httpx_mock: HTTPXMock, ciclo, cfg, workspace):
    """
    Ciclo completo: Watson aprova → Sherlock aprova → consolidação.
    8 chamadas LLM mockadas.
    """
    PACOTE_SH3 = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS, ANALISE_WATSON, AVALIACAO_OK, DECISAO_WATSON,        # Watson (4)
        PACOTE_SH3,                                                    # montar_pacote_sherlock (5)
        VALIDACAO_SHERLOCK, AVALIACAO_OK, DECISAO_SHERLOCK,          # Sherlock (6-8)
        RELATORIO,                                                     # consolidação (9)
    ]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            json=_mock(content),
        )

    orq = Orchestrator(ciclo.cycle_id)
    resultado = orq.executar(ciclo)

    # Output deve ter sido gerado
    assert resultado != ""
    output_path = Path(resultado)
    assert output_path.exists()
    conteudo = output_path.read_text(encoding="utf-8")
    assert "Relatório Preliminar" in conteudo

    # audit_index deve refletir ciclo completo
    record = AuditIndex(workspace).get_cycle(ciclo.cycle_id)
    assert record["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
    assert record["watson_rodadas"] == "0"
    assert record["sherlock_rodadas"] == "0"
    assert record["output_filename"] != ""

    # Stranger's Room: ambas as fases completas
    cycle_dir = workspace / "cycles" / ciclo.cycle_id
    for fase in ["watson_integridade", "sherlock_validacao"]:
        for nome in ["01_apresentacao.md", "99_decisao_final.md"]:
            assert (cycle_dir / "stranger_room" / fase / nome).exists(), \
                f"Faltando {fase}/{nome}"

    # events.jsonl deve ter eventos de ambas as fases
    eventos = [
        json.loads(l)
        for l in (cycle_dir / "_runtime" / "events.jsonl").read_text().splitlines()
        if l.strip()
    ]
    tipos = [e["event_type"] for e in eventos]
    assert "CYCLE_STARTED" in tipos
    assert "CONSOLIDACAO_CONCLUIDA" in tipos
    assert tipos.count("PHASE_ENDED") == 2  # Watson e Sherlock


def test_alerta_critico_pausa_antes_de_sherlock(httpx_mock: HTTPXMock, ciclo, cfg, workspace):
    """
    Watson com alerta crítico: Orquestrador pausa, aguarda Lestrade.
    """
    ANALISE_COM_CRITICO = """## Resumo Executivo\nProblema identificado.\n
## Tabela de Alertas\n| Severidade | Localização | Descrição |\n|---|---|---|\n| CRÍTICA | planilha, aba 1 | Total não fecha |\n
## Arquivos Não Analisáveis\n"""
    DECISAO_CRITICA = """## Decisão Final — Watson\n### Síntese\nAlerta.\n
### Posição Adotada\nMantida.\n### Overrule\nNÃO\n
### Alertas Críticos\nCONTAGEM: 1\n### Notas para Sherlock\nAtenção ao total.\n"""

    for content in [TASKS, ANALISE_COM_CRITICO, AVALIACAO_OK, DECISAO_CRITICA]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            json=_mock(content),
        )

    orq = Orchestrator(ciclo.cycle_id)
    resultado = orq.executar(ciclo)

    # Ciclo pausado — sem output ainda
    assert resultado == ""
    record = AuditIndex(workspace).get_cycle(ciclo.cycle_id)
    assert record["status"] == CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value
    assert record["watson_critical_alerts_count"] == "1"
