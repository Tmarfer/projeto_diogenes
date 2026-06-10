# Auditoria de Conformidade — PRD/SDD vs. Implementação

> **⚠️ SUBSTITUÍDA (2026-06-09):** esta auditoria foi expandida e substituída pela
> **Matriz de Conformidade** em [`docs/conformidade/00_INDICE.md`](conformidade/00_INDICE.md)
> (evidência por `arquivo:linha`, prioridades P0-P3 e mapeamento para ondas de refatoração).
> Este arquivo é preservado como registro histórico do estado em 2026-06-03.

> **Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU
> **Data:** 2026-06-03
> **Escopo:** mapeamento dos requisitos funcionais (RF-*), não funcionais (RNF-*) e
> critérios de aceitação (CA-*) do `PRD_Piloto_Diogenes_v01.md` contra o código em `src/`.
> **Baseline de testes:** 188 passando / 1 falha de ambiente (`docling` não instalado neste host).

---

## Legenda de status

| Símbolo | Significado |
|---|---|
| ✅ | Atendido — implementado e verificável por código/teste |
| 🟡 | Parcial — implementado com lacuna pontual |
| 🔵 | Evoluído — intenção do requisito preservada, mas o meio mudou (ver nota) |
| ❌ | Não atendido |
| 📋 | Verificação manual/qualitativa pendente (próprio do CA-QUA e parte do CA-OPE) |

> **Nota transversal sobre provider.** O PRD foi redigido assumindo **OpenRouter** como
> provider do piloto (Fases A/B/D). A implementação **evoluiu para ChatTCU** (infra interna
> TCU, custo institucional zero) por governança de dados fiscais. Onde um requisito cita
> "OpenRouter" nominalmente, o status é 🔵 e a intenção (abstração de provider — RNF-PORT-03)
> está preservada: `get_llm_client()` isola o provider e a troca é feita em `.env`/`agents_spec.yaml`.

---

## 1. Requisitos Funcionais

### Motor de Start (RF-MS) — `motors/motor_start.py`

| Req | Status | Evidência |
|---|---|---|
| RF-MS-01 | ✅ | `run(module_id, activity)`; CLI `start --module --activity` |
| RF-MS-02 | ✅ | `_verificar_inputs`; A2 exige A1 encerrado via `_resolver_ciclo_anterior` |
| RF-MS-03 | ✅ | `_sha256_file` por arquivo + `package_hash` |
| RF-MS-04 | ✅ | `_generate_cycle_id` → `{MOD}_A{ativ}_{ISO8601Z}`; colisão barrada |
| RF-MS-05 | ✅ | `write_manifesto`; **A2 agora grava `previous_cycle_id`** (corrigido nesta sessão) |
| RF-MS-06 | ✅ | `WorkspaceManager.criar_estrutura_ciclo` (inputs/ stranger_room/ output/) |
| RF-MS-07 | ✅ | cópia para `inputs/` + verificação de integridade (`CopyIntegrityError`); originais intocados |
| RF-MS-08 | ✅ | retorna manifest; CLI exibe caminho e aguarda `confirm-manifest` |
| RF-MS-09 | ✅ | `audit.add_cycle` com status `PREPARADO` |

### Orquestrador (RF-OR) — `orchestrator/orchestrator.py`

| Req | Status | Evidência |
|---|---|---|
| RF-OR-01 | ✅ | fluxo síncrono single-process; sem threads/asyncio (Art. 3) |
| RF-OR-02 | ✅ | `confirm-manifest` → `executar(manifest)`; tasks via `definir_tasks_watson` |
| RF-OR-03 | ✅ | tasks de Mycroft executadas sem reordenação |
| RF-OR-04 | ✅ | `MAX_RODADAS = 2`; loop `while rodada < MAX_RODADAS` |
| RF-OR-05 | ✅ | `decisao_watson.has_critical_alert` → `AGUARDANDO_DECISAO_LESTRADE_ALERTA` + evento |
| RF-OR-06 | ✅ | `montar_pacote_sherlock` (inventário + decisão Watson + metodologia + corpus) |
| RF-OR-07 | ✅ | mesmo protocolo de 2 rodadas em `sherlock_validacao` |
| RF-OR-08 | ✅ | `_consolidar_output_final` → relatório por atividade |
| RF-OR-09 | ✅ | persiste em `output/`; `AGUARDANDO_VERIFICACAO_SAIDA` |
| RF-OR-10 | ✅ | `_abortar_por_falha` → `ABORTADO_FALHA_AGENTE` sem corromper o índice |
| RF-OR-11 | ✅ | `_transicionar` valida `TRANSICOES_VALIDAS` e grava status |

