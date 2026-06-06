"""cli/commands/deliver.py — diogenes deliver

Aciona a Fase de Entrega: gera os entregáveis institucionais (dashboard HTML,
apêndice/relatórios DOCX, ficha síntese) a partir dos artefatos do ciclo.
A geração é determinística; o mapeamento de dados e o QA de Mycroft (LLM) são
opcionais (`--no-qa` para pular; `--no-assets` para pular PDF/PNG da ficha).
"""
from __future__ import annotations

import typer
from rich.panel import Panel

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.orchestrator.entrega import executar_entrega


def deliver(
    cycle: str = typer.Option(..., "--cycle", "-c", help="ID do ciclo."),
    qa: bool = typer.Option(True, "--qa/--no-qa",
                            help="Roda mapeamento de dados + QA de Mycroft (requer LLM)."),
    assets: bool = typer.Option(True, "--assets/--no-assets",
                                help="Gera PDF/PNG da ficha síntese (requer Playwright/Chromium)."),
) -> None:
    """Gera os entregáveis finais do ciclo (Fase de Entrega)."""
    try:
        get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    display.console.print(Panel(
        f"[bold]FASE DE ENTREGA[/bold]  —  ciclo [cyan]{cycle}[/cyan]",
        border_style="blue",
    ))

    try:
        report = executar_entrega(cycle, rodar_qa=qa, with_assets=assets)
    except (KeyError, FileNotFoundError) as e:
        display.passo_erro(str(e))
        raise typer.Exit(1) from e

    console = display.console
    console.print()
    display.passo_ok(f"Artefatos gerados com sucesso: {report.total_artefatos}")
    for a in report.artefatos:
        marca = "[green]✓[/green]" if a.ok else "[red]✗[/red]"
        tam = f"{a.bytes:,} B" if a.bytes else "—"
        console.print(f"  {marca} [{a.tipo}] {a.nome}  [dim]{tam}[/dim]")
        if not a.ok and a.nota:
            console.print(f"      [yellow]{a.nota}[/yellow]")

    if report.avisos:
        console.print()
        console.print("[bold yellow]Avisos:[/bold yellow]")
        for av in report.avisos:
            console.print(f"  • {av}")

    console.print()
    console.print(f"  [dim]Pasta:[/dim] {report.entrega_dir}")
    console.print()
    console.print("Quando estiver satisfeito, prossiga para a chancela:")
    console.print(f"  [bold]diogenes seal --cycle {cycle}[/bold]")
