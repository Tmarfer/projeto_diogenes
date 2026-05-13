"""cli/commands/status.py — diogenes status"""
from __future__ import annotations

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()

@app.command()
def status(
    cycle: str = typer.Option(..., "--cycle", "-c", help="Identificador do ciclo"),
) -> None:
    """Exibe o estado atual de um ciclo."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e
    record = AuditIndex(cfg.workspace.path).get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado.")
        raise typer.Exit(1)
    manifest_exists = (cfg.workspace.path / "cycles" / cycle / "manifest.md").exists()
    display.tabela_status(cycle, record, manifest_exists)
