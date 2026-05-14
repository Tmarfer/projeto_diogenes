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
    setup_local.sh         ← script de setup rápido para Fase A
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

### Setup rápido para Fase A (a partir da raiz do repo)

```bash
chmod +x piloto/setup_local.sh
./piloto/setup_local.sh
```

---

## Stack e estrutura

```
Python 3.11+ | openai SDK | Typer CLI | Pydantic v2 | pytest
```

```
src/diogenes/
  agents/      — Watson, Mycroft (MycrooftAgent), Sherlock + heartbeat + file_prep
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
| `orchestrator/stranger_room.py` | Persiste arquivos imutáveis Markdown+frontmatter YAML da revisão Mycroft↔Watson/Sherlock |
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
4. **Stranger's Room é imutável.** Arquivos escritos nunca são sobrescritos
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

---

## Fases do piloto

| Fase | Módulo | Modelos | Custo |
|------|--------|---------|-------|
| A | MOD_SINT_001 | free (Google Gemini free) | ~0 USD |
| B | MOD_SINT_001 | baratos (Kimi K2, Gemini Flash) | ~5 USD |
| D | MOD_010 | produção (Claude Sonnet/Opus) | ~10 USD |

Trocar de fase: editar `agents_spec.yaml` — comentar linhas `modelo` da fase
atual, descomentar as da próxima, atualizar `fase_ativa` e
`teto_custo_ciclo_usd`.

---

## Fluxo do ciclo completo

```
diogenes start --module MOD_010 --activity 1
  → Motor de Start: verifica inputs, SHA-256, cria workspace/cycles/{id}/
  → Gera manifest.md, registra PREPARADO no audit_index.csv

diogenes confirm-manifest --cycle {id}
  → Orchestrator.executar():
      Mycroft.definir_tasks_watson()
      Watson.analisar_arquivo() × N arquivos   [heartbeat: analise_arquivo]
      Watson.consolidar()
      Mycroft.avaliar_watson()                  [heartbeat: avaliar_agente]
      [até 2 rodadas]
      Mycroft.fixar_decisao_watson()            [heartbeat: fixar_decisao]
      Mycroft.montar_pacote_sherlock()          [heartbeat: montar_pacote_sherlock]
      Sherlock.validar()                        [heartbeat: verificar_ponto]
      Mycroft.avaliar_sherlock()                [heartbeat: avaliar_agente]
      [até 2 rodadas]
      Mycroft.fixar_decisao_sherlock()          [heartbeat: fixar_decisao]
      Mycroft.consolidar()                      [heartbeat: consolidar]
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

---

## Próximos itens pendentes

- [ ] Sprint 6: Fase A — executar ciclo real com MOD_SINT_001 e modelos free
- [ ] Motor de Saída: calibrar padrões contra output real dos modelos (pós-Fase A)
- [ ] Fase B: trocar modelos em `agents_spec.yaml`, executar novamente
- [ ] Fase D: MOD_010 com dados reais da RFB

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
