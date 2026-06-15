# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este projeto

Sistema agêntico de validação da alíquota de referência da CBS para o TCU
(TC 015.848/2025-6). Três agentes LLM auditores (Mycroft, Watson, Sherlock)
operam sequencialmente sob supervisão de um auditor humano (Lestrade), precedidos
por uma fase de catalogação semântica (Irene) que prepara o pacote para Watson.

**Documentos de referência:**
- `docs/antecedentes/PRD_Piloto_Diogenes_v01.md` — requisitos do piloto
- `docs/sdd/SDD_Piloto_Diogenes_v01.md` — arquitetura de software (fonte da verdade)
- `docs/agentes/` — definição dos agentes (soul, skills, agent, heartbeat)
- `INTEGRACAO_DIOGENES.md` — integração do pipeline Irene (catalogação) no Orquestrador

---

## Arquitetura dos agentes

Os três agentes auditores (Mycroft, Watson, Sherlock) e a catalogadora Irene têm
arquivos em `docs/agentes/{agente}/`:

| Arquivo | Uso |
|---------|-----|
| `soul.md` | Identidade, valores e limites constitucionais do agente |
| `skills.md` | Templates de output, critérios de classificação, formatos de seção |
| `heartbeat.md` | Protocolo operacional por call_type — injetado no início do user_prompt |
| `agent.md` | Parâmetros de runtime lidos pelo invocador (valores reais vêm de `agents_spec.yaml`) |

**Construção de prompt — padrão para os três agentes:**
```python
system_prompt = soul.md + "\n\n---\n\n" + skills.md   # lidos do filesystem a cada chamada
user_prompt   = heartbeat.md[call_type] + "\n\n" + inputs
```

Os arquivos são lidos do filesystem a cada chamada — **não são cacheados**. Editar
`soul.md` ou `skills.md` durante o piloto tem efeito imediato na próxima chamada.

**Fluxo obrigatório:** Watson → Mycroft → Sherlock. Watson nunca entrega diretamente
a Sherlock. Todo encaminhamento passa por Mycroft.

**Novos call_types exigem:**
1. Método no invocador Python (`agents/{agente}.py`)
2. Entrada em `agents_spec.yaml`
3. Seção `# Heartbeat de {Agente} — {call_type}` no `heartbeat.md` do agente

**Call_types condicionais** (só acionados quando a Planilha de Verificação está
listada no manifesto):
- `watson.validacao_planilha_rn`
- `sherlock.validacao_planilha_rn_sherlock`

---

## Estrutura do repositório

```
projeto_diogenes/          ← raiz do repositório
  diogenes/                ← pacote Python (trabalhe aqui — é o CWD de todos os comandos)
    src/diogenes/          ← código fonte
    tests/                 ← testes (unit/ + integration/ + fixtures/)
    docs/                  ← PRD, SDD, definição dos agentes
    agents_spec.yaml       ← modelos LLM por agente e fase
    runtime.yaml           ← parâmetros operacionais (ciclo, motor_saida, persistência)
    .env                   ← provider, workspace, flags Irene (não versionado)
    AUDITORIA_*.md / ESTADO_DIOGENES.md  ← relatórios de execução do piloto
  workspace/               ← workspace de runtime (cycles/, input/, _bench/) — gitignored
```

---

## Comandos de desenvolvimento

**Todos os comandos devem ser executados de dentro de `diogenes/`**, pois
`config.py` carrega `runtime.yaml` e `agents_spec.yaml` relativamente ao CWD.

```bash
cd diogenes

# Instalar
pip install -e ".[dev]"

# Fase de Entrega (geração dos entregáveis institucionais) — passo extra obrigatório:
python -m playwright install chromium   # render HTML→PDF/PNG das fichas síntese
# (python-docx e matplotlib já vêm nas dependências do pacote)

# Rodar todos os testes
pytest tests/

# Rodar um único teste
pytest tests/unit/test_motor_start.py::NomeDoTeste -v

# Rodar testes de integração
pytest tests/integration/ -v

# Lint
ruff check src/ tests/

# Formatação
ruff format src/ tests/

# Type check
mypy src/

# Bancada cirúrgica — testar prompts/modelos/conectividade sem rodar o ciclo completo
diogenes bench smoke                                          # checa conectividade
diogenes bench validate-models                                # valida modelos do agents_spec.yaml
diogenes bench preview watson --call-type analise_inicial --prompt "teste"  # monta prompt sem chamar LLM
diogenes bench call watson --call-type analise_inicial --prompt "Responda OK" # chamada real isolada
```

