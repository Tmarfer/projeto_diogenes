"""
agents/mycroft.py — DVA-CBS | Projeto Diógenes
MycrooftAgent (grafia do SDD) — Auditor Chefe.

Todos os call_types recebem a seção correspondente do heartbeat.md
injetada no início do user_prompt (antes dos inputs específicos).
Referência normativa: Bloco 9.2 (SDD v0.1)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from diogenes.agents.heartbeat import HeartbeatLoader, injetar_heartbeat
from diogenes.config import AgentSpec
from diogenes.llm.base import LLMClient
from diogenes.llm.call_id import gerar_call_id
from diogenes.llm.exceptions import LLMCallError, LLMTimeoutError
from diogenes.llm.seed import calcular_seed
from diogenes.models import (
    AvaliacaoMycroft,
    CycleManifest,
    DecisaoFinal,
    DefinirTasksResult,
    LLMCall,
    LLMMessage,
    RelatorioOutput,
    SherlockOutput,
    WatsonOutput,
)

logger = logging.getLogger(__name__)


class MycrooftAgent:
    FASE_WATSON  = "watson_integridade"
    FASE_SHERLOCK = "sherlock_validacao"

    def __init__(self, llm: LLMClient, agent_spec: AgentSpec,
                 cycle_id: str, docs_dir: Path,
                 cycle_dir: Path | None = None) -> None:
        self._llm = llm
        self._spec = agent_spec
        self._cycle_id = cycle_id
        self._docs_dir = docs_dir
        self._cycle_dir = cycle_dir
        self._system_prompt = self._construir_system_prompt()
        self._heartbeat = HeartbeatLoader(docs_dir / "heartbeat.md")

    # ── definir_tasks_watson ──────────────────────────────────

    def definir_tasks_watson(self, manifest: CycleManifest) -> DefinirTasksResult:
        call_type = "definir_tasks_watson"
        arquivos = "\n".join(
            f"- {fi.name} ({fi.extension}, {fi.size_bytes} bytes)"
            for fi in manifest.input_files
        )

        # Ler catálogo do Irene (se disponível no diretório do ciclo)
        catalogo_irene = self._ler_catalogo_irene(self._cycle_dir) if self._cycle_dir else None
        secao_catalogo = self._formatar_secao_catalogo_irene(catalogo_irene)

        user_base = (
            f"## Manifesto do Ciclo\n\n"
            f"Módulo: {manifest.module_id}\n"
            f"Atividade: {manifest.activity}\n"
            f"Sala de Sigilo: {'Sim' if manifest.is_sigilo_module else 'Não'}\n"
            f"Prioridades definidas por Lestrade: "
            f"{manifest.prioridades_analise or '[não preenchido — aplicar ordem padrão]'}\n\n"
            f"{secao_catalogo}\n\n"
            f"## Arquivos do Pacote\n\n{arquivos}\n\n"
            f"Defina as tasks ordenadas para Watson. Produza a seção "
            f"'## Tasks para Watson' com lista numerada e a seção "
            f"'## Inputs Disponíveis' com ordem e origem da priorização.\n"
            f"Inclua o campo '**Planilha de Verificação no pacote:** Sim | Não' "
            f"no cabeçalho do output, indicando se a Planilha de Verificação "
            f"gerada pelo Motor de Regras está entre os arquivos do pacote."
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        resp = self._llm.complete(self._montar_call(call_type, self.FASE_WATSON, user))
        secoes = _extrair_secoes(resp.content)
        tasks_text = secoes.get("Tasks para Watson", resp.content)
        planilha = _extrair_bool_cabecalho(resp.content, "Planilha de Verificação no pacote")
        return DefinirTasksResult(tasks_text=tasks_text,
                                  planilha_verificacao_no_pacote=planilha)

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
        try:
            resp = self._llm.complete(self._montar_call(call_type, fase, user))
            return _parsear_avaliacao(resp.content)
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] avaliar_watson indisponível — APROVADO automático: %s", exc)
            return AvaliacaoMycroft(
                tipo="APROVADO",
                texto=(
                    "## Avaliação\n\nAPROVADO\n\n"
                    "[Aprovação automática de fallback — Mycroft indisponível: ChatTCU timeout. "
                    "Avaliação sem revisão LLM.]"
                ),
                critica="",
            )

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
        try:
            resp = self._llm.complete(self._montar_call(call_type, self.FASE_WATSON, user))
            return _parsear_decisao_final(resp.content, output_final.critical_alerts_count)
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] fixar_decisao_watson indisponível — fallback: %s", exc)
            return DecisaoFinal(
                texto=(
                    "### Síntese\n\n[Fallback automático — Mycroft indisponível]\n\n"
                    "### Posição Adotada\nAPROVADO\n\n"
                    "### Overrule\nNÃO\n\n"
                    f"### Alertas Críticos\nCONTAGEM: {output_final.critical_alerts_count}\n\n"
                    "### Notas para Sherlock\n[Decisão sem revisão LLM — ChatTCU timeout]"
                ),
                mycroft_overruled=False,
                has_critical_alert=output_final.has_critical_alert,
                critical_alerts_count=output_final.critical_alerts_count,
                has_dilemma=False,
                dilemmas_count=0,
            )

    # ── montar_pacote_sherlock ────────────────────────────────

    def montar_pacote_sherlock(
        self, manifest: CycleManifest, inputs_dir: Path, decisao_watson: DecisaoFinal,
        watson_apresentacao: str = "",
        nota_metodologica_detalhes: str = "",
    ) -> str:
        call_type = "montar_pacote_sherlock"
        from diogenes.agents.file_prep import preparar_arquivo
        inventario = "\n".join(
            f"- {fi.name} ({fi.extension}, {fi.size_bytes} bytes)"
            for fi in manifest.input_files
        )
        # Para o LLM de Mycroft: apenas metadados + decisão Watson (sem docs completos)
        # Incluir nota metodológica quando Watson a sinalizou (Premissa 3 do skills.md de Sherlock)
        nota_bloco = ""
        if nota_metodologica_detalhes:
            nota_bloco = (
                f"\n\n## Nota Metodológica com Alteração — Prioridade para Sherlock\n\n"
                f"{nota_metodologica_detalhes}\n\n"
                f"[INSTRUÇÃO: Sherlock deve tratar este ponto com prioridade antes de qualquer "
                f"verificação de ponto individual — Premissa 3 do skills.md]"
            )
        user_base = (
            f"## Contexto do Módulo\n\n"
            f"Módulo: {manifest.module_id} | Atividade: {manifest.activity}\n"
            f"Sala de Sigilo: {'Sim' if manifest.is_sigilo_module else 'Não'}\n\n"
            f"## Decisão Final de Mycroft sobre Watson\n\n{decisao_watson.texto}\n\n"
            f"## Inventário dos Artefatos Entregues\n\n{inventario}"
            f"{nota_bloco}\n\n"
            f"Monte a síntese de contexto para Sherlock conforme o template "
            f"'montar_pacote_sherlock' do skills.md. Foco em: alertas de Watson, "
            f"cadeia de produção, pontos de atenção para análise metodológica."
        )
        user = injetar_heartbeat(self._heartbeat.get_section(call_type), user_base)
        try:
            resp = self._llm.complete(self._montar_call(call_type, self.FASE_SHERLOCK, user))
            sintese_mycroft = resp.content
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] montar_pacote_sherlock indisponível — pacote mínimo: %s", exc)
            sintese_mycroft = (
                "## Síntese para Sherlock\n\n"
                "[Fallback automático — Mycroft indisponível: ChatTCU timeout]\n\n"
                f"## Decisão Final Watson (resumo)\n\n{decisao_watson.texto[:1000]}"
            )

        # Montar pacote completo: síntese Mycroft + análise Watson + documentos metodológicos
        partes: list[str] = [sintese_mycroft]

        # Análise completa de Watson (da Stranger's Room) — insumo principal para Sherlock
        if watson_apresentacao:
            partes.append(
                "\n\n---\n\n## Análise de Integridade Técnica — Resultado Completo\n\n"
                + watson_apresentacao
            )

        # Documentos metodológicos do pacote (.md) injetados diretamente
        # para que Sherlock possa identificar os pontos a verificar
        docs_metodologicos: list[str] = []
        for fi in manifest.input_files:
            if fi.extension == ".md":
                path = inputs_dir / fi.rel_path
                if path.exists():
                    docs_metodologicos.append(
                        f"\n\n---\n\n[DOCUMENTO METODOLÓGICO: {fi.name}]\n\n"
                        + preparar_arquivo(path)
                    )
        if docs_metodologicos:
            partes.append("\n\n---\n\n## Documentos Metodológicos do Pacote")
            partes.extend(docs_metodologicos)

        return "".join(partes)

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
        try:
            resp = self._llm.complete(self._montar_call(call_type, fase, user))
            return _parsear_avaliacao(resp.content)
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] avaliar_sherlock indisponível — APROVADO automático: %s", exc)
            return AvaliacaoMycroft(
                tipo="APROVADO",
                texto=(
                    "## Avaliação\n\nAPROVADO\n\n"
                    "[Aprovação automática de fallback — Mycroft indisponível: ChatTCU timeout. "
                    "Avaliação sem revisão LLM.]"
                ),
                critica="",
            )

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
        try:
            resp = self._llm.complete(self._montar_call(call_type, self.FASE_SHERLOCK, user))
            return _parsear_decisao_sherlock(resp.content, output_final.dilemmas_count)
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] fixar_decisao_sherlock indisponível — fallback: %s", exc)
            return DecisaoFinal(
                texto=(
                    "### Síntese\n\n[Fallback automático — Mycroft indisponível]\n\n"
                    "### Posição Adotada\nAPROVADO\n\n"
                    "### Overrule\nNÃO\n\n"
                    f"### Dilemas\nCONTAGEM: {output_final.dilemmas_count}\n\n"
                    "### Encaminhamento\n[Decisão sem revisão LLM — ChatTCU timeout]"
                ),
                mycroft_overruled=False,
                has_critical_alert=output_final.has_critical_alert,
                critical_alerts_count=output_final.critical_alerts_count,
                has_dilemma=output_final.has_dilemma,
                dilemmas_count=output_final.dilemmas_count,
            )

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
        try:
            resp = self._llm.complete(self._montar_call(call_type, "consolidacao", user))
            overrule_w = _extrair_bool_cabecalho(resp.content, "Overrule Mycroft sobre Watson")
            overrule_s = _extrair_bool_cabecalho(resp.content, "Overrule Mycroft sobre Sherlock")
            return RelatorioOutput(texto=resp.content,
                                   overrule_watson=overrule_w,
                                   overrule_sherlock=overrule_s)
        except (LLMCallError, LLMTimeoutError) as exc:
            logger.warning("[Mycroft] consolidar indisponível — relatório mínimo: %s", exc)
            texto_fallback = (
                f"# {prefixo} — {manifest.module_id} (Atividade {manifest.activity})\n\n"
                f"**Gerado automaticamente (fallback — Mycroft indisponível)**\n\n"
                f"## Decisão de Integridade Técnica (Watson)\n\n{decisao_watson.texto}\n\n"
                f"## Decisão de Validação Metodológica (Sherlock)\n\n{decisao_sherlock.texto}\n"
            )
            return RelatorioOutput(texto=texto_fallback,
                                   overrule_watson=False,
                                   overrule_sherlock=False)

    # ── Catálogo do Irene ────────────────────────────────────

    def _ler_catalogo_irene(self, cycle_dir: Path | None) -> dict | None:
        """
        Lê irene_catalog.yaml do diretório do ciclo.
        Retorna dict com o catálogo ou None se não existir.
        """
        if cycle_dir is None:
            return None
        catalogo_path = cycle_dir / "irene_catalog.yaml"
        if not catalogo_path.exists():
            return None
        try:
            return yaml.safe_load(catalogo_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Falha ao ler irene_catalog.yaml: %s", exc)
            return None

    def _formatar_secao_catalogo_irene(self, catalogo: dict | None) -> str:
        """
        Formata a seção <!-- SECAO: catalogo_irene --> para o MC_tasks_watson.md.
        """
        if catalogo is None:
            return (
                "<!-- SECAO: catalogo_irene -->\n"
                "## Catálogo do Irene — Classificação Semântica\n\n"
                "**Catálogo disponível:** Não\n"
                "<!-- /SECAO: catalogo_irene -->"
            )

        linhas_tabela = []
        orientacoes = []

        for arq in catalogo.get("arquivos", []):
            nome = arq.get("nome_original", "")
            papel = arq.get("papel", "nao_classificado")
            confianca = arq.get("confianca_papel", 0.0)
            flags = ", ".join(arq.get("flags_atencao", [])) or "—"
            rev_hum = "Sim" if arq.get("requer_revisao_humana") else "Não"
            linhas_tabela.append(
                f"| {nome} | {papel} | {confianca:.2f} | {flags} | {rev_hum} |"
            )

            # Orientação de profundidade
            if papel in ("resultado_final", "resultado_intermediario"):
                orientacoes.append(
                    f"- `{nome}` ({papel}): análise completa — todas as varreduras "
                    f"transversais obrigatórias, fórmulas e totalizadores exaustivos."
                )
            elif papel in ("aba_auxiliar", "tabela_mapeamento", "matriz_parametrica"):
                orientacoes.append(
                    f"- `{nome}` ({papel}): verificação de integridade básica — "
                    f"sem aprofundamento de cadeia de produção."
                )
            elif papel == "nao_classificado":
                orientacoes.append(
                    f"- `{nome}` (não classificado pelo Irene): análise completa — "
                    f"Watson determina o papel durante a análise."
                )
            else:
                orientacoes.append(
                    f"- `{nome}` ({papel}): análise padrão com foco em rastreabilidade."
                )

            if arq.get("flags_atencao"):
                orientacoes.append(
                    f"  ⚠ Flags do Irene a verificar: {flags}"
                )
            if arq.get("requer_revisao_humana"):
                orientacoes.append(
                    f"  [ATENÇÃO LESTRADE] Irene sinalizou necessidade de revisão humana."
                )

        tabela_header = (
            "| Arquivo | Papel Irene | Confiança | Flags | Rev. Humana |\n"
            "|---|---|---|---|---|"
        )
        tabela = tabela_header + "\n" + "\n".join(linhas_tabela)
        orientacao_str = "\n".join(orientacoes) if orientacoes else "N/A"

        return (
            "<!-- SECAO: catalogo_irene -->\n"
            "## Catálogo do Irene — Classificação Semântica\n\n"
            f"**Catálogo disponível:** Sim\n"
            f"**Score consolidado Irene:** {catalogo.get('score_consolidado', 0):.4f}\n"
            f"**Recomendação Irene:** {catalogo.get('recomendacao', 'N/A')}\n\n"
            f"{tabela}\n\n"
            f"**Orientação de profundidade para Watson:**\n"
            f"{orientacao_str}\n"
            "<!-- /SECAO: catalogo_irene -->"
        )

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
    # Detect tipo: check "resultado:" header field (template format from skills.md)
    # before falling back to scanning the body of ## Avaliação.
    # The heartbeat template uses resultado: APROVADO|CRITICA in the document header,
    # not "APROVADO"/"QUESTIONAR" as the first line of ## Avaliação (legacy prompt format).
    # Note: Markdown bold wraps "resultado:" as **resultado:** so the colon precedes
    # the closing **, yielding the pattern: resultado:** value.
    # Markdown bold wraps "resultado:" as **resultado:** so the colon precedes the closing **.
    m = re.search(r"resultado:\*{0,2}\s*(APROVADO|CRITICA)", content, re.IGNORECASE)
    if m:
        tipo = "APROVADO" if m.group(1).upper() == "APROVADO" else "QUESTIONAR"
    else:
        tipo = "APROVADO" if "APROVADO" in av.upper() else "QUESTIONAR"
    # Critique text: the template puts it inside ## Avaliação (not ## Pontos para Revisão).
    # Fall back chain: "Pontos para Revisão" (legacy) → "Avaliação" (template) → full text.
    critica = (secoes.get("Pontos para Revisão") or av or content) if tipo == "QUESTIONAR" else ""
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


def _extrair_bool_cabecalho(content: str, campo: str) -> bool:
    """
    Extrai campo booleano de cabeçalho no formato `**campo:** Sim | Não`.
    Retorna False quando o campo está ausente ou tem valor diferente de Sim.
    """
    m = re.search(
        r'\*\*\s*' + re.escape(campo) + r'\s*:?\s*\*{0,2}\s*:?\s*(Sim|Não|Sim\b)',
        content, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower().startswith("sim")
    return False


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
