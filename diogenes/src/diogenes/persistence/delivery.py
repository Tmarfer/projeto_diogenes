"""
persistence/delivery.py — DVA-CBS | Projeto Diógenes
Manifesto de entrega (best-effort).

A intake/preparação dos dados acontece FORA do Diógenes. A entrega chega
acompanhada de um "manifesto de entrega" produzido pelo motor de curadoria externo
— no pack de teste, os artefatos de `02_INSUMOS_GERADOS/` (`metadados.json`,
`hashes_integridade.txt`, `protocolo_recebimento.md`). Este módulo lê esse manifesto
e reconcilia o declarado contra o que o Motor de Start encontrou em disco.

Política: **best-effort**. Nenhuma função aqui levanta exceção por manifesto ausente,
malformado ou divergente — o objetivo é informar o auditor, nunca travar a auditoria.

Referência: AVALIACAO_BENCH_MOD010_GPT55_INPUTS.md (Etapa 1).
"""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Subpasta-base à qual os caminhos do manifesto de entrega são relativos.
_BASE_SUBDIR_PADRAO = "01_ENTRADA_COPIADA"


@dataclass
class DeliveryManifest:
    """Manifesto de entrega lido do pacote (best-effort)."""
    fonte: str                      # nome do arquivo lido
    id_recebimento: str = ""
    modulo: str = ""
    data_entrega: str = ""
    total_declarado: int = 0
    hashes: dict[str, str] = field(default_factory=dict)  # caminho_rel -> sha256


@dataclass
class Reconciliacao:
    """Resultado da comparação declarado × encontrado."""
    status: str                     # PRESENTE_OK | PRESENTE_COM_DIVERGENCIA | AUSENTE
    total_declarado: int = 0
    total_casado: int = 0
    faltando: list[str] = field(default_factory=list)        # declarados sem correspondência
    hash_divergente: list[str] = field(default_factory=list)  # casados com hash diferente
    fonte: str = ""
    id_recebimento: str = ""


def ler_manifesto_entrega(delivery_dir: Path) -> DeliveryManifest | None:
    """Procura e lê o manifesto de entrega na árvore da entrega (best-effort).

    Preferência: `metadados.json` (tem hashes estruturados). Fallback:
    `hashes_integridade.txt`. Retorna None se nada for encontrado ou o parse falhar.
    """
    metadados = sorted(delivery_dir.rglob("metadados.json"))
    if metadados:
        dm = _parse_metadados_json(metadados[0])
        if dm is not None:
            return dm

    hashes_txt = sorted(delivery_dir.rglob("hashes_integridade.txt"))
    if hashes_txt:
        return _parse_hashes_txt(hashes_txt[0])

    return None


def _parse_metadados_json(path: Path) -> DeliveryManifest | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # best-effort: nunca propaga
        logger.warning("Falha ao ler manifesto de entrega %s: %s", path, e)
        return None
    hashes = data.get("hashes") or {}
    if not isinstance(hashes, dict):
        hashes = {}
    totais = data.get("totais") or {}
    return DeliveryManifest(
        fonte=path.name,
        id_recebimento=str(data.get("id_recebimento", "")),
        modulo=str(data.get("modulo", "")),
        data_entrega=str(data.get("data_entrega", "")),
        total_declarado=int(totais.get("arquivos", len(hashes)) or len(hashes)),
        hashes={str(k): str(v) for k, v in hashes.items()},
    )


def _parse_hashes_txt(path: Path) -> DeliveryManifest | None:
    try:
        linhas = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:  # best-effort
        logger.warning("Falha ao ler %s: %s", path, e)
        return None
    hashes: dict[str, str] = {}
    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split(None, 1)  # <hash>  <caminho com espaços>
        if len(partes) != 2:
            continue
        sha, caminho = partes
        hashes[caminho.strip()] = sha.strip()
    if not hashes:
        return None
    return DeliveryManifest(
        fonte=path.name,
        total_declarado=len(hashes),
        hashes=hashes,
    )


