"""
cli/commands/bench/app.py — DVA-CBS | Projeto Diógenes
Typer sub-app para 'diogenes bench'.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

bench_app = typer.Typer(
    name="bench",
    help="Bancada cirúrgica — testes isolados de agentes sem ciclo completo.",
    no_args_is_help=True,
)

console = Console()


@bench_app.command(name="preview")
def preview(
    agent: str = typer.Argument(..., help="ID do agente (watson, sherlock, mycroft)"),
    call_type: Optional[str] = typer.Option(None, "--call-type", "-c", help="call_type para extrair seção do heartbeat"),
    fixture: Optional[str] = typer.Option(None, "--fixture", "-f", help="Caminho para fixture .md"),
    user_prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="User prompt inline (alternativa a --fixture)"),
) -> None:
    """Monta e exibe o prompt sem chamar LLM. Mostra tamanho e redução do heartbeat."""
    from diogenes.bench.core import build_prompt

    prompt_text = _resolve_user_prompt(fixture, user_prompt)
    bundle = build_prompt(agent, prompt_text, call_type=call_type)

    table = Table(title=f"Prompt Preview — {agent}", show_lines=True)
    table.add_column("Campo", style="bold")
    table.add_column("Valor")

    table.add_row("Agent", bundle.agent_id)
    table.add_row("Call Type", bundle.call_type or "(nenhum)")
    table.add_row("Model", bundle.model)
    table.add_row("System chars", f"{bundle.system_chars:,}")
    table.add_row("User chars", f"{bundle.user_chars:,}")
    table.add_row("Estimated tokens", f"{bundle.estimated_tokens:,}")
    table.add_row("Heartbeat full", f"{bundle.heartbeat_full_chars:,} chars")
    table.add_row("Heartbeat used", f"{bundle.heartbeat_used_chars:,} chars")
    table.add_row("Heartbeat reduction", f"{bundle.heartbeat_reduction_pct}%")

    console.print(table)
    console.print(f"\n[dim]System prompt (first 500 chars):[/dim]\n{bundle.system_prompt[:500]}...")


@bench_app.command(name="call")
def call(
    agent: str = typer.Argument(..., help="ID do agente (watson, sherlock, mycroft)"),
    call_type: Optional[str] = typer.Option(None, "--call-type", "-c", help="call_type do heartbeat"),
    fixture: Optional[str] = typer.Option(None, "--fixture", "-f", help="Caminho para fixture .md"),
    user_prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="User prompt inline"),
    model_override: Optional[str] = typer.Option(None, "--model", "-m", help="Modelo alternativo"),
    timeout: int = typer.Option(180, "--timeout", "-t", help="Timeout em segundos"),
    no_raciocinio: bool = typer.Option(False, "--no-raciocinio", help="Desabilitar raciocinio (thinking)"),
) -> None:
    """Chama ChatTCU com fixture isolada. Imprime resposta e metadados."""
    from diogenes.bench.core import build_prompt
    from diogenes.llm.chattcu import ChatTCUClient

    prompt_text = _resolve_user_prompt(fixture, user_prompt)
    bundle = build_prompt(agent, prompt_text, call_type=call_type, model_override=model_override)

    console.print(f"[bold]Chamando ChatTCU...[/bold] modelo={bundle.model}, tokens≈{bundle.estimated_tokens:,}")

    client = ChatTCUClient()
    t0 = time.time()
    resp = client.completar(
        prompt_sistema=bundle.system_prompt,
        prompt_usuario=bundle.user_prompt,
        modelo=bundle.model,
        timeout=timeout,
        raciocinio=not no_raciocinio,
    )
    duration = time.time() - t0

    response_text = resp.get("response", "")
    console.print(Panel(
        f"[green]OK[/green] em {duration:.1f}s | "
        f"Resposta: {len(response_text):,} chars (~{len(response_text)//4:,} tokens)\n"
        f"chat_id: {resp.get('chat_id', 'N/A')}",
        title="Resultado",
    ))
    console.print(f"\n{response_text[:3000]}")
    if len(response_text) > 3000:
        console.print(f"\n[dim]... ({len(response_text) - 3000} chars truncados)[/dim]")


@bench_app.command(name="validate-models")
def validate_models() -> None:
    """Valida modelos configurados contra o catálogo ChatTCU (sem chamar LLM)."""
    from diogenes.bench.core import validate_models as _validate

    console.print("[bold]Validando modelos...[/bold]")
    try:
        results = _validate()
    except Exception as e:
        console.print(f"[red]Erro:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title="Validação de Modelos")
    table.add_column("Agente", style="bold")
    table.add_column("Modelo")
    table.add_column("Status")
    table.add_column("Fornecedora")

    all_ok = True
    for r in results:
        status = "[green]✓ disponível[/green]" if r["available"] else "[red]✗ indisponível[/red]"
        if not r["available"]:
            all_ok = False
        table.add_row(r["agent_id"], r["modelo"], status, r.get("fornecedora") or "—")

    console.print(table)
    if not all_ok:
        console.print("[red]⚠ Alguns modelos não estão disponíveis no ChatTCU.[/red]")
        raise typer.Exit(1)
    console.print("[green]Todos os modelos validados.[/green]")


@bench_app.command(name="smoke")
def smoke(
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout por chamada"),
) -> None:
    """Smoke test: 1 chamada mínima por agente. Valida conectividade e modelos."""
    from diogenes.bench.core import build_prompt, load_agents_spec
    from diogenes.llm.chattcu import ChatTCUClient

    specs = load_agents_spec()
    client = ChatTCUClient()
    minimal_prompt = "Responda apenas: OK"

    table = Table(title="Smoke Test")
    table.add_column("Agente")
    table.add_column("Modelo")
    table.add_column("Status")
    table.add_column("Duração")

    for agent_id in sorted(specs.keys()):
        bundle = build_prompt(agent_id, minimal_prompt)
        t0 = time.time()
        try:
            resp = client.completar(
                prompt_sistema="Responda de forma ultra-breve.",
                prompt_usuario=minimal_prompt,
                modelo=bundle.model,
                timeout=timeout,
                raciocinio=False,
            )
            duration = time.time() - t0
            table.add_row(
                agent_id, bundle.model,
                "[green]✓ OK[/green]",
                f"{duration:.1f}s",
            )
        except Exception as e:
            duration = time.time() - t0
            table.add_row(
                agent_id, bundle.model,
                f"[red]✗ {str(e)[:50]}[/red]",
                f"{duration:.1f}s",
            )

    console.print(table)


def _resolve_user_prompt(fixture: str | None, user_prompt: str | None) -> str:
    """Resolve user prompt from fixture path or inline text."""
    if fixture:
        path = Path(fixture).expanduser().resolve()
        if not path.is_file():
            console.print(f"[red]Fixture não encontrada:[/red] {path}")
            raise typer.Exit(1)
        return path.read_text(encoding="utf-8")
    if user_prompt:
        return user_prompt
    console.print("[red]Informe --fixture ou --prompt[/red]")
    raise typer.Exit(1)
