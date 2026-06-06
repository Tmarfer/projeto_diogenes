"""
delivery/dashboard.py — DVA-CBS | Projeto Diógenes

DashboardGenerator — render genérico (módulo-agnóstico) do painel HTML no padrão
visual GT Reforma Tributária / SecexContas, com paridade ao Dashboard CBS Módulo PF v5.
Dirigido inteiramente pelo PacoteEntrega (o "blueprint" produzido por Mycroft em
`mapear_dados_modulo`): cada bloco vira uma seção navegável renderizada conforme seu
`tipo` — `visao_geral`, `analitica` ou `sensibilidade` — e o insumo de ocorrências do
Sherlock (§11) vira a aba de Inconsistências.

Princípio de auditoria: o renderer apenas formata. Os NÚMEROS já foram lidos
deterministicamente da planilha pelo ExtractorFinanceiro; o texto (narrativa, cards de
metodologia, rótulos) é curado por Mycroft. Funciona para os 18+ módulos porque consome
o esquema canônico, não um layout fixo por módulo.

Sem dependências pesadas: HTML estático com Chart.js via CDN.
"""
from __future__ import annotations

import html
import json

from diogenes.models import (
    BlocoFinanceiro,
    CenarioSensibilidade,
    GraficoEntrega,
    KPIEntrega,
    MetodologiaCard,
    OcorrenciaEntrega,
    PacoteEntrega,
    TabelaEntrega,
)

_NIVEL_CLASSE = {
    "CRITICO": "crit", "ALERTA": "alert", "ATENCAO": "aten", "RESOLVIDO": "ok",
}
_NIVEL_ROTULO = {
    "CRITICO": "Crítico", "ALERTA": "Alerta", "ATENCAO": "Atenção", "RESOLVIDO": "Resolvido",
}

# Vocabulário de badges de linha: célula cujo texto é exatamente um destes vira um chip
# colorido (semântica de débito/crédito/subtração) — espelha o padrão do v5.
_BADGE_VOCAB = {
    "débito": "blue", "debito": "blue", "débitos": "blue", "adição": "blue", "soma": "blue",
    "crédito": "green", "credito": "green", "créditos": "green",
    "subtração": "red", "subtracao": "red", "(−)": "red", "dedução": "red", "deducao": "red",
    "ajuste": "amber", "total": "navy", "líquido": "navy", "liquido": "navy",
}


def gerar_dashboard_html(pacote: PacoteEntrega) -> str:
    secoes_nav: list[str] = []
    secoes_body: list[str] = []
    n = 0

    # Garante uma Visão Geral mesmo em mapas legados (sem bloco tipado).
    tem_visao = any(b.tipo == "visao_geral" for b in pacote.blocos_financeiros)
    if not tem_visao and (pacote.valores_agregados or pacote.sensibilidade_redutor):
        n += 1
        sid = "sec-visao-geral"
        secoes_nav.append(_nav_link(sid, f"{n:02d}", "Visão Geral"))
        secoes_body.append(_visao_geral_legado(sid, f"{n:02d}", pacote))

    for bloco in pacote.blocos_financeiros:
        if _bloco_vazio(bloco):
            continue
        n += 1
        sid = f"sec-{_slug(bloco.id) or n}"
        rotulo = bloco.titulo or f"Seção {n}"
        secoes_nav.append(_nav_link(sid, f"{n:02d}", rotulo))
        secoes_body.append(_render_bloco(sid, f"{n:02d}", bloco, pacote))

    # Aba de Inconsistências (sempre, mesmo que vazia).
    n += 1
    secoes_nav.append(_nav_link("sec-inconsistencias", f"{n:02d}", "Inconsistências"))
    secoes_body.append(_inconsistencias_html(f"{n:02d}", pacote.ocorrencias, pacote))

    chips = "".join(
        f'<span class="hero-chip">{html.escape(k)} <b>{html.escape(v)}</b></span>'
        for k, v in (
            ("Processo", pacote.processo),
            ("Acórdão", pacote.acordao),
            ("Relator", pacote.relator),
            ("Versão", pacote.versao or "—"),
        )
        if v
    )

    return _TEMPLATE.format(
        titulo=html.escape(f"Dashboard — Módulo {pacote.modulo} {pacote.modulo_nome}"),
        css=_CSS,
        modulo=html.escape(str(pacote.modulo)),
        modulo_nome=html.escape(pacote.modulo_nome),
        hero_chips=chips,
        nav="\n".join(secoes_nav),
        body="\n".join(secoes_body),
        rodape=html.escape(f"{pacote.processo} · {pacote.unidade}"),
        chart_js=_CHART_INIT,
    )