Subcomandos do ciclo: `init`, `start`, `confirm-manifest`, `status`, `list`,
`show`, `proceed`, `pause`, `resume`, `abort`, `verify-output`, `seal`,
`complete-sherlock`, `report`. Cada um vive em `cli/commands/{nome}.py`.

```bash
# Painel de acompanhamento local (equivalente ao LangSmith — dados ficam na máquina)
diogenes report --cycle <id>                   # Markdown no terminal
diogenes report --cycle <id> --format html     # HTML no browser (abre automaticamente)
```

---

## Stack e estrutura

```
Python 3.11+ | openai SDK | msal+requests (ChatTCU) | Typer CLI | Pydantic v2 | pytest
file_prep: openpyxl (xlsx) · sqlparse (sql) · nbformat (ipynb) · pdfminer.six (pdf)
```

```
src/diogenes/
  agents/      — Watson, MycrooftAgent, Sherlock + heartbeat + file_prep
                 (file_prep: ARQUIVOS_SEMPRE_ANALISE libera protocolo_recebimento.md + inventario.xlsx)
  bench/       — bancada cirúrgica: core.py + pipeline.py + prompt_builder.py
                 (pipeline herda DIOGENES_CORPUS_JURIDICO_DIR do .env quando --legal-corpus ausente)
  cli/         — app.py + commands/ (um arquivo por subcomando, incl. report.py, deliver.py) + commands/bench/
  config.py    — get_config() com @lru_cache — ÚNICO ponto de leitura de config
  delivery/    — Fase de Entrega: parsing + extractor (openpyxl) + dashboard + builders + pacote
                 (schema canônico em models.py; geradores TCU vendorizados em vendor/tcu/)
  irene.py     — wrapper do pipeline Irene (C1-C5); catalogação semântica pré-Watson
  llm/         — base.py (Protocol/factory) + chattcu.py + openrouter.py + azure_foundry.py + seed.py + call_id.py
  models.py    — TODOS os dataclasses de domínio (LLMCall, CycleRecord, PacoteEntrega, etc.)
  motors/      — motor_start.py + motor_saida.py + motor_entrega.py (determinístico, sem LLM)
  orchestrator/— orchestrator.py + states.py + stranger_room.py + events.py + entrega.py
                 (EventLogger.log() regenera report.html em _cycle_dir/ após cada evento — best-effort)
  persistence/ — audit_index.py + manifest.py + workspace.py
  reports/     — cycle_report.py + render_markdown.py + render_html.py (painel de acompanhamento)
```

### Papéis dos módulos-chave

| Módulo | Responsabilidade |
|--------|-----------------|
| `config.py` | Único ponto de leitura: `.env` + `agents_spec.yaml` + `runtime.yaml` |
| `models.py` | Todos os dataclasses de domínio — sem lógica, sem imports internos |
| `agents/file_prep.py` | Converte xlsx/sql/ipynb/pdf/md em texto para incluir nos prompts de Watson |
| `orchestrator/stranger_room.py` | Persiste arquivos imutáveis Markdown+frontmatter YAML da revisão Mycroft ↔ Watson/Sherlock |
| `orchestrator/events.py` | `EventLogger` — grava JSONL de auditoria + regenera `report.html` ao vivo (best-effort) |
| `reports/cycle_report.py` | `build_report()` agrega eventos/LLM calls/audit_index em `CycleReportData` |
| `persistence/audit_index.py` | Lê/grava `audit_index.csv` com escrita atômica (temp + rename) |
| `llm/base.py` | `LLMClient` Protocol + factory `get_llm_client()` + guardião de governança de provider |
| `irene.py` | `executar_irene()` chama os estágios C1-C5 do pipeline Irene como biblioteca e devolve `(estado, metricas)` ao Orquestrador |

### LLM Providers — governança crítica

**ChatTCU é o ÚNICO provider permitido em produção.** Dados fiscais do
TC 015.848/2025-6 não podem trafegar por serviços externos. `get_llm_client()`
(em `llm/base.py`) é o guardião: levanta `ConfigError` para `openrouter` fora de
contexto pytest, e para qualquer provider != `chattcu`.

