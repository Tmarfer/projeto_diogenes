# Conformidade — Mycroft (RF-MY)

> PRD Bloco 3.3 (linhas 230-244) vs. `src/diogenes/agents/mycroft.py` + `docs/agentes/mycroft/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-MY-01 | Lê manifesto, internaliza contexto, define tasks ordenadas | Conforme | `mycroft.py:56` `definir_tasks_watson`; heartbeat `definir_tasks_watson`; `test_mycroft_avaliacao.py` | — | — | — |
| RF-MY-02 | Nunca analisa arquivos diretamente nem executa cálculos | Conforme | Sem tools de leitura no invocador; opera só sobre outputs; limite reforçado no `soul.md` | — | — | — |
| RF-MY-03 | Aprovar / questionar / decisão pós-2ª rodada | Conforme | `mycroft.py:94` `avaliar_watson`, `:235` `avaliar_sherlock` (APROVADO\|QUESTIONAR); `:125`/`:264` `fixar_decisao_*` | — | — | — |
| RF-MY-04 | Crítica objetiva, localizada, fundamentada | Conforme | Template `avaliar_agente` no `heartbeat.md` exige ponto específico + fundamento | — | — | — |
| RF-MY-05 | Fixa decisão final após 2ª rodada, independentemente de concordância | Conforme | `fixar_decisao_*` invocado incondicionalmente quando há 2ª rodada (orquestrador) | — | — | — |
| RF-MY-06 | Inspeção de alertas críticos ao encerrar fase Watson | Conforme | `### Alertas Críticos / CONTAGEM: N` parseado; `_contar_criticos` com fallback de seção | — | — | — |
| RF-MY-07 | Consolida output final conforme atividade; 3ª pessoa, impessoal | Conforme | `mycroft.py:299` `consolidar`; impessoalidade verificada a posteriori pelo Motor de Saída | Profundidade narrativa da "Posição do Departamento" aquém do padrão-exemplo (1 frase/ocorrência vs 3-5 parágrafos); sem regras de escrita (≤4 linhas/parágrafo, valores abreviados, coluna Fonte) | P1 | 2 |
| RF-MY-08 | A2 incorpora histórico explícito do ciclo A1 | Conforme | `consolidar(historico_a1=...)`; `test_ciclo_atividade2.py` | — | — | — |

**Síntese:** 8/8 Conforme no requisito literal. O gap de RF-MY-07 é de **qualidade** (CA-QUA-02/05, padrão-exemplo), não de presença — alvo central da Onda 2 (calibração de `skills.md`/`heartbeat.md`).

**Call_types além do PRD (Fase de Entrega — ver `12_sdd_gaps.md` para proposta RF-EN):**
- `mapear_dados_modulo` (`mycroft.py:361`): blueprint do dashboard — só coordenadas e texto, nunca valores numéricos (salvaguarda anti-alucinação).
- `avaliar_entrega` (`mycroft.py:409`): QA dos entregáveis (APROVADO\|REQUER_AJUSTE).
- `redigir_apendice` (`mycroft.py:434`): reorganiza o consolidado validado nas 7 seções do apêndice.
- `mapear_pontos`: liga pontos do Apêndice metodológico aos `watson_analise_*.md`.
