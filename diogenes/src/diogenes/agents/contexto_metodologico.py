"""
agents/contexto_metodologico.py — DVA-CBS | Projeto Diógenes
Carregamento da régua metodológica do Sherlock: metodologia/regra de negócio do
módulo (cat. C, copiada nos inputs do ciclo) e arcabouço jurídico curado por módulo
(cat. D, referenciado por config — DIOGENES_CORPUS_JURIDICO_DIR).

Fonte única reusada pelo orquestrador oficial e pelo bench. Best-effort: nunca
levanta exceção; arquivos ausentes são ignorados; conteúdo é truncado a um teto.

Referência: AVALIACAO_BENCH_MOD010_GPT55_INPUTS.md (Etapa 3).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from diogenes.agents.file_prep import classificar, preparar_arquivo

logger = logging.getLogger(__name__)

_MAX_CHARS_METODOLOGIA = 20_000
_MAX_CHARS_CORPUS = 30_000

# Palavras-chave que identificam documentos metodológicos/RN entre os .md da entrega.
_KEYWORDS_METODOLOGIA = (
    "metodolog", "regra", "nota_metodologica", "consideracoes",
    "consideração", "consideracao", "matriz", "incidencia", "incidência",
)

# Documentos transversais do arcabouço (aplicáveis a todos os módulos).
_TRANSVERSAIS = (
    "aliquota_referencia.md",
    "incidencia_base_calculo.md",
    "creditos_nao_cumulatividade.md",
)


def carregar_metodologia_modulo(inputs_dir: Path) -> str:
    """Concatena a metodologia/regra de negócio do módulo a partir dos inputs do ciclo.

    Seleciona apenas `.md` *analisáveis* (file_prep.classificar) cujo nome/caminho casa
    keywords metodológicas — descarta CATALOGO.md/relatorio_cobertura.md/metadados.
    """
    if not inputs_dir or not Path(inputs_dir).is_dir():
        return ""
    inputs_dir = Path(inputs_dir)
    partes: list[str] = []
    total = 0
    for p in sorted(inputs_dir.rglob("*.md")):
        if not p.is_file():
            continue
        rel = p.relative_to(inputs_dir)
        analisavel, _tipo = classificar(rel)
        if not analisavel:
            continue
        alvo = (p.name + " " + rel.as_posix()).lower()
        if not any(k in alvo for k in _KEYWORDS_METODOLOGIA):
            continue
        texto = preparar_arquivo(p)
        partes.append(f"### {rel.as_posix()}\n{texto}")
        total += len(texto)
        if total >= _MAX_CHARS_METODOLOGIA:
            break
    return "\n\n".join(partes)[:_MAX_CHARS_METODOLOGIA]


def carregar_corpus_juridico(corpus_dir: Path | None, module_id: str) -> str:
    """Deriva e concatena o recorte do arcabouço jurídico curado para o módulo.

    Recorte: por_modulo/{module_id}.md (LC) + CONST_{nnn}.md (CF) + transversais +
    INDICE.md (insumo da análise de interseção entre módulos). Best-effort.
    """
    if not corpus_dir:
        return ""
    raiz = Path(corpus_dir)
    if not raiz.is_dir():
        return ""
    base = raiz / "normas_para_motor"
    if not base.is_dir():
        base = raiz  # tolera apontar direto para normas_para_motor

    nums = re.findall(r"\d+", module_id)
    num = nums[-1].zfill(3) if nums else ""
    lc = base / "LC_214_LC_227" / "por_modulo"
    cf = base / "CF_88_EC_132" / "por_modulo"

    candidatos: list[Path] = [lc / f"{module_id}.md"]
    if num:
        candidatos.append(cf / f"CONST_{num}.md")
    candidatos.extend(lc / t for t in _TRANSVERSAIS)
    candidatos.append(base / "LC_214_LC_227" / "INDICE.md")

    partes: list[str] = []
    total = 0
    vistos: set[Path] = set()
    for p in candidatos:
        if p in vistos or not p.is_file():
            continue
        vistos.add(p)
        texto = p.read_text(encoding="utf-8", errors="replace")
        partes.append(f"### {p.name}\n{texto}")
        total += len(texto)
        if total >= _MAX_CHARS_CORPUS:
            break
    if not partes:
        logger.warning("Corpus jurídico vazio para módulo %s em %s", module_id, raiz)
    return "\n\n".join(partes)[:_MAX_CHARS_CORPUS]
