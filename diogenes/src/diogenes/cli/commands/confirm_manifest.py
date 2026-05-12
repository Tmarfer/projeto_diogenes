"""cli/commands/confirm_manifest.py — diogenes confirm-manifest"""
from __future__ import annotations
from datetime import datetime, timezone
import typer
from diogenes.cli import display
from diogenes.config import get_config, ConfigError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.manifest import update_manifesto_confirmado
from diogenes.orchestrator.states import CycleState
from diogenes.orchestrator.orchestrator import Orchestrator

app = typer.Typer()

@app.command(name="confirm-manifest")
def confirm_manifest(
    cycle: str = typer.Option(..., "--cycle", "-c"),
) -> None:
    """Confirma o manifesto e aciona o Orquestrador."""
    try:
        cfg = get_config()
    except ConfigError as e:
        display.erro(str(e)); raise typer.Exit(1)

    audit = AuditIndex(cfg.workspace.path)
    record = audit.get_cycle(cycle)
    if record is None:
        display.erro(f"Ciclo '{cycle}' não encontrado."); raise typer.Exit(1)

    if record["status"] != CycleState.PREPARADO.value:
        display.erro(
            f"Ciclo '{cycle}' está em '{record['status']}', não PREPARADO."
        ); raise typer.Exit(1)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_path = cfg.workspace.path / "cycles" / cycle / "manifest.md"
    if manifest_path.exists():
        update_manifesto_confirmado(manifest_path, now_utc)

    audit.update_status(cycle, CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO.value)
    display.passo_ok(f"Manifesto confirmado: {cycle}")
    display.passo_ok("Acionando Orquestrador...")

    # Reconstruir CycleManifest a partir do arquivo
    import frontmatter as fm
    from diogenes.models import CycleManifest, InputFileInfo
    from pathlib import Path

    post = fm.load(str(manifest_path))
    # Manifesto simplificado para Sprint 2 — Sprint 3 lerá campos completos
    cycle_dir = cfg.workspace.path / "cycles" / cycle
    inputs_dir = cycle_dir / "inputs"
    input_files = [
        InputFileInfo(
            name=p.name, extension=p.suffix.lower(),
            size_bytes=p.stat().st_size, sha256="",
            rel_path=p.relative_to(inputs_dir),
        )
        for p in sorted(inputs_dir.rglob("*")) if p.is_file()
    ]
    manifest = CycleManifest(
        cycle_id=cycle,
        module_id=record["module_id"],
        activity=int(record["activity"]),
        opened_at_utc=record["opened_at_utc"],
        is_sigilo_module=record.get("is_sigilo_module", "false") == "true",
        input_files=input_files,
        package_hash="",
        git_commit=record.get("git_commit", ""),
        diogenes_version=record.get("diogenes_version", ""),
        python_version="",
        openai_version="",
        cycle_num=1,
    )

    try:
        orq = Orchestrator(cycle)
        resultado = orq.executar(manifest)

        if resultado and resultado != "":
            display.passo_ok(f"Ciclo concluído. Relatório gerado em: {resultado}")
            display.passo_ok(f"Próximo: diogenes verify-output --cycle {cycle}")
            return
        if resultado == "":
            # Pausa ou aguardando próximo sprint
            record2 = audit.get_cycle(cycle)
            status = record2["status"] if record2 else "?"
            if status == CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value:
                display.aviso(
                    "Alerta crítico detectado por Watson. "
                    f"Use `diogenes proceed --cycle {cycle}` para autorizar ou "
                    f"`diogenes pause --cycle {cycle}` para pausar."
                )
            else:
                display.passo_ok(f"Fase Watson concluída. Status: {status}")
                display.aviso(
                    "Fase Sherlock será implementada no Sprint 4. "
                    f"Use `diogenes status --cycle {cycle}` para acompanhar."
                )
        else:
            display.passo_ok(f"Ciclo concluído. Output: {resultado}")

    except Exception as e:
        display.erro(f"Erro no Orquestrador: {e}")
        raise typer.Exit(1)