### Mycroft (RF-MY) — `agents/mycroft.py`

| Req | Status | Evidência |
|---|---|---|
| RF-MY-01 | ✅ | `definir_tasks_watson` lê manifesto e produz tasks ordenadas |
| RF-MY-02 | ✅ | sem tools de leitura direta; opera só sobre outputs (sem parsing próprio) |
| RF-MY-03 | ✅ | `avaliar_*` (APROVADO/QUESTIONAR) + `fixar_decisao_*` |
| RF-MY-04 | ✅ | crítica única, localizada e fundamentada (template `avaliar_agente`) |
| RF-MY-05 | ✅ | `fixar_decisao_*` após 2ª rodada independe da concordância |
| RF-MY-06 | ✅ | `### Alertas Críticos / CONTAGEM: N` parseado pelo orquestrador |
| RF-MY-07 | ✅ | `consolidar` → "Relatório Preliminar"/"Relatório Final"; 3ª pessoa, impessoal |
| RF-MY-08 | ✅ | **A2: `consolidar(historico_a1=...)` incorpora histórico do ciclo anterior** (corrigido nesta sessão) |

### Watson (RF-WA) — `agents/watson.py`

| Req | Status | Evidência |
|---|---|---|
| RF-WA-01 | ✅ | recebe `tasks_mycroft`; análise por arquivo do manifesto |
| RF-WA-02 | ✅ | sem injeção de metodologia; regra de não-interpretação no soul/skills |
| RF-WA-03 a 06 | ✅ | `analisar_arquivo` cobre planilha/SQL/notebook/cadeia de produção (via `file_prep`) |
| RF-WA-07 | ✅ | seção de análises extrapolativas segregada (skills.md) |
| RF-WA-08 | ✅ | seção "Arquivos Não Analisáveis"; não aborta os demais |
| RF-WA-09 | ✅ | severidade CRÍTICA/ATENÇÃO/INFORMATIVA; contagem de cabeçalho |
| RF-WA-10 | ✅ | output estruturado; `**Alertas CRITICA:** N` legível por máquina |

### Sherlock (RF-SH) — `agents/sherlock.py`

| Req | Status | Evidência |
|---|---|---|
| RF-SH-01 | ✅ | recebe pacote integrado por Mycroft |
| RF-SH-02 | ✅ | sem tools de Camada 0; opera sobre pacote saneado |
| RF-SH-03 | ✅ | metodologia (cat. C) + corpus jurídico (cat. D) carregados no pacote |
| RF-SH-04 | ✅ | classificação semântica TCU-CBS (Atendido/Divergência/…) |
| RF-SH-05 | ✅ | dilemas registrados (`dilemmas_count`) e encaminhados a Mycroft |
| RF-SH-06 | 🟡 | fundamentação por ponto exigida no template; reprodutibilidade de cálculo é qualitativa |
| RF-SH-07 | ✅ | relatório ponto a ponto + encaminhamento ao contraditório |
| RF-SH-08 | ✅ | output estruturado equivalente ao de Watson |

### Stranger's Room (RF-SR) — `orchestrator/stranger_room.py`

| Req | Status | Evidência |
|---|---|---|
| RF-SR-01 | ✅ | `stranger_room/{watson_integridade,sherlock_validacao}/` |
| RF-SR-02 | ✅ | nomes `01_apresentacao` … `99_decisao_final` |
| RF-SR-03 | ✅ | frontmatter YAML (`StrangerRoomFile`) com hash de conteúdo |
| RF-SR-04 | ✅ | escrita única; `StrangerRoomWriteError` impede sobrescrita (Art. 11) |
| RF-SR-05 | ✅ | leitura sequencial reconstrói a deliberação |
| RF-SR-06 | ✅ | `update_watson_metadata`/`update_sherlock_metadata` no índice |

