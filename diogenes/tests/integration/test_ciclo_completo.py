"""
tests/integration/test_ciclo_completo.py
Ciclo end-to-end com mock de chamadas LLM via pytest-httpx.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from pytest_httpx import HTTPXMock
from diogenes.config import get_config
from diogenes.models import CycleManifest, InputFileInfo
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex
from diogenes.orchestrator.states import CycleState


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

ANALISE_WATSON = """## Resumo Executivo

Análise de integridade do módulo MOD_SINT_001.

## Verificação Numérica das Planilhas

### planilha_cbs.xlsx
- Totais verificados: sim
- Inconsistências: nenhuma

## Tradução dos Scripts SQL

### script_extracao.sql
**O que executa:** seleciona dados de arrecadação

## Cadeia de Produção dos Dados

script → planilha → resultado

## Insights e Anomalias

Nenhuma anomalia detectada.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|
| INFORMATIVA | planilha_cbs.xlsx | Estrutura consistente |

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
    # Mockar as quatro chamadas em ordem
    PACOTE_SH = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS_WATSON, ANALISE_WATSON, AVALIACAO_APROVADO, DECISAO_FINAL,  # Watson (4)
        PACOTE_SH,                                                          # montar_pacote_sherlock (5)
        VALIDACAO_SHERLOCK, AVALIACAO_APROVADO, DECISAO_SHERLOCK_COMPLETO, RELATORIO_COMPLETO,  # Sherlock (6-9)
    ]:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            json=_mock_response(content),
        )

    orq = Orchestrator(ciclo_preparado.cycle_id)
    resultado = orq.executar(ciclo_preparado)

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
    eventos = [json.loads(l) for l in events_path.read_text().splitlines() if l.strip()]
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
    PACOTE_SH2 = "## Pacote para Sherlock\n\nContexto sintetizado."
    for content in [
        TASKS_WATSON, ANALISE_WATSON, AVALIACAO_QUESTIONAR,
        ANALISE_WATSON, AVALIACAO_APROVADO, DECISAO_FINAL,  # Watson com 1 revisão (6)
        PACOTE_SH2,                                         # montar_pacote_sherlock (7)
        VALIDACAO_SHERLOCK, AVALIACAO_APROVADO, DECISAO_SHERLOCK_COMPLETO, RELATORIO_COMPLETO,
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
