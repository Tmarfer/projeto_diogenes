"""
agents/watson.py — DVA-CBS | Projeto Diógenes
WatsonAgent — Auditor de Integridade Técnica.

Fase 1: um arquivo por chamada (analisar_arquivo), sequenciado pelo Orquestrador.
Fase 2: consolidação dos outputs individuais (consolidar).
Referência normativa: RF-WA-01 a RF-WA-10 (PRD v0.1), Bloco 9.3 (SDD v0.1)
"""
from __future__ import annotations

import re
from pathlib import Path

from diogenes.agents.file_prep import preparar_arquivo
from diogenes.agents.heartbeat import HeartbeatLoader, injetar_heartbeat
from diogenes.config import AgentSpec
from diogenes.llm.base import LLMClient
from diogenes.llm.call_id import gerar_call_id
from diogenes.llm.exceptions import LLMCallError, LLMTimeoutError
from diogenes.llm.seed import calcular_seed
from diogenes.models import InputFileInfo, LLMCall, LLMMessage, WatsonOutput


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

    def analisar_arquivo(
        self,
        arquivo_path: Path,
        arquivo_info: InputFileInfo,
        tasks_mycroft: str = "",
        proximo_id_alerta: str = "",
    ) -> WatsonOutput:
        """
        Analisa UM arquivo do pacote RFB em contexto isolado.
        Retorna WatsonOutput com ultimo_id_alerta preenchido para propagar
        o contador de IDs ao próximo arquivo.
        """
        call_type = "analise_inicial"
        hb = self._heartbeat.get_section(call_type)

        partes: list[str] = []
        if proximo_id_alerta:
            partes.append(f"**Próximo ID de alerta disponível:** `{proximo_id_alerta}`")
        if tasks_mycroft:
            partes.append(f"[TASKS DE MYCROFT]\n{tasks_mycroft}")
        conteudo = preparar_arquivo(arquivo_path)
        partes.append(f"[ARQUIVO: {arquivo_info.name}]\n{conteudo}")

        user = injetar_heartbeat(hb, "\n\n".join(partes))
        try:
            resp = self._llm.complete(LLMCall(
                call_id=gerar_call_id("watson", call_type),
                cycle_id=self._cycle_id, phase=self.FASE,
                agent="watson", call_type=call_type,
                model=self._spec.modelo, temperature=self._spec.temperatura,
                max_tokens=self._spec.max_tokens,
                seed=calcular_seed(42, self._cycle_id, self.FASE, call_type,
                                   hash(arquivo_info.name) & 0xFFFF),
                messages=[
                    LLMMessage(role="system", content=self._system_prompt),
                    LLMMessage(role="user", content=user),
                ],
                timeout_segundos=self._spec.timeout_segundos,
                max_tentativas_retry=self._spec.max_tentativas_retry,
                backoff_segundos=self._spec.backoff_segundos,
            ))
            return self._parsear_output(resp.content)
        except (LLMCallError, LLMTimeoutError) as exc:
            # Falha no arquivo individual não aborta o pipeline — registra como não analisável.
            # O erro será incluído no watson_consolidado.md e visível para Mycroft/Sherlock.
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "[Watson] Arquivo '%s' não analisável: %s", arquivo_info.name, exc
            )
            return WatsonOutput(
                texto=(
                    f"## Análise de {arquivo_info.name}\n\n"
                    f"**Status:** NÃO ANALISÁVEL\n"
                    f"**Causa:** Falha persistente de comunicação com o LLM: {exc}\n\n"
                    f"Este arquivo não foi analisado neste ciclo. "
                    f"Registrado como não analisável para consolidação por Watson."
                ),
                critical_alerts_count=0,
                has_unanalyzable_files=True,
                secoes={},
                ultimo_id_alerta=proximo_id_alerta,
            )

    def consolidar(
        self,
        analises: list[WatsonOutput],
        tasks_mycroft: str = "",
    ) -> WatsonOutput:
        """
        Consolida as análises individuais (Fase 2).
        Usa heartbeat consolidar_watson. Agrega critical_alerts_count de todos os arquivos.
        """
        call_type = "consolidar_watson"
        hb = self._heartbeat.get_section(call_type)

        partes: list[str] = []
        if tasks_mycroft:
            partes.append(f"[TASKS DE MYCROFT]\n{tasks_mycroft}")
        for i, a in enumerate(analises, 1):
            partes.append(f"[ANÁLISE DO ARQUIVO #{i}]\n{a.texto}")

        user = injetar_heartbeat(hb, "\n\n---\n\n".join(partes))
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
        consolidado = self._parsear_output(resp.content)
        # Garantir contagem de críticos: máximo entre o que o LLM reportou
        # e a soma das análises individuais (defesa contra omissão na síntese)
        total_criticos = max(
            consolidado.critical_alerts_count,
            sum(a.critical_alerts_count for a in analises),
        )
        has_nao_analisavel = consolidado.has_unanalyzable_files or any(
            a.has_unanalyzable_files for a in analises
        )
        return WatsonOutput(
            texto=consolidado.texto,
            critical_alerts_count=total_criticos,
            has_unanalyzable_files=has_nao_analisavel,
            secoes=consolidado.secoes,
            ultimo_id_alerta=consolidado.ultimo_id_alerta,
        )

    def validacao_planilha_rn(
        self,
        planilha_path: Path,
        analises_watson: list[WatsonOutput],
        tasks_mycroft: str = "",
    ) -> WatsonOutput:
        """
        Fase opcional: percorre a Planilha de Verificação do Motor de Regras
        ponto a ponto sob perspectiva quantitativa/estrutural.
        Acionado apenas quando a planilha está listada no manifesto (call_type validacao_planilha_rn).
        """
        call_type = "validacao_planilha_rn"
        hb = self._heartbeat.get_section(call_type)

        partes: list[str] = []
        if tasks_mycroft:
            partes.append(f"[MC_TASKS_WATSON]\n{tasks_mycroft}")
        planilha_conteudo = preparar_arquivo(planilha_path)
        partes.append(f"[PLANILHA DE VERIFICAÇÃO: {planilha_path.name}]\n{planilha_conteudo}")
        for i, a in enumerate(analises_watson, 1):
            partes.append(f"[watson_analise #{i}]\n{a.texto}")

        user = injetar_heartbeat(hb, "\n\n---\n\n".join(partes))
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
        self,
        critica: str,
        output_anterior: WatsonOutput,
        rodada: int,
        proximo_id_alerta: str = "",
    ) -> WatsonOutput:
        call_type = f"resposta_r{rodada}"
        hb = self._heartbeat.get_section(call_type)

        preamble_partes: list[str] = []
        if proximo_id_alerta:
            preamble_partes.append(
                f"**Próximo ID de alerta disponível:** `{proximo_id_alerta}`"
            )

        conteudo_base = (
            f"## Seu output anterior\n\n{output_anterior.texto}\n\n"
            f"---\n\n## Crítica de Mycroft\n\n{critica}\n\n"
            f"---\n\nResponda a cada ponto da crítica. Acate com correção "
            f"ou sustente com evidência localizada no consolidado."
        )
        user_base = "\n\n".join(preamble_partes + [conteudo_base])
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
        criticos = _contar_criticos(content, secoes)
        nao_analisaveis = _secao_por_nome(secoes, _SECOES_NAO_ANALISAVEIS).strip()
        ultimo_id = _extrair_ultimo_id(secoes, content)
        nota_metodologica = _extrair_nota_metodologica(content)
        return WatsonOutput(
            texto=content,
            critical_alerts_count=criticos,
            has_unanalyzable_files=bool(nao_analisaveis),
            secoes=secoes,
            ultimo_id_alerta=ultimo_id,
            nota_metodologica_com_alteracao=nota_metodologica,
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


# Nomes de seção de alertas conforme os templates do skills.md de Watson:
# Template 1 (analise_arquivo) → "## Alertas Consolidados deste Arquivo"
# Template 2 (consolidar_watson) → "## 3. Alertas Consolidados"
# "Tabela de Alertas" é mantido por retrocompatibilidade com o SDD.
_SECOES_ALERTAS = (
    "Tabela de Alertas",
    "Alertas Consolidados deste Arquivo",
    "3. Alertas Consolidados",
    "Alertas Consolidados",
)
_SECOES_NAO_ANALISAVEIS = (
    "Arquivos Não Analisáveis",
    "Arquivos Não Analisados",
)


def _secao_por_nome(secoes: dict, candidatos: tuple[str, ...]) -> str:
    """Retorna o conteúdo da primeira seção cujo nome casa com um candidato."""
    for nome in candidatos:
        if nome in secoes:
            return secoes[nome]
    return ""


def _contar_criticos(content: str, secoes: dict) -> int:
    """
    Conta alertas CRÍTICOS do output de Watson.

    Fonte primária: o campo de cabeçalho `**Alertas CRITICA:** N` que ambos
    os templates de Watson emitem — sobrevive à truncagem da tabela de alertas.
    Fallback: conta linhas marcadas como CRÍTICA na seção de alertas, tentando
    os vários nomes de seção usados pelos templates.
    """
    m = re.search(
        r'\*\*\s*Alertas\s+CR[IÍ]TICA\s*:?\s*\*\*\s*:?\s*(\d+)',
        content, re.IGNORECASE,
    )
    if m:
        return int(m.group(1))
    tabela = _secao_por_nome(secoes, _SECOES_ALERTAS)
    return sum(
        1 for linha in tabela.splitlines()
        if re.search(r'\bCR[IÍ]TICA\b', linha, re.IGNORECASE)
    )


def _extrair_nota_metodologica(content: str) -> bool:
    """
    Detecta se Watson sinalizou nota metodológica com alteração.
    Campo de cabeçalho: `**Nota metodológica com alteração detectada:** Sim | Não`
    Retorna False por default quando o campo está ausente.
    """
    m = re.search(
        r'\*\*\s*Nota metodológica com alteração detectada\s*:?\s*\*{0,2}\s*:?\s*(Sim|Não)',
        content, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower().startswith("sim")
    return False


def _extrair_ultimo_id(secoes: dict, content: str) -> str:
    """
    Extrai o último ID de alerta do output de Watson.
    Tenta primeiro a seção dedicada `## Último ID de Alerta Usado`,
    depois busca o padrão W\\d+-\\d+ de maior número em todo o texto.
    """
    # 1. Campo de cabeçalho `**Último ID de alerta usado:** WNNN-NNN` (Template 1)
    m = re.search(
        r'\*\*\s*Último ID de alerta usado\s*:?\s*\*\*\s*:?\s*(W\d+-\d+)',
        content, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # 2. Seção dedicada (forma canônica)
    secao = secoes.get("Último ID de Alerta Usado", "").strip()
    if secao:
        m = re.search(r'W\d+-\d+', secao)
        if m:
            return m.group(0)

    # 3. Fallback: maior ID encontrado no texto completo
    ids = re.findall(r'W(\d+)-(\d+)', content)
    if ids:
        return "W" + max(ids, key=lambda t: (int(t[0]), int(t[1])))[0] + \
               "-" + max(ids, key=lambda t: (int(t[0]), int(t[1])))[1]
    return ""
