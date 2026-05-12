"""
cli/display.py — DVA-CBS | Projeto Diógenes
Helpers de formatação Rich. Cores semânticas conforme Design System TCU-CBS.

Não contém lógica de negócio — apenas funções de apresentação.
Referência normativa: RNF-USAB-05, RNF-OBSE-01 (PRD v0.1), Bloco 2.3.8 (SDD v0.1)
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Cores semânticas TCU-CBS
COR_OK      = "green"
COR_ERRO    = "red"
COR_AVISO   = "yellow"
COR_DESTAQUE = "cyan"   # âmbar no Design System; cyan é proxy aceitável no terminal
COR_DIM     = "dim"


def cabecalho_motor_start(module_id: str, activity: int) -> None:
    console.print(Panel(
        f"[bold]MOTOR DE START[/bold]  —  {module_id} / Atividade {activity}",
        border_style="blue",
    ))


def passo_ok(mensagem: str) -> None:
    console.print(f" [{COR_OK}]✓[/{COR_OK}]  {mensagem}")


def passo_erro(mensagem: str) -> None:
    console.print(f" [{COR_ERRO}]✗[/{COR_ERRO}]  {mensagem}")


def resultado_motor_start(cycle_id: str, manifest_path: Path, n_files: int) -> None:
    console.print()
    console.print(f" [bold]Cycle ID :[/bold] [{COR_DESTAQUE}]{cycle_id}[/{COR_DESTAQUE}]")
    console.print(f" Arquivos  : {n_files}")
    console.print(f" Manifesto : {manifest_path}")
    console.print()
    console.print(f"[{COR_AVISO}] Leia o manifesto e confirme para iniciar a execução:[/{COR_AVISO}]")
    console.print()
    console.print(f"   diogenes confirm-manifest --cycle {cycle_id}")
    console.print()
    console.print(f"[{COR_DIM}] Para abortar:[/{COR_DIM}]")
    console.print(f"   diogenes abort --cycle {cycle_id} --reason \"motivo\"")


def erro(mensagem: str) -> None:
    console.print(f"[{COR_ERRO}]Erro:[/{COR_ERRO}] {mensagem}")


def aviso(mensagem: str) -> None:
    console.print(f"[{COR_AVISO}]Aviso:[/{COR_AVISO}] {mensagem}")


def tabela_ciclos(rows: list[dict]) -> None:
    t = Table(title="Ciclos registrados", show_header=True)
    t.add_column("Ciclo", style=COR_DESTAQUE, no_wrap=True)
    t.add_column("Módulo")
    t.add_column("Ativ.")
    t.add_column("Status")
    t.add_column("Aberto em (UTC)")
    for r in rows:
        t.add_row(
            r["cycle_id"],
            r["module_id"],
            r["activity"],
            r["status"],
            r["opened_at_utc"][:19].replace("T", " "),
        )
    console.print(t)


def tabela_status(cycle_id: str, record: dict, manifest_exists: bool) -> None:
    t = Table(title=f"Status: {cycle_id}", show_header=False, box=None)
    t.add_column("Campo", style=COR_DIM)
    t.add_column("Valor")
    t.add_row("Módulo", record["module_id"])
    t.add_row("Atividade", record["activity"])
    t.add_row("Status", f"[{COR_DESTAQUE}]{record['status']}[/{COR_DESTAQUE}]")
    t.add_row("Aberto em", record["opened_at_utc"])
    if record.get("ended_at_utc"):
        t.add_row("Encerrado em", record["ended_at_utc"])
    t.add_row("Commit", record.get("git_commit", "")[:12] or "—")
    t.add_row(
        "Manifesto",
        f"[{COR_OK}]presente[/{COR_OK}]" if manifest_exists
        else f"[{COR_ERRO}]ausente[/{COR_ERRO}]",
    )
    if record.get("custo_total_usd") and record["custo_total_usd"] != "0.00":
        t.add_row("Custo", f"USD {record['custo_total_usd']}")
    console.print(t)
