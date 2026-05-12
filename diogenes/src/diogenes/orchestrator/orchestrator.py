"""
orchestrator/orchestrator.py — DVA-CBS | Projeto Diógenes
Orquestrador — máquina de estados do ciclo. Ciclo completo (Sprint 4).

Sequencialidade absoluta (Art. 3): código síncrono, sem threads, sem asyncio.
Limite de duas rodadas (Art. 8): garantido por construção via MAX_RODADAS.
Referência normativa: RF-OR-01 a RF-OR-11 (PRD v0.1), Bloco 8 (SDD v0.1)
"""
from __future__ import annotations
from pathlib import Path

from diogenes.config import get_config
from diogenes.models import CycleManifest, DecisaoFinal
from diogenes.orchestrator.states import CycleState, TRANSICOES_VALIDAS, InvalidTransitionError
from diogenes.orchestrator.events import EventLogger
from diogenes.orchestrator.stranger_room import StrangerRoom
from diogenes.orchestrator.exceptions import OrchestratorError
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager
from diogenes.llm.base import get_llm_client
from diogenes.llm.exceptions import LLMCallError, LLMTimeoutError, LLMCostLimitError
from diogenes.agents.watson import WatsonAgent
from diogenes.agents.sherlock import SherlockAgent
from diogenes.agents.mycroft import MycrooftAgent


