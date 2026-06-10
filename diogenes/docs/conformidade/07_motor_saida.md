# Conformidade — Motor de Saída (RF-MV)

> PRD Bloco 3.7 (linhas 310-320) vs. `src/diogenes/motors/motor_saida.py`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-MV-01 | Invocado por Lestrade via CLI dedicado sobre o consolidado | Conforme | `cli/commands/verify_output.py`; `motor_saida.py:45` `verificar(cycle_id)` | — | — | — |
| RF-MV-02 | Varre nomes de agentes, cargos, estruturas internas, cycle_id | Conforme | `motor_saida.py:197` `_varrer`; padrões em `runtime.yaml:motor_saida` (4 categorias) | Erro de regex em `runtime.yaml` falharia silenciosamente (não-detecção sem aviso) | P2 | 1 |
| RF-MV-03 | Relatório com localização precisa de cada ocorrência | Conforme | `OcorrenciaDetectada` (linha, contexto, posição via `:258` `_classificar_posicao`, `:266` `_extrair_contexto`) | — | — | — |
| RF-MV-04 | Decisão tripla de Lestrade (substituir/aceitar/devolver) | Evoluído | **Divergência deliberada:** auto-higienização (`motor_saida.py:131` `_sanitizar`) + re-varredura; chancela só se limpo. Caminho "aceitar com justificativa" existe via `seal --accept-occurrences --reason` | Registrar a divergência no PRD-adendo (junto com RF-EN) | P3 | 3 |
| RF-MV-05 | Registra execução no índice (timestamp, ocorrências, hash) | Conforme | `audit_index.py:97` `update_motor_saida` | — | — | — |
| RF-MV-06 | Exclusivamente heurístico (sem LLM), auditável por leitura | Conforme | Regex/keywords apenas; invariante CLAUDE.md §5; `test_motor_saida.py` | — | — | — |

**Síntese:** 5 Conforme, 1 Evoluído (divergência deliberada documentada). Ação da Onda 1 (item P2): teste de sanidade que valida a compilação de todos os padrões de `runtime.yaml:motor_saida` na inicialização e falha ruidosamente em regex inválida.

**Nota Onda 3:** todo texto redigido por LLM na Fase de Entrega (narrativa do dashboard, apêndice redigido) deve passar pela mesma varredura antes de virar DOCX — hoje o `avaliar_entrega` checa marcas vazadas nas amostras, mas a varredura determinística do Motor de Saída sobre os textos da entrega é a salvaguarda correta.
