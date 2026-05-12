"""cli/commands/list_cycles.py — diogenes list"""
from __future__ import annotations
from typing import Optional
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()

@app.command(name="list")
def list_cycles(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    filter_status: Optional[str] = typer.Option(None, "--status", "-s"),
) -> None:
    """Lista ciclos registrados no audit_index.csv."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)
    rows = AuditIndex(cfg.workspace.path).list_cycles(module_id=module, status=filter_status)
    if not rows:
        display.console.print("[dim]Nenhum ciclo encontrado.[/dim]")
        return
    display.tabela_ciclos(rows)
