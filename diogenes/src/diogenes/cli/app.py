"""
cli/app.py — DVA-CBS | Projeto Diógenes
App Typer raiz. Entry point: diogenes.cli.app:app

Registra todos os subcomandos conforme RF-CL-01 a RF-CL-13 (PRD v0.1).
Subcomandos implementados por sprint:
  Sprint 1: init, start, confirm-manifest, status, list
  Sprint 2: show
  Sprint 3: proceed, pause, resume, abort
  Sprint 5: verify-output, seal
"""

from __future__ import annotations

import typer
from rich.panel import Panel

from diogenes.cli import display
from diogenes.cli.commands import (
    abort,
    complete_sherlock,
    confirm_manifest,
    init,
    list_cycles,
    pause,
    proceed,
    resume,
    seal,
    show,
    start,
    status,
    verify_output,
)

app = typer.Typer(
    name="diogenes",
    help="DVA-CBS | Departamento de Validação Assistida da CBS — TC 015.848/2025-6",
    no_args_is_help=True,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        display.console.print(Panel(
            "[bold]DVA-CBS | Projeto Diógenes[/bold]\n"
            "TC 015.848/2025-6 | TCU / SecexContas\n\n"
            "Use [bold]diogenes --help[/bold] para ver os subcomandos.",
            border_style="blue",
        ))


# Registro dos subcomandos — um arquivo por comando conforme SDD Bloco 2.3.8
app.command(name="init")(init.init)
app.command(name="start")(start.start)
app.command(name="confirm-manifest")(confirm_manifest.confirm_manifest)
app.command(name="status")(status.status)
app.command(name="list")(list_cycles.list_cycles)
app.command(name="proceed")(proceed.proceed)
app.command(name="pause")(pause.pause)
app.command(name="resume")(resume.resume)
app.command(name="abort")(abort.abort)
app.command(name="verify-output")(verify_output.verify_output)
app.command(name="seal")(seal.seal)
app.command(name="show")(show.show)
app.command(name="complete-sherlock")(complete_sherlock.complete_sherlock)