`get_llm_client()` tem **duas assinaturas**:
- `get_llm_client(cfg: DiogenesConfig)` → caminho de validação de governança (só valida, não instancia)
- `get_llm_client(cycle_id: str, runtime_dir: Path)` → caminho de produção (instancia o cliente real)

Provider selecionado por `DIOGENES_LLM_PROVIDER` no `.env` (default `chattcu`):
- `chattcu` → `ChatTCUClient` (infra interna TCU; autenticação **MSAL**, sem API key — o browser abre na 1ª execução)
- `azure` → `AzureFoundryClient`
- `openrouter` → `OpenRouterClient` (**bloqueado em produção**; permitido apenas sob `PYTEST_CURRENT_TEST` para mocks com `pytest-httpx`)

Em redes com proxy de inspeção SSL (TCU), definir `DIOGENES_SSL_VERIFY=false`.

---

## Regras arquiteturais inegociáveis (SDD Bloco 1.2)

1. **Sequencialidade absoluta:** código síncrono — sem threads, sem asyncio entre
   agentes. Artigo 3 da Constituição.
2. **`config.py` é o único ponto de leitura de configuração.** Nenhum módulo
   importa `os.environ` diretamente ou lê YAML fora de `config.py`.
3. **`models.py` não importa nenhum módulo interno.** Quebrar essa regra causa
   importação circular.
4. **Stranger Room é imutável.** Arquivos escritos nunca são sobrescritos
   (Artigo 11). `StrangerRoomWriteError` é o guardião.
5. **Motor de Saída não usa LLM.** Apenas heurísticas de string matching/regex.
6. **Originais do pacote RFB nunca são alterados.** O sistema trabalha
   exclusivamente com cópias em `workspace/cycles/{cycle_id}/inputs/`.

---

## Nomenclatura crítica

| No código | Significado |
|-----------|-------------|
| `MycrooftAgent` | Mycroft Holmes — Auditor Chefe (grafia do SDD, com dois 'o') |
| `WatsonAgent` | Dr. Watson — Auditor de Integridade Técnica |
| `SherlockAgent` | Sherlock Holmes — Auditor de Validação Metodológica CBS |
| `StrangerRoom` | Protocolo de revisão Mycroft ↔ Watson/Sherlock |
| `cycle_id` | `{MOD_ID}_A{ATIV}_{TIMESTAMP_UTC}` ex: `MOD_010_A1_20260510T143000Z` |
| `FASE_WATSON` | `"watson_integridade"` |
| `FASE_SHERLOCK` | `"sherlock_validacao"` |

---

## Configuração de ambiente

```bash
# .env obrigatório (copiar de .env.example)
DIOGENES_LLM_PROVIDER=chattcu                              # ÚNICO valor permitido em produção
DIOGENES_CHATTCU_BASE_URL=https://chat-tcu.apps.tcu.gov.br # produção pública; URL desenvol dentro da VPN
DIOGENES_WORKSPACE=/caminho/absoluto/workspace
# ChatTCU autentica via MSAL — sem API key. O browser abre na 1ª execução.

# Irene (fase de catalogação pré-Watson)
DIOGENES_IRENE_HABILITADO=true
IRENE_PROVIDER=chattcu
IRENE_MODEL=gpt-5.5-thinking

# Opcionais
DIOGENES_SSL_VERIFY=false        # em redes TCU com proxy de inspeção SSL
DIOGENES_DEV_MODE=false          # true → retries/timeouts curtos, bloqueia seal, habilita IRENE_C4_SAMPLE_N
IRENE_C4_SAMPLE_N=0              # limita catalogação C4/C5 a N abas (só honrado em DEV_MODE)
DIOGENES_POST_IRENE_COOLDOWN_S=0 # pausa após Irene antes de Mycroft/Watson (ignorada em DEV_MODE)
DIOGENES_CORPUS_JURIDICO_DIR=/caminho/ARCABOCO_JURIDICO  # arcabouço jurídico curado (cat. D)
                                                          # recorte por módulo derivado automaticamente

# Inicializar workspace (rodar de dentro de diogenes/)
diogenes init
```

> **Nota:** o modelo legado usava `DIOGENES_ENV` + `DIOGENES_LLM_API_KEY`/`DIOGENES_LLM_BASE_URL`
> para selecionar OpenRouter/Azure. Esses campos ainda existem em `LLMConfig` por
> compatibilidade com testes, mas **o provider real é `DIOGENES_LLM_PROVIDER`**.

