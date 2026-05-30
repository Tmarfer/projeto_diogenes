"""
tests/integration/test_ciclo_com_irene.py — DVA-CBS | Projeto Diógenes
Testes de integração do fluxo com Irene habilitado.

Estratégia:
  - DIOGENES_IRENE_HABILITADO=true no monkeypatch
  - diogenes.irene.executar_irene e verificar_catalogo_existente mockados
    via unittest.mock.patch — nenhuma chamada real ao Irene/ChatTCU/LLM
  - LLM (Watson/Sherlock/Mycroft) mockados via pytest-httpx (OpenRouter provider)
  - Verifica: transições de estado corretas, métricas gravadas no audit_index,
    OrchestratorError em caso de IRENE_ERRO_FATAL
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_httpx import HTTPXMock

from diogenes.config import get_config
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex


# ── Respostas LLM mockadas ────────────────────────────────────────────────────

def _llm_resp(content: str, model: str = "google/gemini-2.0-flash-exp:free") -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        "system_fingerprint": "fp_test",
    }


# Conteúdo mínimo válido para cada fase LLM — formatos compatíveis com os parsers
_TASKS = "## Tasks para Watson\n\n1. Analisar planilha_cbs.xlsx\n**Planilha de Verificação no pacote:** Não\n"

_ANALISE = """## Análise do Arquivo

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

_CONSOLIDADO = """## Resumo Executivo

Análise de integridade do módulo MOD_SINT_001 concluída.

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|

## Cadeia de Produção dos Dados

script → planilha → resultado

## Posição Consolidada

CONSISTENTE

## Arquivos Não Analisáveis

"""

# "## Avaliação" header é obrigatório — _parsear_avaliacao usa _extrair_secoes
_AVALIACAO = "## Avaliação\n\nAPROVADO. Output completo e tecnicamente consistente.\n"

_DECISAO = """## Decisão Final — Watson
### Síntese
Boa análise.
### Posição Adotada
Acatada.
### Overrule
NÃO
### Alertas Críticos
CONTAGEM: 0
### Notas para Sherlock
Dados bem estruturados.
"""

_PACOTE = "## Pacote para Sherlock\n\nContexto sintetizado.\n"

# VALIDACAO_SHERLOCK precisa das 11 seções 10.1–10.11 para passar na verificação de completude
_SHERLOCK = """## Resumo Executivo
Módulo verificado.
## Classificação Ponto a Ponto
### Item 1
**Status:** ATENDIDO
## Inconsistências para Contraditório

## Limitações e Pontos Não Verificáveis

## 10. Relatório Estruturado do Módulo

### 10.1 Identificação do Ciclo
MOD_SINT_001
### 10.2 Síntese da Metodologia do Módulo
Metodologia CBS.
### 10.3 Resultado da Verificação de Integridade (Camada 0)
Sem críticos.
### 10.4 Resultado da Verificação de Aderência Metodológica (Camadas 1 e 2)
Atendido.
### 10.5 Consistência do Resultado Final (Camada 3)
CONSISTENTE.
### 10.6 Ocorrências Identificadas
Nenhuma.
### 10.7 Verificações Criadas pelos Agentes
Nenhuma.
### 10.8 Análise de Impacto Sistêmico
Nenhum.
### 10.9 Pendências para Validação no Simulador Completo
Nenhuma.
### 10.10 Decisões da Stranger Room
Nenhum dilema.
### 10.11 Histórico de Revalidações
Primeiro ciclo.
"""

_DECISAO_SH = """## Decisão Final — Sherlock
### Síntese
Validação completa.
### Posição Adotada
Acatada.
### Overrule
NÃO
### Dilemas
CONTAGEM: 0
### Encaminhamento
Nenhum.
"""

_CONSOLIDA = """# Relatório Preliminar de Análise
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

_METRICAS_APROVADO = {
    "score_consolidado": 0.9737,
    "recomendacao": "APROVADO",
    "versao_irene": "1.3.1",
    "abas_classificadas": 3,
    "abas_total": 3,
    "tokens_total": 1500,
    "dir_saida": "/tmp/irene_out/MOD_SINT_001",
    "artefatos": {"catalog": "/tmp/irene_out/MOD_SINT_001/irene_catalog.yaml"},
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cfg(env_vars: None, workspace: Path):
    return get_config()


@pytest.fixture
def ciclo_preparado(cfg, module_input: Path, workspace: Path):
    """Cria ciclo via MotorStart e avança para AGUARDANDO_CONFIRMACAO_MANIFESTO."""
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    AuditIndex(workspace).update_status(
        manifest.cycle_id,
        CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value,
    )
    return manifest


def _all_llm_mocks(httpx_mock: HTTPXMock, n_arquivos: int = 4) -> None:
    """Registra mocks LLM para o fluxo completo Watson → Sherlock → Mycroft.

    Sequência (13 chamadas para n_arquivos=4):
      1  definir_tasks_watson
      2–5  analisar_arquivo × n_arquivos
      6  consolidar_watson
      7  avaliar_agente (Watson) → APROVADO
      8  fixar_decisao (Watson)
      9  montar_pacote_sherlock
      10  validacao_inicial (Sherlock)
      11  avaliar_agente (Sherlock) → APROVADO
      12  fixar_decisao (Sherlock)
      13  consolidar (Mycroft — relatório final)
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    respostas = (
        [_TASKS]
        + [_ANALISE] * n_arquivos
        + [_CONSOLIDADO, _AVALIACAO, _DECISAO]
        + [_PACOTE, _SHERLOCK, _AVALIACAO, _DECISAO_SH]
        + [_CONSOLIDA]
    )
    for content in respostas:
        httpx_mock.add_response(url=url, json=_llm_resp(content))


