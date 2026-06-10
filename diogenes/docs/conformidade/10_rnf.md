# Conformidade — Requisitos Não Funcionais (RNF)

> PRD Bloco 4 (linhas 402-534) vs. código em `src/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

## Rastreabilidade (RNF-RAST)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-RAST-01 | Todo raciocínio registrado em arquivo persistente antes da próxima chamada | Conforme | Stranger's Room + `_runtime/`; escrita síncrona no fluxo | — | — | — |
| RNF-RAST-02 | Nenhum arquivo sobrescrito após escrita | Conforme | `StrangerRoomWriteError`; CA-OPE-04 | — | — | — |
| RNF-RAST-03 | Nomes permitem ordenação cronológica | Conforme | Prefixos numerados (SR); timestamps UTC nos cycle_ids | — | — | — |
| RNF-RAST-04 | Leitura humana direta reconstrói o ciclo | Conforme | Markdown puro; validável por CA-QUA-06 | — | — | — |
| RNF-RAST-05 | `audit_index.csv` localiza qualquer ciclo | Conforme | 31+ colunas; `output_filename` registrado | — | — | — |
| RNF-RAST-06 | Trace técnico por chamada LLM | Conforme | `_runtime/llm_calls.jsonl` + JSONs individuais; `LLMCall` em `models.py` | — | — | — |
| RNF-RAST-07 | Reconstrução completa por índice + diretório | Conforme | `diogenes report --cycle` agrega tudo (`reports/cycle_report.py`) | — | — | — |

## Reprodutibilidade (RNF-REPR)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-REPR-01 | Parâmetros completos de cada invocação registrados | Conforme | `LLMCall` com system/user prompt, modelo, temperatura, seed | — | — | — |
| RNF-REPR-02 | Seed determinística por chamada | Conforme | `llm/seed.py` `calcular_seed` | — | — | — |
| RNF-REPR-03 | Modo de re-execução sobre ciclo concluído | Não conforme | Subcomando dedicado ausente | Relevante para benchmark comparativo (MET-10); baixo impacto operacional | P2 | backlog |
| RNF-REPR-04 | Versão do código (git commit) no manifesto | Conforme | `motor_start.py:54` `_git_commit` | — | — | — |
| RNF-REPR-05 | Versão efetiva do modelo registrada | Conforme | `system_fingerprint` no trace quando o provider expõe | — | — | — |

## Custo (RNF-CUST)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-CUST-01 | Custo total USD por ciclo, discriminado por agente | Parcial | Campos no schema e exibição; traces por chamada existem | Agregação ao fim do ciclo não computada (fica `0.00`). Baixo impacto: ChatTCU = custo institucional zero | P2 | backlog |
| RNF-CUST-02 | Teto de custo por ciclo em `runtime.yaml` | Conforme | `LLMCostLimitError`; `teto_custo_ciclo_usd` | — | — | — |
| RNF-CUST-03 | Custo-alvo Fase A = zero (modelos free) | Evoluído | Modelos free OpenRouter abandonados; ChatTCU = custo zero por outra via | — | — | — |
| RNF-CUST-04 | Limites de tokens por chamada e por ciclo | Conforme | `max_tokens: 8000` + `max_tokens_ciclo: 131072` em `agents_spec.yaml` | — | — | — |
| RNF-CUST-05 | Lidar graciosamente com rate-limit de modelos free | Evoluído | OpenRouter free abandonado (rate limit recorrente); retry/backoff genérico no `llm/` | — | — | — |

## Latência (RNF-LATE)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-LATE-01/02 | Ciclo A1 ≤30 min (free) / ≤15 min (baratos) | Não verificável | Ciclos reais MOD_010 ~3h com gpt-5.5 (69 arquivos) — meta do PRD presumia módulo sintético menor | Medir formalmente sobre MOD_SINT_001 e registrar no protocolo (11_aceitacao_metricas.md) | P2 | 2 |
| RNF-LATE-03 | Latência por chamada no trace + aviso de lentidão | Conforme | `LLMCall.duration`; progresso via `rich` | — | — | — |
| RNF-LATE-04 | Motor de Saída em segundos | Conforme | Regex local, sem LLM | — | — | — |
| RNF-LATE-05 | CLI informativa ≤2s | Conforme | Leitura de CSV local | — | — | — |

## Portabilidade (RNF-PORT)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-PORT-01 | Linux/macOS/Windows sem alteração | Conforme | `pathlib` em todo o código; roda em macOS (este host) e Windows (worktree TCU, CLAUDE.md) | — | — | — |
| RNF-PORT-02 | 3 ambientes-alvo sem alteração de código | Parcial | 2 ambientes demonstrados (local macOS + Windows TCU) | Terceiro ambiente (VPS/Azure-sim) não demonstrado — CA-OPE-08 aceita 2 de 3 | P3 | — |
| RNF-PORT-03 | `LLMClient` isola providers | Conforme | `llm/base.py` Protocol + factory `get_llm_client()`; agentes ignoram provider | — | — | — |
| RNF-PORT-04 | Config concentrada em `.env` + `agents_spec.yaml` + `runtime.yaml` | Conforme | `config.py` único leitor (invariante CLAUDE.md §2) | — | — | — |
| RNF-PORT-05 | Sem serviços externos além de LLM + filesystem | Conforme | Sem DB, sem fila, sem observabilidade externa | — | — | — |
| RNF-PORT-06 | Inicialização documentada e curta | Conforme | README + `pip install -e .` + `diogenes init`; Fase de Entrega adiciona `playwright install chromium` (documentado no CLAUDE.md) | — | — | — |

## Observabilidade (RNF-OBSE)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-OBSE-01 | Mensagens estruturadas no console por fase | Conforme | `cli/display.py` (rich) | — | — | — |
| RNF-OBSE-02 | Log técnico JSONL por ciclo | Conforme | `orchestrator/events.py` `EventLogger` → `_runtime/events.jsonl` | — | — | — |
| RNF-OBSE-03 | Traces em `_runtime/llm_calls/` | Evoluído | ChatTCU: `llm_calls.jsonl` consolidado (linha por chamada) + JSONs; intenção preservada | — | — | — |
| RNF-OBSE-04 | `status --cycle` conciso | Conforme | `commands/status.py` | — | — | — |
| RNF-OBSE-05 | Sem observabilidade externa no piloto | Conforme | `diogenes report` é local (equivalente LangSmith sem SaaS) | — | — | — |

## Segurança (RNF-SEGU)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-SEGU-01 | Segredos só em variáveis de ambiente | Conforme | `.env` via `python-dotenv` em `config.py` | — | — | — |
| RNF-SEGU-02 | `.env` gitignored; `.env.example` versionado | Conforme | `.gitignore`; `.env.example` presente | — | — | — |
| RNF-SEGU-03 | Redação automática de segredos nos traces | Parcial | MSAL não trafega API key (mitiga); rotina dedicada de redação não confirmada | Adicionar redação de padrões de segredo na serialização de `LLMCall` | P2 | backlog |
| RNF-SEGU-04 | Inputs do piloto já tratados pelo GT | Conforme | Condição de processo, não de código | — | — | — |
| RNF-SEGU-05 | Sem transmissão a serviços externos além do provider | Conforme | Governança: ChatTCU único em produção (`llm/base.py` guardião; `test_governanca_provider.py`) | — | — | — |
| RNF-SEGU-06 | Controles adicionais ficam para produção Foundry | Conforme | Fora do escopo do piloto (registrado) | — | — | — |

## Manutenibilidade (RNF-MANU)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-MANU-01 | PEP 8 + type hints completos | Parcial | ruff limpo nos arquivos tocados; ~40 erros mypy pré-existentes (dívida conhecida) | Zerar mypy nos módulos novos do delivery | P3 | 1 |
| RNF-MANU-02 | Módulos com responsabilidades delimitadas | Conforme | Estrutura espelha SDD Bloco 2.7 | — | — | — |
| RNF-MANU-03 | Dependências justificadas no `pyproject.toml` | Conforme | Comentário por dependência (inclusive delivery) | — | — | — |
| RNF-MANU-04 | Suíte cobre componentes críticos | Conforme | 305 testes; unit + integration | — | — | — |
| RNF-MANU-05 | E2E da Atividade 1 com mocks | Conforme | `tests/integration/test_ciclo_completo.py` (pytest-httpx) | — | — | — |
| RNF-MANU-06 | README com instalação e operação | Conforme | README presente; CA-OPE-09 marcado ✅ na semente | — | — | — |
| RNF-MANU-07 | PRD/SDD acessíveis no repositório | Conforme | `docs/antecedentes/`, `docs/sdd/` | — | — | — |

## Usabilidade (RNF-USAB)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RNF-USAB-01..05 | `--help` por subcomando; erros acionáveis; confirmação em modificadores; terminologia constitucional; cores TCU-CBS | Conforme | Typer + rich em `cli/`; `test_cli_commands.py` | — | — | — |

**Síntese RNF:** 38 Conforme, 4 Parcial (CUST-01, SEGU-03, MANU-01, PORT-02), 4 Evoluído, 1 Não conforme (REPR-03), 1 Não verificável (LATE-01/02). Nenhum P0.