**Worktree local:** o projeto roda em worktree (`C:\Projetos\Projeto_Diogenes\...`).
A worktree não herda `.env` nem `workspace/` (gitignored). Copiar o `.env` do repo
local principal e ajustar `DIOGENES_WORKSPACE` para um workspace isolado dentro da
worktree. Rodar `pip install -e .` de dentro da worktree.

---

## Fases do piloto e modelos ativos

A configuração corrente roda **todos os modelos via ChatTCU** (provider institucional,
custo zero por chamada — `teto_custo_ciclo_usd: 0.00`). Os nomes de modelo em
`agents_spec.yaml` devem ser escritos **exatamente como listados na plataforma ChatTCU**
(ex: `gpt-5.5-thinking`, `Claude 4.6 Sonnet`), sem prefixo de organização.

**`agents_spec.yaml` é a fonte da verdade dos modelos ativos** — sempre consulte-o
antes de assumir; a frente de avaliação alterna entre famílias (`gpt-5.4-thinking`,
`gpt-5.5-thinking`, Claude) e os relatórios `AUDITORIA_COMPARATIVA_*.md` documentam
essas comparações.

`max_tokens` é conservador no piloto ChatTCU (`8000`/agente, `max_tokens_ciclo:
131072`); escalar na Fase D de produção.

Para trocar de modelo/fase: editar `agents_spec.yaml` — comentar/descomentar as
linhas `modelo` por agente e atualizar `fase_ativa` e `teto_custo_ciclo_usd`.

> **Nota de nomenclatura:** `agents_spec.yaml` rotula a config atual como
> `fase_ativa: B`. O campo `fase_ativa` é livre (string, default `"A"`) e serve
> apenas para rastreabilidade — não altera comportamento. Alinhar quando
> conveniente; não é bloqueante.
>
> **OpenRouter / modelos free foram abandonados** — modelos free causavam rate
> limit recorrente e OpenRouter é bloqueado por governança (dados fiscais). Não
> reintroduzir.

---

## Fluxo do ciclo completo

```
diogenes start --module MOD_010 --activity 1
  → Motor de Start: verifica inputs, SHA-256, cria workspace/cycles/{id}/
  → Gera manifest.md, registra PREPARADO no audit_index.csv

diogenes confirm-manifest --cycle {id}
  → Orchestrator.executar():

      [FASE IRENE]  (CONDICIONAL: só se DIOGENES_IRENE_HABILITADO=true)
      executar_irene()  → estados AGUARDANDO_IRENE → IRENE_CONCLUIDA
        ↳ catalogação semântica C1-C5 dos XLSX/CSV; reusa catálogo existente se
          versão ≥ VERSAO_IRENE_MINIMA, senão roda o pipeline
        ↳ IRENE_ERRO_FATAL → ABORTADO_FALHA_AGENTE (IRENE_BLOQUEADO não é fatal —
          Watson recebe o catálogo com ressalvas)

      [FASE WATSON]
      Mycroft.definir_tasks_watson()             [heartbeat: definir_tasks_watson]
        ↳ inclui premissas globais e verifica se
          Planilha de Verificação está no manifesto
      Watson.analisar_arquivo() × N arquivos     [heartbeat: analise_arquivo]
      Watson.consolidar()                        [heartbeat: consolidar_watson]
      Watson.validacao_planilha_rn()             [heartbeat: validacao_planilha_rn]
        ↳ CONDICIONAL: só se Planilha de Verificação
          estiver listada no manifesto
      Mycroft.avaliar_watson()                   [heartbeat: avaliar_agente]
        [até 2 rodadas de revisão]
      Mycroft.fixar_decisao_watson()             [heartbeat: fixar_decisao]
        ↳ apenas se houver 2ª rodada

      [TRANSIÇÃO]
      Mycroft.montar_pacote_sherlock()           [heartbeat: montar_pacote_sherlock]
        ↳ propaga "Nota metodológica com alteração"
          se Watson sinalizou no consolidado
        ↳ (mapear_pontos: reservado ao modo per-ponto — não ativo na produção)

      [FASE SHERLOCK]
      Sherlock.validar()                         [heartbeat: validacao_inicial]
        ↳ MONOLÍTICO: todos os pontos numa única chamada (Passos 4a-4g);
          o modo per-ponto (verificar_ponto) é reservado à bancada
      Sherlock.validacao_planilha_rn_sherlock()  [heartbeat: validacao_planilha_rn_sherlock]
        ↳ CONDICIONAL: só se Planilha de Verificação
          estiver listada no manifesto
      Sherlock.consolidar()                      [heartbeat: consolidar_sherlock]
        ↳ inclui: analise_impacto_entre_modulos
                  identificacao_pendencias_para_simulador_completo
                  secao_alteracoes_encaminhadas_rfb
                  relatorio_estruturado (11 seções)
                  insumo_json_dashboard
      Mycroft.avaliar_sherlock()                 [heartbeat: avaliar_agente]
        [até 2 rodadas de revisão]
      Mycroft.fixar_decisao_sherlock()           [heartbeat: fixar_decisao]
        ↳ apenas se houver 2ª rodada

      [CONSOLIDAÇÃO]
      Mycroft.consolidar()                       [heartbeat: consolidar]
        ↳ verifica completude das 11 seções do Relatório Estruturado
          antes de emitir MC_consolidado.md
        → grava output/relatorio_preliminar_{id}.md

  → Status: AGUARDANDO_VERIFICACAO_SAIDA

diogenes verify-output --cycle {id}
  → Motor de Saída: varre 4 categorias de marcas internas
  → Status: AGUARDANDO_CHANCELA_LESTRADE (se limpo)

diogenes deliver --cycle {id}            # Fase de Entrega (excursão antes do seal)
  → Mycroft.mapear_dados_modulo (LLM) localiza dados na planilha → entrega_mapa_extracao.json
  → Motor de Entrega (determinístico) gera output/entrega/: Dashboard.html, Apendice_*.docx,
     Relatorio_Narrativo/Consolidado/Pre_Atendimento_*.docx, ficha_sintese_*.{html,pdf,png}
  → Mycroft.avaliar_entrega (LLM) faz QA de aderência (APROVADO | REQUER_AJUSTE)
  → `--no-qa` pula o LLM (só geração); `--no-assets` pula PDF/PNG da ficha
  → Também roda automaticamente ao final do `autorun`

diogenes seal --cycle {id}
  → Status: ENCERRADO_CHANCELADO
```

