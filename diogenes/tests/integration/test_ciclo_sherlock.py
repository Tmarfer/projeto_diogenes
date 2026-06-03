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

ANALISE_ARQUIVO = """## Análise do Arquivo

Arquivo analisado sem inconsistências.

## Insumos da Cadeia

Entrada: dados brutos. Saída: dados processados.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|

## Arquivos Não Analisáveis

## Último ID de Alerta Usado

W001-000
"""

CONSOLIDADO_WATSON = """## Resumo Executivo

Análise de integridade do módulo MOD_SINT_001 concluída.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|
| INFORMATIVA | planilha_cbs.xlsx | Estrutura consistente |

## Cadeia de Produção dos Dados

script → planilha → resultado

## Posição Consolidada

CONSISTENTE

## Arquivos Não Analisáveis

"""

# Mantido para compatibilidade com testes que usam diretamente
ANALISE_WATSON = CONSOLIDADO_WATSON

AVALIACAO_OK = "## Avaliação\n\nAPROVADO. Output completo.\n"

DECISAO_WATSON = """## Decisão Final — Watson\n### Síntese\nBoa análise.\n
### Posição Adotada\nAcatada.\n### Overrule\nNÃO\n
### Alertas Críticos\nCONTAGEM: 0\n### Notas para Sherlock\nDados bem estruturados.\n"""

VALIDACAO_SHERLOCK = """## Resumo Executivo\nMódulo verificado.\n
## Classificação Ponto a Ponto\n### Item 1\n**Status:** ATENDIDO\n
## Inconsistências para Contraditório\n\n## Limitações e Pontos Não Verificáveis\n
## 10. Relatório Estruturado do Módulo\n
### 10.1 Identificação do Ciclo\nMOD_SINT_001\n
### 10.2 Síntese da Metodologia do Módulo\nMetodologia CBS.\n
### 10.3 Resultado da Verificação de Integridade (Camada 0)\nSem críticos.\n
### 10.4 Resultado da Verificação de Aderência Metodológica (Camadas 1 e 2)\nAtendido.\n
### 10.5 Consistência do Resultado Final (Camada 3)\nCONSISTENTE.\n
### 10.6 Ocorrências Identificadas\nNenhuma.\n
### 10.7 Verificações Criadas pelos Agentes\nNenhuma.\n
### 10.8 Análise de Impacto Sistêmico\nNenhum.\n
### 10.9 Pendências para Validação no Simulador Completo\nNenhuma.\n
### 10.10 Decisões da Stranger Room\nNenhum dilema.\n
### 10.11 Histórico de Revalidações\nPrimeiro ciclo.\n"""

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
    13 chamadas LLM mockadas (4 arquivos → 4×analisar_arquivo + 1×consolidar_watson).
    """
    PACOTE_SH3 = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS,                                                              # definir_tasks_watson (1)
        ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, # analisar_arquivo ×4 (2-5)
        CONSOLIDADO_WATSON,                                                 # consolidar_watson (6)
        AVALIACAO_OK, DECISAO_WATSON,                                       # avaliar + fixar Watson (7-8)
        PACOTE_SH3,                                                         # montar_pacote_sherlock (9)
        VALIDACAO_SHERLOCK, VALIDACAO_SHERLOCK,                            # validar + consolidar_sherlock (10-11)
        AVALIACAO_OK, DECISAO_SHERLOCK,                                    # avaliar + fixar Sherlock (12-13)
        RELATORIO,                                                          # consolidação (14)
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
        json.loads(ln)
        for ln in (cycle_dir / "_runtime" / "events.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    tipos = [e["event_type"] for e in eventos]
    assert "CYCLE_STARTED" in tipos
    assert "CONSOLIDACAO_CONCLUIDA" in tipos
    assert tipos.count("PHASE_ENDED") == 2  # Watson e Sherlock


def test_alerta_critico_pausa_antes_de_sherlock(httpx_mock: HTTPXMock, ciclo, cfg, workspace):
    """
    Watson com alerta crítico: Orquestrador pausa, aguarda Lestrade.
    8 chamadas mockadas: tasks + 4×arquivo (1 crítico + 3 normais) + consolidar + avaliar + fixar.
    """
    ANALISE_COM_CRITICO = """## Análise do Arquivo

Problema identificado.

## Insumos da Cadeia

Entrada: dados brutos. Saída: dados com inconsistência.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|
| CRÍTICA | planilha, aba 1 | Total não fecha |

## Arquivos Não Analisáveis

## Último ID de Alerta Usado

W001-001
"""
    CONSOLIDADO_COM_CRITICO = """## Resumo Executivo

Problema identificado na análise dos arquivos.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|
| CRÍTICA | planilha, aba 1 | Total não fecha |

## Posição Consolidada

INCONSISTENTE

## Arquivos Não Analisáveis

"""
    DECISAO_CRITICA = """## Decisão Final — Watson\n### Síntese\nAlerta.\n
### Posição Adotada\nMantida.\n### Overrule\nNÃO\n
### Alertas Críticos\nCONTAGEM: 1\n### Notas para Sherlock\nAtenção ao total.\n"""

    for content in [
        TASKS,                                                              # definir_tasks_watson (1)
        ANALISE_COM_CRITICO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO,  # analisar_arquivo ×4 (2-5)
        CONSOLIDADO_COM_CRITICO,                                            # consolidar_watson (6)
        AVALIACAO_OK, DECISAO_CRITICA,                                      # avaliar + fixar (7-8)
    ]:
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
