"""cli/commands/autorun.py — diogenes autorun

Piloto automático ("auto-Lestrade"): roda o ciclo de ponta a ponta sem paradas
manuais, próprio para execução não assistida (noturna). Auto-resolve as pausas
internas (alerta crítico de Watson, completude do Sherlock), roda o Motor de
Saída e **para antes do seal** — a chancela final imutável fica para revisão
humana. Cada invocação cria um ciclo novo (igual ao `start`).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.models import CycleManifest
from diogenes.motors.exceptions import MotorSaidaError, MotorStartError
from diogenes.motors.motor_saida import MotorSaida
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.manifest import update_manifesto_confirmado

app = typer.Typer()

# Limite de segurança para o loop auto-Lestrade — protege contra encadeamento
# inesperado de pausas (cada iteração resolve no máximo uma pausa do ciclo).
_MAX_RETOMADAS = 6


@app.command()
def autorun(
    module: str = typer.Option(..., "--module", "-m", help="ID do módulo (ex: MOD_010)"),
    activity: int = typer.Option(..., "--activity", "-a", help="1 = Validação | 2 = Revalidação"),
    delivery: str | None = typer.Option(
        None, "--delivery",
        help="Pasta da entrega preparada. Default: workspace/input/<module>.",
    ),
) -> None:
    """Executa o ciclo completo sem paradas (auto-Lestrade), parando antes do seal."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    display.cabecalho_motor_start(module, activity)

    # ── 1. Motor de Start ────────────────────────────────────────────────────
    delivery_dir = Path(delivery).expanduser().resolve() if delivery else None
    try:
        motor = MotorStart(cfg)
        manifest: CycleManifest = motor.run(
            module_id=module, activity=activity, delivery_dir=delivery_dir
        )
    except MotorStartError as e:
        display.passo_erro(str(e))
        raise typer.Exit(1) from e
    except Exception as e:  # noqa: BLE001
        display.erro(f"Erro inesperado no Motor de Start: {e}")
        raise typer.Exit(1) from e

    cycle = manifest.cycle_id
    n_analise = sum(1 for f in manifest.input_files if f.categoria == "analisavel")
    display.passo_ok(
        f"Inputs verificados: {len(manifest.input_files)} arquivos ({n_analise} para análise)"
    )
    display.passo_ok(f"Ciclo criado: {cycle}")

    # ── 2. Confirmação automática do manifesto ───────────────────────────────
    audit = AuditIndex(cfg.workspace.path)
    now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_path = cfg.workspace.path / "cycles" / cycle / "manifest.md"
    if manifest_path.exists():
        update_manifesto_confirmado(manifest_path, now_utc)
    audit.update_status(cycle, CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value)
    display.passo_ok("Manifesto confirmado automaticamente (auto-Lestrade)")

    # ── 3. Orquestrador + loop auto-Lestrade ─────────────────────────────────
    display.passo_ok("Acionando Orquestrador (modo não assistido)...")
    try:
        orq = Orchestrator(cycle)
        resultado = orq.executar(manifest)
        resultado = _resolver_pausas(orq, audit, manifest, resultado)
    except Exception as e:  # noqa: BLE001
        display.erro(f"Erro no Orquestrador: {e}")
        _resumo_final(audit, cycle)
        raise typer.Exit(1) from e

    if not resultado:
        display.aviso(
            "Ciclo não chegou ao output sem intervenção. "
            "Ver estado abaixo e retomar manualmente."
        )
        _resumo_final(audit, cycle)
        raise typer.Exit(1)

    display.passo_ok(f"Output gerado: {resultado}")

    # ── 4. Motor de Saída (verificação), sem seal ────────────────────────────
    display.passo_ok("Acionando Motor de Saída...")
    try:
        report = MotorSaida().verificar(cycle)
    except (MotorSaidaError, FileNotFoundError) as e:
        display.passo_erro(f"Motor de Saída falhou: {e}")
        _resumo_final(audit, cycle)
        raise typer.Exit(1) from e

    if report.documento_limpo:
        display.passo_ok("Motor de Saída: documento LIMPO")
    else:
        display.aviso(
            f"Motor de Saída: {report.total_ocorrencias} ocorrência(s) detectada(s) "
            "— requer decisão humana no seal."
        )

    _resumo_final(audit, cycle)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolver_pausas(
    orq: Orchestrator, audit: AuditIndex, manifest: CycleManifest, resultado: str
) -> str:
    """Auto-resolve as pausas internas do ciclo até obter o output ou estado terminal.

    Enquanto o orquestrador devolve "" (pausa), relê o status e retoma:
      - AGUARDANDO_DECISAO_LESTRADE_ALERTA → retomar_apos_alerta
      - AGUARDANDO_COMPLETUDE             → retomar_apos_completude (rede de segurança)
    Qualquer outro estado encerra o loop (situação inesperada).
    """
    iteracoes = 0
    while resultado == "" and iteracoes < _MAX_RETOMADAS:
        record = audit.get_cycle(manifest.cycle_id)
        status = record["status"] if record else "?"
        if status == CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value:
            display.aviso("Alerta crítico de Watson — autorizando automaticamente (auto-Lestrade).")
            resultado = orq.retomar_apos_alerta(manifest)
        elif status == CycleState.AGUARDANDO_COMPLETUDE.value:
            display.aviso("Completude do Sherlock insuficiente — retomando automaticamente.")
            resultado = orq.retomar_apos_completude(manifest)
        else:
            break
        iteracoes += 1
    return resultado


def _resumo_final(audit: AuditIndex, cycle: str) -> None:
    record = audit.get_cycle(cycle) or {}
    status = record.get("status", "?")
    display.console.print()
    display.console.print(f"  [dim]Cycle ID:[/dim] {cycle}")
    display.console.print(f"  [dim]Estado final:[/dim] {status}")
    if record.get("output_filename"):
        display.console.print(f"  [dim]Output:[/dim] {record['output_filename']}")
    display.console.print()
    if status == CycleState.AGUARDANDO_CHANCELA_LESTRADE.value:
        display.console.print(
            f"Documento LIMPO e pronto para chancela. De manhã: "
            f"[bold]diogenes seal --cycle {cycle}[/bold]"
        )
    elif status == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value:
        display.console.print(
            f"Ocorrências pendentes. De manhã: revisar e "
            f"[bold]diogenes seal --cycle {cycle} --accept-occurrences --reason \"...\"[/bold] "
            f"(ou editar e re-rodar verify-output)."
        )
    else:
        display.console.print(
            f"Acompanhe com [bold]diogenes status --cycle {cycle}[/bold]."
        )
