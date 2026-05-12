"""cli/commands/proceed.py — diogenes proceed"""
from __future__ import annotations
import typer
import frontmatter as fm
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.orchestrator.states import CycleState
from diogenes.orchestrator.orchestrator import Orchestrator
from diogenes.models import CycleManifest, InputFileInfo

app = typer.Typer()

@app.command()
def proceed(cycle: str = typer.Option(..., "--cycle", "-c")) -> None:
    """Autoriza prosseguimento após alerta crítico de Watson."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado."); raise typer.Exit(1)

    estado_ok = CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value
    if record["status"] != estado_ok:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}', "
            f"não em AGUARDANDO_DECISAO_LESTRADE_ALERTA."
        ); raise typer.Exit(1)

    display.passo_ok("Lestrade autorizou prosseguimento. Acionando fase Sherlock...")
    manifest = _reconstruir_manifest(cfg, cycle, record)
    try:
        orq = Orchestrator(cycle)
        resultado = orq.retomar_apos_alerta(manifest)
        if resultado:
            display.passo_ok(f"Ciclo concluído. Output: {resultado}")
            display.passo_ok(f"Próximo: diogenes verify-output --cycle {cycle}")
        else:
            display.aviso("Motor de Saída não implementado. Ver Sprint 5.")
    except Exception as e:
        display.erro(f"Erro no Orquestrador: {e}"); raise typer.Exit(1)


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
