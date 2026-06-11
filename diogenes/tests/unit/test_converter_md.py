"""Testes do conversor mínimo docx/txt/pdf → md (scripts/converter_md.py)."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "converter_md.py"
_spec = importlib.util.spec_from_file_location("converter_md", _SCRIPT)
assert _spec and _spec.loader
converter_md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(converter_md)


def _pdf_minimo(linhas: list[str]) -> bytes:
    """PDF 1.4 mínimo válido (1 página, Helvetica/WinAnsi) construído à mão."""
    def _esc(s: str) -> bytes:
        return (
            s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            .encode("cp1252", errors="replace")
        )

    corpo = b"BT /F1 11 Tf 72 760 Td 14 TL\n"
    for linha in linhas:
        corpo += b"(" + _esc(linha) + b") Tj T*\n"
    corpo += b"ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(corpo)).encode() + b" >>\nstream\n" + corpo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return bytes(out)


def _frontmatter_ok(md: str, nome_original: str) -> None:
    assert md.startswith("---\n")
    assert f"arquivo_original: {nome_original}" in md
    m = re.search(r"sha256_original: ([0-9a-f]+)", md)
    assert m and len(m.group(1)) == 64
    assert "convertido_em_utc:" in md


def test_converter_txt(tmp_path: Path):
    origem = tmp_path / "registro_locacao.txt"
    origem.write_text("CBS sobre locação de bem móvel: R$ 4.455,00", encoding="utf-8")
    destino = converter_md.converter_arquivo(origem, tmp_path / "saida")
    assert destino.name == "registro_locacao.md"
    md = destino.read_text(encoding="utf-8")
    _frontmatter_ok(md, "registro_locacao.txt")
    assert "R$ 4.455,00" in md


def test_converter_docx(tmp_path: Path):
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    doc.add_paragraph("Parecer sobre redução setorial de combustíveis.")
    tabela = doc.add_table(rows=1, cols=2)
    tabela.rows[0].cells[0].text = "CBS declarada"
    tabela.rows[0].cells[1].text = "R$ 65.288,32"
    origem = tmp_path / "parecer.docx"
    doc.save(origem)
    destino = converter_md.converter_arquivo(origem, tmp_path / "saida")
    md = destino.read_text(encoding="utf-8")
    _frontmatter_ok(md, "parecer.docx")
    assert "redução setorial" in md
    assert "R$ 65.288,32" in md


def test_converter_pdf(tmp_path: Path):
    pytest.importorskip("pdfminer")
    origem = tmp_path / "relatorio.pdf"
    origem.write_bytes(_pdf_minimo(["Relatorio de apuracao CBS", "Valor: R$ 9.405,00"]))
    destino = converter_md.converter_arquivo(origem, tmp_path / "saida")
    md = destino.read_text(encoding="utf-8")
    _frontmatter_ok(md, "relatorio.pdf")
    assert "Relatorio de apuracao CBS" in md
    assert "R$ 9.405,00" in md


def test_extensao_nao_suportada(tmp_path: Path):
    origem = tmp_path / "dados.xlsx"
    origem.write_bytes(b"nao importa")
    with pytest.raises(ValueError, match="não conversível"):
        converter_md.extrair_texto(origem)


def test_main_diretorio(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "a.txt").write_text("conteúdo A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("conteúdo B", encoding="utf-8")
    saida = tmp_path / "md"
    assert converter_md.main([str(tmp_path), str(saida)]) == 0
    assert sorted(p.name for p in saida.glob("*.md")) == ["a.md", "b.md"]
