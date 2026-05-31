"""cli/commands/complete_sherlock.py — diogenes complete-sherlock"""
from __future__ import annotations

import typer

from diogenes.cli import display
from diogenes.config import ConfigError, get_config
from diogenes.models import CycleManifest, InputFileInfo
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

app = typer.Typer()


@app.command()
def complete_sherlock(cycle: str = typer.Option(..., "--cycle", "-c")) -> None:
    """Retoma ciclo em AGUARDANDO_COMPLETUDE — Sherlock output incompleto aceito como está."""
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

    estado_ok = CycleState.AGUARDANDO_COMPLETUDE.value
    if record["status"] != estado_ok:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}', "
            f"não em AGUARDANDO_COMPLETUDE."
        )
        raise typer.Exit(1)

    display.passo_ok("Retomando após completude insuficiente do Sherlock...")
    manifest = _reconstruir_manifest(cfg, cycle, record)
    try:
        orq = Orchestrator(cycle)
        resultado = orq.retomar_apos_completude(manifest)
        if resultado:
            display.passo_ok(f"Ciclo avançou para AGUARDANDO_VERIFICACAO_SAIDA.")
            display.passo_ok(f"Próximo: diogenes verify-output --cycle {cycle}")
        else:
            display.aviso(f"Use `diogenes status --cycle {cycle}` para acompanhar.")
    except Exception as e:
        display.erro(f"Erro ao retomar: {e}")
        raise typer.Exit(1) from e


def _reconstruir_manifest(cfg, cycle: str, record: dict) -> CycleManifest:
    inputs_dir = cfg.workspace.path / "cycles" / cycle / "inputs"
    files = [
        InputFileInfo(name=p.name, extension=p.suffix.lower(),
                      size_bytes=p.stat().st_size, sha256="",
                      rel_path=p.relative_to(inputs_dir))
        for p in sorted(inputs_dir.rglob("*")) if p.is_file()
    ]
    return CycleManifest(
        cycle_id=cycle, module_id=record["module_id"],
        activity=int(record["activity"]), opened_at_utc=record["opened_at_utc"],
        is_sigilo_module=record.get("is_sigilo_module", "false") == "true",
        input_files=files, package_hash="", git_commit=record.get("git_commit", ""),
        diogenes_version="", python_version="", openai_version="", cycle_num=1,
    )
