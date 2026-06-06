"""cli/commands/abort.py — diogenes abort"""
from __future__ import annotations

from datetime import UTC, datetime

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()

ESTADOS_TERMINAIS = {
    CycleState.ENCERRADO_CHANCELADO.value,
    CycleState.ABORTADO_LESTRADE.value,
    CycleState.ABORTADO_FALHA_AGENTE.value,
}

@app.command()
def abort(
    cycle: str = typer.Option(..., "--cycle", "-c"),
    reason: str = typer.Option(..., "--reason", "-r", help="Razão do aborto."),
) -> None:
    """Aborta ciclo por decisão de Lestrade. O diretório de trabalho é preservado."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado.")
        raise typer.Exit(1)

    if record["status"] in ESTADOS_TERMINAIS:
        display.erro(
            f"Ciclo '{cycle}' está em estado terminal '{record['status']}' e não pode ser abortado."
        )
        raise typer.Exit(1)

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    audit.update_status(
        cycle, CycleState.ABORTADO_LESTRADE.value,
        ended_at_utc=now, notes=reason[:200],
    )
    try:
        from diogenes.reports.render_html import atualizar_report_html
        atualizar_report_html(cycle, cfg.workspace.path)
    except Exception:
        pass
    display.passo_ok(f"Ciclo '{cycle}' abortado.")
    display.console.print(f"  Razão: {reason}")
    display.console.print("  O diretório de trabalho foi preservado (Art. 16).")

