"""
reports/render_html.py — DVA-CBS | Projeto Diógenes
Renderiza CycleReportData como HTML standalone (zero dependências externas).
CSS inline, Inter via Google Fonts (fallback: system-ui), sem frameworks JS.
"""
from __future__ import annotations

import html as _html
from pathlib import Path

from .assets import carregar_retrato
from .cycle_report import AgentCallStats, CycleReportData

# ── Helpers ───────────────────────────────────────────────────────────────────

def _e(s: object) -> str:
    return _html.escape(str(s))


def _fmt_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def _entrega_verdito_class(v: str) -> str:
    vu = v.upper()
    if "APROVADO" in vu:
        return "success"
    if "REQUER" in vu or "AJUSTE" in vu:
        return "warning"
    return "muted"


def _status_class(status: str) -> str:
    s = status.upper()
    if "ENCERRADO_CHANCELADO" in s:
        return "success"
    if "ABORTADO" in s or "FALHA" in s:
        return "error"
    if "EM_EXECUCAO" in s or "AGUARDANDO" in s:
        return "warning"
    if "PAUSADO" in s:
        return "muted"
    return "info"


def _irene_class(resultado: str) -> str:
    r = resultado.upper()
    if "APROVADO" in r:
        return "success"
    if "ALERTA" in r:
        return "warning"
    if "REUTILIZADO" in r or "CONCLUIDA" in r:
        return "info"
    if "ERRO" in r or "FATAL" in r:
        return "error"
    return "muted"


def _motor_class(limpo: bool, occurrences: int) -> str:
    if limpo and occurrences == 0:
        return "success"
    if limpo:
        return "warning"
    return "error"


# ── Fase de Entrega ───────────────────────────────────────────────────────────

def _entrega_html(data: CycleReportData) -> str:
    """Seção da Fase de Entrega: entregáveis com links + call_types do Mycroft.
    Renderiza só quando houve entrega (invocação ou artefatos)."""
    if not (data.entrega_invocado_at or data.entrega_artefatos_list):
        return ""

    if data.entrega_artefatos_list:
        linhas = "".join(
            f'<tr><td><span class="entrega-tipo">{_e(a.get("tipo", ""))}</span></td>'
            f'<td><a class="output-link" href="file://{_e(a.get("path", ""))}">'
            f'{_e(a.get("nome", ""))} ↗</a></td>'
            f'<td class="mono muted-text">{_e(_fmt_bytes(int(a.get("bytes", 0) or 0)))}</td></tr>'
            for a in data.entrega_artefatos_list
        )
        artefatos_html = (
            '<div class="table-wrap"><table><thead><tr>'
            '<th>Tipo</th><th>Entregável</th><th>Tamanho</th></tr></thead>'
            f'<tbody>{linhas}</tbody></table></div>'
        )
    else:
        artefatos_html = ("<p class='muted-text'>Entrega invocada, mas nenhum artefato "
                          "localizado em <code>output/entrega/</code>.</p>")

    veredito = data.entrega_veredito or "—"
    vc = _entrega_verdito_class(data.entrega_veredito)

    calls = data.entrega_calls_by_type
    if calls:
        chips = "".join(
            f'<span class="entrega-chip">{_e(ct)} <b>{n}</b></span>'
            for ct, n in sorted(calls.items())
        )
        calls_html = (f'<div class="entrega-calls"><span class="entrega-calls-lbl">'
                      f'Chamadas do Mycroft na entrega:</span> {chips}</div>')
    else:
        calls_html = ""

    return f"""
  <!-- Fase de Entrega -->
  <div class="section">
    <h2>Fase de Entrega</h2>
    <div class="cards-row">
      <div class="card">
        <h3>Entregáveis</h3>
        <div class="value">{len(data.entrega_artefatos_list)}</div>
        <div class="sub">artefatos institucionais gerados</div>
      </div>
      <div class="card">
        <h3>QA do Mycroft</h3>
        <div class="sub" style="margin-top:8px">
          <span class="badge badge-{vc}">{_e(veredito)}</span>
        </div>
      </div>
      <div class="card">
        <h3>Invocada em</h3>
        <div class="sub mono" style="margin-top:8px">{_e(data.entrega_invocado_at or '—')}</div>
      </div>
    </div>
    {artefatos_html}
    {calls_html}
  </div>"""


