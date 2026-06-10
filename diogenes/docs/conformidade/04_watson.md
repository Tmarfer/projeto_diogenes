# Conformidade — Watson (RF-WA)

> PRD Bloco 3.4 (linhas 250-268) vs. `src/diogenes/agents/watson.py` + `agents/file_prep.py` + `docs/agentes/watson/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-WA-01 | Recebe tasks ordenadas de Mycroft com lista de arquivos | Conforme | `watson.py:36` `analisar_arquivo(tasks_mycroft, ...)`; orquestrador itera na ordem | — | — | — |
| RF-WA-02 | Não interpreta metodologia nem emite juízo metodológico | Conforme | Sem injeção de metodologia no prompt de Watson; regra de não-interpretação no `soul.md`/`skills.md` | — | — | — |
| RF-WA-03 | Planilhas: totais fecham, fórmulas recalculam, consistência interna | Conforme | `analise_arquivo` sobre texto canonicalizado de `file_prep.py` (openpyxl); catálogo Irene como apoio | — | — | — |
| RF-WA-04 | SQL: tradução para linguagem natural + execução descrita | Conforme | `file_prep.py` via sqlparse; heartbeat `analise_arquivo` cobre SQL | — | — | — |
| RF-WA-05 | Notebooks: tradução das células executáveis | Conforme | `file_prep.py` via nbformat; `test_file_prep.py` | — | — | — |
| RF-WA-06 | Cadeia de produção dos dados entre documentos | Conforme | Seção dedicada no template (`skills.md`); "pontos de ruptura" propagados ao consolidado | — | — | — |
| RF-WA-07 | Análises extrapolativas segregadas das literais | Conforme | Seção própria no template (`skills.md`) | — | — | — |
| RF-WA-08 | Arquivo não analisável: registra e segue | Conforme | Seção "Arquivos Não Analisáveis"; `has_unanalyzable_files` no `WatsonOutput` (`models.py`) | — | — | — |
| RF-WA-09 | Severidade em ≥3 níveis (CRÍTICA/ATENÇÃO/INFORMATIVA) | Conforme | 4 níveis na prática (CRITICA/ALTA/MEDIA/BAIXA); IDs `W{MOD}-NNN` via `orchestrator.py:836` `_proximo_id_alerta` | — | — | — |
| RF-WA-10 | Output estruturado, consumível por Mycroft sem ambiguidade | Conforme | `**Alertas CRITICA:** N` legível por máquina; campos de cabeçalho monitorados (CLAUDE.md) | Descrições de alerta com 1-2 linhas, sem bloco contexto/impacto/recomendação; fonte de dado (aba/célula) nem sempre citada | P1 | 2 |

**Síntese:** 10/10 Conforme no requisito literal. Gap de RF-WA-10 é de **profundidade** (CA-QUA-01, padrão-exemplo) — alvo da Onda 2: template de ocorrência em 4 blocos (contexto, impacto, fundamentação, recomendação) no `skills.md`/`heartbeat.md`.

**Extensões além do PRD:**
- `validacao_planilha_rn` (`watson.py:186`): call_type condicional (Planilha de Verificação no manifesto).
- Checkpoints por arquivo (`_runtime/watson_checkpoints/`): retomada sem reprocessar.
- Confronto A2: instrução de comparação com histórico A1.
