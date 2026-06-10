# Matriz de Conformidade — Índice e Backlog

> **Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU
> **Data:** 2026-06-10 | **Baseline:** 343 testes passando, 2 warnings (pós-Onda 3 — `feat/onda-3-redator-delivery-v2`)
> **Fontes:** `PRD_Piloto_Diogenes_v01.md` + `SDD_Piloto_Diogenes_v01.md` vs. `src/`
> **Semente:** `docs/AUDITORIA_CONFORMIDADE_PRD.md` (2026-06-03) — esta matriz a substitui e detalha.

## Escala de status

| Status | Significado |
|---|---|
| Conforme | Implementado e verificável por código/teste (evidência `arquivo:linha`) |
| Parcial | Implementado com lacuna pontual |
| Evoluído | Intenção preservada; o meio mudou (divergência deliberada documentada) |
| Não conforme | Não implementado |
| Não verificável | Exige execução real / avaliação humana |
| Bloqueado | Pré-requisito ausente impede até a verificação |

## Dashboard consolidado

| Arquivo | Escopo | Conforme | Parcial | Evoluído | Não conf. | Não verif./Bloq. |
|---|---|---|---|---|---|---|
| [01_motor_start.md](01_motor_start.md) | RF-MS-01..09 | 9 | — | — | — | — |
| [02_orquestrador.md](02_orquestrador.md) | RF-OR-01..11 | 11 | — | — | — | — |
| [03_mycroft.md](03_mycroft.md) | RF-MY-01..08 | 8 | — | — | — | — |
| [04_watson.md](04_watson.md) | RF-WA-01..10 | 10 | — | — | — | — |
| [05_sherlock.md](05_sherlock.md) | RF-SH-01..08 | 7 | 1 | — | — | — |
| [06_strangers_room.md](06_strangers_room.md) | RF-SR-01..06 | 6 | — | — | — | — |
| [07_motor_saida.md](07_motor_saida.md) | RF-MV-01..06 | 5 | — | 1 | — | — |
| [08_persistencia.md](08_persistencia.md) | RF-PE-01..06 | 5 | — | 1 | — | — |
| [09_cli.md](09_cli.md) | RF-CL-01..13 | 13 | — | — | — | — |
| [10_rnf.md](10_rnf.md) | RNF-* (48) | 38 | 4 | 4 | 1 | 1 |
| [11_aceitacao_metricas.md](11_aceitacao_metricas.md) | CA-* (27) + MET-* (10) | 19 | 3 | — | — | 15 |
| [12_sdd_gaps.md](12_sdd_gaps.md) | SDD v0.1 vs código | — | — | — | 13 itens de doc | — |

**Leitura executiva:** a implementação dos requisitos **funcionais está essencialmente
conforme** (74 de 77 RFs Conforme; 1 Parcial; 2 Evoluído deliberados; 0 Não conforme).
O passivo real está em três lugares:
1. **Qualidade de output** (CA-QUA, MET-04..08) — não verificável hoje e **bloqueada
   pelo gabarito ausente** do MOD_SINT_001. É o coração das Ondas 2-3.
2. **Documentação defasada** (SDD antecede Irene/ChatTCU/Entrega; PRD sem RFs para
   ~40% do sistema atual) — Onda 3 documental.
3. **Dívidas pontuais de RNF** (re-execução, agregação de custo, redação de segredos,
   cobertura nunca medida) — backlog P2/P3.

## Backlog priorizado

### P1 — fazem a diferença nos objetivos (qualidade de output)

| # | Item | Origem | Onda |
|---|---|---|---|
| 1 | ~~**Criar gabarito de inconsistências do MOD_SINT_001**~~ **✓ FEITO 2026-06-09** — `docs/conformidade/gabarito_mod_sint_001.md` criado; 4 INC primárias + 2 latentes + 6 verdadeiros negativos documentados; MET-04..07 e CA-QUA-01 desbloqueados | 11_aceitacao_metricas | 2 |
| 2 | Corpus jurídico mínimo **versionado** como default + política bloqueante fora de DEV_MODE | 05_sherlock, 02_orquestrador (RF-OR-06/RF-SH-03) | 2 |
| 3 | Sherlock: citação normativa canônica obrigatória + `fundamento_violado` em CRITICO | 05_sherlock (RF-SH-06/07) | 2 |
| 4 | Watson: template de ocorrência em 4 blocos (contexto/impacto/fundamentação/recomendação) + fonte de dado | 04_watson (RF-WA-10) | 2 |
| 5 | Mycroft: regras de escrita padrão-exemplo no consolidado (≤4 linhas/parágrafo, valores abreviados, coluna Fonte) | 03_mycroft (RF-MY-07) | 2 |
| 6 | Baseline de medição: 1 ciclo A1 MOD_SINT_001 pontuado contra o gabarito ANTES de mudar prompts | 11_aceitacao_metricas (protocolo) | 2 |
| 7 | 3º ciclo A1 consecutivo MOD_SINT_001 (CA-FUN-01) + A2 real (CA-FUN-02/CA-QUA-04) | 11_aceitacao_metricas | 2 |
| 8 | SDD v0.2: Blocos 4/6/8/9 atualizados + Bloco 15 (Fase de Entrega) | 12_sdd_gaps | 3 |
| 9 | ~~PRD-adendo com RF-EN-* (+ RF-AU/RP/BE/IR)~~ **✓ FEITO 2026-06-10** — `docs/antecedentes/PRD_adendo_v01_fase_entrega.md` (RF-EN-01..07, RF-AU-01..03, RF-RP-01..02, RF-BE-01..02, RF-IR-01..03) | 12_sdd_gaps | 3 |
| 10 | ~~Motor de Saída varre texto LLM da entrega antes do DOCX (RF-EN-06)~~ **✓ FEITO 2026-06-10** — `sanitizar_delivery_text()` em `motor_saida.py`; integrado em `motor_entrega.py` para narrativo/consolidado/pré-atendimento; 4 testes `TestSanitizarDeliveryText` | 07_motor_saida, 12_sdd_gaps | 3 |

