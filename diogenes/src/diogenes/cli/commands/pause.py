"""cli/commands/pause.py — diogenes pause"""
from __future__ import annotations
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.orchestrator.states import CycleState

app = typer.Typer()

@app.command()
def pause(cycle: str = typer.Option(..., "--cycle", "-c")) -> None:
    """Pausa o ciclo após alerta crítico (aguarda decisão de Lestrade)."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado."); raise typer.Exit(1)

    estados_pausaveis = {
        CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value,
    }
    if record["status"] not in estados_pausaveis:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}' — não pode ser pausado neste estado."
        ); raise typer.Exit(1)

    audit.update_status(cycle, CycleState.PAUSADO_LESTRADE.value)
    display.passo_ok(f"Ciclo '{cycle}' pausado. Use `diogenes proceed` para retomar.")
