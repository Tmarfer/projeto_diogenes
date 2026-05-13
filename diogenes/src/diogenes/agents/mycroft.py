"""
agents/mycroft.py — DVA-CBS | Projeto Diógenes
MycrooftAgent (grafia do SDD) — Auditor Chefe.

Todos os call_types recebem a seção correspondente do heartbeat.md
injetada no início do user_prompt (antes dos inputs específicos).
Referência normativa: Bloco 9.2 (SDD v0.1)
"""
from __future__ import annotations

import re
from pathlib import Path

from diogenes.agents.heartbeat import HeartbeatLoader, injetar_heartbeat
from diogenes.config import AgentSpec
from diogenes.llm.base import LLMClient
from diogenes.llm.call_id import gerar_call_id
from diogenes.llm.seed import calcular_seed
from diogenes.models import (
    AvaliacaoMycroft,
    CycleManifest,
    DecisaoFinal,
    LLMCall,
    LLMMessage,
    RelatorioOutput,
    SherlockOutput,
    WatsonOutput,
)


class MycrooftAgent:
    FASE_WATSON  = "watson_integridade"
    FASE_SHERLOCK = "sherlock_validacao"

    def __init__(self, llm: LLMClient, agent_spec: AgentSpec,
                 cycle_id: str, docs_dir: Path) -> None:
        self._llm = llm
        self._spec = agent_spec
        self._cycle_id = cycle_id
        self._docs_dir = docs_dir
        self._system_prompt = self._construir_system_prompt()
        self._heartbeat = HeartbeatLoader(docs_dir / "heartbeat.md")

    # ── definir_tasks_watson ──────────────────────────────────

    def definir_tasks_watson(self, manifest: CycleManifest) -> str:
        call_type = "definir_tasks_watson"
        arquivos = "\n".join(
            f"- {fi.name} ({fi.extension}, {fi.size_bytes} bytes)"
            for fi in manifest.input_files
        )
        user_base = (
            f"## Manifesto do Ciclo\n\n"
            f"Módulo: {manifest.module_id}\n"
            f"Atividade: {manifest.activity}\n"
            f"Sala de Sigilo: {'Sim' if manifest.is_sigilo_module else 'Não'}\n"
            f"Prioridades definidas por Lestrade: "
            f"{manifest.prioridades_analise or '[não preenchido — aplicar ordem padrão]'}\n\n"
            f"## Arquivos do Pacote\n\n{arquivos}\n\n"
            f"Defina as tasks ordenadas para Watson. Produza a seção "
            f"'## Tasks para Watson' com lista numerada e a seção "
            f"'## Inputs Disponíveis' com ordem e origem da priorização."
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, self.FASE_WATSON, user))
        secoes = _extrair_secoes(resp.content)
        return secoes.get("Tasks para Watson", resp.content)

    # ── avaliar_watson ────────────────────────────────────────

    def avaliar_watson(self, apresentacao: WatsonOutput,
                       fase: str, rodada: int) -> AvaliacaoMycroft:
        call_type = "avaliar_agente"
        user_base = (
            f"## Contexto da Avaliação\n\n"
            f"Agente avaliado: Watson (Auditor de Integridade Técnica)\n"
            f"Rodada: {rodada}\n\n"
            f"## Output de Watson\n\n{apresentacao.texto}\n\n"
            f"Avalie. Produza:\n"
            f"- '## Avaliação' com 'APROVADO' ou 'QUESTIONAR' na primeira linha\n"
            f"- Se QUESTIONAR: '## Pontos para Revisão' com uma crítica única, "
            f"localizada e fundamentada"
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, fase, user))
        return _parsear_avaliacao(resp.content)

    # ── fixar_decisao_watson ──────────────────────────────────

    def fixar_decisao_watson(self, output_final: WatsonOutput,
                              rodadas_executadas: int) -> DecisaoFinal:
        call_type = "fixar_decisao"
        user_base = (
            f"## Contexto\n\nAgente: Watson | Rodadas executadas: {rodadas_executadas}\n\n"
            f"## Output Final de Watson\n\n{output_final.texto}\n\n"
            f"Produza a decisão final com as seções:\n"
            f"### Síntese\n### Posição Adotada\n"
            f"### Overrule\nSIM ou NÃO (com fundamentação se SIM)\n"
            f"### Alertas Críticos\nCONTAGEM: N\n"
            f"### Notas para Sherlock"
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, self.FASE_WATSON, user))
        return _parsear_decisao_final(resp.content, output_final.critical_alerts_count)

    # ── montar_pacote_sherlock ────────────────────────────────

    def montar_pacote_sherlock(
        self, manifest: CycleManifest, inputs_dir: Path, decisao_watson: DecisaoFinal
    ) -> str:
        call_type = "montar_pacote_sherlock"
        from diogenes.agents.file_prep import preparar_arquivo
        inventario = "\n".join(
            f"- {fi.name} ({fi.extension}, {fi.size_bytes} bytes)"
            for fi in manifest.input_files
        )
        docs_textuais: list[str] = []
        for fi in manifest.input_files:
            if fi.extension in (".md", ".pdf", ".txt"):
                path = inputs_dir / fi.rel_path
                if path.exists():
                    docs_textuais.append(
                        f"[DOCUMENTO: {fi.name}]\n{preparar_arquivo(path)}"
                    )
        docs_str = "\n\n".join(docs_textuais) if docs_textuais else \
                   "[Nenhum documento textual no pacote]"
        user_base = (
            f"## Contexto do Módulo\n\n"
            f"Módulo: {manifest.module_id} | Atividade: {manifest.activity}\n"
            f"Sala de Sigilo: {'Sim' if manifest.is_sigilo_module else 'Não'}\n\n"
            f"## Decisão Final de Mycroft sobre Watson\n\n{decisao_watson.texto}\n\n"
            f"## Inventário dos Artefatos Entregues\n\n{inventario}\n\n"
            f"## Documentos do Pacote\n\n{docs_str}\n\n"
            f"Monte o pacote integrado para Sherlock conforme o template "
            f"'montar_pacote_sherlock' do skills.md."
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, self.FASE_SHERLOCK, user))
        return resp.content

    # ── avaliar_sherlock ──────────────────────────────────────

    def avaliar_sherlock(self, apresentacao: SherlockOutput,
                         fase: str, rodada: int) -> AvaliacaoMycroft:
        call_type = "avaliar_sherlock"
        user_base = (
            f"## Contexto da Avaliação\n\n"
            f"Agente avaliado: Sherlock (Auditor de Validação Metodológica CBS)\n"
            f"Rodada: {rodada}\n\n"
            f"## Output de Sherlock\n\n{apresentacao.texto}\n\n"
            f"Avalie. Produza:\n"
            f"- '## Avaliação' com 'APROVADO' ou 'QUESTIONAR' na primeira linha\n"
            f"- Se QUESTIONAR: '## Pontos para Revisão' — classificação questionada, "
            f"dispositivo alternativo, fundamentação"
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, fase, user))
        return _parsear_avaliacao(resp.content)

    # ── fixar_decisao_sherlock ────────────────────────────────

    def fixar_decisao_sherlock(self, output_final: SherlockOutput,
                                rodadas_executadas: int) -> DecisaoFinal:
        call_type = "fixar_decisao_sherlock"
        user_base = (
            f"## Contexto\n\nAgente: Sherlock | Rodadas: {rodadas_executadas}\n\n"
            f"## Output Final de Sherlock\n\n{output_final.texto}\n\n"
            f"Produza a decisão final:\n"
            f"### Síntese\n### Posição Adotada\n"
            f"### Overrule\nSIM ou NÃO\n"
            f"### Dilemas\nCONTAGEM: N\n"
            f"### Encaminhamento"
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, self.FASE_SHERLOCK, user))
        return _parsear_decisao_sherlock(resp.content, output_final.dilemmas_count)

    # ── consolidar ────────────────────────────────────────────

    def consolidar(self, manifest: CycleManifest, decisao_watson: DecisaoFinal,
                   decisao_sherlock: DecisaoFinal) -> RelatorioOutput:
        call_type = "consolidar"
        prefixo = "Relatório Preliminar" if manifest.activity == 1 else "Relatório Final"
        user_base = (
            f"## Contexto do Ciclo\n\n"
            f"Módulo: {manifest.module_id} | Atividade: {manifest.activity}\n\n"
            f"## Decisão Final — Integridade Técnica (Watson)\n\n{decisao_watson.texto}\n\n"
            f"## Decisão Final — Validação Metodológica (Sherlock)\n\n{decisao_sherlock.texto}\n\n"
            f"Produza o {prefixo} do módulo. Use o template 'consolidar' do skills.md. "
            f"Terceira pessoa, impessoal, sem nomes de agentes no corpo."
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, "consolidacao", user))
        return RelatorioOutput(texto=resp.content)

    # ── Internos ─────────────────────────────────────────────

    def _construir_system_prompt(self) -> str:
        soul = (self._docs_dir / "soul.md").read_text(encoding="utf-8")
        skills = (self._docs_dir / "skills.md").read_text(encoding="utf-8")
        return f"{soul}\n\n---\n\n{skills}"

    def _montar_call(self, call_type: str, phase: str, user: str) -> LLMCall:
        return LLMCall(
            call_id=gerar_call_id("mycroft", call_type),
            cycle_id=self._cycle_id, phase=phase,
            agent="mycroft", call_type=call_type,
            model=self._spec.modelo, temperature=self._spec.temperatura,
            max_tokens=self._spec.max_tokens,
            seed=calcular_seed(42, self._cycle_id, phase, call_type),
            messages=[
                LLMMessage(role="system", content=self._system_prompt),
                LLMMessage(role="user", content=user),
            ],
            timeout_segundos=self._spec.timeout_segundos,
            max_tentativas_retry=self._spec.max_tentativas_retry,
            backoff_segundos=self._spec.backoff_segundos,
        )


