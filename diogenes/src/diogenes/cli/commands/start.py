"""cli/commands/start.py — diogenes start"""
from __future__ import annotations

from pathlib import Path

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.motors.exceptions import MotorStartError
from diogenes.motors.motor_start import MotorStart

app = typer.Typer()

@app.command()
def start(
    module: str  = typer.Option(..., "--module",   "-m", help="ID do módulo (ex: MOD_010)"),
    activity: int = typer.Option(..., "--activity", "-a", help="1 = Validação | 2 = Revalidação"),
    delivery: str | None = typer.Option(
        None, "--delivery",
        help="Pasta da entrega preparada (ex: workspace/_teste_inputs/<modulo>/<data>). "
             "Default: workspace/input/<module>.",
    ),
) -> None:
    """Abre novo ciclo de análise (Motor de Start)."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1) from e

    display.cabecalho_motor_start(module, activity)

    delivery_dir = Path(delivery).expanduser().resolve() if delivery else None
    try:
        motor = MotorStart(cfg)
        manifest = motor.run(module_id=module, activity=activity, delivery_dir=delivery_dir)
    except MotorStartError as e:
        display.passo_erro(str(e))
        raise typer.Exit(1) from e
    except Exception as e:
        display.erro(f"Erro inesperado: {e}")
        raise typer.Exit(1) from e

    cycle_dir = cfg.workspace.path / "cycles" / manifest.cycle_id
    n_analise = sum(1 for f in manifest.input_files if f.categoria == "analisavel")
    display.passo_ok(
        f"Inputs verificados: {len(manifest.input_files)} arquivos "
        f"({n_analise} para análise)"
    )
    display.passo_ok("Hashes SHA-256 calculados e verificados")
    display.passo_ok("Diretório de trabalho criado")
    # Manifesto de entrega (best-effort): avisa mas não trava.
    if manifest.delivery_manifest_status == "AUSENTE":
        display.aviso("Manifesto de entrega ausente — ingestão por varredura direta da pasta.")
    elif manifest.delivery_manifest_status == "PRESENTE_COM_DIVERGENCIA":
        display.aviso(
            "Manifesto de entrega com divergências — ver seção "
            "'Reconciliação com Manifesto de Entrega' no manifest.md."
        )
    else:
        display.passo_ok("Manifesto de entrega reconciliado (íntegro)")
    display.passo_ok("Manifesto gerado")
    display.passo_ok("Ciclo registrado no audit_index [PREPARADO]")
    display.resultado_motor_start(
        manifest.cycle_id,
        cycle_dir / "manifest.md",
        len(manifest.input_files),
    )
