"""
orchestrator/orchestrator.py — DVA-CBS | Projeto Diógenes
Orquestrador — máquina de estados do ciclo. Ciclo completo (Sprint 4).

Sequencialidade absoluta (Art. 3): código síncrono, sem threads, sem asyncio.
Limite de duas rodadas (Art. 8): garantido por construção via MAX_RODADAS.
Referência normativa: RF-OR-01 a RF-OR-11 (PRD v0.1), Bloco 8 (SDD v0.1)
"""
from __future__ import annotations

import dataclasses
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from diogenes.agents.mycroft import MycrooftAgent
from diogenes.agents.sherlock import SherlockAgent
from diogenes.agents.watson import WatsonAgent
from diogenes.config import get_config
from diogenes.irene import executar_irene, verificar_catalogo_existente, _derivar_manifesto_irene, copiar_catalogo_para_ciclo
from diogenes.llm.base import get_llm_client
from diogenes.llm.exceptions import LLMCallError, LLMCostLimitError, LLMTimeoutError
from diogenes.models import CycleManifest, DecisaoFinal, DefinirTasksResult, SherlockOutput, WatsonOutput
from diogenes.orchestrator.events import EventLogger
from diogenes.orchestrator.exceptions import CorruptedStateError, OrchestratorError
from diogenes.orchestrator.states import TRANSICOES_VALIDAS, CycleState, InvalidTransitionError
from diogenes.orchestrator.stranger_room import StrangerRoom
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager

_TASKS_CACHE_MAX_DIAS = 30
_TASKS_CACHE_NOME = "mycroft_tasks_watson.json"


def _carregar_tasks_cache(
    module_id: str, workspace_path: Path
) -> DefinirTasksResult | None:
    """Carrega tasks de Watson cacheadas em workspace/<module_id>/mycroft_tasks_watson.json.

    Retorna None se o cache não existe, está corrompido ou ultrapassou _TASKS_CACHE_MAX_DIAS.
    """
    cache_path = workspace_path / module_id / _TASKS_CACHE_NOME
    if not cache_path.exists():
        return None
    try:
        dados = json.loads(cache_path.read_text(encoding="utf-8"))
        criado_em = datetime.fromisoformat(dados["criado_em"])
        if criado_em.tzinfo is None:
            criado_em = criado_em.replace(tzinfo=timezone.utc)
        idade_dias = (datetime.now(timezone.utc) - criado_em).days
        if idade_dias > _TASKS_CACHE_MAX_DIAS:
            return None
        if dados.get("module_id") != module_id:
            return None
        return DefinirTasksResult(
            tasks_text=dados["tasks_text"],
            planilha_verificacao_no_pacote=dados.get("planilha_verificacao_no_pacote", False),
        )
    except Exception:  # noqa: BLE001
        return None


def _salvar_tasks_cache(
    result: DefinirTasksResult, module_id: str, workspace_path: Path
) -> None:
    """Persiste tasks de Watson em workspace/<module_id>/mycroft_tasks_watson.json."""
    cache_dir = workspace_path / module_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    dados = {
        "module_id": module_id,
        "tasks_text": result.tasks_text,
        "planilha_verificacao_no_pacote": result.planilha_verificacao_no_pacote,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }
    (cache_dir / _TASKS_CACHE_NOME).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _watson_ckpt_path(ckpt_dir: Path, rel_path: str | Path) -> Path:
    """Caminho canônico do checkpoint de um arquivo Watson."""
    safe = str(rel_path).replace("/", "__").replace("\\", "__").replace(":", "_")
    return ckpt_dir / f"{safe}.json"


