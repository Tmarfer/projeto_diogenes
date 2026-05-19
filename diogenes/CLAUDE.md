# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este projeto

Sistema agêntico de validação da alíquota de referência da CBS para o TCU
(TC 015.848/2025-6). Três agentes LLM (Mycroft, Watson, Sherlock) operam
sequencialmente sob supervisão de um auditor humano (Lestrade).

**Documentos de referência:**
- `docs/antecedentes/PRD_Piloto_Diogenes_v01.md` — requisitos do piloto
- `docs/sdd/SDD_Piloto_Diogenes_v01.md` — arquitetura de software (fonte da verdade)
- `docs/agentes/` — definição dos agentes (soul, skills, agent, heartbeat)

---

## Arquitetura dos agentes

Cada agente tem quatro arquivos em `docs/agentes/{agente}/`:

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
  diogenes/                ← pacote Python (trabalhe aqui)
    src/diogenes/          ← código fonte
    tests/                 ← testes
    agents_spec.yaml       ← modelos LLM por agente e fase
    runtime.yaml           ← parâmetros operacionais
    .env                   ← chaves e workspace (não versionado)
  piloto/
    setup_local.sh         ← script de setup rápido
  detalhamento/            ← documentos auxiliares (Word, imagens)
```

---

## Comandos de desenvolvimento

**Todos os comandos devem ser executados de dentro de `diogenes/`**, pois
`config.py` carrega `runtime.yaml` e `agents_spec.yaml` relativamente ao CWD.

```bash
cd diogenes

# Instalar
pip install -e ".[dev]"

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
```

---

## Stack e estrutura

```
Python 3.11+ | openai SDK | Typer CLI | Pydantic v2 | pytest
```

```
src/diogenes/
  agents/      — Watson, MycrooftAgent, Sherlock + heartbeat + file_prep
  cli/         — app.py + commands/ (um arquivo por subcomando)
  config.py    — get_config() com @lru_cache — ÚNICO ponto de leitura de config
  llm/         — base.py (Protocol) + openrouter.py + azure_foundry.py + seed.py + call_id.py
  models.py    — TODOS os dataclasses de domínio (LLMCall, CycleRecord, etc.)
  motors/      — motor_start.py + motor_saida.py
  orchestrator/— orchestrator.py + states.py + stranger_room.py + events.py
  persistence/ — audit_index.py + manifest.py + workspace.py
```

### Papéis dos módulos-chave

| Módulo | Responsabilidade |
|--------|-----------------|
| `config.py` | Único ponto de leitura: `.env` + `agents_spec.yaml` + `runtime.yaml` |
| `models.py` | Todos os dataclasses de domínio — sem lógica, sem imports internos |
| `agents/file_prep.py` | Converte xlsx/sql/ipynb/pdf/md em texto para incluir nos prompts de Watson |
| `orchestrator/stranger_room.py` | Persiste arquivos imutáveis Markdown+frontmatter YAML da revisão Mycroft ↔ Watson/Sherlock |
| `orchestrator/events.py` | `EventLogger` — grava JSONL de auditoria em `_runtime/events.jsonl` |
| `persistence/audit_index.py` | Lê/grava `audit_index.csv` com escrita atômica (temp + rename) |
| `llm/base.py` | `LLMClient` Protocol + factory `get_llm_client()` |

### LLM Providers

`get_llm_client()` instancia o cliente pelo valor de `DIOGENES_ENV`:
- `local` / `vps` → `OpenRouterClient` (padrão)
- `azure` → `AzureFoundryClient`

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
DIOGENES_LLM_BASE_URL=https://openrouter.ai/api/v1
DIOGENES_LLM_API_KEY=<chave OpenRouter>
DIOGENES_WORKSPACE=/caminho/absoluto/workspace
DIOGENES_ENV=local          # local | vps | azure

# Opcionais
DIOGENES_SSL_VERIFY=false   # em redes TCU com proxy de inspeção SSL
DIOGENES_OPENROUTER_SITE_URL=https://github.com/tcu/diogenes
DIOGENES_OPENROUTER_APP_NAME=DVA-CBS Projeto Diogenes

# Inicializar workspace (rodar de dentro de diogenes/)
diogenes init
```

