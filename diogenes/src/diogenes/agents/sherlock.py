"""
agents/sherlock.py — DVA-CBS | Projeto Diógenes
SherlockAgent — Auditor de Validação Metodológica CBS.

Recebe pacote integrado de Mycroft. Heartbeat injetado em todas as chamadas.
Referência normativa: RF-SH-01 a RF-SH-08 (PRD v0.1), Bloco 9.4 (SDD v0.1)
"""
from __future__ import annotations

import re
from pathlib import Path

from diogenes.agents.heartbeat import HeartbeatLoader, injetar_heartbeat
from diogenes.config import AgentSpec
from diogenes.llm.base import LLMClient
from diogenes.llm.call_id import gerar_call_id
from diogenes.llm.seed import calcular_seed
from diogenes.models import LLMCall, LLMMessage, SherlockOutput


class SherlockAgent:
    FASE = "sherlock_validacao"

    def __init__(self, llm: LLMClient, agent_spec: AgentSpec,
                 cycle_id: str, docs_dir: Path) -> None:
        self._llm = llm
        self._spec = agent_spec
        self._cycle_id = cycle_id
        self._docs_dir = docs_dir
        self._system_prompt = self._construir_system_prompt()
        self._heartbeat = HeartbeatLoader(docs_dir / "heartbeat.md")

    def validar(self, pacote_sherlock: str) -> SherlockOutput:
        call_type = "validacao_inicial"
        hb = self._heartbeat.get_section(call_type)
        user = injetar_heartbeat(hb, pacote_sherlock)
        resp = self._llm.complete(self._montar_call(call_type, user))
        return self._parsear_output(resp.content)

    def validacao_planilha_rn_sherlock(
        self,
        pacote_sherlock: str,
        watson_planilha_rn: str,
    ) -> SherlockOutput:
        """
        Fase opcional: percorre a Planilha de Verificação já preenchida por Watson
        sob perspectiva metodológica (call_type validacao_planilha_rn_sherlock).
        Acionado apenas quando a planilha está listada no manifesto.
        """
        call_type = "validacao_planilha_rn_sherlock"
        hb = self._heartbeat.get_section(call_type)
        user_base = (
            f"## Pacote de Contexto Sherlock\n\n{pacote_sherlock}\n\n"
            f"---\n\n## Planilha de Verificação preenchida por Watson\n\n{watson_planilha_rn}"
        )
        user = injetar_heartbeat(hb, user_base)
        resp = self._llm.complete(self._montar_call(call_type, user))
        return self._parsear_output(resp.content)

    def consolidar(
        self,
        pontos_output: SherlockOutput,
        planilha_output: SherlockOutput | None = None,
    ) -> SherlockOutput:
        """
        Fase 2 de Sherlock: consolida todos os sherlock_ponto_*.md e, quando
        disponível, o sherlock_planilha_rn.md (call_type consolidar_sherlock).
        Inclui: analise_impacto_entre_modulos, identificacao_pendencias_para_simulador_completo,
        relatorio_estruturado (11 seções), insumo_json_dashboard.
        """
        call_type = "consolidar_sherlock"
        hb = self._heartbeat.get_section(call_type)
        partes: list[str] = [f"## Verificações de Pontos Metodológicos\n\n{pontos_output.texto}"]
        if planilha_output:
            partes.append(
                f"\n\n---\n\n## Validação da Planilha de Verificação\n\n{planilha_output.texto}"
            )
        user = injetar_heartbeat(hb, "\n\n".join(partes))
        resp = self._llm.complete(self._montar_call(call_type, user))
        return self._parsear_output(resp.content)

    def responder_critica(self, critica: str, output_anterior: SherlockOutput,
                          rodada: int) -> SherlockOutput:
        call_type = f"resposta_r{rodada}"
        hb = self._heartbeat.get_section(call_type)
        user_base = (
            f"## Seu output anterior\n\n{output_anterior.texto}\n\n"
            f"---\n\n## Crítica de Mycroft\n\n{critica}\n\n"
            f"---\n\nResponda a cada ponto. Para cada classificação questionada: "
            f"acate com correção ou sustente com citação explícita do dispositivo "
            f"metodológico que fundamenta sua posição."
        )
        user = injetar_heartbeat(hb, user_base)
        resp = self._llm.complete(self._montar_call(call_type, user))
        return self._parsear_output(resp.content)

    # ── Internos ─────────────────────────────────────────────

    def _construir_system_prompt(self) -> str:
        soul = (self._docs_dir / "soul.md").read_text(encoding="utf-8")
        skills = (self._docs_dir / "skills.md").read_text(encoding="utf-8")
        return f"{soul}\n\n---\n\n{skills}"

    def _montar_call(self, call_type: str, user: str) -> LLMCall:
        return LLMCall(
            call_id=gerar_call_id("sherlock", call_type),
            cycle_id=self._cycle_id, phase=self.FASE,
            agent="sherlock", call_type=call_type,
            model=self._spec.modelo, temperature=self._spec.temperatura,
            max_tokens=self._spec.max_tokens,
            seed=calcular_seed(42, self._cycle_id, self.FASE, call_type),
            messages=[
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=user),
            ],
            timeout_segundos=self._spec.timeout_segundos,
            max_tentativas_retry=self._spec.max_tentativas_retry,
            backoff_segundos=self._spec.backoff_segundos,
        )

    def _parsear_output(self, content: str) -> SherlockOutput:
        secoes = _extrair_secoes(content)
        dilemas = secoes.get("Dilemas Interpretativos", "").strip()
        dilemmas_count = _contar_dilemas(dilemas)
        divergencias = any(
            "DIVERGÊNCIA" in v.upper() or "DIVERGENCIA" in v.upper()
            for v in secoes.values()
        )
        nota_metodologica = _extrair_bool_campo(
            content, "Nota metodológica com alteração verificada neste ponto"
        )
        notas_count = _extrair_int_campo(content, "Notas metodológicas com alteração")
        pendencias_count = _extrair_int_campo(content, "Pendências para simulador completo")
        return SherlockOutput(
            texto=content, dilemmas_count=dilemmas_count,
            has_divergencias=divergencias, secoes=secoes,
            nota_metodologica_com_alteracao=nota_metodologica,
            notas_metodologicas_count=notas_count,
            pendencias_simulador_count=pendencias_count,
        )