# ── Testes: Irene APROVADO ────────────────────────────────────────────────────

class TestCicloComIreneAprovado:

    def test_transicoes_estado_corretas(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Com Irene retornando IRENE_APROVADO, o ciclo deve chegar a
        AGUARDANDO_VERIFICACAO_SAIDA com métricas gravadas no audit_index.
        """
        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()
        _all_llm_mocks(httpx_mock)

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(False, ""),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            return_value=("IRENE_APROVADO", _METRICAS_APROVADO),
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            resultado = orq.executar(ciclo_preparado)

        assert resultado != ""
        row = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
        assert row["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
        assert row["irene_resultado"] == "IRENE_APROVADO"
        assert row["irene_score"] == "0.9737"
        assert row["irene_dir_saida"] == "/tmp/irene_out/MOD_SINT_001"
        assert row["irene_invocada_at_utc"] != ""

    def test_metricas_score_gravado_corretamente(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()
        _all_llm_mocks(httpx_mock)

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(False, ""),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            return_value=("IRENE_APROVADO", _METRICAS_APROVADO),
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            orq.executar(ciclo_preparado)

        row = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
        assert float(row["irene_score"]) == pytest.approx(0.9737)


# ── Testes: Irene ERRO_FATAL ──────────────────────────────────────────────────

class TestCicloComIreneErroFatal:

    def test_irene_erro_fatal_aborta_ciclo(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IRENE_ERRO_FATAL → ABORTADO_FALHA_AGENTE + OrchestratorError."""
        from diogenes.orchestrator.exceptions import OrchestratorError

        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(False, ""),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            return_value=("IRENE_ERRO_FATAL", {}),
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            with pytest.raises(OrchestratorError, match="ERRO_FATAL"):
                orq.executar(ciclo_preparado)

        row = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
        assert row["status"] == CycleState.ABORTADO_FALHA_AGENTE.value


# ── Testes: catálogo reutilizável e Irene desabilitado ───────────────────────

class TestCicloComCatalogoReutilizado:

    def test_catalogo_existente_pula_irene(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Com catálogo reutilizável, executar_irene NÃO é chamado."""
        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()
        _all_llm_mocks(httpx_mock)

        executar_irene_mock = MagicMock(return_value=("IRENE_APROVADO", _METRICAS_APROVADO))

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(True, "/tmp/irene_out/MOD_SINT_001/irene_catalog.yaml"),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            executar_irene_mock,
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            resultado = orq.executar(ciclo_preparado)

        executar_irene_mock.assert_not_called()
        assert resultado != ""

    def test_irene_desabilitado_nao_executa(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock
    ) -> None:
        """Com DIOGENES_IRENE_HABILITADO=false (padrão em testes), Irene é ignorado."""
        # env_vars fixture já seta DIOGENES_IRENE_HABILITADO=false
        _all_llm_mocks(httpx_mock)

        executar_irene_mock = MagicMock(return_value=("IRENE_APROVADO", _METRICAS_APROVADO))

        with patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            executar_irene_mock,
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            resultado = orq.executar(ciclo_preparado)

        executar_irene_mock.assert_not_called()
        assert resultado != ""


# ── Testes: IRENE_ALERTA → Watson executa normalmente ────────────────────────

class TestCicloComIreneAlerta:

    def test_irene_alerta_continua_watson(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IRENE_ALERTA não bloqueia — Watson executa normalmente com catálogo."""
        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()
        _all_llm_mocks(httpx_mock)

        metricas_alerta = {
            **_METRICAS_APROVADO,
            "score_consolidado": 0.72,
            "recomendacao": "ALERTA",
        }

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(False, ""),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            return_value=("IRENE_ALERTA", metricas_alerta),
        ), patch(
            "diogenes.orchestrator.orchestrator.copiar_catalogo_para_ciclo",
            return_value=None,
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            resultado = orq.executar(ciclo_preparado)

        assert resultado != ""
        row = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
        assert row["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
        assert row["irene_resultado"] == "IRENE_ALERTA"
        assert float(row["irene_score"]) == pytest.approx(0.72)

    def test_irene_bloqueado_continua_watson(
        self, ciclo_preparado, workspace: Path,
        httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IRENE_BLOQUEADO não é fatal — Watson recebe catálogo com flag."""
        monkeypatch.setenv("DIOGENES_IRENE_HABILITADO", "true")
        get_config.cache_clear()
        _all_llm_mocks(httpx_mock)

        metricas_bloqueado = {
            **_METRICAS_APROVADO,
            "score_consolidado": 0.45,
            "recomendacao": "BLOQUEADO",
        }

        with patch(
            "diogenes.orchestrator.orchestrator.verificar_catalogo_existente",
            return_value=(False, ""),
        ), patch(
            "diogenes.orchestrator.orchestrator.executar_irene",
            return_value=("IRENE_BLOQUEADO", metricas_bloqueado),
        ), patch(
            "diogenes.orchestrator.orchestrator.copiar_catalogo_para_ciclo",
            return_value=None,
        ):
            orq = Orchestrator(ciclo_preparado.cycle_id)
            resultado = orq.executar(ciclo_preparado)

        assert resultado != ""
        row = AuditIndex(workspace).get_cycle(ciclo_preparado.cycle_id)
        assert row["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
        assert row["irene_resultado"] == "IRENE_BLOQUEADO"
