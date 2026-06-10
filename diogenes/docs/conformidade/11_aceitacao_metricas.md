# Conformidade — Critérios de Aceitação (CA) e Métricas (MET)

> PRD Blocos 6 (linhas 638-698) e 7 (linhas 806-824) vs. estado real do piloto
> Auditoria: 2026-06-09 | Ciclos executados: 14 em `workspace/cycles/` (8× MOD_010, 4× MOD_010_PILOTO, 2× MOD_SINT_001)
> Este arquivo é também o **protocolo de medição da Onda 2** (calibração de agentes).

## CA Funcionais (CA-FUN)

| Crit | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| CA-FUN-01 | 3 ciclos A1 consecutivos no MOD_SINT_001 | Parcial | 2 ciclos A1 reais executados (20260606T174710Z, 20260607T133139Z); e2e mockado verde | Falta 3º ciclo consecutivo documentado | P1 | 2 |
| CA-FUN-02 | A2 lê histórico do A1 corretamente | Conforme | `test_ciclo_atividade2.py` (integração); `previous_cycle_id` herdado | Execução real de A2 sobre MOD_SINT_001 pendente | P2 | 2 |
| CA-FUN-03 | 2 rodadas completas da Stranger's Room exercitadas | Não verificável | Protocolo implementado (MAX_RODADAS=2); exercício real exige módulo com controvérsia genuína | Verificar nos ciclos reais existentes se houve R2; senão, plantar dilema no MOD_SINT_001 | P2 | 2 |
| CA-FUN-04 | Motor de Saída detecta e bloqueia com marcas plantadas | Conforme | `test_motor_saida.py` (injeção proposital) | — | — | — |
| CA-FUN-05 | Chancela habilitada quando limpo, sem falsos positivos | Conforme | Classificações `CABECALHO_INSTITUCIONAL`/`RODAPE_RASTREABILIDADE` não disparam | — | — | — |
| CA-FUN-06 | Retomada pós-alerta crítico | Conforme | `retomar_apos_alerta` (`orchestrator.py:219`); coberto em integração | — | — | — |
| CA-FUN-07 | Abort registra razão e preserva diretório | Conforme | `commands/abort.py`; `test_cli_commands.py` | — | — | — |
| CA-FUN-08 | Falha graciosa em input/config inválido | Conforme | Exceções tipadas + mensagens acionáveis | — | — | — |
| CA-FUN-09 | `status`/`list`/`show` operam sobre índice | Conforme | `test_cli_commands.py` | — | — | — |
| CA-FUN-10 | Fase D: A1 sobre MOD_010 real com sucesso | Conforme | 8 ciclos MOD_010 executados (melhor: 20260605T103922Z com entrega completa) | Avaliação humana do relatório (CA-QUA-07) pendente | P2 | 2 |

## CA Operacionais (CA-OPE)

| Crit | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| CA-OPE-01..04, 06 | Índice íntegro; diretório preservado; originais intocados; sem sobrescrita; cronologia | Conforme | `audit_index.csv` com 14 ciclos; invariantes testadas | — | — | — |
| CA-OPE-05 | Custo por ciclo registrado | Parcial | Traces por chamada existem; agregação não computada (ver RNF-CUST-01) | — | P2 | backlog |
| CA-OPE-07 | Operação sob OneDrive ativo | Não verificável | Verificação ambiental pendente | — | P3 | — |
| CA-OPE-08 | ≥2 ambientes-alvo sem alteração de código | Conforme | macOS local + Windows TCU (worktree) documentados no CLAUDE.md | — | — | — |
| CA-OPE-09 | README permite operação por operador novo | Conforme | README + CLAUDE.md; instalação verificada nesta auditoria (`pip install -e ".[dev]"` limpo) | — | — | — |
| CA-OPE-10 | Suíte verde com cobertura ≥70% | Conforme | 305 passando / 1 skipped; **cobertura 75%** (`pytest --cov=diogenes`, 2026-06-09) | Hotspots <20%: `orchestrator/entrega.py` (14%), `cli/commands/autorun.py` (16%), `cli/commands/deliver.py` (19%), `irene_chattcu.py` (0%) — golden tests da Onda 1 atacam os dois primeiros | P2 | 1 |