# ── Seção de agentes com avatares (estilo Sherlock Holmes) ────────────────────

def _avatar_visual(nome: str, deco: str, letra: str) -> str:
    """Retrato (ilustração Paget) como data URI; fallback ao avatar tipográfico."""
    uri = carregar_retrato(nome)
    if uri:
        return f'<img class="avatar-img" src="{uri}" alt="{_e(nome)}" loading="lazy">'
    return f'<div class="avatar-deco">{deco}</div><div class="avatar-letter">{letra}</div>'


def _agent_cards_html(data: CycleReportData) -> str:
    watson = data.calls_by_agent.get("watson", AgentCallStats())
    sherlock = data.calls_by_agent.get("sherlock", AgentCallStats())
    mycroft = data.calls_by_agent.get("mycroft", AgentCallStats())

    ic = _irene_class(data.irene_resultado)
    irene_score_str = f"{data.irene_score:.4f}" if data.irene_score is not None else "—"

    return f"""
  <!-- Equipe de Agentes -->
  <div class="section">
    <h2>Equipe de Agentes</h2>
    <div class="agents-grid">

      <!-- Irene Adler — Catalogação Semântica -->
      <div class="agent-card">
        <div class="agent-avatar irene">
          {_avatar_visual("irene", "✦", "I")}
          <div class="avatar-title">Irene Adler</div>
          <div class="avatar-subtitle">A Catalogadora</div>
        </div>
        <div class="agent-body">
          <div class="agent-role">Catalogação Semântica</div>
          <div class="agent-metrics">
            <div class="metric">
              <span class="metric-val">{_e(irene_score_str)}</span>
              <span class="metric-lbl">score</span>
            </div>
            <div class="metric">
              <span class="metric-val metric-sm">
                <span class="badge badge-{ic}">{_e(data.irene_resultado or '—')}</span>
              </span>
              <span class="metric-lbl">resultado</span>
            </div>
          </div>
          <div class="agent-note">Pipeline C1–C5 independente · sem LLM direto</div>
        </div>
      </div>

      <!-- Dr. Watson — Integridade Técnica -->
      <div class="agent-card">
        <div class="agent-avatar watson">
          {_avatar_visual("watson", "⚙", "W")}
          <div class="avatar-title">Dr. Watson</div>
          <div class="avatar-subtitle">O Analista</div>
        </div>
        <div class="agent-body">
          <div class="agent-role">Auditor de Integridade Técnica</div>
          <div class="agent-metrics">
            <div class="metric">
              <span class="metric-val">{data.arquivos_analisados}</span>
              <span class="metric-lbl">arquivos</span>
            </div>
            <div class="metric">
              <span class="metric-val {'metric-warn' if data.watson_critical_alerts > 0 else 'metric-ok'}">{data.watson_critical_alerts}</span>
              <span class="metric-lbl">alertas críticos</span>
            </div>
            <div class="metric">
              <span class="metric-val">{watson.calls}</span>
              <span class="metric-lbl">chamadas LLM</span>
            </div>
            <div class="metric">
              <span class="metric-val">{watson.prompt_tokens:,}</span>
              <span class="metric-lbl">prompt tokens</span>
            </div>
          </div>
          <div class="agent-note">
            {data.watson_rodadas} rodada{'s' if data.watson_rodadas != 1 else ''} ·
            {'⚠ overruled por Mycroft' if data.watson_overruled else 'aprovado por Mycroft'}
          </div>
        </div>
      </div>

      <!-- Mycroft Holmes — Orquestrador-Chefe -->
      <div class="agent-card">
        <div class="agent-avatar mycroft">
          {_avatar_visual("mycroft", "⚖", "M")}
          <div class="avatar-title">Mycroft Holmes</div>
          <div class="avatar-subtitle">O Orquestrador</div>
        </div>
        <div class="agent-body">
          <div class="agent-role">Auditor Chefe — Decisões &amp; Consolidação</div>
          <div class="agent-metrics">
            <div class="metric">
              <span class="metric-val">{mycroft.calls}</span>
              <span class="metric-lbl">chamadas LLM</span>
            </div>
            <div class="metric">
              <span class="metric-val">{mycroft.prompt_tokens:,}</span>
              <span class="metric-lbl">prompt tokens</span>
            </div>
            <div class="metric">
              <span class="metric-val">{'Sim' if data.watson_overruled else 'Não'}</span>
              <span class="metric-lbl">overrule Watson</span>
            </div>
            <div class="metric">
              <span class="metric-val">{'Sim' if data.sherlock_overruled else 'Não'}</span>
              <span class="metric-lbl">overrule Sherlock</span>
            </div>
          </div>
          <div class="agent-note">
            definir_tasks · avaliar · fixar_decisao · consolidar ·
            mapear_dados · redigir_apendice · avaliar_entrega
          </div>
        </div>
      </div>

      <!-- Sherlock Holmes — Validação Metodológica -->
      <div class="agent-card">
        <div class="agent-avatar sherlock">
          {_avatar_visual("sherlock", "🔎", "S")}
          <div class="avatar-title">Sherlock Holmes</div>
          <div class="avatar-subtitle">O Metodologista</div>
        </div>
        <div class="agent-body">
          <div class="agent-role">Auditor de Validação Metodológica CBS</div>
          <div class="agent-metrics">
            <div class="metric">
              <span class="metric-val">{data.metodologia_chars:,}</span>
              <span class="metric-lbl">chars RN+Metodologia</span>
            </div>
            <div class="metric">
              <span class="metric-val">{data.corpus_juridico_chars:,}</span>
              <span class="metric-lbl">chars corpus jurídico</span>
            </div>
            <div class="metric">
              <span class="metric-val">{data.sherlock_dilemmas}</span>
              <span class="metric-lbl">dilemas</span>
            </div>
            <div class="metric">
              <span class="metric-val">{sherlock.calls}</span>
              <span class="metric-lbl">chamadas LLM</span>
            </div>
          </div>
          <div class="agent-note">
            {data.sherlock_rodadas} rodada{'s' if data.sherlock_rodadas != 1 else ''} ·
            {'⚠ overruled por Mycroft' if data.sherlock_overruled else 'aprovado por Mycroft'}
          </div>
        </div>
      </div>

      <!-- Inspetor Lestrade — Comando do Ciclo -->
      <div class="agent-card">
        <div class="agent-avatar lestrade">
          {_avatar_visual("lestrade", "★", "L")}
          <div class="avatar-title">Insp. Lestrade</div>
          <div class="avatar-subtitle">O Comando</div>
        </div>
        <div class="agent-body">
          <div class="agent-role">Autoridade do Ciclo — Chancela &amp; Decisão</div>
          <div class="agent-metrics">
            <div class="metric">
              <span class="metric-val metric-sm">
                <span class="badge badge-{_status_class(data.status)}">{_e(data.status or '—')}</span>
              </span>
              <span class="metric-lbl">estado</span>
            </div>
            <div class="metric">
              <span class="metric-val">{'Sim' if data.is_terminal else 'Em curso'}</span>
              <span class="metric-lbl">ciclo encerrado</span>
            </div>
          </div>
          <div class="agent-note">Papel humano · abre, autoriza e chancela o ciclo</div>
        </div>
      </div>

    </div>
  </div>"""