---

## Tracker de ID de alerta Watson

O Orquestrador mantém um contador de alertas que persiste entre todas as
chamadas de Watson (analisar_arquivo + consolidar + responder_critica).
O ID é derivado do `module_id` e do contador:

```
W{codigo_modulo}-{n:03d}   ex: W010-001, W010-002
```

Gerado por `Orchestrator._proximo_id_alerta(module_id, counter)`.
O contador acumula após cada chamada: `alert_counter += output_watson.critical_alerts_count`.
O ID é propagado para o próximo arquivo via `InputFileInfo.ultimo_id_alerta`.

`_contar_criticos` lê do campo de cabeçalho `**Alertas CRITICA:** N` (sobrevive
à truncagem da tabela), com fallback para nomes de seção dos templates do skills.md.

---

## Campos de cabeçalho monitorados pelo Orquestrador

O Orquestrador extrai esses campos dos outputs dos agentes para decisões de fluxo.
Parsear com valor default seguro quando ausente.

**Watson — `watson_consolidado.md`:**

| Campo | Tipo | Ação quando `Sim` |
|-------|------|-------------------|
| `Nota metodológica com alteração detectada` | `Sim \| Não` | Orquestrador inclui detalhes da nota no pacote de Mycroft para `montar_pacote_sherlock` |

**Watson — `MC_tasks_watson.md`:**

| Campo | Tipo | Uso |
|-------|------|-----|
| `Planilha de Verificação no pacote` | `Sim \| Não` | Controla acionamento condicional de `validacao_planilha_rn` e `validacao_planilha_rn_sherlock` |

**Mycroft — `MC_consolidado.md`:**

| Campo | Tipo | Uso |
|-------|------|-----|
| `Overrule Mycroft sobre Watson` | `Sim \| Não` | Rastreabilidade de decisões |
| `Overrule Mycroft sobre Sherlock` | `Sim \| Não` | Rastreabilidade de decisões |

**Sherlock — `sherlock_consolidado.md`:**

O Orquestrador verifica a presença das 11 seções obrigatórias (10.1 a 10.11) e
do JSON de ocorrências (seção 11) **antes** de acionar `Mycroft.consolidar()`.
Se alguma seção estiver ausente: status do ciclo vai para `AGUARDANDO_COMPLETUDE`
e Lestrade é notificado.