**Worktree local:** o projeto roda em worktree (`C:\Projetos\Projeto_Diogenes\...`).
A worktree não herda `.env` nem `workspace/` (gitignored). Copiar o `.env` do repo
local principal e ajustar `DIOGENES_WORKSPACE` para um workspace isolado dentro da
worktree. Rodar `pip install -e .` de dentro da worktree.

---

## Fases do piloto e modelos ativos

| Fase | Módulo | Modelos (agents_spec.yaml) | Teto de custo |
|------|--------|---------------------------|---------------|
| A (piloto sintético) | MOD_SINT_001 | Mycroft: `meta-llama/llama-4-maverick` / Watson: `google/gemini-2.5-flash-lite` / Sherlock: `deepseek/deepseek-v4-flash` | USD 5/ciclo |
| D (produção) | MOD_010 | Claude Opus/Sonnet via OpenRouter ou Azure Foundry | ~USD 10/ciclo |

**Modelos free foram abolidos** — causavam rate limit recorrente no OpenRouter.
Não reintroduzir fallback para modelos free.

`max_tokens` ajustados com base em outputs observados: Mycroft/Watson `16384`,
Sherlock `24576`.

Para trocar de fase: editar `agents_spec.yaml` — atualizar `fase_ativa` e os
campos `modelo` por agente.

> **Nota de nomenclatura:** `agents_spec.yaml` rotula a configuração atual como
> `fase_ativa: B`, mas operacionalmente ela corresponde à Fase A do piloto
> (MOD_SINT_001 com modelos pagos baratos). Alinhar essa nomenclatura quando
> conveniente — não é bloqueante.

---

## Fluxo do ciclo completo

```
diogenes start --module MOD_010 --activity 1
  → Motor de Start: verifica inputs, SHA-256, cria workspace/cycles/{id}/
  → Gera manifest.md, registra PREPARADO no audit_index.csv

diogenes confirm-manifest --cycle {id}
  → Orchestrator.executar():

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
      Mycroft.mapear_pontos()                    [heartbeat: mapear_pontos]
        ↳ mapeia pontos do Apêndice aos watson_analise_*.md relevantes

      [FASE SHERLOCK]
      Sherlock.verificar_ponto() × N pontos      [heartbeat: verificar_ponto]
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

**Estado atual:** 88 testes passando, ruff limpo nos arquivos tocados.

---

## Próximos itens pendentes

- [ ] Mitigar degeneração de arquivos `.ipynb`: limpar JSON do notebook antes da
  análise no `file_prep` (extrair só células de código/markdown relevantes,
  descartar metadados e outputs ruidosos) — Watson com gemini-2.5-flash-lite
  entra em loop de whitespace com notebooks pesados
- [ ] Após mitigação: seal de um ciclo sintético íntegro e execução com MOD_010
  (base real da RFB)
- [ ] Implementar call_types novos: `validacao_planilha_rn` (Watson),
  `validacao_planilha_rn_sherlock` (Sherlock), `mapear_pontos` (Mycroft)
- [ ] Implementar detecção de Planilha de Verificação no manifesto e acionamento
  condicional dos call_types correspondentes no Orquestrador
- [ ] Implementar extração dos novos campos de cabeçalho nos parsers (ver seção
  "Campos de cabeçalho monitorados")
- [ ] Implementar verificação de completude das 11 seções do Relatório Estruturado
  antes de `Mycroft.consolidar()`
- [ ] Alinhar nomenclatura de fases em `agents_spec.yaml` (`fase_ativa: B` na
  config atual que operacionalmente é Fase A com modelos pagos)
- [ ] Resolver ~40 erros de mypy pré-existentes (dívida técnica, não bloqueante)

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