# ── Renderer principal ────────────────────────────────────────────────────────

def render_html(data: CycleReportData, live_mode: bool | None = None) -> str:
    """Gera HTML standalone completo para o painel de acompanhamento.

    live_mode: True → inclui meta-refresh de 10s; None → deriva do is_terminal.
    """
    if live_mode is None:
        live_mode = not data.is_terminal

    refresh_tag = '<meta http-equiv="refresh" content="10">' if live_mode else ""
    live_badge = (
        '<span class="badge badge-live pulse">● AO VIVO</span>'
        if live_mode else ""
    )

    sc = _status_class(data.status)
    mc = _motor_class(data.motor_saida_limpo, data.motor_saida_occurrences)

    total_prompt = sum(s.prompt_tokens for s in data.calls_by_agent.values())
    total_compl = sum(s.completion_tokens for s in data.calls_by_agent.values())

    # LLM table rows (mostra todos os agentes que logaram chamadas)
    llm_rows = ""
    for agent, s in sorted(data.calls_by_agent.items()):
        llm_rows += (
            f"<tr><td><strong>{_e(agent)}</strong></td><td>{s.calls}</td>"
            f"<td>{s.prompt_tokens:,}</td><td>{s.completion_tokens:,}</td>"
            f"<td>{s.avg_response_length:,.0f}</td></tr>"
        )
    if not llm_rows:
        llm_rows = "<tr><td colspan='5' class='muted-text'>Sem chamadas registradas</td></tr>"

    # Fase table rows
    fase_rows = ""
    for f in data.fases:
        dur = f"{f.duration_min:.0f}min" if f.duration_min else "—"
        fase_rows += (
            f"<tr><td>{_e(f.fase)}</td><td>{_e(f.started_at)}</td>"
            f"<td>{_e(f.ended_at or '…')}</td><td>{_e(dur)}</td></tr>"
        )
    if not fase_rows:
        fase_rows = "<tr><td colspan='4' class='muted-text'>Sem dados</td></tr>"

    # Key events table rows
    event_rows = ""
    for e in data.key_events:
        det = e.get("details", {})
        det_str = ", ".join(f"{k}={v}" for k, v in det.items() if v not in (None, "", {}))
        event_rows += (
            f"<tr><td class='mono'>{_e(e.get('timestamp_utc', ''))}</td>"
            f"<td>{_e(e.get('event_type', ''))}</td>"
            f"<td class='muted-text'>{_e(e.get('phase') or '')}</td>"
            f"<td class='muted-text'>{_e(det_str)}</td></tr>"
        )

    # Stranger Room html
    sr_html = ""
    if data.stranger_room_files:
        for fase, arquivos in sorted(data.stranger_room_files.items()):
            sr_html += f'<details class="sr-phase"><summary>{_e(fase)} ({len(arquivos)} arquivos)</summary><ul>'
            for arq in arquivos:
                sr_html += f"<li><code>{_e(arq)}</code></li>"
            sr_html += "</ul></details>"
    else:
        sr_html = "<p class='muted-text'>Sem arquivos de deliberação.</p>"

    # Output
    output_html = ""
    if data.output_filename:
        open_link = (
            f'<a class="output-link" href="file://{_e(data.output_path)}">Abrir relatório ↗</a>'
            if data.output_path else ""
        )
        output_html = f"""
        <div class="output-info">
          <div class="output-name">{_e(data.output_filename)}</div>
          <div class="output-hash muted-text mono">{_e(data.output_hash)}</div>
          {open_link}
        </div>"""
    else:
        output_html = "<p class='muted-text'>Output ainda não gerado.</p>"

    # Agent cards
    agent_cards = _agent_cards_html(data)

    # Fase de Entrega
    entrega_html = _entrega_html(data)

    # Watson progress
    watson_progress_html = f"""
        <div class="progress-wrap">
          <div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div>
          <span class="progress-label">{data.arquivos_analisados} arquivos analisados pelo Dr. Watson</span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {refresh_tag}
  <title>Diógenes — {_e(data.cycle_id)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #070d1a;
      --surface: rgba(15, 25, 45, 0.9);
      --surface2: rgba(22, 35, 60, 0.85);
      --border: rgba(148, 163, 184, 0.10);
      --border2: rgba(148, 163, 184, 0.06);
      --text: #e8edf5;
      --muted: #7b90b2;
      --success: #10b981;
      --warning: #f59e0b;
      --error: #ef4444;
      --info: #3b82f6;
      --accent: #6366f1;
      --live: #a855f7;

      /* agentes */
      --irene-1: #064e3b;  --irene-2: #047857;  --irene-3: #10b981;
      --watson-1: #1e2f5e; --watson-2: #1d4ed8; --watson-3: #60a5fa;
      --mycroft-1: #2d1b69; --mycroft-2: #6d28d9; --mycroft-3: #a78bfa;
      --sherlock-1: #78350f; --sherlock-2: #b45309; --sherlock-3: #fbbf24;
      --lestrade-1: #3f2d18; --lestrade-2: #8a6d3b; --lestrade-3: #d4af6a;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      min-height: 100vh;
      padding: 0 0 56px;
    }}
    a {{ color: var(--info); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code, .mono {{ font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace; font-size: 12px; }}
    code {{ background: rgba(148,163,184,0.1); padding: 2px 5px; border-radius: 3px; }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, #060c1a 0%, #0d1633 40%, #1a1040 100%);
      border-bottom: 1px solid var(--border);
      padding: 22px 36px;
      display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
    }}
    .header-brand {{ flex: 1; min-width: 200px; }}
    .brand {{ font-size: 10px; font-weight: 600; text-transform: uppercase;
               letter-spacing: 0.15em; color: var(--muted); margin-bottom: 4px; }}
    .cycle-id {{ font-size: 17px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }}
    .header-right {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}

    /* ── Badges ── */
    .badge {{
      display: inline-block; font-size: 10px; font-weight: 700;
      padding: 3px 10px; border-radius: 100px;
      text-transform: uppercase; letter-spacing: 0.07em;
    }}
    .badge-success {{ background: rgba(16,185,129,0.15); color: var(--success); border: 1px solid rgba(16,185,129,0.25); }}
    .badge-warning {{ background: rgba(245,158,11,0.15); color: var(--warning); border: 1px solid rgba(245,158,11,0.25); }}
    .badge-error   {{ background: rgba(239,68,68,0.15);  color: var(--error);   border: 1px solid rgba(239,68,68,0.25); }}
    .badge-info    {{ background: rgba(59,130,246,0.15); color: var(--info);    border: 1px solid rgba(59,130,246,0.25); }}
    .badge-muted   {{ background: rgba(148,163,184,0.08); color: var(--muted);  border: 1px solid var(--border); }}
    .badge-live    {{ background: rgba(168,85,247,0.15); color: var(--live);    border: 1px solid rgba(168,85,247,0.25); }}
    @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
    .pulse {{ animation: pulse 2.2s ease-in-out infinite; }}

    /* ── Main ── */
    main {{ max-width: 1280px; margin: 0 auto; padding: 36px 28px; }}

    /* ── Section ── */
    .section {{ margin-bottom: 32px; }}
    .section h2 {{
      font-size: 11px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.12em; color: var(--muted);
      margin-bottom: 14px; padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }}

    /* ── Overview cards ── */
    .cards-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }}
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 18px 20px; min-width: 150px; flex: 1;
    }}
    .card h3 {{ font-size: 10px; font-weight: 600; color: var(--muted);
                 text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }}
    .card .value {{ font-size: 26px; font-weight: 800; color: var(--text); line-height: 1.1; }}
    .card .value.success {{ color: var(--success); }}
    .card .value.warning {{ color: var(--warning); }}
    .card .value.error   {{ color: var(--error); }}
    .card .value.info    {{ color: var(--info); }}
    .card .sub {{ font-size: 12px; color: var(--muted); margin-top: 5px; }}

    /* ── Agent cards ── */
    .agents-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}
    .agent-card {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      transition: border-color 0.2s;
    }}
    .agent-card:hover {{ border-color: rgba(148,163,184,0.25); }}

    /* Avatar area */
    .agent-avatar {{
      position: relative;
      height: 200px;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      overflow: hidden;
      user-select: none;
    }}
    .agent-avatar::before {{
      content: '';
      position: absolute; inset: 0; z-index: 1;
      background: linear-gradient(180deg, var(--ava, rgba(255,255,255,0.2)) 0%, transparent 58%);
      mix-blend-mode: overlay; opacity: 0.6;
      pointer-events: none;
    }}
    .agent-avatar::after {{
      content: '';
      position: absolute; bottom: 0; left: 0; right: 0; height: 88px; z-index: 1;
      background: linear-gradient(to top, rgba(4,8,18,0.82) 8%, transparent);
      pointer-events: none;
    }}
    .agent-avatar.irene   {{ background: linear-gradient(170deg, var(--irene-1) 0%, var(--irene-2) 100%); --ava: var(--irene-3); }}
    .agent-avatar.watson  {{ background: linear-gradient(170deg, var(--watson-1) 0%, var(--watson-2) 100%); --ava: var(--watson-3); }}
    .agent-avatar.mycroft {{ background: linear-gradient(170deg, var(--mycroft-1) 0%, var(--mycroft-2) 100%); --ava: var(--mycroft-3); }}
    .agent-avatar.sherlock {{ background: linear-gradient(170deg, var(--sherlock-1) 0%, var(--sherlock-2) 100%); --ava: var(--sherlock-3); }}
    .agent-avatar.lestrade {{ background: linear-gradient(170deg, var(--lestrade-1) 0%, var(--lestrade-2) 100%); --ava: var(--lestrade-3); }}

    /* Retrato (ilustração Paget, domínio público) — tonalizado à paleta */
    .avatar-img {{
      position: absolute; inset: 0; z-index: 0;
      width: 100%; height: 100%;
      object-fit: cover; object-position: center 20%;
      filter: grayscale(1) sepia(0.45) brightness(1.03) contrast(1.04);
    }}
    .agent-avatar.mycroft  .avatar-img {{ object-position: center 10%; }}
    .agent-avatar.watson   .avatar-img {{ object-position: 32% 18%; }}
    .agent-avatar.sherlock .avatar-img {{ object-position: center 30%; }}
    .agent-avatar.irene    .avatar-img {{ object-position: center 16%; }}
    .agent-avatar.lestrade .avatar-img {{ object-position: center 18%; }}

    .avatar-deco {{
      font-size: 28px; opacity: 0.75;
      position: absolute; top: 16px; right: 16px; z-index: 1;
    }}
    .avatar-letter {{
      font-size: 88px; font-weight: 900; line-height: 1;
      letter-spacing: -0.04em;
      color: rgba(255,255,255,0.88);
      text-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 2px 4px rgba(0,0,0,0.4);
      z-index: 1;
    }}
    .avatar-title {{
      font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.95);
      position: absolute; bottom: 20px; left: 0; right: 0;
      text-align: center; z-index: 2; letter-spacing: 0.01em;
    }}
    .avatar-subtitle {{
      font-size: 10px; font-weight: 500;
      color: rgba(255,255,255,0.55);
      position: absolute; bottom: 6px; left: 0; right: 0;
      text-align: center; z-index: 2; letter-spacing: 0.08em; text-transform: uppercase;
    }}

    /* Agent body */
    .agent-body {{ padding: 16px 18px; }}
    .agent-role {{ font-size: 11px; color: var(--muted); margin-bottom: 12px;
                    font-weight: 500; text-transform: uppercase; letter-spacing: 0.07em; }}
    .agent-metrics {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }}
    .metric {{ display: flex; flex-direction: column; align-items: flex-start; }}
    .metric-val {{ font-size: 20px; font-weight: 800; color: var(--text); line-height: 1.1; }}
    .metric-val.metric-warn {{ color: var(--warning); }}
    .metric-val.metric-ok   {{ color: var(--success); }}
    .metric-val.metric-sm   {{ font-size: 14px; }}
    .metric-lbl {{ font-size: 10px; color: var(--muted); text-transform: uppercase;
                    letter-spacing: 0.07em; margin-top: 2px; }}
    .agent-note {{ font-size: 11px; color: var(--muted); border-top: 1px solid var(--border2);
                    padding-top: 10px; font-style: italic; }}

    /* ── Fase de Entrega ── */
    .entrega-tipo {{ font-size: 10px; font-weight: 600; text-transform: uppercase;
                      letter-spacing: 0.06em; color: var(--lestrade-3);
                      background: rgba(212,175,106,0.10); border: 1px solid rgba(212,175,106,0.25);
                      border-radius: 5px; padding: 2px 7px; white-space: nowrap; }}
    .entrega-calls {{ margin-top: 12px; font-size: 12px; color: var(--muted);
                       display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .entrega-calls-lbl {{ text-transform: uppercase; font-size: 10px; letter-spacing: 0.07em; }}
    .entrega-chip {{ font-size: 11px; font-family: 'SF Mono','Fira Code',monospace;
                      color: var(--text); background: rgba(148,163,184,0.08);
                      border: 1px solid var(--border); border-radius: 6px; padding: 2px 8px; }}
    .entrega-chip b {{ color: var(--mycroft-3); }}

    /* ── Progress bar ── */
    .progress-wrap {{ margin: 14px 0; }}
    .progress-bar {{
      height: 5px; background: rgba(148,163,184,0.12);
      border-radius: 3px; overflow: hidden; margin-bottom: 6px;
    }}
    .progress-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--info), var(--accent));
      border-radius: 3px; transition: width 0.5s ease;
    }}
    .progress-label {{ font-size: 12px; color: var(--muted); }}

    /* ── Tables ── */
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .table-wrap {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; overflow: hidden;
    }}
    th {{
      background: rgba(7,13,26,0.7); color: var(--muted);
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.1em; padding: 10px 16px; text-align: left;
    }}
    td {{ padding: 10px 16px; border-top: 1px solid var(--border2); vertical-align: middle; }}
    tr:hover td {{ background: rgba(148,163,184,0.03); }}
    .muted-text {{ color: var(--muted); }}

    /* ── Details / Summary ── */
    details {{
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
      overflow: hidden;
    }}
    summary {{
      padding: 13px 18px; font-size: 13px; font-weight: 500;
      color: var(--text); cursor: pointer; list-style: none;
      display: flex; align-items: center; gap: 8px;
      user-select: none;
    }}
    summary::-webkit-details-marker {{ display: none; }}
    summary::before {{ content: "▶"; font-size: 9px; color: var(--muted); transition: transform 0.15s; }}
    details[open] > summary::before {{ transform: rotate(90deg); }}
    details .table-wrap {{ border-radius: 0; border: none; border-top: 1px solid var(--border); }}

    /* ── Stranger Room ── */
    .sr-phase {{ margin-bottom: 8px; border-radius: 10px; }}
    .sr-phase ul {{ padding: 12px 18px; list-style: none; }}
    .sr-phase li {{ padding: 3px 0; color: var(--muted); font-size: 12px; }}

    /* ── Output ── */
    .output-info {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 18px 22px;
    }}
    .output-name {{ font-size: 14px; font-weight: 600; margin-bottom: 6px; }}
    .output-hash {{ font-size: 11px; margin-bottom: 10px; color: var(--muted); }}
    .output-link {{ font-size: 13px; font-weight: 500; color: var(--info); }}

    /* ── Stat summary ── */
    .stat-summary {{ font-size: 13px; color: var(--muted); margin-bottom: 14px; }}

    /* ── Footer ── */
    footer {{
      max-width: 1280px; margin: 36px auto 0; padding: 16px 28px;
      border-top: 1px solid var(--border); color: var(--muted);
      font-size: 11px; display: flex; justify-content: space-between;
      flex-wrap: wrap; gap: 8px; letter-spacing: 0.02em;
    }}
  </style>
</head>
<body>

<header>
  <div class="header-brand">
    <div class="brand">DVA-CBS | TC 015.848/2025-6 | TCU / SecexContas</div>
    <div class="cycle-id">{_e(data.cycle_id)}</div>
  </div>
  <div class="header-right">
    <span class="badge badge-{sc}">{_e(data.status)}</span>
    {live_badge}
  </div>
</header>

<main>

  <!-- Visão Geral -->
  <div class="section">
    <h2>Visão Geral</h2>
    <div class="cards-row">
      <div class="card">
        <h3>Duração</h3>
        <div class="value">{_e(data.duration_str)}</div>
        <div class="sub">{_e(data.opened_at_utc)} UTC</div>
      </div>
      <div class="card">
        <h3>Módulo</h3>
        <div class="value" style="font-size:20px">{_e(data.module_id)}</div>
        <div class="sub">Atividade {data.activity}</div>
      </div>
      <div class="card">
        <h3>Chamadas LLM</h3>
        <div class="value">{data.total_calls}</div>
        <div class="sub">{total_prompt:,} prompt + {total_compl:,} completion</div>
      </div>
      <div class="card">
        <h3>Versão</h3>
        <div class="value" style="font-size:20px">v{_e(data.diogenes_version)}</div>
        <div class="sub"><code>{_e(data.git_commit)}</code></div>
      </div>
    </div>
  </div>

  {agent_cards}

  <!-- Watson — progresso -->
  <div class="section">
    <h2>Análise de Arquivos (Dr. Watson)</h2>
    {watson_progress_html}
  </div>

  <!-- Chamadas LLM por Agente -->
  <div class="section">
    <h2>Chamadas LLM por Agente</h2>
    <p class="stat-summary">
      {data.total_calls} chamadas · {total_prompt:,} prompt tokens · {total_compl:,} completion tokens
      &nbsp;·&nbsp; <em>Irene usa pipeline C1–C5 próprio, não contabilizado aqui</em>
    </p>
    <details open>
      <summary>Detalhe por agente ({len(data.calls_by_agent)} registrados)</summary>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Agente</th><th>Chamadas</th><th>Prompt Tokens</th>
              <th>Completion Tokens</th><th>Resp. Média (chars)</th>
            </tr>
          </thead>
          <tbody>{llm_rows}</tbody>
        </table>
      </div>
    </details>
  </div>

  <!-- Timeline de Fases -->
  <div class="section">
    <h2>Timeline de Fases</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Fase</th><th>Início (UTC)</th><th>Fim (UTC)</th><th>Duração</th></tr>
        </thead>
        <tbody>{fase_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Motor de Saída -->
  <div class="section">
    <h2>Motor de Saída</h2>
    <div class="cards-row">
      <div class="card">
        <h3>Ocorrências</h3>
        <div class="value {'error' if data.motor_saida_occurrences > 0 else 'success'}">{data.motor_saida_occurrences}</div>
        <div class="sub">encontradas antes da higienização</div>
      </div>
      <div class="card">
        <h3>Decisão</h3>
        <div class="sub" style="margin-top:8px">
          <span class="badge badge-{mc}">{_e(data.motor_saida_decision or '—')}</span>
        </div>
      </div>
    </div>
  </div>
  {entrega_html}

  <!-- Deliberações Internas -->
  <div class="section">
    <h2>Deliberações Internas</h2>
    {sr_html}
  </div>

  <!-- Eventos-chave -->
  <div class="section">
    <h2>Eventos-chave</h2>
    <details>
      <summary>{len(data.key_events)} eventos milestone</summary>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Evento</th><th>Fase</th><th>Detalhes</th></tr>
          </thead>
          <tbody>{event_rows}</tbody>
        </table>
      </div>
    </details>
  </div>

  <!-- Output Final -->
  <div class="section">
    <h2>Output Final</h2>
    {output_html}
  </div>

</main>

<footer>
  <span>DVA-CBS | TC 015.848/2025-6 | Uso Interno Restrito</span>
  <span>{"● Atualiza a cada 10s" if live_mode else "Ciclo concluído"} &nbsp;·&nbsp; Gerado em {_e(data.generated_at)} UTC</span>
</footer>
</body>
</html>"""


def atualizar_report_html(cycle_id: str, workspace: Path) -> None:
    """Atualiza o arquivo report.html no diretório do ciclo (best-effort)."""
    try:
        from diogenes.reports.cycle_report import build_report
        data = build_report(cycle_id, workspace)
        html = render_html(data)
        html_path = workspace / "cycles" / cycle_id / "report.html"
        html_path.write_text(html, encoding="utf-8")
    except Exception:
        pass