## CA Qualitativos (CA-QUA) — exigem avaliação humana (Lestrade)

| Crit | Resumo | Status | Observação |
|---|---|---|---|
| CA-QUA-01 | Detecção ≥70% das inconsistências propositais | Não verificável | Gabarito criado 2026-06-10 (`docs/conformidade/gabarito_mod_sint_001.md` — 4 INC primárias); aguarda ciclo de baseline |
| CA-QUA-02 | Relatório institucional, impessoal, classificação coerente | Não verificável | Scaffold em `docs/avaliacao_piloto.md`; veredicto pendente |
| CA-QUA-03 | Stranger's Room como deliberação técnica real | Não verificável | Idem |
| CA-QUA-04 | Relatório Final A2 usa histórico A1 efetivamente | Não verificável | Exige execução real A2 |
| CA-QUA-05 | Dilemas com raciocínio ponderado de Mycroft | Não verificável | Idem |
| CA-QUA-06 | Auditor externo reconstrói o ciclo pelos arquivos | Não verificável | Idem |
| CA-QUA-07 | Fase D: relatório sobre MOD_010 com utilidade técnica real | Não verificável | 8 ciclos disponíveis para avaliação; usar 20260605T103922Z |

## Métricas de Benchmark (MET-01..10)

| Met | Resumo | Instrumentação | Status |
|---|---|---|---|
| MET-01 | Custo USD total por execução | Traces por chamada; agregação pendente (RNF-CUST-01) | Parcial |
| MET-02 | Latência total do ciclo | `events.jsonl` + `LLMCall.duration`; agregação manual via `diogenes report` | Conforme |
| MET-03 | Tokens por agente/chamada | `LLMCall` registra input/output tokens | Conforme |
| MET-04 | Taxa de detecção de inconsistências (meta ≥70%) | Avaliação humana com tabela de pontuação de `gabarito_mod_sint_001.md` | Não verificável |
| MET-05 | Taxa de falsos positivos (meta <15%) | Alertas emitidos que não correspondem a INC-01..06 / total de alertas | Não verificável |
| MET-06 | Qualidade da classificação semântica | Avaliação humana sobre detecções corretas | Não verificável |
| MET-07 | Qualidade da fundamentação metodológica | Avaliação humana; **métrica-alvo da Onda 2** (citação normativa rastreável) | Não verificável |
| MET-08 | Aderência ao protocolo Stranger's Room | Avaliação qualitativa (4 níveis) | Não verificável |
| MET-09 | Impessoalidade (marcas internas) | Automática via Motor de Saída (`ocorrencias_*` no índice) | Conforme |
| MET-10 | Estabilidade entre 3 execuções | Exige RNF-REPR-03 (re-execução) ou 3 runs manuais | Parcial |

---

## Protocolo de medição da Onda 2 (calibração de agentes)

**Pré-requisito P1 — gabarito:** ✓ **CRIADO 2026-06-10** em `docs/conformidade/gabarito_mod_sint_001.md`.
Contém: 4 INC primárias (INC-01..04) + 2 latentes (INC-05/06) + 6 verdadeiros negativos + tabela de pontuação para MET-04..07.

**Baseline (antes de mudar prompts):**
1. 1 ciclo A1 completo sobre MOD_SINT_001 com a config atual (`gpt-5.5-thinking` via ChatTCU).
2. Pontuar contra o gabarito: MET-04 (detecção), MET-05 (FP), MET-06 (classificação), MET-07 (fundamentação — % de ocorrências com citação normativa rastreável).
3. MET-09 lido do `audit_index.csv` (ocorrências do Motor de Saída).
4. Registrar em `bench/results/` no formato das execuções comparativas anteriores.

**Por iteração de calibração:**
- Iterar prompt → `diogenes bench preview/call` (validação cirúrgica) → 1 ciclo A1 completo → repontuar.
- Critério de aceite da Onda 2: MET-04 ≥ baseline e ≥70%; MET-07 ≥ baseline; sem regressão em MET-05 (<15%) e MET-09; MET-02/03 dentro dos tetos (`max_tokens_ciclo: 131072`).

**Encerramento:** transcrever veredictos para `docs/avaliacao_piloto.md` (CA-QUA) — exige ≥6 de 7 positivos (PRD 6.5).