class Orchestrator:
    MAX_RODADAS = 2  # Artigo 8 da Constituição

    def __init__(self, cycle_id: str) -> None:
        self._cycle_id = cycle_id
        self._cfg = get_config()
        ws = self._cfg.workspace.path
        self._wm = WorkspaceManager(ws)
        self._cycle_dir = self._wm.get_cycle_dir(cycle_id)
        self._runtime_dir = self._cycle_dir / "_runtime"
        self._sr_dir = self._cycle_dir / "stranger_room"
        self._audit = AuditIndex(ws)
        self._events = EventLogger(self._runtime_dir, cycle_id)
        self._sr = StrangerRoom(cycle_id, self._sr_dir, self._cfg)
        self._llm = get_llm_client(cycle_id, self._runtime_dir)
        docs = Path("docs/agentes")
        self._mycroft = MycrooftAgent(
            llm=self._llm, agent_spec=self._cfg.agentes.mycroft,
            cycle_id=cycle_id, docs_dir=docs / "mycroft",
        )
        self._watson = WatsonAgent(
            llm=self._llm, agent_spec=self._cfg.agentes.watson,
            cycle_id=cycle_id, docs_dir=docs / "watson",
        )
        self._sherlock = SherlockAgent(
            llm=self._llm, agent_spec=self._cfg.agentes.sherlock,
            cycle_id=cycle_id, docs_dir=docs / "sherlock",
        )

    # ── Ponto de entrada ─────────────────────────────────────

    def executar(self, manifest: CycleManifest) -> str:
        """
        Executa o ciclo completo. Retorna caminho do output ou "" se pausado.
        """
        self._events.log("CYCLE_STARTED", details={"cycle_id": manifest.cycle_id})
        try:
            decisao_watson = self._executar_fase_watson(manifest)

            if decisao_watson.has_critical_alert:
                self._transicionar(CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA)
                self._events.log("CRITICAL_ALERT_NOTIFIED", phase="watson_integridade",
                                 details={"count": decisao_watson.critical_alerts_count})
                return ""   # CLI notifica Lestrade e aguarda proceed/pause

            return self._executar_fase_sherlock_e_consolidar(manifest)

        except LLMCostLimitError as exc:
            self._events.log("COST_LIMIT_REACHED", details={"error": str(exc)})
            raise
        except (LLMCallError, LLMTimeoutError) as exc:
            self._abortar_por_falha(exc, "ciclo")
            raise

    def retomar_apos_alerta(self, manifest: CycleManifest) -> str:
        """Chamado por `diogenes proceed` após alerta crítico de Watson."""
        self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
        self._events.log("LESTRADE_PROCEED_AUTHORIZED")
        return self._executar_fase_sherlock_e_consolidar(manifest)

    def abortar(self, razao: str) -> None:
        """Aborta o ciclo por decisão de Lestrade."""
        self._transicionar(CycleState.ABORTADO_LESTRADE)
        self._events.log("CYCLE_ABORTED", details={"razao": razao})

    # ── Fase Watson ──────────────────────────────────────────

    def _executar_fase_watson(self, manifest: CycleManifest) -> DecisaoFinal:
        fase = "watson_integridade"
        self._transicionar(CycleState.EM_EXECUCAO_WATSON)
        self._events.log("PHASE_STARTED", phase=fase, agent="watson")

        tasks = self._mycroft.definir_tasks_watson(manifest)

        inputs_dir = self._cycle_dir / "inputs"
        output_watson = self._watson.analisar(inputs_dir, manifest, tasks)
        self._sr.escrever_apresentacao(fase=fase, author="watson",
                                        content=output_watson.texto)

        rodada = 0
        while rodada < self.MAX_RODADAS:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON)
            avaliacao = self._mycroft.avaliar_watson(output_watson, fase, rodada)
            self._events.log("MYCROFT_CRITIQUE_ISSUED" if avaliacao.tipo == "QUESTIONAR"
                             else "MYCROFT_APPROVED", agent="mycroft",
                             phase=fase, details={"tipo": avaliacao.tipo, "rodada": rodada})

            if avaliacao.tipo == "APROVADO":
                break

            rodada += 1
            self._sr.escrever_critica(fase, rodada, "mycroft", avaliacao.critica)
            self._transicionar(CycleState.EM_EXECUCAO_WATSON)
            output_watson = self._watson.responder_critica(avaliacao.critica, output_watson, rodada)
            self._sr.escrever_resposta(fase, rodada, "watson", output_watson.texto)
            if rodada == self.MAX_RODADAS:
                break

        # Garantir estado correto antes de fixar_decisao
        record = self._audit.get_cycle(self._cycle_id)
        if record and record["status"] == CycleState.EM_EXECUCAO_WATSON.value:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON)

        decisao = self._mycroft.fixar_decisao_watson(output_watson, rodada)
        self._sr.escrever_decisao_final(fase=fase, author="mycroft", decisao=decisao)
        self._events.log("MYCROFT_DECISION_FINAL", agent="mycroft", phase=fase,
                         details={"overruled": decisao.mycroft_overruled,
                                  "critical_alerts": decisao.critical_alerts_count})

        self._audit.update_watson_metadata(
            self._cycle_id, rodada,
            decisao.mycroft_overruled, decisao.critical_alerts_count,
        )
        self._sr.validar_fase_completa(fase)
        self._events.log("PHASE_ENDED", phase=fase)
        return decisao

    # ── Fase Sherlock + consolidação ─────────────────────────

    def _executar_fase_sherlock_e_consolidar(self, manifest: CycleManifest) -> str:
        fase = "sherlock_validacao"

        # Mycroft monta o pacote para Sherlock a partir da decisão de Watson
        decisao_watson = self._sr.ler_decisao_final("watson_integridade")
        inputs_dir = self._cycle_dir / "inputs"
        pacote = self._mycroft.montar_pacote_sherlock(manifest, inputs_dir, decisao_watson)

        self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
        self._events.log("PHASE_STARTED", phase=fase, agent="sherlock")

        output_sherlock = self._sherlock.validar(pacote)
        self._sr.escrever_apresentacao(fase=fase, author="sherlock",
                                        content=output_sherlock.texto)

        rodada = 0
        while rodada < self.MAX_RODADAS:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)
            avaliacao = self._mycroft.avaliar_sherlock(output_sherlock, fase, rodada)
            self._events.log("MYCROFT_CRITIQUE_ISSUED" if avaliacao.tipo == "QUESTIONAR"
                             else "MYCROFT_APPROVED", agent="mycroft",
                             phase=fase, details={"tipo": avaliacao.tipo, "rodada": rodada})

            if avaliacao.tipo == "APROVADO":
                break

            rodada += 1
            self._sr.escrever_critica(fase, rodada, "mycroft", avaliacao.critica)
            self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
            output_sherlock = self._sherlock.responder_critica(
                avaliacao.critica, output_sherlock, rodada
            )
            self._sr.escrever_resposta(fase, rodada, "sherlock", output_sherlock.texto)
            if rodada == self.MAX_RODADAS:
                break

        # Garantir estado correto antes de fixar_decisao
        record = self._audit.get_cycle(self._cycle_id)
        if record and record["status"] == CycleState.EM_EXECUCAO_SHERLOCK.value:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)

        decisao_sherlock = self._mycroft.fixar_decisao_sherlock(output_sherlock, rodada)
        self._sr.escrever_decisao_final(fase=fase, author="mycroft", decisao=decisao_sherlock)
        self._events.log("MYCROFT_DECISION_FINAL", agent="mycroft", phase=fase,
                         details={"overruled": decisao_sherlock.mycroft_overruled,
                                  "dilemmas": decisao_sherlock.dilemmas_count})

        self._audit.update_sherlock_metadata(
            self._cycle_id, rodada,
            decisao_sherlock.mycroft_overruled, decisao_sherlock.dilemmas_count,
        )
        self._sr.validar_fase_completa(fase)
        self._events.log("PHASE_ENDED", phase=fase)

        # Consolidação final
        output_path = self._consolidar_output_final(manifest, decisao_watson, decisao_sherlock)
        self._transicionar(CycleState.AGUARDANDO_VERIFICACAO_SAIDA)
        self._events.log("CYCLE_READY_FOR_MOTOR_SAIDA",
                         details={"output": str(output_path)})
        return str(output_path)

    def _consolidar_output_final(
        self,
        manifest: CycleManifest,
        decisao_watson: DecisaoFinal,
        decisao_sherlock: DecisaoFinal,
    ) -> Path:
        relatorio = self._mycroft.consolidar(manifest, decisao_watson, decisao_sherlock)
        prefixo = "relatorio_preliminar" if manifest.activity == 1 else "relatorio_final"
        output_filename = f"{prefixo}_{self._cycle_id}.md"
        output_path = self._cycle_dir / "output" / output_filename
        output_path.write_text(relatorio.texto, encoding="utf-8")
        self._audit.update_output_info(self._cycle_id, output_filename)
        self._events.log("CONSOLIDACAO_CONCLUIDA", details={"arquivo": output_filename})
        return output_path

    # ── Helpers ──────────────────────────────────────────────

    def _transicionar(self, destino: CycleState) -> None:
        record = self._audit.get_cycle(self._cycle_id)
        if not record:
            raise OrchestratorError(f"Ciclo '{self._cycle_id}' não encontrado.")
        try:
            atual = CycleState(record["status"])
        except ValueError:
            self._audit.update_status(self._cycle_id, destino.value)
            return
        if destino not in TRANSICOES_VALIDAS.get(atual, set()):
            raise InvalidTransitionError(atual, destino)
        self._audit.update_status(self._cycle_id, destino.value)

    def _proximo_id_alerta(self, module_id: str) -> str:
        """Deriva o prefixo W{dígitos}-001 para Watson a partir do module_id."""
        import re as _re
        nums = _re.findall(r'\d+', module_id)
        codigo = nums[-1].zfill(3) if nums else "000"
        return f"W{codigo}-001"

    def _abortar_por_falha(self, exc: Exception, fase: str) -> None:
        try:
            self._transicionar(CycleState.ABORTADO_FALHA_AGENTE)
        except InvalidTransitionError:
            self._audit.update_status(self._cycle_id, CycleState.ABORTADO_FALHA_AGENTE.value)
        self._events.log("CYCLE_ABORTED_FAILURE",
                         details={"fase": fase, "erro": str(exc)})
