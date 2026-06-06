#!/usr/bin/env python3
"""
gerar_ficha_sintese_pdf_png.py
──────────────────────────────────────────────────────────────────────────────
Gerador de documentos das Fichas Síntese — HTML → PDF + PNG (alta resolução).

FONTE: O arquivo HTML da Ficha Síntese é a fonte única de verdade.
  A partir do HTML são gerados automaticamente o PDF vetorial e os PNGs.

SAÍDAS geradas a partir de um HTML de Ficha Síntese:
  • PDF  — vetorial A4, renderizado pelo Chromium nativo (margin=0, backgrounds)
  • PNG  — um arquivo por página, resolução 3× (288dpi) — qualidade de impressão

ABORDAGEM:
  PDF: page.pdf() nativo do Playwright/Chromium com @media print e @page A4
  PNG: screenshot por elemento div.page em modo screen (device_scale_factor=3)
       preservando todas as cores, gradientes CSS e conic-gradient

  Uma única sessão do Chromium gera ambos os formatos (eficiência).

Requisito do HTML de origem:
  - Cada div.page deve ter width=794px e height≤1123px (A4@96dpi, sem overflow)
  - CSS: @page { size: A4; margin: 0; }
  - CSS: @media print { .page { page-break-after: always; } }

Projeto: Cálculo da Alíquota de Referência CBS · TC 015.848/2025-6
Unidade: SecexContas / TCU

Uso:
  # Arquivo único → gera .pdf + _p01.png, _p02.png, ... no mesmo diretório
  python3 gerar_ficha_sintese_pdf_png.py ficha_sintese_mod008_v1.html

  # Saída em diretório específico
  python3 gerar_ficha_sintese_pdf_png.py ficha_sintese_mod008_v1.html --dir-saida /tmp/saida/

  # Somente PDF (sem PNG)
  python3 gerar_ficha_sintese_pdf_png.py ficha_sintese_mod008_v1.html --somente-pdf

  # Somente PNGs (sem PDF)
  python3 gerar_ficha_sintese_pdf_png.py ficha_sintese_mod008_v1.html --somente-png

  # Escala PNG personalizada (padrão=3 → 288dpi; use 4 para 384dpi ultra-HD)
  python3 gerar_ficha_sintese_pdf_png.py ficha_sintese_mod008_v1.html --escala-png 4

  # Processa TODOS os ficha_sintese_*.html de uma pasta
  python3 gerar_ficha_sintese_pdf_png.py --pasta 3-PAINEIS_DASHBOARDS/DEV/MOD_008_Simples_Nacional/

  # Processa todos os módulos DEV recursivamente
  python3 gerar_ficha_sintese_pdf_png.py --pasta 3-PAINEIS_DASHBOARDS/DEV/ --recursivo

Requisitos:
  pip3 install playwright
  python3 -m playwright install chromium
──────────────────────────────────────────────────────────────────────────────
"""

import argparse
import sys
import time
from pathlib import Path

# ── Dependências ──────────────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌  Playwright não encontrado. Execute:")
    print("      pip3 install playwright")
    print("      python3 -m playwright install chromium")
    sys.exit(1)


# ── Configurações padrão ──────────────────────────────────────────────────────

# Viewport: 794px = largura exata A4@96dpi; altura generosa
VIEWPORT = {"width": 794, "height": 1300}

# Escala para PNG: 3 → 288dpi (qualidade de impressão profissional)
# A4 @ 3×: ~2382×3369px por página
PNG_ESCALA_PADRAO = 3

# Tempo de espera após carregamento (ms) — garante renderização de fontes/gradientes
WAIT_MS = 1000

# Seletor das páginas dentro do HTML
PAGE_SELECTOR = ".page"


# ── Gerador principal ─────────────────────────────────────────────────────────
def gerar_documentos(
    html_path: Path,
    saida_dir: Path,
    gerar_pdf: bool = True,
    gerar_png: bool = True,
    png_escala: int = PNG_ESCALA_PADRAO,
) -> dict:
    """
    Gera PDF e/ou PNGs a partir de um HTML de Ficha Síntese.

    Parâmetros:
        html_path  — caminho absoluto do HTML de origem
        saida_dir  — diretório onde os arquivos serão salvos
        gerar_pdf  — se True, gera arquivo PDF A4 vetorial
        gerar_png  — se True, gera um PNG por página (alta resolução)
        png_escala — fator de escala para PNGs (padrão=3 → 288dpi)

    Retorna dict com chaves:
        "pdf"  : Path do PDF gerado (ou None se não gerado / erro)
        "pngs" : lista de Paths dos PNGs gerados
        "ok"   : True se nenhum erro ocorreu
    """
    resultado = {"pdf": None, "pngs": [], "ok": False}

    if not html_path.exists():
        print(f"  ✗  Arquivo não encontrado: {html_path}")
        return resultado

    saida_dir.mkdir(parents=True, exist_ok=True)
    url = html_path.resolve().as_uri()
    stem = html_path.stem  # ex: "ficha_sintese_mod008_v1"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)

            # ── PNGs (modo screen, alta resolução) ───────────────────────────
            if gerar_png:
                ctx = browser.new_context(
                    viewport=VIEWPORT,
                    device_scale_factor=png_escala,
                )
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                pg.wait_for_timeout(WAIT_MS)
                pg.evaluate("() => { const b = document.getElementById('btn-pdf'); if(b) b.style.display='none'; }")

                elems = pg.locator(PAGE_SELECTOR).all()
                for i, elem in enumerate(elems, start=1):
                    raw = elem.screenshot(type="png")
                    png_path = saida_dir / f"{stem}_p{i:02d}.png"
                    png_path.write_bytes(raw)
                    resultado["pngs"].append(png_path)
                    w_px = len(raw)  # tamanho em bytes (indicativo)
                    # Dimensão real em px (calculada)
                    w_pt = 794 * png_escala
                    h_pt = 1123 * png_escala
                    size_kb = len(raw) // 1024
                    print(f"  ✓  {png_path.name}  ({size_kb} KB · {w_pt}×{h_pt}px · {96*png_escala}dpi)")

                ctx.close()

            # ── PDF (modo print, vetorial A4) ─────────────────────────────────
            if gerar_pdf:
                ctx = browser.new_context(viewport=VIEWPORT)
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_load_state("networkidle")
                pg.wait_for_timeout(WAIT_MS)

                pdf_bytes = pg.pdf(
                    format="A4",
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    print_background=True,
                )
                ctx.close()

                pdf_path = saida_dir / f"{stem}.pdf"
                pdf_path.write_bytes(pdf_bytes)
                resultado["pdf"] = pdf_path
                n_pag = pdf_bytes.count(b"/MediaBox")
                size_kb = len(pdf_bytes) // 1024
                print(f"  ✓  {pdf_path.name}  ({size_kb} KB · {n_pag} página(s) · vetorial)")

            browser.close()

        resultado["ok"] = True

    except Exception as exc:
        print(f"  ✗  Erro ao processar {html_path.name}: {exc}")

    return resultado


