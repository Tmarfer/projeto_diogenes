"""cli/commands/init.py — diogenes init"""
from __future__ import annotations

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager

app = typer.Typer()

@app.command()
def init() -> None:
    """Inicializa o workspace do Departamento (cria estrutura e audit_index.csv)."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e
    ws = cfg.workspace.path
    WorkspaceManager(ws).inicializar_workspace()
    AuditIndex(ws).create_if_not_exists()
    display.passo_ok(f"Workspace inicializado: {ws}")
    display.passo_ok("input/  — pacotes de módulos (intocáveis pelo sistema)")
    display.passo_ok("cycles/ — diretórios de trabalho dos ciclos")
    display.passo_ok("audit_index.csv")