---

## Contexto metodológico relevante ao código

**Anos-base alterados:** a metodologia homologada pelo Acórdão 2833/2025-Plenário
fixou originalmente os anos-base de 2024 e 2025. A RFB alterou para **2023 e 2024**
por indisponibilidade da ECF de 2025. Referências a `2023/2024` nos arquivos de
definição dos agentes estão corretas — não são bug.

**Módulo sintético:** `MOD_SINT_001` é o módulo de teste com inconsistências
controladas, usado nas Fases A e B. `MOD_010` (Pessoa Física) é o primeiro módulo
real, usado na Fase D.

---

## Padrões de código estabelecidos

- `from __future__ import annotations` em todos os módulos
- Type hints completos; `X | None` em vez de `Optional[X]`
- Exceções tipadas em `motors/exceptions.py` e `orchestrator/exceptions.py`
- Testes em `tests/unit/` e `tests/integration/`; fixtures globais em `conftest.py`
- Mocks LLM via `pytest-httpx` (o openai SDK usa httpx internamente)
- Testes CLI via `typer.testing.CliRunner`
- `get_config.cache_clear()` obrigatório antes/depois de cada teste (feito via
  fixture `clear_config_cache` com `autouse=True` em `conftest.py`)
- Nunca usar `os.environ` diretamente — sempre via `get_config()`
- Nunca importar `from diogenes.X import Y` dentro de `models.py`
- Exceções em `except` clauses usam `raise ... from e` (B904)
- Nenhuma semicolon em statements múltiplos (E702)

**Estado atual:** 374 testes passando, ruff limpo nos arquivos tocados.

---

## Estado atual e itens pendentes

Consulte `ESTADO_DIOGENES.md` para o estado vivo do piloto. `AUDITORIA_COMPARATIVA_*.md`
e `AUDITORIA_BENCH_*.md` na raiz de `diogenes/` documentam as execuções comparativas
entre famílias de modelo (`gpt-5.4`, `gpt-5.5`, Claude).

### Correções e funcionalidades entregues (2026-06-03/04)

**Calibrações de prompt (auditoria 2026-06-03):**
- Watson `soul.md`/`skills.md`/`heartbeat.md` — segurança ChatTCU, formato numérico estrito.
- Sherlock `heartbeat.py` — mapeamento `validacao_inicial` corrigido (causa raiz NV-GLOBAL-01).
- Sherlock `heartbeat.md`/`soul.md` — protocolo monolítico multi-ponto.
- Mycroft `soul.md` — segurança ChatTCU.

**Correções pós-ciclo noturno (2026-06-04):**
- `contexto_metodologico.py` — `_MAX_CHARS_METODOLOGIA` 20k→80k: RN de 28.5k chega
  completa ao Sherlock. Antes só ~6.3k passavam (Metodologia_Foco esgotava o teto primeiro).
- `motor_saida.py` — Etapa 2.5: remove `[arquivo_interno.md]` antes do split de filename.
- `runtime.yaml` — padrões e substituições para `"Stranger Room"` (sem apóstrofo),
  `MC_decisao`, `MC_consolidado`, `watson_consolidado`, `sherlock_consolidado`.
- `sherlock/skills.md` — seção 10.10 "Deliberações Internas do Ciclo" (era "Stranger Room").
- `agents/file_prep.py` — `ARQUIVOS_SEMPRE_ANALISE` libera `protocolo_recebimento.md` e
  `inventario.xlsx` independentemente de `DIRS_IGNORADOS`.

**Novas funcionalidades:**
- `motors/motor_start.py` + `orchestrator/` + `agents/mycroft.py` — Atividade 2 (revalidação):
  herda histórico A1, Watson recebe instrução de confronto, Mycroft classifica inconsistências.
- `reports/` + `cli/commands/report.py` — `diogenes report`: painel HTML local ao vivo,
  avatares dos 4 agentes, live auto-refresh, sem envio de dados externos.
- `bench/pipeline.py` — fallback de corpus para `DIOGENES_CORPUS_JURIDICO_DIR` do `.env`.

