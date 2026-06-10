"""
delivery/builders.py — DVA-CBS | Projeto Diógenes

Converte o PacoteEntrega nos formatos que os geradores vendorizados consomem:

- dados_apendice()              → dicionário do ApendiceGerador (7 seções)
- gerar_apendice_docx()         → .docx do apêndice
- gerar_relatorio_docx()        → .docx institucional a partir de markdown (TCUFormatter)
- montar_markdown_narrativo()   → markdown do relatório narrativo
- montar_markdown_pre_atendimento() → markdown do relatório de pré-atendimento (usa ata RFB)
- gerar_ficha_html()            → HTML A4 (2 páginas) da Ficha Síntese
- gerar_ficha_assets()          → PDF + PNGs da ficha (Playwright)

Geração é deterministicamente derivada do PacoteEntrega — sem LLM.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from diogenes.delivery import vendor
from diogenes.models import PacoteEntrega

# Sherlock nível → vocabulário de status do Apêndice
_NIVEL_PARA_STATUS = {
    "RESOLVIDO": "Atendido",
    "CRITICO": "Divergência",
    "ALERTA": "Divergência",
    "ATENCAO": "Atendido Parcialmente",
}


# ── Apêndice (7 seções) ─────────────────────────────────────────

def dados_apendice(p: PacoteEntrega) -> dict[str, Any]:
    """Monta o dicionário do ApendiceGerador mesclando:

    - **Qualitativo** redigido por Mycroft (`p.apendice_conteudo`, via call_type
      `redigir_apendice`) — proposta, objetivo, arquivos, testes nas 3 camadas com
      subcategorias, INC com consequência/tratamento redigidos, alterações e premissas.
    - **Determinístico** do PacoteEntrega — valores agregados/sensibilidade (números lidos
      das células), status das INC via nível §11 e códigos das ocorrências (rastreabilidade).

    Sem `apendice_conteudo`, recai no mapeamento fino derivado do blueprint (retrocompatível).
    """
    conteudo = p.apendice_conteudo or {}

    inconsistencias = _inconsistencias_apendice(p, conteudo)
    testes = _testes_apendice(p, conteudo)
    conclusao = _conclusao_apendice(p, conteudo)
    proposta, objetivo, objetivo_detalhado, arquivos = _identidade_apendice(p, conteudo)

    return {
        "modulo": p.modulo,
        "modulo_nome": p.modulo_nome,
        "versao": p.versao or "1.0",
        "proposta": proposta,
        "objetivo": objetivo,
        "objetivo_detalhado": objetivo_detalhado,
        "arquivos": arquivos,
        "testes": testes,
        "inconsistencias": inconsistencias,
        "alteracoes_metodologicas": list(conteudo.get("alteracoes_metodologicas", []) or []),
        "notas_metodologicas": [
            {
                "nome": n.nome, "data": n.data, "descricao": n.descricao,
                "conteudo_resumo": n.conteudo_resumo,
                "situacao_inventario": n.situacao_inventario,
                "observacao": n.observacao,
            }
            for n in p.notas_metodologicas
        ],
        "conclusao": conclusao,
    }


def _identidade_apendice(p: PacoteEntrega, c: dict[str, Any]) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    _cp = c.get("proposta")
    cp: dict[str, Any] = _cp if isinstance(_cp, dict) else {}
    proposta: dict[str, Any] = {
        "descricao": cp.get("descricao") or p.proposta_descricao,
        "contexto_narrativo": cp.get("contexto_narrativo") or p.proposta_contexto,
        "fonte": cp.get("fonte") or p.proposta_fonte,
    }
    _ca = c.get("arquivos")
    ca: dict[str, Any] = _ca if isinstance(_ca, dict) else {}
    arquivos: dict[str, Any] = {
        "principal": ca.get("principal") or p.arquivos_principal,
        "auxiliares": ca.get("auxiliares") or p.arquivos_auxiliares,
        "fontes": ca.get("fontes") or p.arquivos_fontes,
    }
    return (proposta, c.get("objetivo") or p.objetivo,
            c.get("objetivo_detalhado") or p.objetivo_detalhado, arquivos)


def _testes_apendice(p: PacoteEntrega, c: dict[str, Any]) -> dict[str, Any]:
    """Camadas/subcategorias do conteúdo redigido; fallback nos testes do blueprint."""
    def _do_pacote(itens: list[Any]) -> list[dict[str, Any]]:
        return [{"id": t.id, "descricao": t.descricao,
                 "resultado": t.resultado, "status": t.status} for t in itens]

    _ct = c.get("testes")
    ct: dict[str, Any] = _ct if isinstance(_ct, dict) else {}
    if ct:
        def _camada(nome: str, fallback: list[dict[str, Any]]) -> dict[str, Any]:
            _bloco = ct.get(nome)
            bloco: dict[str, Any] = _bloco if isinstance(_bloco, dict) else {}
            bloco = {k: list(v or []) for k, v in bloco.items()}
            # garante ao menos a subcategoria principal preenchida pelo blueprint
            principal = {"camada_1": "conformidade", "camada_2": "conformidade",
                         "camada_3": "reproducao"}[nome]
            if not any(bloco.values()) and fallback:
                bloco[principal] = fallback
            return bloco
        return {
            "camada_1": _camada("camada_1", _do_pacote(p.testes_camada_1)),
            "camada_2": _camada("camada_2", _do_pacote(p.testes_camada_2)),
            "camada_3": _camada("camada_3", _do_pacote(p.testes_camada_3)),
        }
    return {
        "camada_1": {"conformidade": _do_pacote(p.testes_camada_1)},
        "camada_2": {"conformidade": _do_pacote(p.testes_camada_2)},
        "camada_3": {"reproducao": _do_pacote(p.testes_camada_3)},
    }


def _inconsistencias_apendice(p: PacoteEntrega, c: dict[str, Any]) -> list[dict[str, Any]]:
    """INC: status determinístico (nível §11); consequência/tratamento redigidos por Mycroft."""
    redigido = {i.get("id"): i for i in c.get("inconsistencias", []) or [] if isinstance(i, dict)}
    out = []
    for o in p.ocorrencias:
        r = redigido.get(o.codigo, {})
        out.append({
            "id": o.codigo,
            "titulo": r.get("titulo") or o.titulo,
            "descricao": r.get("descricao") or o.descricao,
            "consequencia": r.get("consequencia") or o.fundamento_violado,
            "tratamento": r.get("tratamento") or o.status_resolucao or o.solicitacao_rfb,
            "status": _NIVEL_PARA_STATUS.get(o.nivel, "Pendente"),
        })
    return out


def _conclusao_apendice(p: PacoteEntrega, c: dict[str, Any]) -> dict[str, Any]:
    _cc = c.get("conclusao")
    cc: dict[str, Any] = _cc if isinstance(_cc, dict) else {}
    conclusao: dict[str, Any] = {
        "conformidade": (cc.get("conformidade") or p.conclusao_conformidade
                         or f"Veredito: {p.veredito or 'não consolidado'}."),
        "consistencia": cc.get("consistencia") or p.conclusao_consistencia,
        # Premissas: texto qualitativo redigido; NUNCA carregam valor monetário.
        "premissas": list(cc.get("premissas", []) or []),
        # Valores agregados/evolução: SEMPRE determinísticos (lidos das células).
        "valores_agregados": p.valores_agregados,
    }
    if p.sensibilidade_redutor:
        conclusao["sensibilidade_redutor"] = p.sensibilidade_redutor
    return conclusao


def gerar_apendice_docx(p: PacoteEntrega, out_path: Path) -> Path:
    ApendiceGerador = vendor.carregar_apendice_gerador()  # type: ignore[no-untyped-call]
    gerador = ApendiceGerador(dados_apendice(p), modulo=p.modulo)
    return Path(gerador.gerar(str(out_path)))


# ── DOCX a partir de markdown (TCUFormatter) ────────────────────

def gerar_relatorio_docx(markdown_text: str, out_path: Path, titulo: str,
                         modulo: int, versao: str = "") -> Path:
    fmt = vendor.carregar_formatter()  # type: ignore[no-untyped-call]
    md_path = out_path.with_suffix(".md")
    md_path.write_text(markdown_text, encoding="utf-8")
    fmt.format_md(
        md_path, out_path,
        titulo=titulo, modulo=modulo, versao=versao or None,
        gerar_capa=True, validar=False, gerar_checklist=False,
    )
    md_path.unlink(missing_ok=True)
    return out_path


# ── Markdown narrativo ──────────────────────────────────────────

def montar_markdown_narrativo(p: PacoteEntrega) -> str:
    L: list[str] = [f"# Relatório Narrativo — Módulo {p.modulo}: {p.modulo_nome}", ""]
    if p.proposta_descricao:
        L += ["## Bloco 1: Proposta do Módulo", "", p.proposta_descricao, ""]
    if p.proposta_contexto:
        L += [p.proposta_contexto, ""]
    if p.objetivo:
        L += ["## Bloco 2: Objetivo", "", p.objetivo, ""]
        if p.objetivo_detalhado:
            L += [p.objetivo_detalhado, ""]

    if p.valores_agregados:
        L += ["## Bloco 3: Resultados Financeiros", "",
              "| Componente | 2023 | 2024 |", "|---|---|---|"]
        L += [f"| {v.get('descricao','')} | {v.get('valor_2023','')} | {v.get('valor_2024','')} |"
              for v in p.valores_agregados]
        L += [""]

    for b in p.blocos_financeiros:
        if not b.tabelas and not b.kpis:
            continue
        L += [f"### {b.titulo}", ""]
        if b.descricao:
            L += [b.descricao, ""]
        for t in b.tabelas:
            if not t.headers:
                continue
            L += [f"**{t.titulo}**", "",
                  "| " + " | ".join(t.headers) + " |",
                  "|" + "|".join("---" for _ in t.headers) + "|"]
            L += ["| " + " | ".join(str(c) for c in row) + " |" for row in t.rows]
            if t.fonte:
                L += [f"Fonte: {t.fonte}"]
            L += [""]

    if p.ocorrencias:
        L += ["## Bloco 4: Inconsistências Identificadas", ""]
        for o in p.ocorrencias:
            L += [f"### {o.codigo} — {o.titulo}", ""]
            if o.fundamento_violado:
                L += [f"**Fundamento:** {o.fundamento_violado}", ""]
            if o.descricao:
                L += [o.descricao, ""]
            if o.solicitacao_rfb:
                L += [f"**Solicitação à RFB:** {o.solicitacao_rfb}", ""]

    if p.veredito or p.conclusao_conformidade:
        L += ["## Bloco 5: Conclusão", ""]
        if p.veredito:
            L += [f"**Veredito de conformidade:** {p.veredito}", ""]
        if p.conclusao_conformidade:
            L += [p.conclusao_conformidade, ""]
        if p.conclusao_consistencia:
            L += [p.conclusao_consistencia, ""]
    return "\n".join(L)


def montar_markdown_pre_atendimento(p: PacoteEntrega) -> str:
    """Cruza as inconsistências com a ata da reunião de entrega da RFB."""
    L: list[str] = [f"# Relatório de Pré-Atendimento — Módulo {p.modulo}: {p.modulo_nome}", "",
                    "Documento que confronta as inconsistências identificadas com as "
                    "declarações registradas na reunião de entrega.", ""]
    if p.ata_rfb_markdown:
        L += ["## Bloco 1: Ata da Reunião de Entrega", "", p.ata_rfb_markdown.strip(), ""]
    L += ["## Bloco 2: Batimento Inconsistências × Posição da RFB", ""]
    for o in p.ocorrencias:
        L += [f"### {o.codigo} — {o.titulo}", ""]
        if o.descricao:
            L += [f"**Apontamento:** {o.descricao}", ""]
        if o.solicitacao_rfb:
            L += [f"**Solicitação à RFB:** {o.solicitacao_rfb}", ""]
        situacao = o.status_resolucao or "Aguardando manifestação da RFB na reunião de entrega."
        L += [f"**Situação preliminar:** {situacao}", ""]
    return "\n".join(L)


# ── Ficha Síntese (HTML A4, 2 páginas) ──────────────────────────

def gerar_ficha_html(p: PacoteEntrega) -> str:
    kpis = "".join(
        f'<div class="k"><div class="kv">{html.escape(k.valor)}</div>'
        f'<div class="kl">{html.escape(k.rotulo)}</div></div>'
        for b in p.blocos_financeiros for k in b.kpis
    )[:4000]
    val_rows = "".join(
        f"<tr><td>{html.escape(v.get('descricao',''))}</td>"
        f"<td>{html.escape(v.get('valor_2023',''))}</td>"
        f"<td>{html.escape(v.get('valor_2024',''))}</td></tr>"
        for v in p.valores_agregados
    )
    val_tbl = (f'<table><thead><tr><th>Componente</th><th>2023</th><th>2024</th></tr></thead>'
               f'<tbody>{val_rows}</tbody></table>') if val_rows else ""

    contagem: dict[str, int] = {}
    for o in p.ocorrencias:
        contagem[o.nivel] = contagem.get(o.nivel, 0) + 1
    chips = "".join(f'<span class="chip">{html.escape(n)}: {c}</span>' for n, c in contagem.items())
    inc_rows = "".join(
        f'<tr><td>{html.escape(o.codigo)}</td><td>{html.escape(o.nivel)}</td>'
        f'<td>{html.escape(o.titulo)}</td><td>{html.escape(o.status)}</td></tr>'
        for o in p.ocorrencias
    )
    inc_tbl = (f'<table><thead><tr><th>Código</th><th>Nível</th><th>Ocorrência</th>'
               f'<th>Status</th></tr></thead><tbody>{inc_rows}</tbody></table>') if inc_rows else \
        "<p>Nenhuma inconsistência identificada.</p>"

    return _FICHA_TEMPLATE.format(
        modulo=p.modulo, modulo_nome=html.escape(p.modulo_nome),
        processo=html.escape(p.processo), acordao=html.escape(p.acordao),
        versao=html.escape(p.versao or "1.0"),
        descricao=html.escape(p.proposta_descricao[:600]),
        kpis=kpis, val_tbl=val_tbl,
        veredito=html.escape(p.veredito or "—"),
        chips=chips, inc_tbl=inc_tbl,
    )


def gerar_ficha_assets(html_path: Path, saida_dir: Path) -> dict[str, Any]:
    """Converte o HTML da ficha em PDF + PNGs (Playwright/Chromium)."""
    ficha = vendor.carregar_ficha()  # type: ignore[no-untyped-call]
    return dict(ficha.gerar_documentos(html_path, saida_dir, gerar_pdf=True, gerar_png=True))


_FICHA_TEMPLATE = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><style>
@page{{size:A4;margin:0}}
@media print{{.page{{page-break-after:always}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;color:#1B3A4B}}
.page{{width:794px;min-height:1123px;padding:40px 46px;background:#fff;position:relative}}
.hdr{{border-bottom:3px solid #B8963E;padding-bottom:12px;margin-bottom:18px}}
.hdr .t1{{font-size:11px;letter-spacing:2px;color:#B8963E;text-transform:uppercase}}
.hdr .t2{{font-size:24px;color:#0B1E2D;font-weight:700;margin-top:4px}}
.meta{{font-size:11px;color:#5A6A74;margin-top:6px}}
h2{{font-size:15px;color:#1B3A4B;margin:18px 0 8px;border-left:4px solid #B8963E;padding-left:8px}}
p{{font-size:12.5px;line-height:1.55;color:#33444f}}
.kgrid{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}}
.k{{flex:1;min-width:150px;border:1px solid #E8EDF0;border-top:3px solid #B8963E;border-radius:8px;padding:12px}}
.kv{{font-size:19px;font-weight:700;color:#0B1E2D}}.kl{{font-size:10.5px;color:#5A6A74;margin-top:3px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px;margin:8px 0}}
th{{background:#0B1E2D;color:#fff;padding:7px 9px;text-align:left}}
td{{padding:6px 9px;border-bottom:1px solid #E8EDF0}}
.chip{{display:inline-block;font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;
background:#FDF3DC;border:1px solid #DFC07A;color:#9C6E1A;margin:3px 4px 0 0}}
.verd{{background:#EAF5F0;border:1px solid #A8D5C0;color:#27604A;padding:8px 12px;border-radius:8px;
font-size:13px;margin:10px 0}}
.foot{{position:absolute;bottom:24px;left:46px;right:46px;font-size:9px;color:#B0BEC5;
border-top:1px solid #E8EDF0;padding-top:6px}}
</style></head><body>
<div class="page">
  <div class="hdr"><div class="t1">TCU · SecexContas · GT Reforma Tributária</div>
    <div class="t2">Ficha Síntese — Módulo {modulo}: {modulo_nome}</div>
    <div class="meta">{processo} · Acórdão {acordao} · Versão {versao}</div></div>
  <h2>Descrição do Módulo</h2><p>{descricao}</p>
  <h2>Indicadores</h2><div class="kgrid">{kpis}</div>
  <h2>Valores Agregados</h2>{val_tbl}
  <div class="foot">{processo} · Documento de uso interno restrito</div>
</div>
<div class="page">
  <div class="hdr"><div class="t1">Conformidade e Inconsistências</div>
    <div class="t2">Módulo {modulo} — {modulo_nome}</div></div>
  <div class="verd">Veredito de conformidade: <b>{veredito}</b></div>
  <h2>Resumo por nível</h2><div>{chips}</div>
  <h2>Inconsistências Identificadas</h2>{inc_tbl}
  <div class="foot">{processo} · Documento de uso interno restrito</div>
</div>
</body></html>
"""
