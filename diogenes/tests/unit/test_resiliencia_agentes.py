"""
tests/unit/test_resiliencia_agentes.py

Resiliência pós-rodada noturna MOD_010 (2026-06-11):
- Sherlock.validar com degradação escalonada (pacote completo → réguas truncadas
  → fallback determinístico marcado is_fallback=True);
- Watson.consolidar em lotes (map-reduce) acima do limiar de chars;
- Fallbacks marcados is_fallback para o gate do Orquestrador pausar o ciclo
  em vez de chancelar relatório materialmente vazio.
"""
from __future__ import annotations

from pathlib import Path

from diogenes.agents.sherlock import (
    _LIMITES_REDUCAO_PACOTE,
    SherlockAgent,
    reduzir_pacote_sherlock,
)
from diogenes.agents.watson import (
    _MAX_CHARS_CONSOLIDACAO_MONOLITICA,
    WatsonAgent,
    dividir_lotes_consolidacao,
)
from diogenes.config import AgentSpec
from diogenes.llm.exceptions import LLMTimeoutError
from diogenes.models import LLMCall, LLMResponse, SherlockOutput, WatsonOutput
from diogenes.orchestrator.states import TRANSICOES_VALIDAS, CycleState

_DOCS = Path("docs/agentes")


def _spec() -> AgentSpec:
    return AgentSpec(
        modelo="modelo-teste", temperatura=0.0, max_tokens=1000,
        max_tokens_ciclo=100000, timeout_segundos=10,
        max_tentativas_retry=4, backoff_segundos=0,
    )


class _LLMRoteirizado:
    """LLM fake: levanta timeout nas N primeiras chamadas, depois responde."""

    def __init__(self, timeouts_antes_de_responder: int, resposta: str = "OK") -> None:
        self._timeouts = timeouts_antes_de_responder
        self._resposta = resposta
        self.calls: list[LLMCall] = []

    def complete(self, call: LLMCall) -> LLMResponse:
        self.calls.append(call)
        if len(self.calls) <= self._timeouts:
            raise LLMTimeoutError(f"timeout simulado (chamada {len(self.calls)})")
        return LLMResponse(
            call_id=call.call_id, content=self._resposta,
            model_used="modelo-teste", system_fingerprint=None,
            prompt_tokens=1, completion_tokens=1, total_tokens=2,
            cost_usd=0.0, latency_ms=1, retry_attempts=0, http_status=200,
        )


def _pacote_sherlock_grande() -> str:
    metodologia = "M" * 60_000
    corpus = "J" * 25_000
    return (
        "## Síntese de Mycroft\n\nsintese"
        "\n\n---\n\n## Análise de Integridade Técnica — Resultado Completo\n\n"
        + "W" * 10_000
        + "\n\n---\n\n## Metodologia e Regra de Negócio do Módulo\n\n" + metodologia
        + "\n\n---\n\n## Arcabouço Jurídico Curado — Dispositivos Aplicáveis\n\n" + corpus
    )


# ── reduzir_pacote_sherlock ───────────────────────────────────────────────────

class TestReduzirPacoteSherlock:
    def test_trunca_reguas_e_preserva_watson(self):
        pacote = _pacote_sherlock_grande()
        reduzido = reduzir_pacote_sherlock(pacote)
        assert len(reduzido) < len(pacote)
        assert "RÉGUA TRUNCADA" in reduzido
        # análise Watson permanece íntegra
        assert "W" * 10_000 in reduzido
        # corpo da metodologia respeitou o limite
        limite_met = _LIMITES_REDUCAO_PACOTE["## Metodologia e Regra de Negócio do Módulo"]
        assert "M" * (limite_met + 1) not in reduzido

    def test_pacote_pequeno_intocado(self):
        pacote = (
            "## Síntese\n\nok\n\n---\n\n## Metodologia e Regra de Negócio do Módulo\n\ncurta"
        )
        assert reduzir_pacote_sherlock(pacote) == pacote

    def test_sem_secoes_de_regua(self):
        assert reduzir_pacote_sherlock("texto sem reguas") == "texto sem reguas"


# ── Sherlock.validar — degradação escalonada ──────────────────────────────────

class TestSherlockValidarEscalonado:
    def _agente(self, llm) -> SherlockAgent:
        return SherlockAgent(
            llm=llm, agent_spec=_spec(), cycle_id="CICLO_TESTE",
            docs_dir=_DOCS / "sherlock",
        )

    def test_estagio1_sucesso_nao_degrada(self):
        llm = _LLMRoteirizado(0, resposta="## Validação\n\nconteudo")
        out = self._agente(llm).validar(_pacote_sherlock_grande())
        assert not out.is_fallback
        assert len(llm.calls) == 1
        # estágio 1 usa retries reduzidos por estágio
        assert llm.calls[0].max_tentativas_retry == 2

    def test_estagio2_usa_pacote_reduzido(self):
        llm = _LLMRoteirizado(1, resposta="## Validação\n\nconteudo degradado")
        out = self._agente(llm).validar(_pacote_sherlock_grande())
        assert not out.is_fallback
        assert len(llm.calls) == 2
        user_2 = llm.calls[1].messages[-1].content
        assert "MODO DEGRADADO" in user_2
        assert "RÉGUA TRUNCADA" in user_2

    def test_estagio3_fallback_marcado(self):
        llm = _LLMRoteirizado(99)
        out = self._agente(llm).validar(_pacote_sherlock_grande())
        assert out.is_fallback
        assert "INVÁLIDO PARA CONSOLIDAÇÃO" in out.texto
        # 2 estágios LLM tentados antes do fallback
        assert len(llm.calls) == 2

    def test_pacote_sem_reguas_pula_estagio2(self):
        llm = _LLMRoteirizado(99)
        out = self._agente(llm).validar("pacote curto sem seções de régua")
        assert out.is_fallback
        assert len(llm.calls) == 1