**Fase de Entrega (2026-06-04) — `diogenes deliver` + hook no `autorun`:**
- `delivery/` + `motors/motor_entrega.py` + `orchestrator/entrega.py` — gera os entregáveis
  GT Reforma (dashboard HTML, apêndice/relatórios DOCX, ficha síntese PDF/PNG) em
  `output/entrega/` a partir do `PacoteEntrega` canônico (models.py). Determinístico.
- `agents/mycroft.py` — call_types `mapear_dados_modulo` (localiza dados na planilha, sem
  transcrever números) e `avaliar_entrega` (QA de aderência); seções no `mycroft/heartbeat.md`.
- Geradores TCU **vendorizados** em `delivery/vendor/tcu/` (cópias de
  `01-BIBLIOTECAS_UTILITARIAS/` — não referenciar o OneDrive em runtime; ver `VENDOR.md`).
- Deps obrigatórias novas: `python-docx`, `matplotlib`, `playwright` (+ `playwright install chromium`).
- Esquema do mapa de extração: `delivery/MAPA_EXTRACAO.md`. Testes: `tests/unit/test_motor_entrega.py`.

### Dívida técnica conhecida (não bloqueante)
- ~40 erros de mypy pré-existentes (`dict` sem type args, etc.)
- `fase_ativa: B` em `agents_spec.yaml` é apenas rótulo de rastreabilidade

### Resiliência pós-rodada noturna MOD_010 (2026-06-11)

Causa raiz da rodada de 7h "perdida": `sherlock.validacao_inicial` estourou o
read-timeout de 1500s **4× idênticas** e caiu num fallback determinístico que
fabricava as 11 seções — passou na completude, Mycroft aprovou e o `--auto-seal`
chancelou um ciclo metodologicamente vazio (`NAO_VERIFICAVEL_MAJORITARIAMENTE`
era artefato da falha, não achado). Correções:

- `models.py` — `is_fallback` em `WatsonOutput`/`SherlockOutput`; todo fallback
  determinístico agora é marcado e **nunca** segue para revisão/consolidação.
- `agents/sherlock.py` — `validar()` com degradação escalonada: pacote completo
  (2 tentativas) → réguas truncadas via `reduzir_pacote_sherlock` (40k metodologia /
  15k corpus, com ressalva obrigatória no output) → fallback marcado.
- `agents/watson.py` — `consolidar()` map-reduce: acima de 600k chars as análises
  são consolidadas por lotes (`[CONSOLIDAÇÃO PARCIAL — LOTE i/N]`) e reduzidas numa
  chamada final (marcadores documentados no heartbeat). Evita a chamada monolítica
  de 2,43M chars/615k tokens da rodada noturna. Fix adicional: o consolidado não
  descarta mais `nota_metodologica_com_alteracao` (a propagação à Frente 3b nunca
  disparava).
- `orchestrator.py` — gate de fallback ANTES de escrever no Stranger Room (fase
  permanece re-executável): pausa em `PAUSADO_LESTRADE` com marker
  `_runtime/fallback_{fase}.md`; `retomar_apos_fallback()` re-executa a fase
  (análises Watson voltam dos checkpoints). `states.py`: transições
  `EM_EXECUCAO_{WATSON,SHERLOCK} → PAUSADO_LESTRADE` e `PAUSADO → EM_EXECUCAO_WATSON`.
- `autorun.py` — pausa por fallback: até 2 retomadas automáticas com cooldown de
  300s; esgotadas, o ciclo fica pausado SEM seal. Nova flag `--reuse-watson-from
  <cycle_id>`: copia checkpoints Watson de ciclo anterior validando SHA-256 por
  arquivo (re-rodada do MOD_010 sem repetir ~5h de análise por arquivo).
- `resume.py` — despacha para `retomar_apos_fallback` quando há marker pendente.
- Testes: `tests/unit/test_resiliencia_agentes.py` (17 testes).

### Próximo passo
Re-rodada do MOD_010 reaproveitando a análise por arquivo da rodada de 2026-06-11:

```bash
caffeinate -i diogenes autorun --module MOD_010 --activity 1 \
  --delivery .../MOD_010_Pessoa_Fisica \
  --reuse-watson-from MOD_010_A1_20260611T020454Z \
  --auto-seal
```

Com os checkpoints reaproveitados, o ciclo pula direto para a consolidação Watson
(agora em lotes) e re-tenta a fase Sherlock com degradação escalonada. Se o ChatTCU
voltar a não responder, o ciclo pausa SEM chancela — retomar com `diogenes resume`.

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
