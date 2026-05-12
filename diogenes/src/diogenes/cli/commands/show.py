"""cli/commands/show.py — diogenes show"""
from __future__ import annotations
from typing import Optional
import typer
import frontmatter
from rich.panel import Panel
from rich.syntax import Syntax
from diogenes.cli import display
from diogenes.config import get_config, ConfigError

app = typer.Typer()

@app.command()
def show(
    cycle: str = typer.Option(..., "--cycle", "-c"),
    phase: Optional[str] = typer.Option(
        None, "--phase", "-p",
        help="watson | sherlock | ambas (padrão: ambas)"
    ),
) -> None:
    """Exibe os arquivos da Stranger's Room de um ciclo."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)

    cycle_dir = cfg.workspace.path / "cycles" / cycle
    sr_dir = cycle_dir / "stranger_room"

    if not sr_dir.exists():
        display.erro(f"Stranger's Room não encontrada para ciclo '{cycle}'."); raise typer.Exit(1)

    fases_map = {
        "watson": ["watson_integridade"],
        "sherlock": ["sherlock_validacao"],
        None: ["watson_integridade", "sherlock_validacao"],
        "ambas": ["watson_integridade", "sherlock_validacao"],
    }
    fases = fases_map.get(phase, ["watson_integridade", "sherlock_validacao"])

    console = display.console
    for fase in fases:
        fase_dir = sr_dir / fase
        if not fase_dir.exists():
            console.print(f"[dim]Fase '{fase}' ainda não executada.[/dim]")
            continue

        arquivos = sorted(fase_dir.glob("*.md"))
        if not arquivos:
            console.print(f"[dim]Fase '{fase}': nenhum arquivo.[/dim]")
            continue

        console.print()
        console.rule(f"[bold]{fase.replace('_', ' ').title()}[/bold]")

        for path in arquivos:
            try:
                post = frontmatter.load(str(path))
                meta = post.metadata
                author = meta.get("author", "?")
                file_type = meta.get("file_type", "?")
                ts = meta.get("timestamp_utc", "")
                round_n = meta.get("round")
                title = f"{path.name} — {author} | {file_type}"
                if round_n:
                    title += f" | rodada {round_n}"
                if ts:
                    title += f" | {ts}"

                # Campos semânticos (apenas para 99_decisao_final)
                sem_info = ""
                if file_type == "decisao_final":
                    has_crit = meta.get("has_critical_alert")
                    has_dil = meta.get("has_dilemma")
                    overruled = meta.get("mycroft_overruled")
                    if has_crit is not None:
                        cor = "red" if has_crit else "green"
                        sem_info += f"[{cor}]Alerta crítico: {has_crit}[/{cor}]  "
                    if has_dil is not None:
                        sem_info += f"Dilema: {has_dil}  "
                    if overruled is not None:
                        cor = "yellow" if overruled else "green"
                        sem_info += f"[{cor}]Overrule: {overruled}[/{cor}]"

                body = post.content.strip()
                preview = body[:600] + ("…" if len(body) > 600 else "")
                content_str = (sem_info + "\n\n" if sem_info else "") + preview

                console.print(Panel(content_str, title=title, border_style="dim"))
            except Exception as e:
                console.print(f"[red]Erro ao ler {path.name}: {e}[/red]")