# ── render por tipo de bloco ────────────────────────────────────

def _render_bloco(sid: str, num: str, b: BlocoFinanceiro, p: PacoteEntrega) -> str:
    if b.tipo == "visao_geral":
        return _bloco_visao_geral(sid, num, b, p)
    if b.tipo == "sensibilidade":
        return _bloco_sensibilidade(sid, num, b, p)
    return _bloco_analitico(sid, num, b)


def _bloco_visao_geral(sid: str, num: str, b: BlocoFinanceiro, p: PacoteEntrega) -> str:
    partes = [_sec_abre(sid, num, b.titulo or "Visão Geral", colapsavel=False)]
    if p.veredito:
        partes.append(f'<div class="verdict v-{_verdict_classe(p.veredito)}">'
                      f'Veredito de conformidade: <b>{html.escape(p.veredito)}</b></div>')
    if b.narrativa:
        partes.append(f'<p class="sec-desc">{html.escape(b.narrativa)}</p>')
    if b.kpis:
        partes.append(_kpi_grid(b.kpis))
    if b.cards_metodologia:
        partes.append(_metod_grid(b.cards_metodologia))
    partes.append(_graficos_html(sid, b.graficos))
    for t in b.tabelas:
        partes.append(_tabela_html(t))
    partes.append("</section>")
    return "".join(partes)


def _bloco_analitico(sid: str, num: str, b: BlocoFinanceiro) -> str:
    partes = [_sec_abre(sid, num, b.titulo or "Seção", colapsavel=True)]
    if b.narrativa:
        partes.append(f'<p class="sec-desc">{html.escape(b.narrativa)}</p>')
    elif b.descricao:
        partes.append(f'<p class="sec-desc">{html.escape(b.descricao)}</p>')
    if b.kpis:
        partes.append(_kpi_grid(b.kpis))
    partes.append(_graficos_html(sid, b.graficos))
    for t in b.tabelas:
        partes.append(_tabela_html(t))
    partes.append("</div></section>")
    return "".join(partes)


def _bloco_sensibilidade(sid: str, num: str, b: BlocoFinanceiro, p: PacoteEntrega) -> str:
    partes = [_sec_abre(sid, num, b.titulo or "Sensibilidade", colapsavel=True)]
    if b.narrativa:
        partes.append(f'<p class="sec-desc">{html.escape(b.narrativa)}</p>')
    elif b.descricao:
        partes.append(f'<p class="sec-desc">{html.escape(b.descricao)}</p>')
    if b.cenarios:
        partes.append(_scenario_grid(b.cenarios))
    partes.append(_graficos_html(sid, b.graficos))
    # Série de sensibilidade do mapa legado, se houver e o bloco não trouxe gráfico próprio.
    if not b.graficos and p.sensibilidade_redutor:
        sr = p.sensibilidade_redutor
        partes.append(_grafico_html(f"g-{sid}-sens", GraficoEntrega(
            tipo="linha", titulo="Sensibilidade ao redutor de comportamento",
            labels=[f"{r}%" for r in sr.get("redutores", [])], series=sr.get("valores", []),
            layout="full")))
    for t in b.tabelas:
        partes.append(_tabela_html(t))
    partes.append("</div></section>")
    return "".join(partes)


def _visao_geral_legado(sid: str, num: str, p: PacoteEntrega) -> str:
    """Visão Geral sintetizada a partir de mapas antigos (sem bloco tipado)."""
    partes = [_sec_abre(sid, num, "Visão Geral", colapsavel=False)]
    if p.veredito:
        partes.append(f'<div class="verdict v-{_verdict_classe(p.veredito)}">'
                      f'Veredito de conformidade: <b>{html.escape(p.veredito)}</b></div>')
    if p.valores_agregados:
        rows = [[v.get("descricao", ""), v.get("valor_2023", ""), v.get("valor_2024", "")]
                for v in p.valores_agregados]
        partes.append(_tabela_html(TabelaEntrega(
            titulo="Valores agregados (2023 vs 2024)",
            headers=["Componente", "2023", "2024"], rows=rows)))
    if p.sensibilidade_redutor:
        sr = p.sensibilidade_redutor
        partes.append(_grafico_html(f"g-{sid}-sens", GraficoEntrega(
            tipo="linha", titulo="Sensibilidade ao redutor de comportamento",
            labels=[f"{r}%" for r in sr.get("redutores", [])], series=sr.get("valores", []),
            layout="full")))
    partes.append("</section>")
    return "".join(partes)


