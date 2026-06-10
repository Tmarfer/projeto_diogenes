# Conformidade — Orquestrador (RF-OR)

> PRD Bloco 3.2 (linhas 204-224) vs. `src/diogenes/orchestrator/orchestrator.py`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-OR-01 | Um agente por vez, por construção; sem paralelismo | Conforme | Fluxo síncrono single-process; sem threads/asyncio em todo `src/` (Art. 3); `test_orchestrator.py` | — | — | — |
| RF-OR-02 | Confirmação do manifesto → validação interna → tasks de Mycroft | Conforme | `orchestrator.py:172` `executar(manifest)`; tasks via `mycroft.py:56` `definir_tasks_watson` | — | — | — |
| RF-OR-03 | Executa tasks na ordem de Mycroft, sem reordenação | Conforme | Loop de arquivos segue ordem das tasks; sem sort/filtro adicional | — | — | — |
| RF-OR-04 | Output de Watson → Stranger's Room → Mycroft avalia | Conforme | `orchestrator.py:536` loop `while rodada < MAX_RODADAS` (fase Watson); `stranger_room.py:51-60` | — | — | — |
| RF-OR-05 | Alerta crítico na decisão final → pausa + notificação a Lestrade | Conforme | `has_critical_alert` → `AGUARDANDO_DECISAO_LESTRADE_ALERTA`; retomada via `orchestrator.py:219` `retomar_apos_alerta`; `test_ciclo_completo.py` | — | — | — |
| RF-OR-06 | Monta pacote integrado para Sherlock (inventário + decisão Watson + metodologia) | Conforme | `mycroft.py:160` `montar_pacote_sherlock`; metodologia+corpus injetados em `orchestrator.py:~538-614` via `contexto_metodologico.py` | Corpus jurídico ausente é só evento (`SHERLOCK_CORPUS_AUSENTE`, `orchestrator.py:614`), não bloqueia | P1 | 2 |
| RF-OR-07 | Mesmo protocolo de 2 rodadas na fase `sherlock_validacao` | Conforme | `orchestrator.py:671` segundo loop `while rodada < MAX_RODADAS` | — | — | — |
| RF-OR-08 | Consolidação final por Mycroft conforme atividade | Conforme | `orchestrator.py:747` `_consolidar_output_final`; `mycroft.py:299` `consolidar` (A2 com `historico_a1`) | — | — | — |
| RF-OR-09 | Persiste consolidado em `output/`, atualiza índice, notifica | Conforme | grava `output/relatorio_preliminar_{id}.md`; estado `AGUARDANDO_VERIFICACAO_SAIDA` | — | — | — |
| RF-OR-10 | Falha de agente → retry/timeout → aborto controlado sem corromper índice | Conforme | `orchestrator.py:842` `_abortar_por_falha` → `ABORTADO_FALHA_AGENTE`; retries em `llm/` | — | — | — |
| RF-OR-11 | Toda transição atualiza status validado no índice | Conforme | `orchestrator.py:781` `_transicionar` valida `TRANSICOES_VALIDAS` (`states.py`) | — | — | — |

**Síntese:** 11/11 Conforme. Um gap de política (não de requisito) registrado em RF-OR-06: tornar corpus ausente bloqueante fora de DEV_MODE (Onda 2).

**Extensões além do PRD (auditáveis, sem RF correspondente — ver `12_sdd_gaps.md`):**
- **Fase Irene** (estados `AGUARDANDO_IRENE` → `IRENE_CONCLUIDA`, `orchestrator.py:358+`): catalogação semântica C1-C5 pré-Watson. Coberta por `test_ciclo_com_irene.py`.
- **Fase de Entrega** (`orchestrator/entrega.py:34` `executar_entrega`): pós-verificação, pré-seal.
- **Estado `AGUARDANDO_COMPLETUDE`**: verificação das 11 seções do Sherlock antes da consolidação; retomada via `orchestrator.py:229` `retomar_apos_completude`.
- **EventLogger** (`orchestrator/events.py`): JSONL + regeneração ao vivo de `report.html`.
