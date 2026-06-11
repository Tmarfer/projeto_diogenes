"""
scripts/gerar_mod_sint_formatos.py — DVA-CBS | Projeto Diógenes

Gera os módulos sintéticos de formato (um por formato de arquivo) em
`workspace/input/`, a partir das fontes versionadas em `scripts/massa_fontes/`:

    MOD_SINT_SQL    .sql copiados direto           (parser sqlparse)
    MOD_SINT_IPYNB  .ipynb montados das fontes .py (parser nbformat, separador `# %%`)
    MOD_SINT_MD     .md copiados direto            (caminho texto puro)
    MOD_SINT_PDF    .txt → .pdf → .md convertido   (fidelidade pdf→md)
    MOD_SINT_DOCX   .txt → .docx → .md convertido  (fidelidade docx→md)
    MOD_SINT_TXT    .txt → .md convertido          (fidelidade txt→md)

Os nativos pré-conversão (pdf/docx/txt) ficam em `{workspace}/_fontes_originais/{MOD}/`
— fora de `input/` para não serem analisados em paralelo aos .md convertidos.
Cada módulo recebe `protocolo_recebimento.md` e `inventario.xlsx` com SHA-256 reais.

Gabaritos das inconsistências plantadas: `docs/conformidade/gabarito_mod_sint_*.md`
(uso restrito — nunca incluir na massa de entrada).

Uso (de dentro de diogenes/):
    python scripts/gerar_mod_sint_formatos.py [--workspace /caminho/workspace]
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_MASSA_FONTES = _SCRIPTS_DIR / "massa_fontes"

if str(_SCRIPTS_DIR) not in sys.path:  # permite importar converter_md como módulo irmão
    sys.path.insert(0, str(_SCRIPTS_DIR))

# módulo → (estratégia, subdir de fontes)
MODULOS = {
    "MOD_SINT_SQL": "copiar",
    "MOD_SINT_IPYNB": "notebook",
    "MOD_SINT_MD": "copiar",
    "MOD_SINT_PDF": "pdf_convertido",
    "MOD_SINT_DOCX": "docx_convertido",
    "MOD_SINT_TXT": "txt_convertido",
}


# ── builders de formato nativo (determinísticos) ─────────────────────────────

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


def _construir_docx(fonte_txt: Path, destino: Path) -> None:
    import docx
    doc = docx.Document()
    for linha in fonte_txt.read_text(encoding="utf-8").splitlines():
        doc.add_paragraph(linha)
    doc.save(destino)


def _construir_ipynb(fonte_py: Path, destino: Path) -> None:
    import nbformat
    nb = nbformat.v4.new_notebook()
    texto = fonte_py.read_text(encoding="utf-8")
    celulas = [c.strip() for c in texto.split("# %%") if c.strip()]
    nb.cells = [nbformat.v4.new_code_cell(c) for c in celulas]
    nbformat.write(nb, str(destino))


# ── protocolo e inventário (obrigatórios em todo pacote) ─────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def _escrever_protocolo(input_dir: Path, module_id: str, arquivos: list[Path]) -> None:
    agora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas = [
        f"# Protocolo de Recebimento — {module_id}",
        "**DVA-CBS | TC 015.848/2025-6 | TCU / SecexContas**",
        "",
        "| Campo | Valor |",
        "|-------|-------|",
        f"| Módulo | {module_id} |",
        "| Atividade | 1 — Validação CBS |",
        "| Período de referência | Anos-base 2023/2024 — competências de 2024 |",
        f"| Data/hora recebimento | {agora} |",
        f"| Data de geração deste protocolo | {agora} |",
        "| Responsável recebimento | Insp. Lestrade / DVA-CBS |",
        f"| Total de arquivos | {len(arquivos) + 2} |",
        f"| Arquivos para análise | {len(arquivos)} |",
        "",
        "## Arquivos Recebidos",
        "",
        "| # | Arquivo | Tipo | Status |",
        "|---|---------|------|--------|",
    ]
    for i, p in enumerate(sorted(arquivos), start=1):
        linhas.append(f"| {i} | {p.name} | {p.suffix.lstrip('.').upper()} | ✓ Íntegro |")
    n = len(arquivos)
    linhas += [
        f"| {n + 1} | protocolo_recebimento.md | MD | (este arquivo) |",
        f"| {n + 2} | inventario.xlsx | XLSX | ✓ Íntegro |",
        "",
        "## Declaração de Integridade",
        "",
        "Todos os arquivos listados foram recebidos sem adulteração confirmada",
        "via hash SHA-256. Os originais são mantidos intactos em conformidade",
        "com o Art. 13 do regimento interno DVA-CBS (Projeto Diógenes — Motor de Start).",
        "",
        "---",
        "*Uso interno restrito — DVA-CBS / TCU / SecexContas*",
    ]
    (input_dir / "protocolo_recebimento.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _escrever_inventario(input_dir: Path, arquivos: list[Path]) -> None:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"
    hoje = datetime.now(UTC).strftime("%Y-%m-%d")
    ws.append(["Período de referência:", "Anos-base 2023/2024 — competências de 2024",
               "", "Data de geração:", hoje, "", "", "", ""])
    ws.append(["N°", "Nome do Arquivo", "Tipo", "Categoria", "Tamanho Estimado",
               "Hash SHA-256 (primeiros 16)", "Responsável Envio", "Data Envio", "Observação"])
    for i, p in enumerate(sorted(arquivos), start=1):
        ws.append([i, p.name, p.suffix.lstrip(".").upper(), "Analisável",
                   f"~{max(1, p.stat().st_size // 1024)} KB", _sha256(p)[:16],
                   "RFB-COFIS", hoje, "Massa sintética de formato"])
    wb.save(input_dir / "inventario.xlsx")


# ── geração por módulo ───────────────────────────────────────────────────────

def gerar_modulo(module_id: str, workspace: Path) -> list[Path]:
    estrategia = MODULOS[module_id]
    fontes_dir = _MASSA_FONTES / module_id
    input_dir = workspace / "input" / module_id
    nativos_dir = workspace / "_fontes_originais" / module_id
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(parents=True)

    gerados: list[Path] = []

    # metodologia comum: âncora normativa do Sherlock (sem ela a validação
    # metodológica declara o módulo inteiro não verificável)
    comum_dir = _MASSA_FONTES / "_comum"
    if comum_dir.is_dir():
        for doc in sorted(comum_dir.glob("*.md")):
            destino = input_dir / doc.name
            shutil.copy2(doc, destino)
            gerados.append(destino)

    for fonte in sorted(fontes_dir.iterdir()):
        if not fonte.is_file():
            continue
        if estrategia == "copiar":
            destino = input_dir / fonte.name
            shutil.copy2(fonte, destino)
        elif estrategia == "notebook":
            destino = input_dir / (fonte.stem + ".ipynb")
            _construir_ipynb(fonte, destino)
        else:
            # formatos pré-convertidos: nativo em _fontes_originais/, .md em input/
            nativos_dir.mkdir(parents=True, exist_ok=True)
            if estrategia == "pdf_convertido":
                nativo = nativos_dir / (fonte.stem + ".pdf")
                nativo.write_bytes(_pdf_minimo(fonte.read_text(encoding="utf-8").splitlines()))
            elif estrategia == "docx_convertido":
                nativo = nativos_dir / (fonte.stem + ".docx")
                _construir_docx(fonte, nativo)
            else:  # txt_convertido
                nativo = nativos_dir / fonte.name
                shutil.copy2(fonte, nativo)
            from converter_md import converter_arquivo
            destino = converter_arquivo(nativo, input_dir)
        gerados.append(destino)

    _escrever_protocolo(input_dir, module_id, gerados)
    _escrever_inventario(input_dir, gerados)
    return gerados


def main(argv: list[str]) -> int:
    workspace: Path | None = None
    if "--workspace" in argv:
        workspace = Path(argv[argv.index("--workspace") + 1])
    if workspace is None:
        from diogenes.config import get_config
        workspace = Path(get_config().workspace.path)

    for module_id in MODULOS:
        gerados = gerar_modulo(module_id, workspace)
        print(f"✓ {module_id}: {len(gerados)} arquivo(s) analisável(is) + protocolo + inventário")
        for p in gerados:
            print(f"    {p.name}")
    print(f"\nMódulos gerados em {workspace / 'input'}")
    print("Rode, por exemplo: diogenes autorun --module MOD_SINT_SQL --activity 1 --auto-seal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
