"""
agents/file_prep.py — Preparação de conteúdo de arquivos para Watson.
Extrai conteúdo legível de xlsx, sql, ipynb, pdf, md.
Referência normativa: RF-WA-03 a RF-WA-05 (PRD v0.1), Bloco 9.3.2 (SDD v0.1)
"""
from __future__ import annotations
from pathlib import Path

_SQL_MAX_CHARS = 8_000


def preparar_arquivo(path: Path) -> str:
    """Retorna representação textual do arquivo para inclusão em prompt."""
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return _ler_excel(path)
    if ext == ".sql":
        return _ler_sql(path)
    if ext == ".ipynb":
        return _ler_notebook(path)
    if ext == ".pdf":
        return _ler_pdf(path)
    # Markdown e texto puro
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERRO AO LER ARQUIVO: {e}]"


def _ler_excel(path: Path) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=False)
        partes: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            linhas: list[str] = []
            for i, row in enumerate(ws.iter_rows(values_only=False)):
                if i >= 15:   # primeiras 15 linhas + fórmulas
                    break
                celulas = []
                for cell in row:
                    val = cell.value
                    if val is None:
                        celulas.append("")
                    elif isinstance(val, str) and val.startswith("="):
                        celulas.append(f"[FORMULA:{val}]")
                    else:
                        celulas.append(str(val))
                linhas.append("\t".join(celulas))
            partes.append(f"--- Aba: {sheet_name} ---\n" + "\n".join(linhas))
        return "\n\n".join(partes)
    except Exception as e:
        return f"[ERRO AO LER EXCEL: {e}]"


def _ler_sql(path: Path) -> str:
    try:
        import sqlparse
        raw = path.read_text(encoding="utf-8")
        formatado = sqlparse.format(raw, reindent=True, keyword_case="upper")
        if len(formatado) > _SQL_MAX_CHARS:
            return formatado[:_SQL_MAX_CHARS] + f"\n\n[TRUNCADO — {len(formatado)} chars totais]"
        return formatado
    except Exception as e:
        return f"[ERRO AO LER SQL: {e}]"


def _ler_notebook(path: Path) -> str:
    try:
        import nbformat
        nb = nbformat.read(str(path), as_version=4)
        celulas: list[str] = []
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == "code":
                src = cell.source.strip()
                if src:
                    celulas.append(f"# Célula {i+1}\n{src}")
        return "\n\n".join(celulas) if celulas else "[Notebook sem células de código]"
    except Exception as e:
        return f"[ERRO AO LER NOTEBOOK: {e}]"


def _ler_pdf(path: Path) -> str:
    try:
        from pdfminer.high_level import extract_text
        texto = extract_text(str(path))
        return texto.strip() if texto else "[PDF sem texto extraível]"
    except Exception as e:
        return f"[ERRO AO LER PDF: {e}]"
