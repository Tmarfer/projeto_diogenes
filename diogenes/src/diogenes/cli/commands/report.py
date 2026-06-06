"""cli/commands/report.py — diogenes report
Gera painel de acompanhamento local (HTML ou Markdown) de um ciclo.
Lê artefatos gravados em _runtime/ sem chamar nenhum modelo de linguagem.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.markdown import Markdown

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()


@app.command()
def report(
    cycle: str = typer.Option(..., "--cycle", "-c", help="Identificador do ciclo"),
    format: str = typer.Option(
        "markdown", "--format", "-f",
        help="Formato de saída: markdown | html",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Arquivo de destino. Sem esta opção: exibe no terminal (Markdown) "
             "ou abre no browser (html).",
    ),
) -> None:
    """Gera relatório de acompanhamento local de um ciclo."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    record = AuditIndex(cfg.workspace.path).get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado no audit_index.")
        raise typer.Exit(1)

    # Imports lazy para não atrasar o startup da CLI
    from diogenes.reports.cycle_report import build_report
    from diogenes.reports.render_html import render_html
    from diogenes.reports.render_markdown import render_markdown

    try:
        data = build_report(cycle, cfg.workspace.path)
    except Exception as e:  # noqa: BLE001
        display.erro(f"Erro ao gerar relatório: {e}")
        raise typer.Exit(1) from e

    fmt = format.lower().strip()

    if fmt == "html":
        content = render_html(data)
        if output:
            output.write_text(content, encoding="utf-8")
            display.passo_ok(f"HTML salvo em: {output}")
            _tentar_abrir_browser(output)
        else:
            # Salva no diretório do ciclo e abre no browser
            cycle_dir = cfg.workspace.path / "cycles" / cycle
            html_path = cycle_dir / "report.html"
            html_path.write_text(content, encoding="utf-8")
            display.passo_ok(f"HTML salvo em: {html_path}")
            _tentar_abrir_browser(html_path)
    else:
        content = render_markdown(data)
        if output:
            output.write_text(content, encoding="utf-8")
            display.passo_ok(f"Markdown salvo em: {output}")
        else:
            display.console.print(Markdown(content))


def _tentar_abrir_browser(path: Path) -> None:
    url = path.resolve().as_uri()
    display.console.print(f"  [dim]URL:[/dim] {url}")
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
