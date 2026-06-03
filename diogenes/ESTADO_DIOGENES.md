# ESTADO DO PROJETO DIÓGENES
## Snapshot para onboarding
**Data:** 2026-06-03
**Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU

---

## 1. Estado operacional atual

| Campo | Valor |
|---|---|
| Versão do pacote | 0.1.0 |
| Python requerido | ≥ 3.11 (executando 3.14) |
| Provider LLM (produção) | ChatTCU (infra interna TCU) |
| Modelo ativo (todos os agentes) | `gpt-5.5-thinking` via `agents_spec.yaml` |
| Fase piloto ativa | Fase D — módulo real MOD_010 (Pessoa Física) |
| Teto de custo por ciclo | USD 0.00 (ChatTCU — custo institucional zero) |
| Suite de testes | **187 testes passando** (0 falhas, 0 skips) |
| Último ciclo completo | `MOD_010_A1_20260602T202655Z` — 10/10 passos OK |

---

## 2. Arquitetura de agentes

Quatro agentes, dois papéis:

| Agente | Tipo | Função |
|---|---|---|
| **Irene Adler** | Biblioteca Python (C1–C5) | Catalogação semântica de XLSX/CSV via LLM (estágio C4) |
| **Watson** | LLM (ChatTCU) | Integridade técnica — consistência de dados, scripts e planilhas |
| **Sherlock** | LLM (ChatTCU) | Validação metodológica — aderência ao Acórdão 2833/2025-Plenário |
| **Mycroft** | LLM (ChatTCU) | Orquestrador-chefe — tasking, revisão, integração e consolidação |

Cada agente tem 4 arquivos de definição em `docs/agentes/{agente}/`:
- `soul.md` — identidade, valores, limites constitucionais
- `skills.md` — templates de output, critérios, formatos
- `heartbeat.md` — protocolo operacional por call_type
- `agent.md` — parâmetros de runtime (modelos e configurações reais vêm de `agents_spec.yaml`)

**Os arquivos são lidos do filesystem a cada chamada — editar Markdown tem efeito imediato.**

---

## 3. Fluxo do ciclo

```
diogenes start → confirm-manifest →
  [Irene]  catalogação semântica dos XLSX/CSV
  [Mycroft] definir tarefas Watson
  [Watson]  análise de integridade por arquivo (×N)
  [Watson]  consolidação cross-file
  [Mycroft] avaliar Watson (Stranger Room, até 2 rodadas)
  [Mycroft] montar pacote Sherlock
  [Sherlock] validação metodológica monolítica (validacao_inicial)
  [Mycroft] avaliar Sherlock (Stranger Room, até 2 rodadas)
  [Mycroft] consolidação final → relatorio_preliminar_*.md
→ verify-output → seal
```

---

## 4. Calibrações aplicadas (auditoria sistemática 2026-06-03)

A auditoria comparou o contrato projetado com o comportamento real de cada agente
e calibrou os prompts onde havia desvio. Registro completo em `docs/auditoria_agentes/`.

### Watson
- `soul.md` — adicionada seção "Prevenção de Interceptação de Segurança (ChatTCU)":
  mascaramento de PII, não-transcrição de dados brutos, síntese de conteúdo.
- `skills.md` — formato numérico estrito para contadores de cabeçalho
  (`**Alertas CRITICA:** N` deve ser inteiro, nunca prosa).
- `heartbeat.md` — restrições ativas na seção `consolidar_watson`: contadores
  inteiros obrigatórios, proibição de PII literal.

### Sherlock
- `src/diogenes/agents/heartbeat.py` — mapeamento `"validacao_inicial"` corrigido
  de `"verificar_ponto"` para `"validacao_inicial"`. Causa raiz do NV-GLOBAL-01:
  Sherlock recebia instrução `UM_PONTO_POR_CHAMADA` mas era chamado monoliticamente.
- `heartbeat.md` — adicionada seção `# Heartbeat de Sherlock — validacao_inicial`
  com protocolo de validação monolítica multi-ponto.
- `soul.md` — exceção de trace em 1ª pessoa (Art. 14) + seção "Prevenção de
  Interceptação de Segurança (ChatTCU)".

### Mycroft
- `agent.md` — modelo atualizado de `claude-sonnet-4-6` para `gpt-5.5-thinking`
  (alinhamento com produção real via ChatTCU).
