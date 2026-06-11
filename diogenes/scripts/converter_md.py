"""
scripts/converter_md.py — DVA-CBS | Projeto Diógenes

Conversor mínimo determinístico docx/doc/pdf/txt → Markdown (sem LLM).

Semente do futuro motor de pré-conversão que antecederá o Departamento de
Validação (docx/txt/pdf convertidos para .md antes da entrada, registrados
no catálogo). Por ora é um utilitário FORA do pipeline, usado para gerar a
massa dos módulos sintéticos de formato (MOD_SINT_PDF/DOCX/TXT).

Reusa os leitores de `diogenes.agents.file_prep` — não duplica parsing.
A saída leva frontmatter de rastreabilidade (arquivo original, SHA-256,
data de conversão), conforme o padrão de auditoria do projeto.

Uso:
    python scripts/converter_md.py <origem> <destino_dir>

  <origem>      arquivo .docx/.doc/.pdf/.txt ou diretório (converte todos)
  <destino_dir> diretório onde os .md serão gravados
"""
from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

from diogenes.agents.file_prep import _ler_docx, _ler_pdf

EXTENSOES_CONVERSIVEIS = {".docx", ".doc", ".pdf", ".txt"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def extrair_texto(origem: Path) -> str:
    """Extrai o texto do arquivo de origem usando os leitores do file_prep."""
    ext = origem.suffix.lower()
    if ext in {".docx", ".doc"}:
        return _ler_docx(origem)
    if ext == ".pdf":
        return _ler_pdf(origem)
    if ext == ".txt":
        return origem.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Extensão não conversível: '{ext}' ({origem.name})")


def converter_arquivo(origem: Path, destino_dir: Path) -> Path:
    """Converte um arquivo para .md com frontmatter de rastreabilidade."""
    texto = extrair_texto(origem)
    frontmatter = (
        "---\n"
        f"arquivo_original: {origem.name}\n"
        f"sha256_original: {_sha256(origem)}\n"
        f"convertido_em_utc: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        "conversor: scripts/converter_md.py (determinístico, sem LLM)\n"
        "---\n\n"
    )
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / (origem.stem + ".md")
    destino.write_text(frontmatter + texto.strip() + "\n", encoding="utf-8")
    return destino


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    origem, destino_dir = Path(argv[0]), Path(argv[1])
    if origem.is_dir():
        alvos = sorted(
            p for p in origem.rglob("*")
            if p.is_file() and p.suffix.lower() in EXTENSOES_CONVERSIVEIS
        )
    else:
        alvos = [origem]
    if not alvos:
        print(f"Nenhum arquivo conversível em {origem}")
        return 1
    for alvo in alvos:
        gerado = converter_arquivo(alvo, destino_dir)
        print(f"  ✓ {alvo.name} → {gerado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