def _watson_ckpt_salvar(
    ckpt_dir: Path, rel_path: str | Path,
    output: WatsonOutput, proximo_id_apos: str,
) -> None:
    """Persiste WatsonOutput de um arquivo individual em JSON para retomada."""
    p = _watson_ckpt_path(ckpt_dir, rel_path)
    p.write_text(
        json.dumps(
            {
                "arquivo": str(rel_path),
                "proximo_id_apos": proximo_id_apos,
                "output": dataclasses.asdict(output),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _watson_ckpt_carregar(
    ckpt_dir: Path, rel_path: str | Path,
) -> tuple[WatsonOutput, str] | None:
    """Carrega WatsonOutput do checkpoint se existir; retorna None caso contrário."""
    p = _watson_ckpt_path(ckpt_dir, rel_path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return WatsonOutput(**data["output"]), data["proximo_id_apos"]
    except Exception:  # noqa: BLE001
        return None  # checkpoint corrompido — reanalisar


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
            cycle_dir=self._cycle_dir,
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
        """Executa o ciclo completo. Retorna caminho do output ou "" se pausado."""
        if self._cfg.dev_mode:
            self._events.log("DEV_MODE_ACTIVE", details={
                "timeout_max": 30, "retries": 1, "cooldown_skip": True,
            })
        self._events.log("CYCLE_STARTED", details={"cycle_id": manifest.cycle_id})
        try:
            # Fase Irene — catalogação semântica antes de Watson (requer DIOGENES_IRENE_HABILITADO=true)
            if self._cfg.irene_habilitado:
                irene_executou = self._executar_fase_irene(manifest)
                if irene_executou and self._cfg.post_irene_cooldown_s > 0 and not self._cfg.dev_mode:
                    import time as _time
                    cooldown = self._cfg.post_irene_cooldown_s
                    self._events.log("POST_IRENE_COOLDOWN_INICIO",
                                     details={"segundos": cooldown})
                    _time.sleep(cooldown)
                    self._events.log("POST_IRENE_COOLDOWN_FIM",
                                     details={"segundos": cooldown})

            decisao_watson, tasks_result, output_watson, _ = (
                self._executar_fase_watson(manifest)
            )

            if decisao_watson.has_critical_alert:
                self._transicionar(CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA)
                self._events.log("CRITICAL_ALERT_NOTIFIED", phase="watson_integridade",
                                 details={"count": decisao_watson.critical_alerts_count})
                return ""   # CLI notifica Lestrade e aguarda proceed/pause

            return self._executar_fase_sherlock_e_consolidar(
                manifest, tasks_result, output_watson
            )

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
        # Ao retomar após alerta, não temos tasks_result/output_watson em memória.
        # Usamos defaults seguros: sem planilha de verificação, sem nota metodológica.
        from diogenes.models import DefinirTasksResult as _DTR
        return self._executar_fase_sherlock_e_consolidar(
            manifest, _DTR(tasks_text="", planilha_verificacao_no_pacote=False), None
        )

    def retomar_apos_completude(self, manifest: CycleManifest) -> str:
        """
        Chamado por `diogenes complete-sherlock` quando o ciclo está em
        AGUARDANDO_COMPLETUDE (Sherlock gerou output sem as seções ### 10.x).
        Reutiliza o output já gravado no stranger_room, chama fixar_decisao_sherlock
        com fallback e completa o pipeline até AGUARDANDO_VERIFICACAO_SAIDA.
        """
        record = self._audit.get_cycle(self._cycle_id)
        if not record or record["status"] != CycleState.AGUARDANDO_COMPLETUDE.value:
            estado_atual = record.get("status") if record else "N/A"
            raise OrchestratorError(
                f"Ciclo não está em AGUARDANDO_COMPLETUDE (estado atual: {estado_atual})"
            )

        fase = "sherlock_validacao"
        rodada = 0

        # Recuperar Watson decision do stranger_room (já gravada na fase Watson)
        try:
            decisao_watson = self._sr.ler_decisao_final("watson_integridade")
        except FileNotFoundError:
            decisao_watson = DecisaoFinal(
                texto="[Decisão Watson indisponível — recuperação automática]",
                mycroft_overruled=False, has_critical_alert=False,
                critical_alerts_count=0, has_dilemma=False, dilemmas_count=0,
            )

        # Recuperar output Sherlock do stranger_room (já gravado por validar())
        texto_sherlock = self._sr.ler_apresentacao(fase)
        if not texto_sherlock:
            raise OrchestratorError(
                f"Apresentação Sherlock ausente em stranger_room/{fase}/01_apresentacao.md"
            )
        output_sherlock = SherlockOutput(
            texto=texto_sherlock, dilemmas_count=0, has_divergencias=False, secoes={},
        )

        self._events.log("COMPLETUDE_RETOMADA", phase=fase,
                         details={"motivo": "Sherlock output sem seções ### 10.x — continuando com fallback"})

        # fixar_decisao_sherlock tem fallback — não depende de ChatTCU
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

        output_path = self._consolidar_output_final(manifest, decisao_watson, decisao_sherlock)
        self._transicionar(CycleState.AGUARDANDO_VERIFICACAO_SAIDA)
        self._events.log("CYCLE_READY_FOR_MOTOR_SAIDA", details={"output": str(output_path)})
        return str(output_path)

    def abortar(self, razao: str) -> None:
        """Aborta o ciclo por decisão de Lestrade."""
        self._transicionar(CycleState.ABORTADO_LESTRADE)
        self._events.log("CYCLE_ABORTED", details={"razao": razao})

    # ── Fase Irene ───────────────────────────────────────────

    def _executar_fase_irene(self, manifest: CycleManifest) -> bool:
        """
        Executa a fase de catalogação semântica (Irene v1.3.1).

        Retorna True se o pipeline Irene foi executado, False se o catálogo
        existente foi reutilizado (sem chamadas LLM ao ChatTCU).

        Fluxo:
          1. VERIFICANDO_EXISTENCIA: verifica se catálogo reutilizável existe.
             Se sim, pula para EM_EXECUCAO_WATSON diretamente.
          2. AGUARDANDO_IRENE: executa pipeline C1-C5.
          3. IRENE_CONCLUIDA: persiste métricas no audit_index e avança.

        Em caso de IRENE_ERRO_FATAL, transiciona para ABORTADO_FALHA_AGENTE
        e levanta OrchestratorError para interromper o ciclo.

        IRENE_BLOQUEADO não é tratado como fatal aqui — Watson recebe o catálogo
        e decide como ponderar a recomendação (conforme INTEGRACAO_DIOGENES.md §5.1).
        """
        from datetime import datetime, timezone

        # ── VERIFICANDO_EXISTENCIA ────────────────────────────────────────────
        self._transicionar(CycleState.VERIFICANDO_EXISTENCIA)
        self._events.log("IRENE_VERIFICACAO_INICIO", details={"modulo": manifest.module_id})

        existe, caminho_catalogo = verificar_catalogo_existente(
            manifest.module_id, self._cfg.workspace.path
        )

        if existe:
            self._events.log("IRENE_CATALOGO_REUTILIZADO",
                             details={"catalogo": caminho_catalogo, "modulo": manifest.module_id})
            # Fica em VERIFICANDO_EXISTENCIA — _executar_fase_watson() transitará para
            # EM_EXECUCAO_WATSON, e VERIFICANDO_EXISTENCIA → EM_EXECUCAO_WATSON é válida.
            return False

        # ── AGUARDANDO_IRENE ──────────────────────────────────────────────────
        self._transicionar(CycleState.AGUARDANDO_IRENE)
        invocada_at_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._events.log("IRENE_INICIO", details={"modulo": manifest.module_id})

        # Derivar manifesto do Irene a partir do workspace
        manifest_path = _derivar_manifesto_irene(
            manifest.cycle_id, self._cfg.workspace.path
        )

        estado, metricas = executar_irene(
            caminho_manifesto=manifest_path,
            modulo=manifest.module_id,
            dir_saida=self._cfg.workspace.path,
        )

        self._events.log("IRENE_FIM", details={"estado": estado, **{
            k: str(v) for k, v in metricas.items() if k != "artefatos"
        }})

        if estado == "IRENE_ERRO_FATAL":
            self._transicionar(CycleState.ABORTADO_FALHA_AGENTE)
            self._events.log("IRENE_ERRO_FATAL_REGISTRADO", details={"modulo": manifest.module_id})
            raise OrchestratorError(
                f"Irene falhou com ERRO_FATAL para o módulo '{manifest.module_id}'. "
                f"Verifique os logs em {metricas.get('dir_saida', '?')}."
            )

        # ── IRENE_CONCLUIDA ───────────────────────────────────────────────────
        self._transicionar(CycleState.IRENE_CONCLUIDA)
        self._audit.update_irene(
            self._cycle_id,
            resultado=estado,
            score=metricas.get("score_consolidado", 0.0),
            dir_saida=metricas.get("dir_saida", ""),
            invocada_at_utc=invocada_at_utc,
        )
        self._events.log("IRENE_CONCLUIDA_REGISTRADA",
                         details={"estado": estado,
                                  "score": metricas.get("score_consolidado", 0.0)})

        # Copiar catálogo para o diretório do ciclo (consumido por definir_tasks_watson)
        copiar_catalogo_para_ciclo(metricas, self._cycle_id, self._cfg.workspace.path)

        # Avança para Watson — transição IRENE_CONCLUIDA → EM_EXECUCAO_WATSON
        # feita implicitamente: _executar_fase_watson chama _transicionar(EM_EXECUCAO_WATSON).
        # IRENE_BLOQUEADO: Watson recebe catálogo com flag de bloqueio e decide.
        return True

    # ── Fase Watson ──────────────────────────────────────────

    def _executar_fase_watson(
        self, manifest: CycleManifest
    ) -> tuple[DecisaoFinal, DefinirTasksResult, WatsonOutput, list[WatsonOutput]]:
        """
        Retorna (decisao_final, tasks_result, output_watson_consolidado, analises_por_arquivo).
        tasks_result carrega planilha_verificacao_no_pacote para uso na fase Sherlock.
        output_watson_consolidado carrega nota_metodologica_com_alteracao para propagação.
        analises_por_arquivo é necessário para validacao_planilha_rn (Frente 1/3).
        """
        fase = "watson_integridade"
        self._transicionar(CycleState.EM_EXECUCAO_WATSON)
        self._events.log("PHASE_STARTED", phase=fase, agent="watson")

        # Cache de tasks — evita chamada LLM cara quando Mycroft está saturado.
        # O cache é válido por _TASKS_CACHE_MAX_DIAS dias (mesmo manifesto/módulo).
        ws_path = self._cfg.workspace.path
        tasks_result = _carregar_tasks_cache(manifest.module_id, ws_path)
        if tasks_result is not None:
            self._events.log("TASKS_WATSON_CACHE_HIT",
                             details={"module_id": manifest.module_id})
        else:
            tasks_result = self._mycroft.definir_tasks_watson(manifest)
            _salvar_tasks_cache(tasks_result, manifest.module_id, ws_path)
            self._events.log("TASKS_WATSON_CACHE_SAVED",
                             details={"module_id": manifest.module_id})
        tasks = tasks_result.tasks_text
        inputs_dir = self._cycle_dir / "inputs"

        # Fase 1: análise por arquivo — sequencialidade absoluta (Artigo 3)
        # `proximo_id` é a ÚNICA fonte de verdade do contador de alertas: a cada
        # chamada de Watson, é avançado com base no maior ID efetivamente
        # parseado do output (não na contagem bruta reportada pelo LLM, que é
        # frágil e pode ser re-emitida por inteiro a cada rodada). Isso garante
        # IDs contíguos independentemente de como Watson formata a resposta.
        #
        # Checkpointing: cada WatsonOutput é persistido em _runtime/watson_checkpoints/
        # após análise. Se o processo morrer e o ciclo for reiniciado, os arquivos
        # já analisados são carregados do checkpoint sem nova chamada LLM.
        ckpt_dir = self._runtime_dir / "watson_checkpoints"
        ckpt_dir.mkdir(exist_ok=True)

        proximo_id = self._proximo_id_alerta(manifest.module_id, 1)
        analises_watson: list[WatsonOutput] = []
        for fi in manifest.input_files:
            ckpt = _watson_ckpt_carregar(ckpt_dir, fi.rel_path)
            if ckpt is not None:
                analise_fi, proximo_id = ckpt
                analises_watson.append(analise_fi)
                continue  # arquivo já analisado — pula sem novo evento

            analise_fi = self._watson.analisar_arquivo(
                arquivo_path=inputs_dir / fi.rel_path,
                arquivo_info=fi,
                tasks_mycroft=tasks,
                proximo_id_alerta=proximo_id,
            )
            analises_watson.append(analise_fi)
            proximo_id = _avancar_id_alerta(proximo_id, analise_fi)
            _watson_ckpt_salvar(ckpt_dir, fi.rel_path, analise_fi, proximo_id)
            self._events.log("WATSON_ARQUIVO_ANALISADO",
                             details={"arquivo": fi.name, "criticos": analise_fi.critical_alerts_count})

        # Fase 2: consolidação
        output_watson = self._watson.consolidar(analises_watson, tasks)
        self._sr.escrever_apresentacao(fase=fase, author="watson",
                                        content=output_watson.texto)
        proximo_id = _avancar_id_alerta(proximo_id, output_watson)

        # Fase opcional: validacao_planilha_rn — acionado condicionalmente quando a
        # Planilha de Verificação do Motor de Regras está listada no manifesto (Frente 1/3a)
        if tasks_result.planilha_verificacao_no_pacote:
            planilha_path = _localizar_planilha_verificacao(manifest, inputs_dir)
            if planilha_path:
                output_planilha_rn = self._watson.validacao_planilha_rn(
                    planilha_path=planilha_path,
                    analises_watson=analises_watson,
                    tasks_mycroft=tasks,
                )
                # Persiste o output na pasta _runtime para ingestão por Sherlock
                (self._runtime_dir / "watson_planilha_rn.md").write_text(
                    output_planilha_rn.texto, encoding="utf-8"
                )
                self._events.log("WATSON_PLANILHA_RN_CONCLUIDA", phase=fase)

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
            output_watson = self._watson.responder_critica(
                avaliacao.critica, output_watson, rodada, proximo_id
            )
            self._sr.escrever_resposta(fase, rodada, "watson", output_watson.texto)
            proximo_id = _avancar_id_alerta(proximo_id, output_watson)

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
        return decisao, tasks_result, output_watson, analises_watson

    # ── Fase Sherlock + consolidação ─────────────────────────

    def _executar_fase_sherlock_e_consolidar(
        self,
        manifest: CycleManifest,
        tasks_result: DefinirTasksResult,
        output_watson_consolidado: WatsonOutput | None,
    ) -> str:
        fase = "sherlock_validacao"

        # Mycroft monta o pacote para Sherlock a partir da decisão de Watson
        decisao_watson = self._sr.ler_decisao_final("watson_integridade")
        inputs_dir = self._cycle_dir / "inputs"
        watson_apresentacao = self._sr.ler_apresentacao("watson_integridade")

        # Frente 3b: propagar nota metodológica quando Watson a sinalizou.
        # A nota é incluída no pacote de contexto de Sherlock como Premissa 3
        # do skills.md — Sherlock a trata com prioridade antes dos pontos individuais.
        nota_metodologica_detalhes = ""
        if output_watson_consolidado and output_watson_consolidado.nota_metodologica_com_alteracao:
            # Extrair o conteúdo da seção 2 (Notas Metodológicas) do consolidado Watson
            nota_metodologica_detalhes = (
                output_watson_consolidado.secoes.get("2. Notas Metodológicas com Alteração", "")
                or output_watson_consolidado.secoes.get("Notas Metodológicas com Alteração", "")
                or "[Nota metodológica com alteração identificada — ver watson_consolidado.md seção 2]"
            )

        pacote = self._mycroft.montar_pacote_sherlock(
            manifest, inputs_dir, decisao_watson, watson_apresentacao,
            nota_metodologica_detalhes=nota_metodologica_detalhes,
        )

        self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
        self._events.log("PHASE_STARTED", phase=fase, agent="sherlock")

        output_sherlock = self._sherlock.validar(pacote)

        # Frente 3a: validacao_planilha_rn_sherlock — acionado condicionalmente quando
        # a Planilha de Verificação está no manifesto e Watson já a validou.
        # Executado após verificar_ponto (embutido em validar()) e antes da avaliação
        # de Mycroft, para que Sherlock tenha perspectiva metodológica da planilha.
        watson_planilha_rn_path = self._runtime_dir / "watson_planilha_rn.md"
        if tasks_result.planilha_verificacao_no_pacote and watson_planilha_rn_path.exists():
            watson_planilha_rn_texto = watson_planilha_rn_path.read_text(encoding="utf-8")
            output_planilha_sherlock = self._sherlock.validacao_planilha_rn_sherlock(
                pacote_sherlock=pacote,
                watson_planilha_rn=watson_planilha_rn_texto,
            )
            (self._runtime_dir / "sherlock_planilha_rn.md").write_text(
                output_planilha_sherlock.texto, encoding="utf-8"
            )
            self._events.log("SHERLOCK_PLANILHA_RN_CONCLUIDA", phase=fase)

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

        # Garantir estado correto antes de fixar_decisao
        record = self._audit.get_cycle(self._cycle_id)
        if record and record["status"] == CycleState.EM_EXECUCAO_SHERLOCK.value:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)

        # Frente 3c: verificar completude das 11 seções do Relatório Estruturado (10.1–10.11)
        # e do JSON de ocorrências (seção 11) antes de acionar Mycroft.consolidar().
        # Se incompleto: estado AGUARDANDO_COMPLETUDE e Lestrade notificado.
        secoes_faltando = _verificar_completude_sherlock(output_sherlock.texto)
        if secoes_faltando:
            self._transicionar(CycleState.AGUARDANDO_COMPLETUDE)
            self._events.log("SHERLOCK_COMPLETUDE_INSUFICIENTE", phase=fase,
                             details={"secoes_faltando": secoes_faltando})
            return ""   # CLI notifica Lestrade; retomada via comando futuro

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
        except ValueError as exc:
            # Status no audit_index não é um CycleState conhecido — corrupção
            # do registro de auditoria. Fail-fast: nunca mascarar (Art. 11).
            raise CorruptedStateError(
                f"Ciclo '{self._cycle_id}' tem status inválido "
                f"'{record['status']}' no audit_index."
            ) from exc
        if destino not in TRANSICOES_VALIDAS.get(atual, set()):
            raise InvalidTransitionError(atual, destino)
        self._audit.update_status(self._cycle_id, destino.value)

    def _proximo_id_alerta(self, module_id: str, counter: int = 1) -> str:
        """Gera ID de alerta sequencial: W{codigo_modulo}-{counter:03d}."""
        nums = re.findall(r'\d+', module_id)
        codigo = nums[-1].zfill(3) if nums else "000"
        return f"W{codigo}-{counter:03d}"

    def _abortar_por_falha(self, exc: Exception, fase: str) -> None:
        try:
            self._transicionar(CycleState.ABORTADO_FALHA_AGENTE)
        except InvalidTransitionError:
            self._audit.update_status(self._cycle_id, CycleState.ABORTADO_FALHA_AGENTE.value)
        self._events.log("CYCLE_ABORTED_FAILURE",
                         details={"fase": fase, "erro": str(exc)})


# ── Helpers de módulo ────────────────────────────────────────────────────────

def _localizar_planilha_verificacao(
    manifest: CycleManifest, inputs_dir: Path
) -> Path | None:
    """
    Busca no manifesto um arquivo cujo nome contenha 'verificacao' (case-insensitive).
    Retorna o Path do arquivo ou None se não encontrado.
    Usado para acionar watson.validacao_planilha_rn condicionalmente (Frente 3a).
    """
    for fi in manifest.input_files:
        if "verificacao" in fi.name.lower():
            candidate = inputs_dir / fi.rel_path
            if candidate.exists():
                return candidate
    return None


_SECOES_RELATORIO_OBRIGATORIAS = [
    "### 10.1", "### 10.2", "### 10.3", "### 10.4", "### 10.5",
    "### 10.6", "### 10.7", "### 10.8", "### 10.9", "### 10.10", "### 10.11",
]


def _verificar_completude_sherlock(texto_sherlock: str) -> list[str]:
    """
    Verifica a presença das 11 subseções obrigatórias do Relatório Estruturado
    (10.1 a 10.11) no sherlock_consolidado.md.
    Retorna lista de seções faltando (vazia = completo).
    Usado pela Frente 3c antes de acionar Mycroft.consolidar().
    """
    return [s for s in _SECOES_RELATORIO_OBRIGATORIAS if s not in texto_sherlock]


# ── Helpers de ID de alerta ──────────────────────────────────────────────────


def _avancar_id_alerta(proximo_id_atual: str, output: WatsonOutput) -> str:
    """
    Avança o próximo ID de alerta disponível com base no maior ID
    efetivamente parseado do output de Watson (`ultimo_id_alerta`).

    Se o output não contém nenhum ID de alerta, nenhum ID novo foi
    consumido — mantém `proximo_id_atual`. Isso torna o contador imune
    a Watson re-emitir a tabela inteira a cada rodada de revisão.
    """
    if output.ultimo_id_alerta:
        return _incrementar_id_alerta(output.ultimo_id_alerta)
    return proximo_id_atual


def _incrementar_id_alerta(ultimo_id: str) -> str:
    """
    Incrementa o contador de ID de alerta de Watson.
    "W010-003" → "W010-004"
    Retorna o mesmo string se o formato não for reconhecido.
    """
    import re as _re
    m = _re.match(r'^(W\d+-)(\d+)$', ultimo_id)
    if not m:
        return ultimo_id
    prefixo = m.group(1)       # "W010-"
    n = int(m.group(2)) + 1    # 3 → 4
    return f"{prefixo}{n:03d}"
