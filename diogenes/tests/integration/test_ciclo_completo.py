"""
tests/integration/test_ciclo_completo.py
Ciclo end-to-end com mock de chamadas LLM via pytest-httpx.
"""
from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from diogenes.config import get_config
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex


def _mock_response(content: str, model: str = "google/gemini-2.0-flash-exp:free") -> dict:
    """Monta resposta no formato da API OpenAI-compatible."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        "system_fingerprint": "fp_test",
    }


# Respostas mockadas para o ciclo Watson completo
TASKS_WATSON = """## Tasks para Watson

1. Analisar planilha_cbs.xlsx: verificar fechamento numérico
2. Traduzir script_extracao.sql para linguagem natural
3. Identificar cadeia de produção dos dados
"""

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

ANALISE_WATSON = ANALISE_ARQUIVO  # alias mantido para testes de revisão

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

AVALIACAO_APROVADO = """## Avaliação

APROVADO. O output de Watson é completo e tecnicamente consistente.
"""

DECISAO_FINAL = """## Decisão Final — Watson

### Síntese

Watson produziu análise completa e aprovada.

### Posição Adotada

Análise acatada integralmente.

### Overrule

NÃO

### Alertas Críticos

CONTAGEM: 0

### Notas para Sherlock

Módulo com dados bem estruturados e rastreáveis.
"""

VALIDACAO_SHERLOCK = """## Resumo Executivo\nMódulo verificado.\n
## Classificação Ponto a Ponto\n### Item 1\n**Status:** ATENDIDO\n
## Inconsistências para Contraditório\n\n## Limitações\n"""

DECISAO_SHERLOCK_COMPLETO = """## Decisão Final\n### Síntese\nValidação completa.\n
### Posição Adotada\nAcatada.\n### Overrule\nNÃO\n
### Dilemas\nCONTAGEM: 0\n### Encaminhamento\nNenhum.\n"""

RELATORIO_COMPLETO = """# Relatório Preliminar de Análise\n**Processo:** TC 015.848/2025-6\n"""



@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


@pytest.fixture
def ciclo_preparado(cfg, module_input, workspace):
    """
    Prepara ciclo via Motor de Start e avança para AGUARDANDO_CONFIRMACAO_MANIFESTO,
    simulando o que `diogenes confirm-manifest` faz antes de acionar o Orquestrador.
    """
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    # Simular confirm-manifest: avançar o status
    from diogenes.orchestrator.states import CycleState
    AuditIndex(workspace).update_status(
        manifest.cycle_id,
        CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value,
    )
    return manifest


def test_fase_watson_completa_sem_revisao(httpx_mock: HTTPXMock, ciclo_preparado, cfg, workspace):
    """
    Testa o fluxo Watson completo: Mycroft define tasks → Watson analisa →
    Mycroft aprova → Mycroft fixa decisão.
    Quatro chamadas LLM mockadas.
    """
    # 4 arquivos no módulo → 4 calls analisar_arquivo + 1 consolidar_watson
    PACOTE_SH = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS_WATSON,                                               # definir_tasks_watson (1)
        ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO,  # analisar_arquivo ×4 (2-5)
        CONSOLIDADO_WATSON,                                         # consolidar_watson (6)
        AVALIACAO_APROVADO, DECISAO_FINAL,                         # avaliar + fixar Watson (7-8)
        PACOTE_SH,                                                  # montar_pacote_sherlock (9)
        VALIDACAO_SHERLOCK, AVALIACAO_APROVADO, DECISAO_SHERLOCK_COMPLETO, RELATORIO_COMPLETO,  # Sherlock (10-13)
    ]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            json=_mock_response(content),
        )

    orq = Orchestrator(ciclo_preparado.cycle_id)
    orq.executar(ciclo_preparado)

    # Verificar estado no audit_index
    record = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
    assert record is not None
    assert record["watson_rodadas"] == "0"
    assert record["watson_critical_alerts_count"] == "0"
    assert record["mycroft_overruled_watson"] == "false"
    # Sprint 2: após Watson sem alerta, sistema aguarda Sherlock (Sprint 4)
    assert record["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value

    # Verificar arquivos da Stranger's Room
    cycle_dir = workspace / "cycles" / ciclo_preparado.cycle_id
    sr_dir = cycle_dir / "stranger_room" / "watson_integridade"
    assert (sr_dir / "01_apresentacao.md").exists()
    assert (sr_dir / "99_decisao_final.md").exists()
    # Sem revisão → apenas apresentacao e decisao_final
    assert not (sr_dir / "02_critica_mycroft_r1.md").exists()

    # Verificar events.jsonl
    events_path = cycle_dir / "_runtime" / "events.jsonl"
    assert events_path.exists()
    eventos = [json.loads(ln) for ln in events_path.read_text().splitlines() if ln.strip()]
    tipos = [e["event_type"] for e in eventos]
    assert "CYCLE_STARTED" in tipos
    assert "PHASE_ENDED" in tipos


def test_fase_watson_com_uma_revisao(httpx_mock: HTTPXMock, ciclo_preparado, cfg, workspace):
    """
    Testa Watson com uma rodada de revisão: Mycroft questiona → Watson responde
    → Mycroft aprova → Mycroft fixa decisão. Seis chamadas mockadas.
    """
    AVALIACAO_QUESTIONAR = """## Avaliação

QUESTIONAR. Há pontos a esclarecer.

## Pontos para Revisão

1. Seção "Verificação Numérica": detalhar o método de verificação dos totais
"""
    # 4 arquivos → 4 per-file + 1 consolidar + revisão Watson
    PACOTE_SH2 = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS_WATSON,                                               # definir_tasks_watson (1)
        ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO, ANALISE_ARQUIVO,  # analisar_arquivo ×4 (2-5)
        CONSOLIDADO_WATSON,                                         # consolidar_watson (6)
        AVALIACAO_QUESTIONAR,                                       # avaliar r0 → QUESTIONAR (7)
        ANALISE_WATSON,                                             # resposta_r1 Watson (8)
        AVALIACAO_APROVADO, DECISAO_FINAL,                         # avaliar r1 + fixar (9-10)
        PACOTE_SH2,                                                 # montar_pacote_sherlock (11)
        VALIDACAO_SHERLOCK, AVALIACAO_APROVADO, DECISAO_SHERLOCK_COMPLETO, RELATORIO_COMPLETO,  # Sherlock (12-15)
    ]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            json=_mock_response(content),
        )

    orq = Orchestrator(ciclo_preparado.cycle_id)
    orq.executar(ciclo_preparado)

    record = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
    assert record["watson_rodadas"] == "1"
    assert record["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value

    sr_dir = workspace / "cycles" / ciclo_preparado.cycle_id / "stranger_room" / "watson_integridade"
    assert (sr_dir / "02_critica_mycroft_r1.md").exists()
    assert (sr_dir / "03_resposta_r1.md").exists()
    assert not (sr_dir / "04_critica_mycroft_r2.md").exists()
