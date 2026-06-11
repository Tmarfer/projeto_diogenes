"""
motors/motor_entrega.py — DVA-CBS | Projeto Diógenes

Motor de Entrega — gera os entregáveis institucionais (dashboard HTML, apêndice
e relatórios DOCX, ficha síntese) a partir do PacoteEntrega canônico. Roda após o
Motor de Saída, sobre o relatório já higienizado.

DETERMINÍSTICO — não usa modelo de linguagem (Artigo 5, espelha o Motor de Saída).
O agente (Mycroft) apenas (a) localiza os dados via mapa de extração e (b) avalia
os artefatos gerados; a geração em si é heurística e auditável por leitura.

Cada artefato é gerado em try/except isolado: a falta de uma dependência ou a
falha de um gerador não derruba a entrega inteira — registra aviso e segue.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from diogenes.config import get_config
from diogenes.delivery import builders
from diogenes.delivery import pacote as pacote_mod
from diogenes.models import ArtefatoEntrega, MotorEntregaReport, PacoteEntrega
from diogenes.motors.exceptions import MotorSaidaError
from diogenes.motors.motor_saida import sanitizar_delivery_text
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager

logger = logging.getLogger(__name__)

NOME_DASHBOARD = "Dashboard.html"
NOME_MANIFESTO = "entrega_manifesto.json"


class MotorEntrega:
    def __init__(self) -> None:
        self._cfg = get_config()
        ws = Path(self._cfg.workspace.path)
        self._audit = AuditIndex(ws)
        self._wm = WorkspaceManager(ws)

    def gerar(self, cycle_id: str, *, with_assets: bool = True) -> MotorEntregaReport:
        record = self._audit.get_cycle(cycle_id)
        if record is None:
            raise MotorSaidaError(f"Ciclo '{cycle_id}' não encontrado no audit_index.")

        cycle_dir = self._wm.get_cycle_dir(cycle_id)
        module_id = record.get("module_id", cycle_id)
        try:
            activity = int(record.get("activity", "1") or "1")
        except ValueError:
            activity = 1

        pacote, avisos = pacote_mod.montar_pacote(cycle_dir, module_id, activity)

        entrega_dir = cycle_dir / "output" / "entrega"
        entrega_dir.mkdir(parents=True, exist_ok=True)

        artefatos: list[ArtefatoEntrega] = []
        artefatos.append(self._gerar_dashboard(pacote, entrega_dir, avisos))
        artefatos.append(self._gerar_apendice(pacote, entrega_dir, avisos))
        artefatos.append(self._gerar_narrativo(pacote, entrega_dir, avisos))
        artefatos.append(self._gerar_consolidado(pacote, entrega_dir, avisos))
        # Pré-atendimento sai sempre — sem a ata, o builder omite o Bloco 1 e
        # preserva o batimento das inconsistências (o aviso da ata já foi registrado).
        artefatos.append(self._gerar_pre_atendimento(pacote, entrega_dir, avisos))
        artefatos.extend(self._gerar_ficha(pacote, entrega_dir, with_assets, avisos))

        artefatos = [a for a in artefatos if a is not None]
        now_utc = datetime.now(UTC).strftime(self._cfg.persistencia.timestamp_iso_format)

        report = MotorEntregaReport(
            cycle_id=cycle_id,
            gerado_em_utc=now_utc,
            artefatos=artefatos,
            total_artefatos=sum(1 for a in artefatos if a.ok),
            entrega_dir=entrega_dir,
            avisos=avisos,
        )
        self._escrever_manifesto(entrega_dir, report, pacote)
        self._registrar_audit(cycle_id, now_utc, report)
        return report

    # ── geradores individuais ────────────────────────────────────

    def _gerar_dashboard(self, p: PacoteEntrega, d: Path, avisos: list[str]) -> ArtefatoEntrega:
        from diogenes.delivery.dashboard import gerar_dashboard_html
        path = d / NOME_DASHBOARD
        return self._tentar(
            "dashboard", path, avisos,
            lambda: path.write_text(gerar_dashboard_html(p), encoding="utf-8"),
        )

    def _gerar_apendice(self, p: PacoteEntrega, d: Path, avisos: list[str]) -> ArtefatoEntrega:
        path = d / f"Apendice_Modulo{p.modulo}.docx"
        return self._tentar(
            "apendice", path, avisos,
            lambda: builders.gerar_apendice_docx(p, path),
        )

    def _gerar_narrativo(self, p: PacoteEntrega, d: Path, avisos: list[str]) -> ArtefatoEntrega:
        path = d / f"Relatorio_Narrativo_Modulo{p.modulo}.docx"
        return self._tentar(
            "narrativo", path, avisos,
            lambda: builders.gerar_relatorio_docx(
                sanitizar_delivery_text(builders.montar_markdown_narrativo(p)), path,
                titulo=f"Relatório Narrativo — Módulo {p.modulo}", modulo=p.modulo, versao=p.versao),
        )

    def _gerar_consolidado(self, p: PacoteEntrega, d: Path, avisos: list[str]) -> ArtefatoEntrega:
        path = d / f"Relatorio_Consolidado_Modulo{p.modulo}.docx"
        if not p.relatorio_markdown.strip():
            avisos.append("Relatório consolidado vazio — DOCX consolidado não gerado.")
            return ArtefatoEntrega("consolidado", path.name, path, "", 0, False, "markdown vazio")
        return self._tentar(
            "consolidado", path, avisos,
            lambda: builders.gerar_relatorio_docx(
                sanitizar_delivery_text(p.relatorio_markdown), path,
                titulo=f"Relatório Consolidado — Módulo {p.modulo}", modulo=p.modulo, versao=p.versao),
        )

    def _gerar_pre_atendimento(self, p: PacoteEntrega, d: Path, avisos: list[str]) -> ArtefatoEntrega:
        path = d / f"Relatorio_Pre_Atendimento_Modulo{p.modulo}.docx"
        return self._tentar(
            "pre_atendimento", path, avisos,
            lambda: builders.gerar_relatorio_docx(
                sanitizar_delivery_text(builders.montar_markdown_pre_atendimento(p)), path,
                titulo=f"Relatório de Pré-Atendimento — Módulo {p.modulo}", modulo=p.modulo, versao=p.versao),
        )

    def _gerar_ficha(self, p: PacoteEntrega, d: Path, with_assets: bool,
                     avisos: list[str]) -> list[ArtefatoEntrega]:
        html_path = d / f"ficha_sintese_modulo{p.modulo}.html"
        art_html = self._tentar(
            "ficha", html_path, avisos,
            lambda: html_path.write_text(builders.gerar_ficha_html(p), encoding="utf-8"),
        )
        out = [art_html]
        if with_assets and art_html.ok:
            try:
                res = builders.gerar_ficha_assets(html_path, d)
                if res.get("pdf"):
                    out.append(self._artefato("ficha", Path(res["pdf"]), True))
                for png in res.get("pngs", []):
                    out.append(self._artefato("ficha", Path(png), True))
                if not res.get("ok"):
                    avisos.append("Ficha síntese: PDF/PNG não gerados (Playwright/Chromium ausente?). HTML disponível.")
            except Exception as exc:  # noqa: BLE001
                avisos.append(f"Ficha síntese PDF/PNG falhou ({type(exc).__name__}): HTML disponível.")
        return out

    # ── infraestrutura ──────────────────────────────────────────

    def _tentar(self, tipo: str, path: Path, avisos: list[str], fn: Any) -> ArtefatoEntrega:
        try:
            fn()
            return self._artefato(tipo, path, True)
        except ImportError as exc:
            msg = f"{tipo}: dependência ausente ({exc.name}) — artefato não gerado."
            avisos.append(msg)
            logger.warning(msg)
            return ArtefatoEntrega(tipo, path.name, path, "", 0, False, msg)
        except Exception as exc:  # noqa: BLE001
            msg = f"{tipo}: falha na geração ({type(exc).__name__}: {exc})."
            avisos.append(msg)
            logger.warning(msg)
            return ArtefatoEntrega(tipo, path.name, path, "", 0, False, msg)

    @staticmethod
    def _artefato(tipo: str, path: Path, ok: bool) -> ArtefatoEntrega:
        if path.exists():
            data = path.read_bytes()
            return ArtefatoEntrega(
                tipo=tipo, nome=path.name, path=path,
                hash="sha256:" + hashlib.sha256(data).hexdigest(),
                bytes=len(data), ok=ok,
            )
        return ArtefatoEntrega(tipo, path.name, path, "", 0, False, "arquivo não encontrado")

    def _escrever_manifesto(self, d: Path, report: MotorEntregaReport, p: PacoteEntrega) -> None:
        """Manifesto JSON dos artefatos — insumo para Mycroft.avaliar_entrega (QA)."""
        manifesto = {
            "cycle_id": report.cycle_id,
            "modulo": p.modulo,
            "modulo_nome": p.modulo_nome,
            "gerado_em_utc": report.gerado_em_utc,
            "veredito": p.veredito,
            "contagem": {
                "ocorrencias": len(p.ocorrencias),
                "blocos_financeiros": len(p.blocos_financeiros),
                "valores_agregados": len(p.valores_agregados),
                "tem_sensibilidade": p.sensibilidade_redutor is not None,
            },
            "artefatos": [
                {"tipo": a.tipo, "nome": a.nome, "bytes": a.bytes, "ok": a.ok,
                 "hash": a.hash, "nota": a.nota}
                for a in report.artefatos
            ],
            "avisos": report.avisos,
        }
        (d / NOME_MANIFESTO).write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")

    def _registrar_audit(self, cycle_id: str, now_utc: str, report: MotorEntregaReport) -> None:
        try:
            self._audit.update_entrega(
                cycle_id=cycle_id,
                invocado_at_utc=now_utc,
                artefatos=report.total_artefatos,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao registrar entrega no audit_index: %s", exc)