def reconciliar(
    manifesto: DeliveryManifest | None,
    encontrados: list[tuple[str, str]],
    base_subdir: str = _BASE_SUBDIR_PADRAO,
) -> Reconciliacao:
    """Compara o declarado no manifesto de entrega contra o encontrado em disco.

    `encontrados`: lista de (rel_path_posix, sha256) coletada pelo Motor de Start.
    Os caminhos do manifesto são relativos a `base_subdir` (ex. `01_ENTRADA_COPIADA`);
    o casamento tolera esse prefixo comparando por sufixo de caminho.
    Best-effort: nunca levanta exceção.
    """
    if manifesto is None or not manifesto.hashes:
        return Reconciliacao(status="AUSENTE")

    # Normaliza Unicode (NFC) dos caminhos: o manifesto pode vir do macOS (NFD) e o
    # disco em NFC — sem isso, nomes acentuados não casam byte-a-byte.
    def _norm(s: str) -> str:
        return unicodedata.normalize("NFC", s)

    # Índice dos encontrados por caminho posix normalizado.
    por_caminho: dict[str, str] = {_norm(rel): sha for rel, sha in encontrados}

    def _achar_sha(declarado: str) -> str | None:
        # tenta caminho direto; depois prefixado pela base; depois por sufixo.
        if declarado in por_caminho:
            return por_caminho[declarado]
        prefixado = f"{base_subdir}/{declarado}"
        if prefixado in por_caminho:
            return por_caminho[prefixado]
        for rel, sha in por_caminho.items():
            if rel.endswith("/" + declarado) or rel == declarado:
                return sha
        return None

    faltando: list[str] = []
    hash_divergente: list[str] = []
    casados = 0
    for declarado, sha_declarado in manifesto.hashes.items():
        sha_encontrado = _achar_sha(_norm(declarado))
        if sha_encontrado is None:
            faltando.append(declarado)
            continue
        casados += 1
        if sha_declarado and sha_encontrado and sha_declarado.lower() != sha_encontrado.lower():
            hash_divergente.append(declarado)

    status = "PRESENTE_OK" if not faltando and not hash_divergente else "PRESENTE_COM_DIVERGENCIA"
    return Reconciliacao(
        status=status,
        total_declarado=len(manifesto.hashes),
        total_casado=casados,
        faltando=faltando,
        hash_divergente=hash_divergente,
        fonte=manifesto.fonte,
        id_recebimento=manifesto.id_recebimento,
    )


def render_reconciliacao_md(rec: Reconciliacao) -> str:
    """Renderiza a reconciliação para a seção correspondente do manifesto de abertura."""
    if rec.status == "AUSENTE":
        return (
            "**Status:** AUSENTE — nenhum manifesto de entrega localizado.\n"
            "Ingestão realizada por varredura direta da pasta da entrega "
            "(best-effort; integridade não conferida contra declaração externa)."
        )

    linhas = [
        f"**Status:** {rec.status}",
        f"**Fonte:** `{rec.fonte}`" + (f" | Recebimento: `{rec.id_recebimento}`" if rec.id_recebimento else ""),
        f"**Arquivos declarados:** {rec.total_declarado} | **casados em disco:** {rec.total_casado}",
    ]
    if rec.faltando:
        linhas.append(f"\n**Declarados não encontrados ({len(rec.faltando)}):**")
        linhas.extend(f"- `{c}`" for c in rec.faltando[:50])
        if len(rec.faltando) > 50:
            linhas.append(f"- … (+{len(rec.faltando) - 50})")
    if rec.hash_divergente:
        linhas.append(f"\n**Hash divergente ({len(rec.hash_divergente)}):**")
        linhas.extend(f"- `{c}`" for c in rec.hash_divergente[:50])
        if len(rec.hash_divergente) > 50:
            linhas.append(f"- … (+{len(rec.hash_divergente) - 50})")
    if rec.status == "PRESENTE_OK":
        linhas.append("\nTodos os arquivos declarados foram localizados com hash conferido.")
    return "\n".join(linhas)