# ── componentes ─────────────────────────────────────────────────

def _sec_abre(sid: str, num: str, titulo: str, *, colapsavel: bool) -> str:
    cabecalho = (
        f'<div class="sec-h"><span class="sec-n">{num}</span>'
        f'<h2 class="sec-t">{html.escape(titulo)}</h2></div>'
    )
    if not colapsavel:
        return f'<section id="{sid}" class="sec">{cabecalho}'
    return (
        f'<section id="{sid}" class="sec">'
        f'<div class="sec-bar" onclick="toggleSec(this)">{cabecalho}'
        f'<span class="sec-toggle">▾</span></div><div class="sec-body open">'
    )


def _kpi_grid(kpis: list[KPIEntrega]) -> str:
    cards = []
    for k in kpis:
        delta = ""
        if k.delta:
            delta = f'<span class="kpi-delta d-{html.escape(k.delta_tipo or "neutral")}">{html.escape(k.delta)}</span>'
        unidade = f'<span class="kpi-unit">{html.escape(k.unidade)}</span>' if k.unidade else ""
        nota = f'<div class="kpi-n">{html.escape(k.nota)}</div>' if k.nota else ""
        cards.append(
            f'<div class="kpi {html.escape(k.destaque)}">'
            f'<div class="kpi-top"><span class="kpi-v">{html.escape(k.valor)}</span>{unidade}{delta}</div>'
            f'<div class="kpi-l">{html.escape(k.rotulo)}</div>{nota}</div>'
        )
    return f'<div class="kpi-grid">{"".join(cards)}</div>'


def _metod_grid(cards: list[MetodologiaCard]) -> str:
    blocos = []
    for c in cards:
        chips = "".join(f'<span class="metod-chip">{html.escape(ch)}</span>' for ch in c.chips)
        chips_wrap = f'<div class="metod-chips">{chips}</div>' if chips else ""
        tag = f'<div class="metod-tag">{html.escape(c.tag)}</div>' if c.tag else ""
        blocos.append(
            f'<div class="metod-card">{tag}'
            f'<div class="metod-title">{html.escape(c.titulo)}</div>'
            f'<div class="metod-body">{html.escape(c.corpo)}</div>{chips_wrap}</div>'
        )
    return f'<div class="metod-grid">{"".join(blocos)}</div>'


def _scenario_grid(cenarios: list[CenarioSensibilidade]) -> str:
    cards = []
    for c in cenarios:
        nota = f'<div class="scn-n">{html.escape(c.nota)}</div>' if c.nota else ""
        cards.append(
            f'<div class="scn {html.escape(c.destaque)}">'
            f'<div class="scn-l">{html.escape(c.rotulo)}</div>'
            f'<div class="scn-v">{html.escape(c.valor)}</div>{nota}</div>'
        )
    return f'<div class="scn-grid">{"".join(cards)}</div>'


def _graficos_html(sid: str, graficos: list[GraficoEntrega]) -> str:
    if not graficos:
        return ""
    partes: list[str] = []
    fila: list[str] = []   # acumula gráficos "grid" para emparelhar

    def _fecha_fila() -> None:
        if fila:
            partes.append(f'<div class="chart-grid">{"".join(fila)}</div>')
            fila.clear()

    for i, g in enumerate(graficos):
        card = _grafico_html(f"g-{sid}-{i}", g)
        if g.layout == "full":
            _fecha_fila()
            partes.append(f'<div class="chart-full">{card}</div>')
        else:
            fila.append(card)
    _fecha_fila()
    return "".join(partes)


