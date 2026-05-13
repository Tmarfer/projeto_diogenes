"""
motors/motor_saida.py — DVA-CBS | Projeto Diógenes
Motor de Saída — varre marcas internas antes da chancela de Lestrade.

Opera exclusivamente com regras heurísticas — sem modelo de linguagem.
Toda a lógica é auditável por leitura direta deste arquivo.

Referência normativa: RF-MV-01 a RF-MV-06 (PRD v0.1), Bloco 11 (SDD v0.1)
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

from diogenes.config import get_config
from diogenes.models import MotorSaidaReport, OcorrenciaDetectada
from diogenes.motors.exceptions import MotorSaidaError
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager


class MotorSaida:
    """
    Varre o documento de output do ciclo à procura de marcas internas
    do Departamento antes da chancela final de Lestrade.
    """

    def __init__(self) -> None:
        self._cfg = get_config()
        self._ms_cfg = self._cfg.motor_saida
        ws = Path(self._cfg.workspace.path)
        self._audit = AuditIndex(ws)
        self._wm = WorkspaceManager(ws)

        # Pré-compilar expressões regulares (performance + detectar erros cedo)
        self._regex_cargos = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in self._ms_cfg.padroes_cargo_identificador
        ]
        self._regex_cycle_id = re.compile(self._ms_cfg.regex_cycle_id)

    def verificar(self, cycle_id: str) -> MotorSaidaReport:
        """
        Executa a varredura sobre o documento de output do ciclo.

        Levanta:
            MotorSaidaError: estado inválido ou documento não encontrado.
        """
        record = self._audit.get_cycle(cycle_id)
        if record is None:
            raise MotorSaidaError(f"Ciclo '{cycle_id}' não encontrado no audit_index.")

        if record["status"] != CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value:
            raise MotorSaidaError(
                f"Ciclo '{cycle_id}' está em '{record['status']}', "
                f"não AGUARDANDO_VERIFICACAO_SAIDA. "
                f"Use `diogenes status --cycle {cycle_id}` para verificar."
            )

        cycle_dir = self._wm.get_cycle_dir(cycle_id)
        output_dir = cycle_dir / "output"
        outputs = sorted(output_dir.glob("relatorio_*.md"))
        if not outputs:
            raise MotorSaidaError(
                f"Nenhum documento de output em '{output_dir}'. "
                f"O ciclo pode estar em estado inconsistente."
            )
        doc_path = outputs[0]

        encoding = self._cfg.persistencia.encoding
        doc_content = doc_path.read_text(encoding=encoding)
        doc_hash = "sha256:" + hashlib.sha256(doc_content.encode("utf-8")).hexdigest()

        ocorrencias = self._varrer(doc_content)

        now_utc = datetime.now(UTC).strftime(
            self._cfg.persistencia.timestamp_iso_format
        )
        report = MotorSaidaReport(
            cycle_id=cycle_id,
            doc_path=doc_path,
            doc_hash=doc_hash,
            ocorrencias=ocorrencias,
            verificado_em_utc=now_utc,
            total_ocorrencias=len(ocorrencias),
            documento_limpo=len(ocorrencias) == 0,
        )

        # Registrar invocação no audit_index
        self._audit.update_motor_saida(
            cycle_id=cycle_id,
            invocado_at_utc=now_utc,
            occurrences=len(ocorrencias),
            output_hash=doc_hash,
        )

        # Se limpo, avançar para AGUARDANDO_CHANCELA_LESTRADE
        if report.documento_limpo:
            self._audit.update_status(
                cycle_id, CycleState.AGUARDANDO_CHANCELA_LESTRADE.value
            )

        return report

    # ── Varredura ────────────────────────────────────────────

    def _varrer(self, content: str) -> list[OcorrenciaDetectada]:
        linhas = content.splitlines()
        total = len(linhas)
        ocorrencias: list[OcorrenciaDetectada] = []

        for i, linha in enumerate(linhas, start=1):
            posicao = _classificar_posicao(i, total)

            # Cat. 1: nomes dos agentes
            for padrao in self._ms_cfg.padroes_agentes:
                if padrao.lower() in linha.lower():
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=i, categoria="NOME_AGENTE",
                        padrao_detectado=padrao,
                        contexto=_extrair_contexto(linhas, i - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=None,
                    ))

            # Cat. 2: cargos em contexto identificador (regex)
            for regex in self._regex_cargos:
                m = regex.search(linha)
                if m:
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=i, categoria="CARGO_IDENTIFICADOR",
                        padrao_detectado=m.group(0),
                        contexto=_extrair_contexto(linhas, i - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=None,
                    ))

            # Cat. 3: estruturas internas
            for padrao in self._ms_cfg.padroes_estruturas_internas:
                if padrao.lower() in linha.lower():
                    classif = None
                    if padrao.lower() == "projeto diógenes" and posicao == "CABECALHO":
                        classif = "CABECALHO_INSTITUCIONAL"
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=i, categoria="ESTRUTURA_INTERNA",
                        padrao_detectado=padrao,
                        contexto=_extrair_contexto(linhas, i - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=classif,
                    ))

            # Cat. 4: cycle_id no corpo (RODAPE é legítimo)
            for match in self._regex_cycle_id.findall(linha):
                classif = "RODAPE_RASTREABILIDADE" if posicao == "RODAPE" else None
                ocorrencias.append(OcorrenciaDetectada(
                    linha=i, categoria="CYCLE_ID",
                    padrao_detectado=match,
                    contexto=_extrair_contexto(linhas, i - 1),
                    posicao_documento=posicao,
                    classificacao_automatica=classif,
                ))

        return ocorrencias


# ── Helpers puros ─────────────────────────────────────────────────────────

def _classificar_posicao(num_linha: int, total_linhas: int) -> str:
    if num_linha <= 5:
        return "CABECALHO"
    if num_linha >= total_linhas - 9:
        return "RODAPE"
    return "CORPO"


def _extrair_contexto(linhas: list[str], idx: int) -> str:
    """Extrai 2 linhas antes e depois da ocorrência para contexto."""
    inicio = max(0, idx - 2)
    fim = min(len(linhas), idx + 3)
    return "\n".join(
        f"{'>>>' if i == idx - inicio else '   '} {linha}"
        for i, linha in enumerate(linhas[inicio:fim])
    )