# ── Helpers de parsing ────────────────────────────────────────────────────

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


def _parsear_avaliacao(content: str) -> AvaliacaoMycroft:
    secoes = _extrair_secoes(content)
    av = secoes.get("Avaliação", "")
    tipo = "APROVADO" if "APROVADO" in av.upper() else "QUESTIONAR"
    critica = secoes.get("Pontos para Revisão", "") if tipo == "QUESTIONAR" else ""
    return AvaliacaoMycroft(tipo=tipo, texto=content, critica=critica)


def _parsear_decisao_final(content: str, watson_criticos: int) -> DecisaoFinal:
    overruled = False
    contagem = watson_criticos
    m = re.search(r"###\s+Overrule\s*\n+(.*?)(?:\n###|\Z)", content, re.DOTALL | re.IGNORECASE)
    if m:
        overruled = m.group(1).strip().upper().startswith("SIM")
    m2 = re.search(r"CONTAGEM:\s*(\d+)", content, re.IGNORECASE)
    if m2:
        contagem = int(m2.group(1))
    return DecisaoFinal(
        texto=content, mycroft_overruled=overruled,
        has_critical_alert=contagem > 0, critical_alerts_count=contagem,
        has_dilemma=False, dilemmas_count=0,
    )


def _parsear_decisao_sherlock(content: str, sherlock_dilemas: int) -> DecisaoFinal:
    overruled = False
    dilemmas = sherlock_dilemas
    m = re.search(r"###\s+Overrule\s*\n+(.*?)(?:\n###|\Z)", content, re.DOTALL | re.IGNORECASE)
    if m:
        overruled = m.group(1).strip().upper().startswith("SIM")
    m2 = re.search(r"CONTAGEM:\s*(\d+)", content, re.IGNORECASE)
    if m2:
        dilemmas = int(m2.group(1))
    return DecisaoFinal(
        texto=content, mycroft_overruled=overruled,
        has_critical_alert=False, critical_alerts_count=0,
        has_dilemma=dilemmas > 0, dilemmas_count=dilemmas,
    )