def _tabela_html(t: TabelaEntrega) -> str:
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in t.headers)
    total_set = {s.strip().lower() for s in t.total_labels}
    trs = []
    for linha in t.rows:
        primeiro = str(linha[0]).strip().lower() if linha else ""
        is_total = bool(primeiro) and (primeiro in total_set
                                       or "líquid" in primeiro or "liquid" in primeiro)
        tds = "".join(f"<td>{_celula_render(c, is_total)}</td>" for c in linha)
        cls = ' class="total-row"' if is_total else ""
        trs.append(f"<tr{cls}>{tds}</tr>")
    cap = f'<div class="tbl-cap">{html.escape(t.titulo)}</div>' if t.titulo else ""
    sub = f'<div class="tbl-sub">{html.escape(t.subtitulo)}</div>' if t.subtitulo else ""
    src = f'<div class="tbl-src">Fonte: {html.escape(t.fonte)}</div>' if t.fonte else ""
    thead = f"<thead><tr>{th}</tr></thead>" if th else ""
    return (f'<div class="tbl-wrap">{cap}{sub}<table class="data-table">'
            f'{thead}<tbody>{"".join(trs)}</tbody></table>{src}</div>')


def _celula_render(valor: object, is_total: bool) -> str:
    txt = "" if valor is None else str(valor)
    chave = txt.strip().lower()
    cor = _BADGE_VOCAB.get(chave)
    if cor:
        return f'<span class="badge b-{cor}">{html.escape(txt)}</span>'
    esc = html.escape(txt)
    return f"<b>{esc}</b>" if is_total else esc


def _grafico_html(cid: str, g: GraficoEntrega) -> str:
    tipo_js = {"barras": "bar", "barras_horizontais": "bar", "rosca": "doughnut",
               "linha": "line"}.get(g.tipo, "bar")
    cfg = json.dumps({"id": cid, "tipo": tipo_js, "labels": list(g.labels),
                      "series": list(g.series), "horizontal": g.tipo == "barras_horizontais"})
    titulo = f'<div class="card-title">{html.escape(g.titulo)}</div>' if g.titulo else ""
    sub = f'<div class="card-sub">{html.escape(g.subtitulo)}</div>' if g.subtitulo else ""
    src = f'<div class="tbl-src">{html.escape(g.nota)}</div>' if g.nota else ""
    return (f'<div class="card">{titulo}{sub}'
            f'<div class="chart-wrap" data-chart=\'{html.escape(cfg)}\'>'
            f'<canvas id="{cid}"></canvas></div>{src}</div>')


def _inconsistencias_html(num: str, ocorrencias: list[OcorrenciaEntrega], p: PacoteEntrega) -> str:
    contagem: dict[str, int] = {}
    for o in ocorrencias:
        contagem[o.nivel] = contagem.get(o.nivel, 0) + 1
    resumo = "".join(
        f'<span class="chip {_NIVEL_CLASSE.get(niv, "aten")}">'
        f'{_NIVEL_ROTULO.get(niv, niv)}: {contagem[niv]}</span>'
        for niv in ("CRITICO", "ALERTA", "ATENCAO", "RESOLVIDO") if niv in contagem
    ) or '<span class="chip ok">Nenhuma ocorrência registrada</span>'

    cards = []
    for o in ocorrencias:
        classe = _NIVEL_CLASSE.get(o.nivel, "aten")
        cards.append(
            f'<div class="inc inc-{classe}">'
            f'<div class="inc-top"><span class="inc-cod">{html.escape(o.codigo)}</span>'
            f'<span class="chip {classe}">{_NIVEL_ROTULO.get(o.nivel, o.nivel)}</span>'
            f'<span class="inc-st">{html.escape(o.status)}</span></div>'
            f'<div class="inc-tit">{html.escape(o.titulo)}</div>'
            + (f'<div class="inc-fund">Fundamento: {html.escape(o.fundamento_violado)}</div>'
               if o.fundamento_violado else "")
            + (f'<p class="inc-desc">{html.escape(o.descricao)}</p>' if o.descricao else "")
            + (f'<div class="inc-rfb"><b>Solicitação à RFB:</b> {html.escape(o.solicitacao_rfb)}</div>'
               if o.solicitacao_rfb else "")
            + (f'<div class="inc-res"><b>Resolução:</b> {html.escape(o.status_resolucao)}</div>'
               if o.status_resolucao else "")
            + "</div>"
        )
    corpo = "".join(cards) or '<p class="sec-desc">Nenhuma inconsistência identificada neste ciclo.</p>'

    pend = ""
    if p.pendencias_simulador:
        linhas = "".join(
            f'<li><b>{html.escape(pp.codigo)}</b>: {html.escape(pp.descricao)} '
            f'<span class="muted">({html.escape(pp.verificacao_futura)})</span></li>'
            for pp in p.pendencias_simulador
        )
        pend = (f'<h3 class="sub-t">Pendências para o Simulador Completo</h3>'
                f'<ul class="pend">{linhas}</ul>')

    return (f'<section id="sec-inconsistencias" class="sec">'
            f'<div class="sec-h"><span class="sec-n">{num}</span>'
            f'<h2 class="sec-t">Inconsistências Identificadas</h2></div>'
            f'<div class="resumo">{resumo}</div><div class="inc-grid">{corpo}</div>{pend}</section>')


