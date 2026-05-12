"""cli/commands/resume.py — diogenes resume"""
from __future__ import annotations
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.orchestrator.states import CycleState
from diogenes.orchestrator.orchestrator import Orchestrator

app = typer.Typer()

@app.command()
def resume(cycle: str = typer.Option(..., "--cycle", "-c")) -> None:
    """Retoma ciclo pausado por Lestrade."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado."); raise typer.Exit(1)

    if record["status"] != CycleState.PAUSADO_LESTRADE.value:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}', não PAUSADO_LESTRADE."
        ); raise typer.Exit(1)

    display.passo_ok("Retomando ciclo...")
    # Retomada tem mesma semântica de proceed: aciona fase Sherlock
    from diogenes.cli.commands.proceed import _reconstruir_manifest
    manifest = _reconstruir_manifest(cfg, cycle, record)
    # Avançar de PAUSADO_LESTRADE para AGUARDANDO_DECISAO para permitir proceed
    audit.update_status(cycle, CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value)

    try:
        orq = Orchestrator(cycle)
        resultado = orq.retomar_apos_alerta(manifest)
        if resultado:
            display.passo_ok(f"Ciclo concluído. Output: {resultado}")
        else:
            display.aviso("Ciclo em execução. Aguarde.")
    except Exception as e:
        display.erro(f"Erro na retomada: {e}"); raise typer.Exit(1)
