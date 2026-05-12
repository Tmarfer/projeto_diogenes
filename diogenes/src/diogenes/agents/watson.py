"""
agents/watson.py — DVA-CBS | Projeto Diógenes
WatsonAgent — Auditor de Integridade Técnica.

Constrói prompts com heartbeat injetado, chama LLM, parseia output.
Referência normativa: RF-WA-01 a RF-WA-10 (PRD v0.1), Bloco 9.3 (SDD v0.1)
"""
from __future__ import annotations
from pathlib import Path

from diogenes.config import AgentSpec
from diogenes.models import LLMCall, LLMMessage, WatsonOutput, CycleManifest
from diogenes.llm.base import LLMClient
from diogenes.llm.seed import calcular_seed
from diogenes.llm.call_id import gerar_call_id
from diogenes.agents.file_prep import preparar_arquivo
from diogenes.agents.heartbeat import HeartbeatLoader, injetar_heartbeat


class WatsonAgent:
    FASE = "watson_integridade"

    def __init__(self, llm: LLMClient, agent_spec: AgentSpec,
                 cycle_id: str, docs_dir: Path) -> None:
        self._llm = llm
        self._spec = agent_spec
        self._cycle_id = cycle_id
        self._docs_dir = docs_dir
        self._system_prompt = self._construir_system_prompt()
        self._heartbeat = HeartbeatLoader(docs_dir / "heartbeat.md")

    def analisar(
        self,
        inputs_dir: Path,
        manifest: CycleManifest,
        tasks_mycroft: str = "",
        proximo_id_alerta: str = "",
    ) -> WatsonOutput:
        """
        Análise de integridade do pacote completo.
        proximo_id_alerta: ex. "W010-001" — injetado no preamble para Watson.
        """
        call_type = "analise_inicial"
        hb = self._heartbeat.get_section(call_type)

        # Preamble: próximo ID de alerta (se fornecido)
        preamble_partes: list[str] = []
        if proximo_id_alerta:
            preamble_partes.append(
                f"**Próximo ID de alerta disponível:** `{proximo_id_alerta}`"
            )

        # Inputs: tasks de Mycroft + arquivos
        conteudo_partes: list[str] = []
        if tasks_mycroft:
            conteudo_partes.append(f"[TASKS DE MYCROFT]\n{tasks_mycroft}")
        for fi in manifest.input_files:
            path = inputs_dir / fi.rel_path
            conteudo = preparar_arquivo(path)
            conteudo_partes.append(f"[ARQUIVO: {fi.name}]\n{conteudo}")

        user_base = "\n\n".join(preamble_partes + conteudo_partes)
        user = injetar_heartbeat(hb, user_base)

        resp = self._llm.complete(LLMCall(
            call_id=gerar_call_id("watson", call_type),
            cycle_id=self._cycle_id, phase=self.FASE,
            agent="watson", call_type=call_type,
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
        ))
        return self._parsear_output(resp.content)

    def responder_critica(
        self, critica: str, output_anterior: WatsonOutput, rodada: int
    ) -> WatsonOutput:
        call_type = f"resposta_r{rodada}"
        hb = self._heartbeat.get_section(call_type)

        user_base = (
            f"## Seu output anterior\n\n{output_anterior.texto}\n\n"
            f"---\n\n## Crítica de Mycroft\n\n{critica}\n\n"
            f"---\n\nResponda a cada ponto da crítica. Acate com correção "
            f"ou sustente com evidência localizada no consolidado."
        )
        user = injetar_heartbeat(hb, user_base)

        resp = self._llm.complete(LLMCall(
            call_id=gerar_call_id("watson", call_type),
            cycle_id=self._cycle_id, phase=self.FASE,
            agent="watson", call_type=call_type,
            model=self._spec.modelo, temperature=self._spec.temperatura,
            max_tokens=self._spec.max_tokens,
            seed=calcular_seed(42, self._cycle_id, self.FASE, call_type, rodada),
            messages=[
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=user),
            ],
            timeout_segundos=self._spec.timeout_segundos,
            max_tentativas_retry=self._spec.max_tentativas_retry,
            backoff_segundos=self._spec.backoff_segundos,
        ))
        return self._parsear_output(resp.content)

    # ── Internos ─────────────────────────────────────────────

    def _construir_system_prompt(self) -> str:
        soul = (self._docs_dir / "soul.md").read_text(encoding="utf-8")
        skills = (self._docs_dir / "skills.md").read_text(encoding="utf-8")
        return f"{soul}\n\n---\n\n{skills}"

    def _parsear_output(self, content: str) -> WatsonOutput:
        secoes = _extrair_secoes(content)
        criticos = _contar_criticos(secoes.get("Tabela de Alertas", ""))
        nao_analisaveis = secoes.get("Arquivos Não Analisáveis", "").strip()
        return WatsonOutput(
            texto=content,
            critical_alerts_count=criticos,
            has_unanalyzable_files=bool(nao_analisaveis),
            secoes=secoes,
        )


def _extrair_secoes(content: str) -> dict:
    secoes: dict = {}
    atual: str | None = None
    linhas: list[str] = []
    for linha in content.splitlines():
        if linha.startswith("## "):
            if atual is not None:
                secoes[atual] = "\n".join(linhas).strip()
            atual = linha[3:].strip()
            linhas = []
        elif atual is not None:
            linhas.append(linha)
    if atual is not None:
        secoes[atual] = "\n".join(linhas).strip()
    return secoes


def _contar_criticos(tabela: str) -> int:
    return sum(
        1 for l in tabela.splitlines()
        if "CRÍTICA" in l.upper() or "CRITICA" in l.upper()
    )
