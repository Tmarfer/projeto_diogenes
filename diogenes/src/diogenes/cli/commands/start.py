"""cli/commands/start.py — diogenes start"""
from __future__ import annotations
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.motors.motor_start import MotorStart
from diogenes.motors.exceptions import MotorStartError

app = typer.Typer()

@app.command()
def start(
    module: str  = typer.Option(..., "--module",   "-m", help="ID do módulo (ex: MOD_010)"),
    activity: int = typer.Option(..., "--activity", "-a", help="1 = Validação | 2 = Revalidação"),
) -> None:
    """Abre novo ciclo de análise (Motor de Start)."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e))
        raise typer.Exit(1)

    display.cabecalho_motor_start(module, activity)

    try:
        motor = MotorStart(cfg)
        manifest = motor.run(module_id=module, activity=activity)
    except MotorStartError as e:
        display.passo_erro(str(e))
        raise typer.Exit(1)
    except Exception as e:
        display.erro(f"Erro inesperado: {e}")
        raise typer.Exit(1)

    cycle_dir = cfg.workspace.path / "cycles" / manifest.cycle_id
    display.passo_ok(f"Inputs verificados: {len(manifest.input_files)} arquivos")
    display.passo_ok("Hashes SHA-256 calculados e verificados")
    display.passo_ok("Diretório de trabalho criado")
    display.passo_ok("Manifesto gerado")
    display.passo_ok(f"Ciclo registrado no audit_index [PREPARADO]")
    display.resultado_motor_start(
        manifest.cycle_id,
        cycle_dir / "manifest.md",
        len(manifest.input_files),
    )
