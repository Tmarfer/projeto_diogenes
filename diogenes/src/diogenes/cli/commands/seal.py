"""cli/commands/seal.py — diogenes seal"""
from __future__ import annotations

from datetime import UTC, datetime

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.motors.exceptions import MotorSaidaError
from diogenes.motors.motor_saida import MotorSaida
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()

@app.command()
def seal(
    cycle: str = typer.Option(..., "--cycle", "-c"),
    accept_occurrences: bool = typer.Option(
        False, "--accept-occurrences",
        help="Aceita ocorrências detectadas como falsos positivos."
    ),
    reason: str | None = typer.Option(
        None, "--reason", "-r",
        help="Justificativa (obrigatória com --accept-occurrences)."
    ),
) -> None:
    """Chancela final de Lestrade sobre o output do ciclo."""
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

    status = record["status"]

    # Caminho normal: documento limpo → AGUARDANDO_CHANCELA_LESTRADE
    if status == CycleState.AGUARDANDO_CHANCELA_LESTRADE.value:
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        audit.seal_cycle(cycle, "LIMPO", now)
        _exibir_chancela(cycle, "LIMPO", record.get("output_filename", ""))
        return

    # Aceite de ocorrências: documento com ocorrências → Lestrade aceita
    if status == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value and accept_occurrences:
        if not reason:
            display.erro(
                "--reason é obrigatório com --accept-occurrences. "
                "Descreva por que as ocorrências são falsos positivos."
            )
            raise typer.Exit(1)
        # Re-executar Motor de Saída para registrar o hash atual
        try:
            motor = MotorSaida()
            motor.verificar(cycle)  # registra no audit_index
        except MotorSaidaError:
            pass  # pode já ter sido verificado; continuar
        # Forçar transição para chancela
        audit.update_status(cycle, CycleState.AGUARDANDO_CHANCELA_LESTRADE.value)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        audit.seal_cycle(cycle, "ACEITO_JUSTIFICADO", now, notes=reason)
        _exibir_chancela(cycle, "ACEITO_JUSTIFICADO", record.get("output_filename", ""))
        display.console.print(f"  [dim]Justificativa registrada:[/dim] {reason}")
        return

    # Estado inválido
    display.erro(
        f"Ciclo '{cycle}' está em '{status}'. "
        f"Para chancela, execute primeiro `diogenes verify-output --cycle {cycle}`."
    )
    raise typer.Exit(1)


def _exibir_chancela(cycle: str, decision: str, output_filename: str) -> None:
    display.console.print()
    display.passo_ok(f"Chancela de Lestrade registrada — decisão: [bold]{decision}[/bold]")
    display.passo_ok(f"Ciclo encerrado: [cyan]{cycle}[/cyan]")
    if output_filename:
        display.passo_ok(f"Output final: {output_filename}")
    display.console.print()
    display.console.print(
        "[dim]Status: ENCERRADO_CHANCELADO — ciclo imutável a partir deste momento.[/dim]"
    )