### Motor de Saída (RF-MV) — `motors/motor_saida.py`

| Req | Status | Evidência |
|---|---|---|
| RF-MV-01 | ✅ | `verify-output --cycle` sobre o documento de output |
| RF-MV-02 | ✅ | varre nomes de agente, cargos identificadores, estruturas internas, cycle_id |
| RF-MV-03 | ✅ | `OcorrenciaDetectada` (linha, contexto, posição, classificação) |
| RF-MV-04 | 🔵 | **Divergência deliberada:** em vez de exigir decisão tripla de Lestrade, o Motor **auto-higieniza** (Art. 14/15) e re-varre; só habilita chancela se ficar limpo. O caminho "aceitar com justificativa" existe via `seal --accept-occurrences --reason`. |
| RF-MV-05 | ✅ | `update_motor_saida` grava timestamp, ocorrências e hash |
| RF-MV-06 | ✅ | exclusivamente heurístico (regex/keywords); auditável por leitura direta |

### Persistência (RF-PE) — `persistence/audit_index.py`, `models.py`

| Req | Status | Evidência |
|---|---|---|
| RF-PE-01 | ✅ | `DIOGENES_WORKSPACE` via `config.py` |
| RF-PE-02 | ✅ | estrutura `input/`, `cycles/{id}/…`, `audit_index.csv` |
| RF-PE-03 | 🔵 | schema **superset** de 31 colunas (`AUDIT_INDEX_COLUMNS`) inclui os campos do PRD + tokens/custo/Irene |
| RF-PE-04 | ✅ | `_write_atomic` (mkstemp + `replace`) |
| RF-PE-05 | ✅ | sem lock files; `pathlib`; nomes compatíveis com sync |

### CLI (RF-CL) — `cli/commands/`

| Req | Status | Evidência |
|---|---|---|
| RF-CL-01 a 12 | ✅ | subcomandos `start, confirm-manifest, proceed, pause, resume, verify-output, seal, abort, status, list, show` presentes |
| RF-CL-08 | ✅ | `seal` falha se não passou por `verify-output` (exige `AGUARDANDO_CHANCELA_LESTRADE`) |
| RF-CL-13 | ✅ | comandos informativos idempotentes; modificadores falham antes de escrever |

---

## 2. Requisitos Não Funcionais (síntese)

| Dimensão | Status | Nota |
|---|---|---|
| RNF-RAST-01..07 | ✅ | escrita antes da próxima chamada; sem sobrescrita; `audit_index` + `_runtime/`; traces LLM persistidos |
| RNF-REPR-01,02,04,05 | ✅ | `LLMCall` com prompt/seed; `calcular_seed`; `git_commit` no manifesto; `system_fingerprint` no trace |
| RNF-REPR-03 | ❌ | **modo de re-execução de ciclo concluído não implementado** (subcomando dedicado ausente) |
| RNF-CUST-01 | 🟡 | campos `custo_total_usd`/`tokens_*` existem no schema e são exibidos, mas **não são agregados ao fim do ciclo**. Baixo impacto: ChatTCU = custo institucional zero. Traces por chamada existem. |
| RNF-CUST-02 | ✅ | teto por ciclo (`LLMCostLimitError`); `teto_custo_ciclo_usd` |
| RNF-CUST-04 | ✅ | `max_tokens` por chamada + `max_tokens_ciclo` em `agents_spec.yaml` |
| RNF-LATE-* | 🟡 | latência registrada por chamada; aviso de progresso via `rich`. Metas de 15/30 min não medidas formalmente. |
| RNF-PORT-01..06 | ✅ | `pathlib`; 3 arquivos de config; `LLMClient` isola provider; `pip install -e .` + `diogenes init` |
| RNF-OBSE-01,02,04 | ✅ | console `rich`; `events.jsonl`; `status` agrega estado |
| RNF-OBSE-03 | 🔵 | OpenRouter: 1 JSON/chamada em `llm_calls/`. ChatTCU: `llm_calls.jsonl` (linha por chamada). Intenção (RNF-RAST-06) preservada. |
| RNF-SEGU-01,02 | ✅ | segredos só em `.env` (gitignored); `.env.example` versionado |
| RNF-SEGU-03 | 🟡 | autenticação ChatTCU via MSAL (sem API key em trafego); redação explícita de segredos não confirmada como rotina dedicada |
| RNF-MANU-01..07 | ✅ | ruff/type hints; suíte com mocks; e2e em `tests/integration/`; README aponta PRD/SDD |
| RNF-USAB-01..05 | ✅ | `--help` por subcomando; mensagens de erro acionáveis; `rich` |