# ── helpers ─────────────────────────────────────────────────────

def _verdict_classe(v: str) -> str:
    vu = v.upper()
    if "RESSALVA" in vu or "PARCIAL" in vu:
        return "amber"
    if "REQUER" in vu or ("INCONSISTENTE" in vu and "PARCIAL" not in vu):
        return "red"
    if "NAO_VERIFICAVEL" in vu:
        return "alert"
    return "green"


def _nav_link(sid: str, num: str, titulo: str) -> str:
    return (f'<a class="sb-link" href="#{sid}"><span class="snum">{num}</span>'
            f'<span class="stxt">{html.escape(titulo)}</span></a>')


def _slug(texto: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (texto or "").lower()).strip("-")


def _bloco_vazio(b: BlocoFinanceiro) -> bool:
    """Sem componente de dado, não vira seção — evita seções fantasma de mapas
    rasos/legados cujos campos não foram extraídos (só sobrou um título/descrição)."""
    return not (b.kpis or b.tabelas or b.graficos or b.cards_metodologia or b.cenarios)


# ── template e estilos ──────────────────────────────────────────

_CSS = """
:root{--navy-deep:#0B1E2D;--navy-dark:#162A3A;--navy:#1B3A4B;--navy-mid:#2A5068;--navy-light:#3D6E8A;
--gold:#B8963E;--gold-light:#D4AE56;--gold-pale:#EDD98A;
--cream-light:#FAF7F0;--white:#fff;--gray:#5A6A74;--gray-light:#E8EDF0;--gray-mid:#B0BEC5;
--red:#B83232;--red-soft:#FEF0EE;--green:#27604A;--green-soft:#EAF5F0;--amber:#9C6E1A;--amber-soft:#FDF3DC;
--blue-soft:#EAF1F7;--blue-border:#B5CCE0;
--shadow-sm:0 1px 3px rgba(11,30,45,.07);--radius:12px;--radius-sm:7px;
--font-display:'DM Serif Display',serif;--font-body:'Plus Jakarta Sans',sans-serif;--font-mono:'DM Mono',monospace;--sb-w:222px}
*{box-sizing:border-box;margin:0;padding:0}html{scroll-behavior:smooth}
body{font-family:var(--font-body);background:var(--cream-light);color:var(--navy);font-size:15px;line-height:1.6}
.sidebar{position:fixed;left:0;top:0;bottom:0;width:var(--sb-w);background:var(--navy-deep);display:flex;flex-direction:column;z-index:100;box-shadow:4px 0 20px rgba(0,0,0,.22)}
.sb-brand{padding:20px 18px 14px;border-bottom:1px solid rgba(255,255,255,.06)}
.sb-brand-top{font-family:var(--font-mono);font-size:9px;color:rgba(255,255,255,.3);letter-spacing:1.5px;text-transform:uppercase}
.sb-brand-name{font-family:var(--font-display);font-size:16px;color:var(--gold-light);line-height:1.2;margin-top:4px}
.sb-label{font-family:var(--font-mono);font-size:8.5px;color:rgba(255,255,255,.28);letter-spacing:1.5px;text-transform:uppercase;padding:14px 18px 5px}
.sb-nav{flex:1;overflow-y:auto;padding:6px 0}
.sb-link{display:flex;align-items:center;gap:9px;padding:8px 18px;color:rgba(255,255,255,.58);font-size:12.5px;font-weight:500;text-decoration:none;border-left:2px solid transparent}
.sb-link:hover{color:#fff;background:rgba(255,255,255,.05);border-left-color:var(--gold-light)}
.sb-link.open{color:var(--gold-light);border-left-color:var(--gold-light);background:linear-gradient(90deg,rgba(212,174,86,.1),transparent);font-weight:600}
.sb-link .snum{font-family:var(--font-mono);font-size:10px;opacity:.45;width:18px}
.sb-link .stxt{flex:1}
.sb-footer{padding:12px 18px;border-top:1px solid rgba(255,255,255,.06);font-family:var(--font-mono);font-size:9px;color:rgba(255,255,255,.25);line-height:1.8}
.page-main{margin-left:var(--sb-w);min-height:100vh}
.hero{background:linear-gradient(135deg,var(--navy-deep) 0%,var(--navy-dark) 55%,#0d2535 100%);padding:34px 40px 28px}
.hero-tag{font-family:var(--font-mono);font-size:9.5px;color:var(--gold-light);letter-spacing:2px;text-transform:uppercase;opacity:.8}
.hero-title{font-family:var(--font-display);font-size:28px;color:#fff;line-height:1.15;margin:10px 0}
.hero-title em{color:var(--gold-pale);font-style:italic}
.hero-meta{display:flex;gap:9px;flex-wrap:wrap;margin-top:14px}
.hero-chip{font-size:10.5px;font-family:var(--font-mono);color:rgba(255,255,255,.55);background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:3px 9px}
.hero-chip b{color:var(--gold-light)}
.wrap{max-width:1000px;padding:0 40px 90px}
.sec{padding:8px 0 4px;border-top:1px solid var(--gray-light)}
.sec-h{display:flex;align-items:baseline;gap:12px;padding:22px 0 12px}
.sec-bar{display:flex;align-items:center;gap:12px;cursor:pointer;user-select:none}
.sec-bar .sec-h{flex:1;padding:22px 0 18px}
.sec-toggle{font-size:13px;color:var(--gold);transition:transform .2s;padding-right:2px}
.sec-bar.collapsed .sec-toggle{transform:rotate(-90deg)}
.sec-body{display:block}
.sec-body:not(.open){display:none}
.sec-n{font-family:var(--font-mono);font-size:10.5px;color:var(--gold);background:rgba(184,150,62,.12);border:1px solid rgba(184,150,62,.28);border-radius:6px;padding:2px 8px}
.sec-t{font-family:var(--font-display);font-size:21px;color:var(--navy-deep)}
.sub-t{font-family:var(--font-display);font-size:16px;color:var(--navy-mid);margin:20px 0 8px}
.sec-desc{color:var(--gray);margin:2px 0 16px;max-width:780px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:13px;margin-bottom:18px}
.kpi{background:var(--white);border:1px solid var(--gray-light);border-radius:10px;padding:15px 17px;position:relative;overflow:hidden;box-shadow:var(--shadow-sm)}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--gold);opacity:.7}
.kpi.red::after{background:var(--red)}.kpi.green::after{background:var(--green)}.kpi.amber::after{background:var(--amber)}.kpi.navy::after{background:var(--navy-mid)}
.kpi-top{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.kpi-v{font-family:var(--font-display);font-size:23px;color:var(--navy-deep);line-height:1}
.kpi-unit{font-size:11px;color:var(--gray);font-family:var(--font-mono)}
.kpi-delta{font-size:10.5px;font-weight:700;font-family:var(--font-mono);margin-left:auto;padding:1px 6px;border-radius:5px}
.kpi-delta.d-up{color:var(--green);background:var(--green-soft)}
.kpi-delta.d-down{color:var(--red);background:var(--red-soft)}
.kpi-delta.d-neutral{color:var(--navy-mid);background:var(--blue-soft)}
.kpi-l{font-size:11.5px;color:var(--gray);margin-top:5px}
.kpi-n{font-size:10px;color:var(--gray-mid);font-family:var(--font-mono);margin-top:4px}
.metod-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:13px;margin-bottom:18px}
.metod-card{background:var(--white);border:1px solid var(--gray-light);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow-sm);border-top:3px solid var(--gold-light)}
.metod-tag{font-family:var(--font-mono);font-size:9px;color:var(--gold);letter-spacing:1.4px;text-transform:uppercase;margin-bottom:6px}
.metod-title{font-family:var(--font-display);font-size:15px;color:var(--navy-deep);margin-bottom:7px}
.metod-body{font-size:13px;color:#33444f;line-height:1.55}
.metod-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.metod-chip{font-size:9.5px;font-family:var(--font-mono);background:var(--blue-soft);color:var(--navy-mid);border:1px solid var(--blue-border);border-radius:4px;padding:2px 7px}
.scn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:13px;margin-bottom:18px}
.scn{background:var(--white);border:1px solid var(--gray-light);border-radius:10px;padding:15px 16px;box-shadow:var(--shadow-sm);border-left:4px solid var(--navy-mid)}
.scn.red{border-left-color:var(--red)}.scn.green{border-left-color:var(--green)}.scn.amber{border-left-color:var(--amber)}.scn.navy{border-left-color:var(--navy-deep)}
.scn-l{font-size:11px;color:var(--gray);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.4px}
.scn-v{font-family:var(--font-display);font-size:21px;color:var(--navy-deep);margin-top:5px}
.scn-n{font-size:10.5px;color:var(--gray-mid);margin-top:4px}
.chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:14px 0}
.chart-full{margin:14px 0}
.card{background:var(--white);border:1px solid var(--gray-light);border-radius:var(--radius);padding:15px 17px;box-shadow:var(--shadow-sm)}
.card-title{font-size:11.5px;font-weight:700;color:var(--navy-deep);text-transform:uppercase;letter-spacing:.5px;font-family:var(--font-mono)}
.card-sub{font-size:11px;color:var(--gray);margin:3px 0 8px}
.chart-wrap{margin-top:8px}
.chart-wrap canvas{max-height:300px}
.tbl-wrap{margin:16px 0}
.tbl-cap{font-family:var(--font-display);font-size:14.5px;color:var(--navy-mid);margin-bottom:3px}
.tbl-sub{font-size:11px;color:var(--gray);margin-bottom:7px}
.tbl-src{font-size:10px;color:var(--gray-mid);font-family:var(--font-mono);margin-top:6px}
.data-table{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--white);border:1px solid var(--gray-light);border-radius:8px;overflow:hidden;box-shadow:var(--shadow-sm)}
.data-table th{background:var(--navy-deep);color:#fff;padding:9px 12px;text-align:left;font-size:10.5px;font-family:var(--font-mono);font-weight:500;letter-spacing:.3px}
.data-table td{padding:8px 12px;border-bottom:1px solid var(--gray-light);vertical-align:middle}
.data-table tr:nth-child(even){background:#FAFAFA}
.data-table tr.total-row{background:var(--navy-dark) !important}
.data-table tr.total-row td{color:#fff !important;font-weight:700;border-color:rgba(255,255,255,.08)}
.badge{font-size:9.5px;font-family:var(--font-mono);font-weight:600;border-radius:4px;padding:2px 7px;white-space:nowrap}
.badge.b-blue{background:var(--blue-soft);color:var(--navy-mid);border:1px solid var(--blue-border)}
.badge.b-green{background:var(--green-soft);color:var(--green);border:1px solid #A8D5C0}
.badge.b-red{background:var(--red-soft);color:var(--red);border:1px solid #E8B4AE}
.badge.b-amber{background:var(--amber-soft);color:var(--amber);border:1px solid #DFC07A}
.badge.b-navy{background:var(--navy-deep);color:#fff;border:1px solid var(--navy-deep)}
.verdict{padding:10px 14px;border-radius:8px;margin:4px 0 16px;font-size:14px;border:1px solid}
.v-green{background:var(--green-soft);border-color:#A8D5C0;color:var(--green)}
.v-amber{background:var(--amber-soft);border-color:#DFC07A;color:var(--amber)}
.v-red{background:var(--red-soft);border-color:#E8B4AE;color:var(--red)}
.v-alert{background:var(--blue-soft);border-color:var(--blue-border);color:var(--navy-mid)}
.resumo{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 18px}
.chip{font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;border:1px solid}
.chip.crit{background:var(--red-soft);border-color:#E8B4AE;color:var(--red)}
.chip.alert{background:var(--amber-soft);border-color:#DFC07A;color:var(--amber)}
.chip.aten{background:var(--blue-soft);border-color:var(--blue-border);color:var(--navy-mid)}
.chip.ok{background:var(--green-soft);border-color:#A8D5C0;color:var(--green)}
.inc-grid{display:grid;gap:12px}
.inc{background:var(--white);border:1px solid var(--gray-light);border-left-width:4px;border-radius:8px;padding:14px 16px;box-shadow:var(--shadow-sm)}
.inc-crit{border-left-color:var(--red)}.inc-alert{border-left-color:var(--amber)}
.inc-aten{border-left-color:var(--navy-mid)}.inc-ok{border-left-color:var(--green)}
.inc-top{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.inc-cod{font-family:var(--font-mono);font-size:11px;color:var(--gold);font-weight:600}
.inc-st{margin-left:auto;font-size:10.5px;font-family:var(--font-mono);color:var(--gray-mid);text-transform:uppercase}
.inc-tit{font-weight:600;color:var(--navy-deep);margin-bottom:4px}
.inc-fund{font-size:11.5px;color:var(--gray);font-family:var(--font-mono);margin-bottom:6px}
.inc-desc{font-size:13.5px;color:#33444f;margin:6px 0}
.inc-rfb,.inc-res{font-size:12.5px;color:var(--navy-mid);margin-top:6px;padding:7px 10px;background:#F6F2E8;border-radius:6px}
.pend{margin-left:18px;font-size:13px}.pend li{margin-bottom:6px}.muted{color:var(--gray-mid)}
"""

