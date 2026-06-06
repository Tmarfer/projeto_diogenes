"""
delivery/parsing.py — DVA-CBS | Projeto Diógenes

Heurísticas de extração (sem LLM) que leem os outputs já produzidos pelos
agentes e os convertem em estruturas do PacoteEntrega:

- o JSON de ocorrências do Sherlock (skills.md §11 — insumo_json_dashboard);
- as seções 10.x do Relatório Estruturado;
- o veredito de conformidade.

Toda a lógica é auditável por leitura direta. Funções puras — sem efeitos colaterais.
"""
from __future__ import annotations

import json
import re

from diogenes.models import OcorrenciaEntrega, PendenciaSimulador

# Mapa de status textual de classificação → status de resolução do dashboard
_STATUS_VALIDOS = {"aberto", "encaminhado", "resolvido"}
_NIVEIS_VALIDOS = {"CRITICO", "ALERTA", "ATENCAO", "RESOLVIDO"}


def extrair_json_dashboard(texto: str) -> dict | None:
    """
    Extrai o objeto JSON da seção 'insumo_json_dashboard' (seção 11) do
    consolidado de Sherlock. Procura, em ordem:
      1. bloco delimitado por <!-- SECAO: insumo_json_dashboard --> ... <!-- /SECAO -->;
      2. primeira cerca ```json após o cabeçalho '## 11.';
      3. primeira cerca ```json com a chave "ocorrencias".
    Retorna o dict ou None se nada parseável for encontrado.
    """
    candidatos: list[str] = []

    # 1. Bloco entre marcadores de seção
    m = re.search(
        r"<!--\s*SECAO:\s*insumo_json_dashboard\s*-->(.*?)<!--\s*/SECAO",
        texto, re.DOTALL | re.IGNORECASE,
    )
    escopo = m.group(1) if m else texto

    # 2/3. Cercas ```json dentro do escopo
    for bloco in re.findall(r"```json\s*(.*?)```", escopo, re.DOTALL | re.IGNORECASE):
        candidatos.append(bloco)
    # Fallback: qualquer cerca json no texto inteiro
    if not candidatos:
        for bloco in re.findall(r"```json\s*(.*?)```", texto, re.DOTALL | re.IGNORECASE):
            candidatos.append(bloco)

    for bruto in candidatos:
        obj = _tentar_json(bruto)
        if isinstance(obj, dict) and "ocorrencias" in obj:
            return obj
    # Último recurso: primeiro objeto que parsear
    for bruto in candidatos:
        obj = _tentar_json(bruto)
        if isinstance(obj, dict):
            return obj
    return None


def _tentar_json(bruto: str) -> object | None:
    bruto = bruto.strip()
    try:
        return json.loads(bruto)
    except json.JSONDecodeError:
        # Tolerância: remove vírgulas finais antes de } ou ]
        limpo = re.sub(r",\s*([}\]])", r"\1", bruto)
        try:
            return json.loads(limpo)
        except json.JSONDecodeError:
            return None


def ocorrencias_de_json(obj: dict) -> tuple[list[OcorrenciaEntrega], list[PendenciaSimulador]]:
    """Converte o dict do insumo_json_dashboard em dataclasses do PacoteEntrega."""
    ocorrencias: list[OcorrenciaEntrega] = []
    for o in obj.get("ocorrencias", []) or []:
        if not isinstance(o, dict):
            continue
        nivel = str(o.get("nivel", "ATENCAO")).strip().upper()
        if nivel not in _NIVEIS_VALIDOS:
            nivel = "ATENCAO"
        status = str(o.get("status", "aberto")).strip().lower()
        if status not in _STATUS_VALIDOS:
            status = "aberto"
        ocorrencias.append(OcorrenciaEntrega(
            codigo=str(o.get("codigo", "")).strip() or "S/N",
            titulo=str(o.get("titulo", "")).strip(),
            nivel=nivel,
            fundamento_violado=str(o.get("fundamento_violado", "")).strip(),
            descricao=str(o.get("descricao", "")).strip(),
            solicitacao_rfb=str(o.get("solicitacao_rfb", "")).strip(),
            status=status,
            status_resolucao=(o.get("status_resolucao") or None),
        ))

    pendencias: list[PendenciaSimulador] = []
    for p in obj.get("pendencias_simulador", []) or []:
        if not isinstance(p, dict):
            continue
        pendencias.append(PendenciaSimulador(
            codigo=str(p.get("codigo", "")).strip() or "PC-?",
            descricao=str(p.get("descricao", "")).strip(),
            verificacao_futura=str(p.get("verificacao_futura", "")).strip(),
        ))
    return ocorrencias, pendencias


def extrair_secao(texto: str, numero: str) -> str:
    """
    Extrai o corpo de uma seção do Relatório Estruturado por número
    (ex.: '10.5'). Casa cabeçalhos '### 10.5 ...', '## 10.5 ...' ou
    '**10.5 ...**' e devolve o texto até o próximo cabeçalho de mesmo nível.
    """
    padrao = re.compile(
        rf"^#{{1,4}}\s*{re.escape(numero)}\b.*?$(.*?)(?=^#{{1,4}}\s*\d+(?:\.\d+)*\b|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = padrao.search(texto)
    return m.group(1).strip() if m else ""


def extrair_veredito(texto: str) -> str:
    """
    Detecta o veredito de conformidade do módulo a partir do vocabulário
    canônico de Sherlock (seção Posição Consolidada / 10.5).
    """
    for termo in (
        "APROVADO_COM_RESSALVAS",
        "REQUER_CONTRADITORIO",
        "NAO_VERIFICAVEL_MAJORITARIAMENTE",
        "PARCIALMENTE_CONSISTENTE",
        "INCONSISTENTE",
        "CONSISTENTE",
        "APROVADO",
    ):
        if re.search(rf"\b{termo}\b", texto, re.IGNORECASE):
            return termo
    return ""
