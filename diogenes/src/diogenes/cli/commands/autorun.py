"""cli/commands/autorun.py — diogenes autorun

Piloto automático ("auto-Lestrade"): roda o ciclo de ponta a ponta sem paradas
manuais, próprio para execução não assistida (noturna). Auto-resolve as pausas
internas (alerta crítico de Watson, completude do Sherlock), roda o Motor de
Saída e **para antes do seal** — a chancela final imutável fica para revisão
humana. Cada invocação cria um ciclo novo (igual ao `start`).

Com --auto-seal: se o Motor de Saída confirmar o documento LIMPO (sem
ocorrências), o ciclo é chancelado automaticamente. Bloqueado em dev_mode.
"""
from __future__ import annotations

import hashlib
import shutil
import time
import webbrowser
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

# Pausa por fallback determinístico (LLM indisponível): número máximo de
# retomadas automáticas e cooldown entre elas — dá tempo ao ChatTCU recuperar
# antes de re-executar a fase. Esgotadas as retomadas, o ciclo permanece
# PAUSADO_LESTRADE sem seal; retomar de manhã com `diogenes resume`.
_MAX_RETOMADAS_FALLBACK = 2
_FALLBACK_RETRY_COOLDOWN_S = 300


@app.command()
def autorun(
    module: str = typer.Option(..., "--module", "-m", help="ID do módulo (ex: MOD_010)"),
    activity: int = typer.Option(..., "--activity", "-a", help="1 = Validação | 2 = Revalidação"),
    delivery: str | None = typer.Option(
        None, "--delivery",
        help="Pasta da entrega preparada. Default: workspace/input/<module>.",
    ),
    auto_seal: bool = typer.Option(
        False, "--auto-seal",
        help="Se o Motor de Saída confirmar LIMPO, chancela automaticamente. Bloqueado em dev_mode.",
    ),
    reuse_watson_from: str | None = typer.Option(
        None, "--reuse-watson-from",
        help=(
            "Cycle ID anterior do qual reaproveitar checkpoints de análise Watson. "
            "Copia apenas checkpoints de arquivos com SHA-256 idêntico — arquivos "
            "alterados são reanalisados normalmente."
        ),
    ),
) -> None:
    """Executa o ciclo completo sem paradas (auto-Lestrade).

    Por padrão para antes do seal (revisar manualmente com `diogenes seal`).
    Com --auto-seal, chancela automaticamente se o documento sair LIMPO.
    """
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

    # ── 1b. Reuso de checkpoints Watson de ciclo anterior (opcional) ─────────
    if reuse_watson_from:
        copiados, ignorados = _reusar_checkpoints_watson(
            cfg.workspace.path, manifest, reuse_watson_from
        )
        display.passo_ok(
            f"Checkpoints Watson reaproveitados de {reuse_watson_from}: "
            f"{copiados} arquivo(s) (sha idêntico); {ignorados} serão reanalisados."
        )

    _abrir_painel(cfg.workspace.path, cycle)

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

    try:
        from diogenes.reports.render_html import atualizar_report_html
        atualizar_report_html(cycle, cfg.workspace.path)
    except Exception:
        pass

    # ── 4b. Auto-seal (opcional) ─────────────────────────────────────────────
    if auto_seal:
        if cfg.dev_mode:
            display.aviso("--auto-seal ignorado: DIOGENES_DEV_MODE=true bloqueia seal.")
        elif not report.documento_limpo:
            display.aviso(
                "--auto-seal ignorado: documento com ocorrências — chancela manual obrigatória."
            )
        else:
            now_seal = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            audit.seal_cycle(cycle, "LIMPO", now_seal)
            try:
                from diogenes.reports.render_html import atualizar_report_html as _ahr
                _ahr(cycle, cfg.workspace.path)
            except Exception:
                pass
            display.passo_ok(f"Chancela automática registrada: ENCERRADO_CHANCELADO [{now_seal}]")

    # ── 5. Fase de Entrega (gera os entregáveis; não bloqueia o seal) ─────────
    display.passo_ok("Acionando Fase de Entrega...")
    try:
        from diogenes.orchestrator.entrega import executar_entrega
        entrega = executar_entrega(cycle, rodar_qa=True, with_assets=True)
        display.passo_ok(
            f"Fase de Entrega: {entrega.total_artefatos} artefato(s) em {entrega.entrega_dir}"
        )
        for av in entrega.avisos[:6]:
            display.aviso(av)
    except Exception as e:  # noqa: BLE001
        display.aviso(f"Fase de Entrega não concluída ({type(e).__name__}: {e}) — seguir manualmente com `diogenes deliver`.")

    _resumo_final(audit, cycle)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolver_pausas(
    orq: Orchestrator, audit: AuditIndex, manifest: CycleManifest, resultado: str
) -> str:
    """Auto-resolve as pausas internas do ciclo até obter o output ou estado terminal.

    Enquanto o orquestrador devolve "" (pausa), relê o status e retoma:
      - AGUARDANDO_DECISAO_LESTRADE_ALERTA → retomar_apos_alerta
      - AGUARDANDO_COMPLETUDE             → retomar_apos_completude (rede de segurança)
      - PAUSADO_LESTRADE com marker de fallback → cooldown + retomar_apos_fallback
        (até _MAX_RETOMADAS_FALLBACK vezes; depois o ciclo permanece pausado, SEM seal)
    Qualquer outro estado encerra o loop (situação inesperada).
    """
    iteracoes = 0
    retomadas_fallback = 0
    while resultado == "" and iteracoes < _MAX_RETOMADAS:
        record = audit.get_cycle(manifest.cycle_id)
        status = record["status"] if record else "?"
        if status == CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value:
            display.aviso("Alerta crítico de Watson — autorizando automaticamente (auto-Lestrade).")
            resultado = orq.retomar_apos_alerta(manifest)
        elif status == CycleState.AGUARDANDO_COMPLETUDE.value:
            display.aviso("Completude do Sherlock insuficiente — retomando automaticamente.")
            resultado = orq.retomar_apos_completude(manifest)
        elif (status == CycleState.PAUSADO_LESTRADE.value
              and orq.tem_fallback_pendente() is not None):
            if retomadas_fallback >= _MAX_RETOMADAS_FALLBACK:
                display.aviso(
                    "Fallback determinístico persistente — retomadas automáticas esgotadas. "
                    f"Ciclo permanece pausado; de manhã: diogenes resume --cycle {manifest.cycle_id}"
                )
                break
            retomadas_fallback += 1
            display.aviso(
                f"Agente em fallback determinístico (LLM indisponível) — aguardando "
                f"{_FALLBACK_RETRY_COOLDOWN_S}s e retomando a fase "
                f"({retomadas_fallback}/{_MAX_RETOMADAS_FALLBACK})."
            )
            time.sleep(_FALLBACK_RETRY_COOLDOWN_S)
            resultado = orq.retomar_apos_fallback(manifest)
        else:
            break
        iteracoes += 1
    return resultado