- `soul.md` — adicionada seção "Prevenção de Interceptação de Segurança (ChatTCU)":
  mascaramento de PII nos outputs de avaliação, decisão e consolidação.

### Irene
- `agent.md` — modelo atualizado de `Claude 4.6 Sonnet` para `gpt-5.5-thinking`.
- `heartbeat.md` — passo 1 e passo 2 atualizados para refletir busca do catálogo
  em `cycles/{cycle_id}/` e geração automática de `CATALOGO.json` mínimo se ausente.

---

## 5. Bancada de testes (`diogenes bench`)

| Comando | O que faz |
|---|---|
| `diogenes bench smoke` | Testa conectividade ChatTCU |
| `diogenes bench validate-models` | Valida modelos do `agents_spec.yaml` |
| `diogenes bench preview <agente> --call-type <ct> --prompt "..."` | Monta prompt exato sem chamar LLM (custo zero) |
| `diogenes bench call <agente> --call-type <ct> --fixture <path>` | Chamada LLM isolada — 1 agente, 1 arquivo |
| `diogenes bench pipeline <módulo> --delivery <pasta> [--limit N] [--timeout S]` | Pipeline completo com `_audit.json` |

Resultado de referência pós-calibração:
`bench pipeline MOD_010 --limit 3 --timeout 600` → **10/10 OK, ✅ SUCESSO**
(Watson analisa 3 arquivos, Sherlock produz pontos metodológicos reais, Mycroft avalia sem bloqueio)

---

## 6. Suite de testes

| Resultado | Quantidade |
|---|---|
| Total | **187** |
| Passed | **187** |
| Failed | 0 |
| Skipped | 0 |

Cobertura: unit tests em `tests/unit/` + integration tests em `tests/integration/`.
Mocks LLM via `pytest-httpx`. Fixture global `clear_config_cache` em `conftest.py`.

```bash
cd diogenes && pytest tests/ -q   # ~17-30s
```

---

## 7. Provider LLM — governança crítica

**ChatTCU é o ÚNICO provider permitido em produção.** Dados fiscais do TC 015.848/2025-6
não podem trafegar por serviços externos. `get_llm_client()` em `llm/base.py` é o guardião.

| Provider | Uso |
|---|---|
| `chattcu` | Produção obrigatória — autenticação MSAL (browser na 1ª execução) |
| `azure` | Alternativo institucional |
| `openrouter` | Bloqueado em produção; permitido apenas em testes pytest com mock |

---

## 8. Estrutura de código

```
src/diogenes/
  agents/       — watson.py, sherlock.py, mycroft.py + heartbeat.py + file_prep.py
  bench/        — core.py + pipeline.py + prompt_builder.py
  cli/          — app.py + commands/ (start, confirm-manifest, bench/, autorun, …)
  config.py     — get_config() com @lru_cache — ÚNICO ponto de config
  irene.py      — wrapper pipeline Irene C1-C5
  irene_chattcu.py — adaptador ChatTCU para Irene C4 (LLM)
  llm/          — base.py + chattcu.py + openrouter.py + azure_foundry.py
  models.py     — TODOS os dataclasses de domínio
  motors/       — motor_start.py + motor_saida.py
  orchestrator/ — orchestrator.py + states.py + stranger_room.py + events.py
  persistence/  — audit_index.py + manifest.py + workspace.py + delivery.py
```

---

## 9. Máquina de estados (CycleState)

17 estados implementados, incluindo os 3 de integração Irene:
`PREPARADO` → `AGUARDANDO_CONFIRMACAO_MANIFESTO` → `VERIFICANDO_EXISTENCIA` →
`AGUARDANDO_IRENE` → `IRENE_CONCLUIDA` → `EM_EXECUCAO_WATSON` → …
→ `AGUARDANDO_VERIFICACAO_SAIDA` → `AGUARDANDO_CHANCELA_LESTRADE` → `ENCERRADO_CHANCELADO`

---

## 10. Próximo passo recomendado

Executar o ciclo completo em produção sobre o pacote real do MOD_010:
```bash
cd diogenes
diogenes start --module MOD_010 --activity 1
diogenes confirm-manifest --cycle <cycle_id>
# ou
diogenes autorun --module MOD_010 --activity 1
```

Todos os prompts foram calibrados e testados via `bench pipeline 10/10 OK`.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Atualizado em 2026-06-03 — pós-auditoria sistemática dos 4 agentes*