# ── Watson — divisão em lotes e consolidação map-reduce ──────────────────────

def _analise(texto: str, criticos: int = 0) -> WatsonOutput:
    return WatsonOutput(
        texto=texto, critical_alerts_count=criticos,
        has_unanalyzable_files=False, secoes={},
    )


class TestDividirLotes:
    def test_abaixo_do_limite_um_lote(self):
        analises = [_analise("a" * 100) for _ in range(5)]
        assert len(dividir_lotes_consolidacao(analises, max_chars=1000)) == 1

    def test_particiona_contiguamente(self):
        analises = [_analise(f"{i}" * 400) for i in range(6)]
        lotes = dividir_lotes_consolidacao(analises, max_chars=1000)
        assert len(lotes) == 3
        assert [len(lote) for lote in lotes] == [2, 2, 2]
        # ordem preservada
        flat = [a for lote in lotes for a in lote]
        assert flat == analises

    def test_analise_maior_que_limite_vira_lote_proprio(self):
        analises = [_analise("x" * 50), _analise("y" * 2000), _analise("z" * 50)]
        lotes = dividir_lotes_consolidacao(analises, max_chars=1000)
        assert len(lotes) == 3


class TestWatsonConsolidarLotes:
    def _agente(self, llm) -> WatsonAgent:
        return WatsonAgent(
            llm=llm, agent_spec=_spec(), cycle_id="CICLO_TESTE",
            docs_dir=_DOCS / "watson",
        )

    def test_monolitico_abaixo_do_limiar(self):
        llm = _LLMRoteirizado(0, resposta="## 1. Síntese Executiva\n\nok")
        out = self._agente(llm).consolidar([_analise("pequena", criticos=2)])
        assert not out.is_fallback
        assert out.critical_alerts_count == 2
        assert len(llm.calls) == 1

    def test_lotes_acima_do_limiar(self):
        tam = _MAX_CHARS_CONSOLIDACAO_MONOLITICA // 2 + 1000
        analises = [_analise("a" * tam, criticos=1) for _ in range(3)]
        llm = _LLMRoteirizado(0, resposta="## 1. Síntese Executiva\n\nparcial/final")
        out = self._agente(llm).consolidar(analises)
        assert not out.is_fallback
        # 3 lotes + 1 redução final = 4 chamadas
        assert len(llm.calls) == 4
        users = [c.messages[-1].content for c in llm.calls]
        assert all("CONSOLIDAÇÃO PARCIAL — LOTE" in u for u in users[:3])
        assert "CONSOLIDAÇÃO FINAL — REDUÇÃO DE 3 LOTES" in users[3]
        # defesa de contagem: soma das análises individuais prevalece
        assert out.critical_alerts_count == 3

    def test_fallback_marcado_preserva_contagens(self):
        llm = _LLMRoteirizado(99)
        out = self._agente(llm).consolidar(
            [_analise("a", criticos=3), _analise("b", criticos=2)]
        )
        assert out.is_fallback
        assert out.critical_alerts_count == 5
        assert "INVÁLIDO PARA CONSOLIDAÇÃO" in out.texto


# ── Máquina de estados: pausa e retomada por fallback ─────────────────────────

class TestTransicoesFallback:
    def test_fases_executoras_podem_pausar(self):
        assert CycleState.PAUSADO_LESTRADE in TRANSICOES_VALIDAS[CycleState.EM_EXECUCAO_WATSON]
        assert CycleState.PAUSADO_LESTRADE in TRANSICOES_VALIDAS[CycleState.EM_EXECUCAO_SHERLOCK]

    def test_pausado_retoma_para_ambas_as_fases(self):
        destinos = TRANSICOES_VALIDAS[CycleState.PAUSADO_LESTRADE]
        assert CycleState.EM_EXECUCAO_WATSON in destinos
        assert CycleState.EM_EXECUCAO_SHERLOCK in destinos


def test_sherlock_output_default_nao_e_fallback():
    out = SherlockOutput(texto="x", dilemmas_count=0, has_divergencias=False, secoes={})
    assert out.is_fallback is False


# ── Fallback da planilha RN também marcado ────────────────────────────────────

def test_sherlock_planilha_rn_fallback_marcado():
    llm = _LLMRoteirizado(99)
    ag = SherlockAgent(
        llm=llm, agent_spec=_spec(), cycle_id="CICLO_TESTE",
        docs_dir=_DOCS / "sherlock",
    )
    out = ag.validacao_planilha_rn_sherlock("pacote", "planilha")
    assert out.is_fallback