def _sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _reusar_checkpoints_watson(
    workspace: Path, manifest: CycleManifest, src_cycle: str
) -> tuple[int, int]:
    """
    Copia para o ciclo novo os checkpoints Watson do ciclo `src_cycle` cujos
    arquivos de input têm SHA-256 idêntico ao do manifesto atual. Evita re-rodar
    horas de análise por arquivo quando o pacote de entrega não mudou.
    Retorna (copiados, ignorados).
    """
    from diogenes.orchestrator.orchestrator import _watson_ckpt_path

    src_dir = workspace / "cycles" / src_cycle
    src_ckpt = src_dir / "_runtime" / "watson_checkpoints"
    src_inputs = src_dir / "inputs"
    if not src_ckpt.is_dir():
        display.aviso(
            f"--reuse-watson-from: ciclo '{src_cycle}' sem watson_checkpoints — ignorado."
        )
        return 0, 0

    dst_ckpt = workspace / "cycles" / manifest.cycle_id / "_runtime" / "watson_checkpoints"
    dst_ckpt.mkdir(parents=True, exist_ok=True)

    copiados = 0
    ignorados = 0
    for fi in manifest.input_files:
        if fi.categoria != "analisavel":
            continue
        ckpt_origem = _watson_ckpt_path(src_ckpt, fi.rel_path)
        arquivo_antigo = src_inputs / fi.rel_path
        if not ckpt_origem.exists() or not arquivo_antigo.exists():
            ignorados += 1
            continue
        if fi.sha256 and _sha256_arquivo(arquivo_antigo) != fi.sha256:
            ignorados += 1   # conteúdo mudou — reanalisar
            continue
        shutil.copy2(ckpt_origem, _watson_ckpt_path(dst_ckpt, fi.rel_path))
        copiados += 1
    return copiados, ignorados


def _abrir_painel(workspace: Path, cycle: str) -> None:
    """Gera o HTML inicial do painel e abre no browser (best-effort)."""
    try:
        from diogenes.reports.cycle_report import build_report
        from diogenes.reports.render_html import render_html

        data = build_report(cycle, workspace)
        html = render_html(data)
        html_path = workspace / "cycles" / cycle / "report.html"
        html_path.write_text(html, encoding="utf-8")
        url = html_path.resolve().as_uri()
        display.console.print(f"  [dim]Painel:[/dim] {url}")
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass


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
