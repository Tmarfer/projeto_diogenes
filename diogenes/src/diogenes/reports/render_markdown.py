"""
reports/render_markdown.py — DVA-CBS | Projeto Diógenes
Renderiza CycleReportData como Markdown para terminal ou arquivo.
"""
from __future__ import annotations

from .cycle_report import CycleReportData


def render_markdown(data: CycleReportData) -> str:
    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"\n{'#' * level} {text}\n")

    def row(k: str, v: str) -> None:
        lines.append(f"| {k} | {v} |")

    def sep() -> None:
        lines.append("")

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    lines.append(f"# Relatório de Execução — {data.cycle_id}")
    lines.append(f"\n*DVA-CBS | TC 015.848/2025-6 | Gerado em {data.generated_at} UTC*\n")

    # ── Visão geral ──────────────────────────────────────────────────────────
    h(2, "Visão Geral")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    row("Ciclo", data.cycle_id)
    row("Módulo", f"{data.module_id} — Atividade {data.activity}")
    row("Status", data.status)
    row("Início", data.opened_at_utc)
    row("Fim", data.ended_at_utc or "em andamento")
    row("Duração", data.duration_str)
    row("Versão", data.diogenes_version)
    row("Commit", data.git_commit)

    # ── Irene ────────────────────────────────────────────────────────────────
    h(2, "Irene — Catalogação Semântica")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    row("Resultado", data.irene_resultado or "—")
    row("Score", f"{data.irene_score:.4f}" if data.irene_score is not None else "—")
    row("Invocada em", data.irene_invocada_at or "—")

    # ── Watson ───────────────────────────────────────────────────────────────
    h(2, "Watson — Integridade Técnica")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    row("Arquivos analisados", str(data.arquivos_analisados))
    row("Alertas críticos", str(data.watson_critical_alerts))
    row("Rodadas", str(data.watson_rodadas))
    row("Mycroft overruled", "Sim" if data.watson_overruled else "Não")

    # ── Sherlock ─────────────────────────────────────────────────────────────
    h(2, "Sherlock — Validação Metodológica")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    row("Metodologia carregada", f"{data.metodologia_chars:,} chars")
    row("Corpus jurídico", f"{data.corpus_juridico_chars:,} chars")
    row("Dilemas", str(data.sherlock_dilemmas))
    row("Rodadas", str(data.sherlock_rodadas))
    row("Mycroft overruled", "Sim" if data.sherlock_overruled else "Não")

    # ── LLM Calls ────────────────────────────────────────────────────────────
    h(2, "Chamadas LLM")
    total_prompt = sum(s.prompt_tokens for s in data.calls_by_agent.values())
    total_compl = sum(s.completion_tokens for s in data.calls_by_agent.values())
    lines.append(
        f"**Total:** {data.total_calls} chamadas · "
        f"{total_prompt:,} prompt tokens · {total_compl:,} completion tokens\n"
    )
    if data.calls_by_agent:
        lines.append("| Agente | Chamadas | Prompt Tokens | Completion Tokens | Resp. Média (chars) |")
        lines.append("|---|---|---|---|---|")
        for agent, s in sorted(data.calls_by_agent.items()):
            lines.append(
                f"| {agent} | {s.calls} | {s.prompt_tokens:,} | {s.completion_tokens:,} "
                f"| {s.avg_response_length:,.0f} |"
            )

    # ── Timeline de fases ────────────────────────────────────────────────────
    h(2, "Timeline de Fases")
    if data.fases:
        lines.append("| Fase | Início (UTC) | Fim (UTC) | Duração |")
        lines.append("|---|---|---|---|")
        for f in data.fases:
            dur = f"{f.duration_min:.0f}min" if f.duration_min else "—"
            lines.append(f"| {f.fase} | {f.started_at} | {f.ended_at or '…'} | {dur} |")
    else:
        lines.append("*(nenhuma fase registrada)*")

    # ── Motor de Saída ───────────────────────────────────────────────────────
    h(2, "Motor de Saída")
    lines.append("| Campo | Valor |")
    lines.append("|---|---|")
    row("Ocorrências encontradas", str(data.motor_saida_occurrences))
    row("Decisão", data.motor_saida_decision or "—")
    row("Documento limpo", "Sim" if data.motor_saida_limpo else "Não")

    # ── Stranger Room ────────────────────────────────────────────────────────
    h(2, "Deliberações Internas (Stranger Room)")
    if data.stranger_room_files:
        for fase, arquivos in sorted(data.stranger_room_files.items()):
            lines.append(f"\n**{fase}/** ({len(arquivos)} arquivos)")
            for arq in arquivos:
                lines.append(f"- `{arq}`")
    else:
        lines.append("*(sem arquivos)*")

    # ── Output final ─────────────────────────────────────────────────────────
    h(2, "Output Final")
    if data.output_filename:
        lines.append("| Campo | Valor |")
        lines.append("|---|---|")
        row("Arquivo", data.output_filename)
        row("Hash", data.output_hash)
        if data.output_path:
            row("Caminho", str(data.output_path))
    else:
        lines.append("*(output não gerado ainda)*")

    # ── Eventos-chave ────────────────────────────────────────────────────────
    if data.key_events:
        h(2, f"Eventos-chave ({len(data.key_events)})")
        lines.append("| Timestamp | Evento | Fase | Detalhes |")
        lines.append("|---|---|---|---|")
        for e in data.key_events:
            det = e.get("details", {})
            det_str = ", ".join(f"{k}={v}" for k, v in det.items() if v not in (None, "", {}))
            lines.append(
                f"| {e.get('timestamp_utc', '')} "
                f"| {e.get('event_type', '')} "
                f"| {e.get('phase') or ''} "
                f"| {det_str} |"
            )

    sep()
    lines.append(f"*Relatório gerado em {data.generated_at} UTC — DVA-CBS | Uso Interno Restrito*")

    return "\n".join(lines)