def _extrair_secoes(content: str) -> dict:
    secoes: dict = {}
    atual: str | None = None
    linhas: list[str] = []
    for linha in content.splitlines():
        if linha.startswith("## "):
            if atual:
                secoes[atual] = "\n".join(linhas).strip()
            atual = linha[3:].strip()
            linhas = []
        elif atual:
            linhas.append(linha)
    if atual:
        secoes[atual] = "\n".join(linhas).strip()
    return secoes


def _contar_dilemas(secao: str) -> int:
    return sum(1 for linha in secao.splitlines() if linha.startswith("### Dilema"))


def _extrair_bool_campo(content: str, campo: str) -> bool:
    """
    Extrai campo booleano de cabeçalho no formato `**campo:** Sim | Não | Não aplicável`.
    Retorna False por default quando ausente.
    """
    m = re.search(
        r'\*\*\s*' + re.escape(campo) + r'\s*:?\s*\*{0,2}\s*:?\s*(Sim|Não)',
        content, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower().startswith("sim")
    return False


def _extrair_int_campo(content: str, campo: str) -> int:
    """
    Extrai campo numérico de cabeçalho no formato `**campo:** n | 0`.
    Retorna 0 por default quando ausente ou não parseável.
    """
    m = re.search(
        r'\*\*\s*' + re.escape(campo) + r'\s*:?\s*\*{0,2}\s*:?\s*(\d+)',
        content, re.IGNORECASE,
    )
    if m:
        return int(m.group(1))
    return 0
