"""cli/commands/abort.py — diogenes abort"""
from __future__ import annotations
from datetime import datetime, timezone
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.orchestrator.states import CycleState

app = typer.Typer()

ESTADOS_ABORTAVEIS = {
    CycleState.PREPARADO.value,
    CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value,
    CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value,
    CycleState.PAUSADO_LESTRADE.value,
    CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value,
    CycleState.AGUARDANDO_CHANCELA_LESTRADE.value,
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
        display.erro(str(e)); raise typer.Exit(1)

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado."); raise typer.Exit(1)

    if record["status"] not in ESTADOS_ABORTAVEIS:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}' e não pode ser abortado. "
            f"Ciclos em EM_EXECUCAO precisam aguardar a conclusão da chamada LLM corrente."
        ); raise typer.Exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    audit.update_status(
        cycle, CycleState.ABORTADO_LESTRADE.value,
        ended_at_utc=now, notes=reason[:200],
    )
    display.passo_ok(f"Ciclo '{cycle}' abortado.")
    display.console.print(f"  Razão: {reason}")
    display.console.print(f"  O diretório de trabalho foi preservado (Art. 16).")