### P2 — robustez e medição

| # | Item | Origem | Onda |
|---|---|---|---|
| 11 | ~~Golden tests estruturais do delivery~~ **✓ FEITO 2026-06-09** — `tests/integration/test_delivery_golden.py` (15 testes, todos passando) | plano Onda 1 | 1 |
| 12 | ~~Reconciliar vendor TCU vs. geradores de `output_exemplo` (drift) + atualizar VENDOR.md~~ **✓ FEITO 2026-06-09** — sem drift; `delivery/vendor/tcu/VENDOR.md` atualizado | plano Onda 1 | 1 |
| 13 | ~~Teste de sanidade dos regex de `runtime.yaml:motor_saida`~~ **✓ FEITO 2026-06-09** — coberto em `test_delivery_golden.py` (`test_padroes_*`, `test_regex_*`, `test_substituicoes_*`) | 07_motor_saida (RF-MV-02) | 1 |
| 14 | ~~Medir cobertura e registrar (CA-OPE-10)~~ **Feito 2026-06-09: 75% (≥70% ✓)**; restam hotspots <20% em `orchestrator/entrega.py`, `cli/autorun.py`, `cli/deliver.py` | 11_aceitacao_metricas | 1 |
| 15 | Fallback explícito para `heartbeat.md` ausente (erro claro, não prompt truncado) | fragilidade conhecida | 2 |
| 16 | RNF-REPR-03: modo de re-execução de ciclo (habilita MET-10) | 10_rnf | backlog |
| 17 | RNF-CUST-01/CA-OPE-05: agregação de custo/tokens por ciclo no índice | 10_rnf | backlog |
| 18 | RNF-SEGU-03: redação de padrões de segredo na serialização de traces | 10_rnf | backlog |
| 19 | Medir RNF-LATE-01/02 formalmente sobre MOD_SINT_001 | 10_rnf | 2 |

### P3 — higiene

| # | Item | Origem | Onda |
|---|---|---|---|
| 20 | ~~mypy zerado nos módulos novos do delivery~~ **✓ FEITO 2026-06-09** — 0 erros em 7 módulos (`builders`, `parsing`, `extractor`, `pacote`, `motor_entrega`, `orchestrator/entrega`, `reports/cycle_report`) | 10_rnf (RNF-MANU-01) | 1 |
| 21 | ~~Cabeçalho do SDD ("Bloco 1 de 14") corrigido~~ **✓ FEITO 2026-06-10** — SDD status atualizado; Bloco 15 adicionado; tabela Bloco 14.8 expandida | 12_sdd_gaps | 3 |
| 22 | CA-OPE-07 (OneDrive ativo) verificado em ambiente real | 08_persistencia | — |
| 23 | ~~Registrar RF-MV-04 Evoluído no PRD-adendo~~ **✓ FEITO 2026-06-10** — resolução R-13 e RF-MV-04 documentadas no PRD-adendo | 07_motor_saida | 3 |

## Mapa de ondas

- **Onda 1 — Hardening do delivery:** itens 11-14, 20. Pré-requisito: nenhum (merge já feito).
- **Onda 2 — Calibração de agentes:** itens 1-7, 15, 19. Pré-requisito: gabarito (item 1).
- **Onda 3 — Redator/entrega + documentação:** ~~itens 8-10, 21, 23~~ **✓ FEITOS 2026-06-10** (itens 9, 10, 21, 23 concluídos; item 8 parcial: Bloco 15 adicionado, Blocos 4/6/8/9 pendentes).
- **Backlog técnico:** itens 16-18, 22 — não bloqueiam os objetivos de qualidade.