---

## 3. Critérios de Aceitação

### Funcionais (CA-FUN)

| Crit | Status | Nota |
|---|---|---|
| CA-FUN-01 | 🟡 | ciclo A1 e2e validado por mocks e por `bench pipeline 10/10`; execução real 3× pendente (módulo sintético) |
| CA-FUN-02 | ✅ | **A2 herda `previous_cycle_id` e incorpora histórico** — coberto por `test_ciclo_atividade2.py` |
| CA-FUN-03 | 📋 | protocolo de 2 rodadas implementado; exercício real com módulo controverso pendente |
| CA-FUN-04 | ✅ | Motor de Saída detecta marcas injetadas (testes de `motor_saida`) |
| CA-FUN-05 | ✅ | termos genéricos não disparam (classificação `CABECALHO_INSTITUCIONAL`/`RODAPE_RASTREABILIDADE`) |
| CA-FUN-06 | ✅ | `proceed` retoma após alerta crítico (`retomar_apos_alerta`) |
| CA-FUN-07 | ✅ | `abort` registra razão e preserva diretório |
| CA-FUN-08 | ✅ | falhas de input/config com mensagem acionável |
| CA-FUN-09 | ✅ | `status`/`list`/`show` sobre o índice |
| CA-FUN-10 | 📋 | Fase D MOD_010 — execução real em produção pendente (fora do escopo desta sessão) |

### Operacionais (CA-OPE)

| Crit | Status | Nota |
|---|---|---|
| CA-OPE-01..04, 06 | ✅ | índice íntegro; diretório preservado; originais intocados; sem sobrescrita; cronologia coerente |
| CA-OPE-05 | 🟡 | custo agregado por ciclo não computado (ver RNF-CUST-01) |
| CA-OPE-07 | 📋 | operação sob OneDrive ativo — verificação ambiental pendente |
| CA-OPE-08 | 🟡 | portabilidade por código garantida; execução em ≥2 ambientes a documentar |
| CA-OPE-09 | ✅ | README com instalação + operação básica |
| CA-OPE-10 | 🟡 | 188 testes passando; cobertura ≥70% a medir com `pytest --cov` |

### Qualitativos (CA-QUA)

| Crit | Status |
|---|---|
| CA-QUA-01..07 | 📋 — exigem avaliação humana documentada (`docs/avaliacao_piloto.md`) |

---

## 4. Lacunas remanescentes (priorizadas)

1. **RNF-REPR-03** — modo de re-execução de ciclo concluído (subcomando) **não implementado**.
   Impacto: baixo no piloto; relevante para auditoria comparativa de modelos.
2. **RNF-CUST-01 / CA-OPE-05** — agregação de custo/tokens por ciclo no `audit_index`.
   Impacto: baixo (ChatTCU = custo zero), mas o campo existe e fica sempre em `0.00`.
3. **CA-FUN-01/03, CA-QUA-\*** — dependem do **módulo sintético `MOD_SINT_001`**, hoje
   ausente do workspace, e de execução real + avaliação humana.
4. **CA-FUN-10 / CA-QUA-07** — execução real da Fase D sobre MOD_010 (não solicitada nesta sessão).

## 5. Divergências deliberadas (não são defeitos)

- **RF-MV-04** — auto-higienização do Motor de Saída em vez de decisão tripla obrigatória.
- **Provider** — ChatTCU substitui OpenRouter por governança de dados fiscais (RNF-PORT-03 honrado).
- **RF-PE-03** — schema do índice é superset do exigido.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Auditoria gerada em 2026-06-03 — reflete o estado pós-implementação da Atividade 2.*
