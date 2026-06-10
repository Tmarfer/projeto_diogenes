# Conformidade — Sherlock (RF-SH)

> PRD Bloco 3.5 (linhas 274-288) vs. `src/diogenes/agents/sherlock.py` + `docs/agentes/sherlock/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-SH-01 | Recebe pacote integrado por Mycroft | Conforme | `sherlock.py:37` `validar(pacote_sherlock)`; pacote de `mycroft.py:160` | — | — | — |
| RF-SH-02 | Não analisa integridade estrutural; opera sobre pacote saneado | Conforme | Sem tools de Camada 0; limite no `soul.md` | — | — | — |
| RF-SH-03 | Aplica metodologia homologada (Acórdão 2833/2025) do módulo | Conforme | Metodologia (cat. C) + corpus jurídico (cat. D) no pacote via `contexto_metodologico.py:39` `carregar_metodologia_modulo` (teto 80k chars) e `:68` `carregar_corpus_juridico` (teto 30k) | Corpus depende de `DIOGENES_CORPUS_JURIDICO_DIR` externo; sem default versionado no repo; ausência não bloqueia | P1 | 2 |
| RF-SH-04 | Classificação semântica TCU-CBS (Atendido/Parcial/Divergência/Atenção/Limitação/Não Verificável) | Conforme | Vocabulário exato no `skills.md`; quadro de classificações na seção 10.4 | — | — | — |
| RF-SH-05 | Dilema com duas interpretações → registra e encaminha a Mycroft | Conforme | `dilemmas_count` no `SherlockOutput` (`models.py`); protocolo no heartbeat | — | — | — |
| RF-SH-06 | Cálculos próprios reproduzíveis (fórmula, inputs, resultado) | Parcial | Fundamentação por ponto exigida no template; reprodutibilidade do cálculo declarada mas não verificada deterministicamente | Citação normativa por ponto não obrigatória; `fundamento_violado` do JSON opcional mesmo em CRITICO | P1 | 2 |
| RF-SH-07 | Relatório ponto a ponto com fundamentação explícita | Conforme | `sherlock.py:77` `consolidar` — 11 seções obrigatórias (10.1-10.11) verificadas pelo orquestrador antes de Mycroft.consolidar | Fundamentação cita metodologia mas raramente dispositivo legal (LC 214/2025, art. X) — zero citações nos outputs reais auditados | P1 | 2 |
| RF-SH-08 | Output estruturado equivalente ao de Watson | Conforme | `SherlockOutput` espelha `WatsonOutput`; JSON de ocorrências (seção 11) para dashboard | — | — | — |

**Síntese:** 7 Conforme, 1 Parcial (RF-SH-06). Os gaps concentram a **fundamentação legal** — gap nº 2 da comparação com os exemplos — e são o alvo prioritário da Onda 2 em Sherlock:
1. Corpus jurídico mínimo versionado no repo como default (`docs/corpus_juridico/`), com política bloqueante fora de DEV_MODE.
2. `skills.md`/`heartbeat.md`: formato canônico de citação ("LC 214/2025, art. X, §Y"; "Acórdão 2.833/2025-TCU-Plenário, item Z") obrigatório quando o corpus estiver no pacote.
3. `fundamento_violado` obrigatório no JSON para ocorrências CRITICO.

**Extensões além do PRD:**
- `validacao_planilha_rn_sherlock` (`sherlock.py:48`): condicional à Planilha de Verificação.
- Seção 10.10 renomeada "Deliberações Internas do Ciclo" (higiene de marca interna).
- `responder_critica` (`sherlock.py:103`): protocolo Stranger's Room.