# ── Descoberta de arquivos ────────────────────────────────────────────────────
def encontrar_fichas(pasta: Path, recursivo: bool = False) -> list[Path]:
    pattern = "ficha_sintese_*.html"
    if recursivo:
        return sorted(pasta.rglob(pattern))
    return sorted(pasta.glob(pattern))


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Gerador de Fichas Síntese · TCU · HTML → PDF + PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "html",
        nargs="?",
        metavar="ARQUIVO.html",
        help="HTML de origem da Ficha Síntese",
    )
    group.add_argument(
        "--pasta",
        metavar="PASTA",
        help="Converte todos os ficha_sintese_*.html da pasta",
    )

    parser.add_argument(
        "--dir-saida",
        metavar="PASTA",
        help="Diretório de saída para PDF e PNGs "
             "(padrão: mesmo diretório do HTML)",
    )
    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Com --pasta: busca em subpastas recursivamente",
    )
    parser.add_argument(
        "--somente-pdf",
        action="store_true",
        help="Gera apenas o PDF (sem PNGs)",
    )
    parser.add_argument(
        "--somente-png",
        action="store_true",
        help="Gera apenas os PNGs (sem PDF)",
    )
    parser.add_argument(
        "--escala-png",
        type=int,
        default=PNG_ESCALA_PADRAO,
        metavar="N",
        help="Fator de escala dos PNGs: 2=192dpi, 3=288dpi (padrão), 4=384dpi",
    )

    args = parser.parse_args()

    # Resolve flags de saída
    gerar_pdf = not args.somente_png
    gerar_png = not args.somente_pdf

    dpi_png = 96 * args.escala_png
    a4_w = 794 * args.escala_png
    a4_h = 1123 * args.escala_png

    print()
    print("═" * 66)
    print("  📄  Gerador de Fichas Síntese · TCU / SecexContas")
    saidas = []
    if gerar_pdf: saidas.append("PDF A4 vetorial")
    if gerar_png: saidas.append(f"PNG {a4_w}×{a4_h}px @ {dpi_png}dpi")
    print(f"       Saídas: {' + '.join(saidas)}")
    print("═" * 66)

    inicio = time.time()
    ok = erros = 0

    # ── Arquivo único ─────────────────────────────────────────────────
    if args.html:
        html_path = Path(args.html).resolve()
        saida_dir = Path(args.dir_saida).resolve() if args.dir_saida else html_path.parent
        print(f"\n  HTML   : {html_path.name}")
        print(f"  Saída  : {saida_dir}\n")

        res = gerar_documentos(
            html_path, saida_dir,
            gerar_pdf=gerar_pdf, gerar_png=gerar_png,
            png_escala=args.escala_png,
        )
        ok += 1 if res["ok"] else 0
        erros += 0 if res["ok"] else 1

    # ── Pasta ─────────────────────────────────────────────────────────
    else:
        pasta  = Path(args.pasta).resolve()
        fichas = encontrar_fichas(pasta, recursivo=args.recursivo)

        if not fichas:
            print(f"\n  ⚠  Nenhum ficha_sintese_*.html encontrado em:\n     {pasta}")
            sys.exit(0)

        print(f"\n  {len(fichas)} arquivo(s) encontrado(s) em: {pasta}\n")
        dir_saida_base = Path(args.dir_saida).resolve() if args.dir_saida else None

        for html_path in fichas:
            saida_dir = dir_saida_base if dir_saida_base else html_path.parent
            print(f"  ▶  {html_path.name}")
            res = gerar_documentos(
                html_path, saida_dir,
                gerar_pdf=gerar_pdf, gerar_png=gerar_png,
                png_escala=args.escala_png,
            )
            ok += 1 if res["ok"] else 0
            erros += 0 if res["ok"] else 1

    # ── Resumo ────────────────────────────────────────────────────────
    elapsed = time.time() - inicio
    print()
    print("─" * 66)
    print(f"  ✓ {ok} gerado(s)   ✗ {erros} erro(s)   {elapsed:.1f}s")
    print("─" * 66)
    print()

    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