_CHART_INIT = """
document.querySelectorAll('.chart-wrap[data-chart]').forEach(function(w){
  var c=JSON.parse(w.getAttribute('data-chart'));var el=document.getElementById(c.id);if(!el)return;
  var gold='#B8963E',navy='#1B3A4B',mid='#2A5068',red='#B83232',green='#27604A',amber='#9C6E1A';
  var palette=[navy,gold,mid,green,amber,red,'#3D6E8A'];
  var ds={label:'',data:c.series,
    backgroundColor:c.tipo==='line'?'rgba(184,150,62,0.15)':c.labels.map(function(_,i){return palette[i%palette.length]}),
    borderColor:c.tipo==='line'?gold:navy,fill:c.tipo==='line',tension:0.3,borderWidth:2};
  new Chart(el,{type:c.tipo,data:{labels:c.labels,datasets:[ds]},
    options:{responsive:true,indexAxis:c.horizontal?'y':'x',
      plugins:{legend:{display:c.tipo==='doughnut'}},
      scales:c.tipo==='doughnut'?{}:{x:{beginAtZero:true},y:{beginAtZero:true}}}});
});
function toggleSec(bar){bar.classList.toggle('collapsed');
  var b=bar.parentElement.querySelector('.sec-body');if(b)b.classList.toggle('open');}
(function(){var links=[].slice.call(document.querySelectorAll('.sb-link'));
  var secs=links.map(function(l){return document.querySelector(l.getAttribute('href'))});
  function onScroll(){var y=window.scrollY+140,cur=0;
    secs.forEach(function(s,i){if(s&&s.offsetTop<=y)cur=i});
    links.forEach(function(l,i){l.classList.toggle('open',i===cur)})}
  window.addEventListener('scroll',onScroll);onScroll();})();
"""

_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');{css}</style>
</head><body>
<aside class="sidebar">
  <div class="sb-brand"><div class="sb-brand-top">TCU · SecexContas</div>
    <div class="sb-brand-name">Módulo {modulo}</div>
    <div class="sb-brand-top" style="margin-top:4px">{modulo_nome}</div></div>
  <div class="sb-label">Seções</div>
  <nav class="sb-nav">{nav}</nav>
  <div class="sb-footer">{rodape}</div>
</aside>
<main class="page-main">
  <header class="hero">
    <div class="hero-tag">GT Reforma Tributária · CBS</div>
    <h1 class="hero-title">Módulo {modulo} — <em>{modulo_nome}</em></h1>
    <div class="hero-meta">{hero_chips}</div>
  </header>
  <div class="wrap">{body}</div>
</main>
<script>{chart_js}</script>
</body></html>
"""
