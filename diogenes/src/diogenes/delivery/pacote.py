"""
delivery/pacote.py — DVA-CBS | Projeto Diógenes

Monta o PacoteEntrega canônico a partir dos artefatos já gravados no diretório
do ciclo. Combina três fontes:

1. **Auditoria** — JSON de ocorrências do Sherlock (skills.md §11) + veredito e
   seções do relatório consolidado/higienizado.
2. **Narrativa** — campos descritivos (proposta, objetivo, arquivos, notas, testes)
   fornecidos pelo agente no "mapa de extração" (texto, nunca números).
3. **Financeiro** — números EXATOS lidos da planilha principal pelo ExtractorFinanceiro,
   a partir das localizações (aba/célula/intervalo) declaradas no mapa.

Sem LLM. Best-effort: campos ausentes geram aviso, não exceção.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from diogenes.delivery import parsing
from diogenes.delivery.extractor import ExtracaoError, ExtractorFinanceiro
from diogenes.models import (
    NotaMetodologica,
    PacoteEntrega,
    TesteRealizado,
)

NOME_MAPA_EXTRACAO = "entrega_mapa_extracao.json"
NOME_SHERLOCK_JSON = "sherlock_ocorrencias.json"
NOME_APENDICE_CONTEUDO = "entrega_apendice.json"


def montar_pacote(cycle_dir: Path, module_id: str, activity: int) -> tuple[PacoteEntrega, list[str]]:
    avisos: list[str] = []
    output_dir = cycle_dir / "output"

    mapa = _carregar_mapa(output_dir, avisos)
    narrativa = mapa.get("narrativa", {}) if mapa else {}

    modulo_num = _modulo_num(module_id)
    modulo_nome = mapa.get("modulo_nome") or narrativa.get("modulo_nome") or module_id
    versao = str(mapa.get("versao") or f"1.0 | Atividade {activity}")

    # 1. Auditoria — relatório consolidado/higienizado
    relatorio_md = _ler_relatorio(output_dir, avisos)
    veredito = parsing.extrair_veredito(relatorio_md) if relatorio_md else ""
    conclusao_conf = parsing.extrair_secao(relatorio_md, "10.4") if relatorio_md else ""
    conclusao_cons = parsing.extrair_secao(relatorio_md, "10.5") if relatorio_md else ""

    ocorrencias, pendencias = _carregar_ocorrencias(cycle_dir, output_dir, relatorio_md, avisos)

    # 3. Financeiro — extração determinística
    blocos, agregados, sensibilidade = _extrair_financeiro(cycle_dir, mapa, avisos)


    # Unpack proposta
    prop_val = narrativa.get("proposta", "") if isinstance(narrativa, dict) else ""
    if isinstance(prop_val, dict):
        prop_desc = prop_val.get("descricao", "")
        prop_cont = prop_val.get("contexto_narrativo", "")
        prop_font = prop_val.get("fonte", "")
    else:
        prop_desc = str(prop_val)
        prop_cont = ""
        prop_font = ""

    # Unpack arquivos
    arq_val = narrativa.get("arquivos", []) if isinstance(narrativa, dict) else []
    principal = []
    auxiliares = []
    fontes = []
    if isinstance(arq_val, dict):
        principal = arq_val.get("principal", [])
        auxiliares = arq_val.get("auxiliares", [])
        fontes = arq_val.get("fontes", [])
    elif isinstance(arq_val, list):
        for item in arq_val:
            if isinstance(item, dict):
                tipo = str(item.get("tipo", "")).lower()
                if "principal" in tipo:
                    principal.append(item)
                elif "fonte" in tipo:
                    fontes.append(item)
                else:
                    auxiliares.append(item)
            elif isinstance(item, str):
                auxiliares.append({"nome": item, "descricao": ""})

    pacote = PacoteEntrega(
        cycle_id=cycle_dir.name,
        modulo=modulo_num,
        modulo_nome=modulo_nome,
        versao=versao,
        timestamp_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        proposta_descricao=prop_desc,
        proposta_contexto=prop_cont,
        proposta_fonte=prop_font,
        objetivo=narrativa.get("objetivo", "") if isinstance(narrativa, dict) else "",
        objetivo_detalhado=narrativa.get("objetivo_detalhado", "") if isinstance(narrativa, dict) else "",
        arquivos_principal=principal,
        arquivos_auxiliares=auxiliares,
        arquivos_fontes=fontes,
        blocos_financeiros=blocos,
        valores_agregados=agregados,
        sensibilidade_redutor=sensibilidade,
        ocorrencias=ocorrencias,
        pendencias_simulador=pendencias,
        testes_camada_1=_testes(narrativa, "camada_1"),
        testes_camada_2=_testes(narrativa, "camada_2"),
        testes_camada_3=_testes(narrativa, "camada_3"),
        notas_metodologicas=_notas(narrativa),
        veredito=veredito,
        conclusao_conformidade=conclusao_conf,
        conclusao_consistencia=conclusao_cons,
        relatorio_markdown=relatorio_md,
        ata_rfb_markdown=_ler_ata(cycle_dir, avisos),
        apendice_conteudo=_carregar_apendice_conteudo(output_dir, avisos),
    )
    return pacote, avisos


# ── fontes ──────────────────────────────────────────────────────

def _carregar_mapa(output_dir: Path, avisos: list[str]) -> dict:
    path = output_dir / NOME_MAPA_EXTRACAO
    if not path.exists():
        avisos.append(
            f"Mapa de extração ausente ({NOME_MAPA_EXTRACAO}) — camada financeira e "
            f"textos descritivos não serão preenchidos. Gere via Mycroft.mapear_dados_modulo."
        )
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        avisos.append(f"Mapa de extração inválido: {exc}")
        return {}


def _carregar_apendice_conteudo(output_dir: Path, avisos: list[str]) -> dict | None:
    path = output_dir / NOME_APENDICE_CONTEUDO
    if not path.exists():
        avisos.append(
            f"Conteúdo do apêndice ausente ({NOME_APENDICE_CONTEUDO}) — apêndice usará o "
            f"mapeamento fino do blueprint. Gere via Mycroft.redigir_apendice."
        )
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        avisos.append(f"Conteúdo do apêndice inválido ({NOME_APENDICE_CONTEUDO}): {exc}")
        return None


def _ler_relatorio(output_dir: Path, avisos: list[str]) -> str:
    for padrao in ("relatorio_higienizado_*.md", "relatorio_*.md"):
        achados = sorted(output_dir.glob(padrao))
        if achados:
            return achados[0].read_text(encoding="utf-8")
    avisos.append("Relatório consolidado não encontrado no output do ciclo.")
    return ""


def _carregar_ocorrencias(cycle_dir: Path, output_dir: Path, relatorio_md: str,
                          avisos: list[str]):
    # 1. arquivo json dedicado
    jpath = output_dir / NOME_SHERLOCK_JSON
    if jpath.exists():
        try:
            obj = json.loads(jpath.read_text(encoding="utf-8"))
            return parsing.ocorrencias_de_json(obj)
        except json.JSONDecodeError as exc:
            avisos.append(f"{NOME_SHERLOCK_JSON} inválido: {exc}")

    # 2. parsear bloco json do consolidado de Sherlock (stranger_room ou output)
    candidatos = list((cycle_dir / "stranger_room" / "sherlock_validacao").glob("*.md")) \
        if (cycle_dir / "stranger_room" / "sherlock_validacao").is_dir() else []
    for texto in [relatorio_md] + [c.read_text(encoding="utf-8") for c in candidatos]:
        if not texto:
            continue
        obj = parsing.extrair_json_dashboard(texto)
        if obj:
            return parsing.ocorrencias_de_json(obj)

    avisos.append("JSON de ocorrências de Sherlock não localizado — aba de inconsistências vazia.")
    return [], []


def _extrair_financeiro(cycle_dir: Path, mapa: dict, avisos: list[str]):
    if not mapa or not any(k in mapa for k in ("blocos", "valores_agregados", "sensibilidade_redutor")):
        return [], [], None
    planilha = _localizar_planilha(cycle_dir, mapa, avisos)
    if planilha is None:
        return [], [], None
    try:
        ext = ExtractorFinanceiro(planilha)
        res = ext.extrair(mapa)
        avisos.extend(ext.avisos)
        return res["blocos_financeiros"], res["valores_agregados"], res["sensibilidade_redutor"]
    except ExtracaoError as exc:
        avisos.append(f"Extração financeira falhou: {exc}")
        return [], [], None


def _localizar_planilha(cycle_dir: Path, mapa: dict, avisos: list[str]) -> Path | None:
    inputs = cycle_dir / "inputs"
    nome = mapa.get("planilha_principal", "")
    if nome:
        achados = list(inputs.rglob(nome))
        if achados:
            return achados[0]
        avisos.append(f"Planilha principal '{nome}' não encontrada em inputs/.")
    # Heurística: primeiro .xlsx em inputs/
    xlsx = sorted(inputs.rglob("*.xlsx"))
    if xlsx:
        avisos.append(f"Usando planilha heurística: {xlsx[0].name}")
        return xlsx[0]
    avisos.append("Nenhuma planilha .xlsx encontrada em inputs/.")
    return None


def _ler_ata(cycle_dir: Path, avisos: list[str]) -> str:
    inputs = cycle_dir / "inputs"
    if not inputs.is_dir():
        return ""
    for arq in inputs.rglob("*"):
        if arq.is_file() and re.search(r"(ata|reuni|entrega|atendimento)", arq.name, re.IGNORECASE) \
                and arq.suffix.lower() in (".md", ".txt"):
            return arq.read_text(encoding="utf-8", errors="replace")
    avisos.append("Ata da reunião RFB não localizada — pré-atendimento ficará sem o bloco da ata.")
    return ""


# ── helpers de narrativa ────────────────────────────────────────

def _testes(narrativa: dict, camada: str) -> list[TesteRealizado]:
    if not isinstance(narrativa, dict):
        return []
    testes_val = narrativa.get("testes", []) or []
    if isinstance(testes_val, dict):
        itens = testes_val.get(camada, []) or []
    elif isinstance(testes_val, list) and camada == "camada_1":
        itens = testes_val
    else:
        itens = []

    res = []
    for idx, t in enumerate(itens):
        if isinstance(t, dict):
            res.append(TesteRealizado(
                id=t.get("id", f"T-{idx+1}"),
                descricao=t.get("descricao", ""),
                resultado=t.get("resultado", ""),
                status=t.get("status", ""),
            ))
        elif isinstance(t, str):
            res.append(TesteRealizado(
                id=f"T-{idx+1}",
                descricao=t,
                resultado="Executado",
                status="Atendido",
            ))
    return res


def _notas(narrativa: dict) -> list[NotaMetodologica]:
    if not isinstance(narrativa, dict):
        return []
    notas_val = narrativa.get("notas_metodologicas", []) or []
    res = []
    if isinstance(notas_val, list):
        for idx, n in enumerate(notas_val):
            if isinstance(n, dict):
                res.append(NotaMetodologica(
                    nome=n.get("nome", ""), data=n.get("data", ""),
                    descricao=n.get("descricao", ""), conteudo_resumo=n.get("conteudo_resumo", ""),
                    situacao_inventario=n.get("situacao_inventario", ""), observacao=n.get("observacao", ""),
                ))
            elif isinstance(n, str):
                res.append(NotaMetodologica(
                    nome=f"Nota {idx+1}",
                    descricao=n,
                ))
    return res


def _modulo_num(module_id: str) -> int:
    m = re.search(r"(\d+)", module_id)
    return int(m.group(1)) if m else 0
