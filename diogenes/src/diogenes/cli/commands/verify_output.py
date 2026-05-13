"""cli/commands/verify_output.py — diogenes verify-output"""
from __future__ import annotations

import typer
from rich.panel import Panel

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.models import MotorSaidaReport
from diogenes.motors.exceptions import MotorSaidaError
from diogenes.motors.motor_saida import MotorSaida

app = typer.Typer()

@app.command(name="verify-output")
def verify_output(
    cycle: str = typer.Option(..., "--cycle", "-c"),
) -> None:
    """Aciona o Motor de Saída para verificação do documento de output."""
    try:
        get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    display.console.print(Panel(
        f"[bold]MOTOR DE SAÍDA[/bold]  —  ciclo [cyan]{cycle}[/cyan]",
        border_style="blue",
    ))

    try:
        motor = MotorSaida()
        report = motor.verificar(cycle)
    except MotorSaidaError as e:
        display.passo_erro(str(e))
        raise typer.Exit(1) from e
    except FileNotFoundError as e:
        display.passo_erro(str(e))
        raise typer.Exit(1) from e

    _exibir_relatorio(report, cycle)


def _exibir_relatorio(report: MotorSaidaReport, cycle: str) -> None:
    console = display.console

    if report.documento_limpo:
        console.print()
        display.passo_ok(f"Documento verificado: {report.doc_path.name}")
        display.passo_ok("Ocorrências detectadas: 0")
        display.passo_ok("Documento classificado como [bold green]LIMPO[/bold green]")
        console.print()
        console.print(f"  [dim]Hash:[/dim] {report.doc_hash}")
        console.print()
        console.print("O documento está pronto para chancela. Execute:")
        console.print(f"  [bold]diogenes seal --cycle {cycle}[/bold]")
        return

    # Com ocorrências
    console.print()
    display.passo_erro(f"Documento: {report.doc_path.name}")
    display.passo_erro(f"Ocorrências detectadas: {report.total_ocorrencias}")
    console.print()

    for idx, oc in enumerate(report.ocorrencias, start=1):
        classif = oc.classificacao_automatica or "(nenhuma)"
        cor = "yellow" if oc.classificacao_automatica else "red"
        console.print(Panel(
            f"[bold]Categoria:[/bold] {oc.categoria}  |  "
            f"[bold]Padrão:[/bold] \"{oc.padrao_detectado}\"\n"
            f"[bold]Posição:[/bold] {oc.posicao_documento}  |  "
            f"[bold]Classificação auto:[/bold] {classif}\n\n"
            f"[dim]{oc.contexto}[/dim]",
            title=f"Ocorrência {idx} — Linha {oc.linha}",
            border_style=cor,
        ))

    console.print()
    console.print("[bold]Opções:[/bold]")
    console.print()
    console.print(
        f"  [cyan]diogenes seal --cycle {cycle} "
        f"--accept-occurrences --reason \"motivo\"[/cyan]"
    )
    console.print("    Aceita todas as ocorrências como falsos positivos (ACEITO_JUSTIFICADO).")
    console.print()
    console.print(
        f"  Editar manualmente {report.doc_path.name} e re-executar "
        f"[cyan]diogenes verify-output --cycle {cycle}[/cyan]"
    )
    console.print("    Após correção, re-varre o documento (CORRIGIDO_MANUAL).")
    console.print()
    console.print(
        f"  [red]diogenes abort --cycle {cycle} --reason \"motivo\"[/red]"
    )
    console.print("    Aborta o ciclo para regeneração (RETORNADO_MYCROFT).")
