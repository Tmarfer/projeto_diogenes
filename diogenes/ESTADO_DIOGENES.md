# ESTADO DO PROJETO DIÓGENES
## Snapshot para onboarding
**Data:** 2026-06-04
**Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU

---

## 1. Estado operacional atual

| Campo | Valor |
|---|---|
| Versão do pacote | 0.1.0 |
| Python requerido | ≥ 3.11 (executando 3.13) |
| Provider LLM (produção) | ChatTCU (infra interna TCU) |
| Modelo ativo (todos os agentes) | `gpt-5.5-thinking` via `agents_spec.yaml` |
| Fase piloto ativa | Fase D — módulo real MOD_010 (Pessoa Física) |
| Teto de custo por ciclo | USD 0.00 (ChatTCU — custo institucional zero) |
| Suite de testes | **216 passed, 1 skipped** (0 falhas) |
| Branch ativa | `feat/revalidacao-e-auditoria-prd` |
| Último ciclo completo | `MOD_010_A1_20260604T013158Z` — ENCERRADO_CHANCELADO |
| Duração do último ciclo | 13h 07min · 116 arquivos · 130 chamadas LLM |

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
diogenes autorun --module MOD_010 --activity 1
  (abre report.html no browser automaticamente)
  [Irene]   catalogação semântica dos XLSX/CSV (reusa catálogo se versão ≥ mínima)
  [Mycroft] definir tarefas Watson
  [Watson]  análise de integridade por arquivo (×N)
  [Watson]  consolidação cross-file
  [Mycroft] avaliar Watson (Stranger Room, até 2 rodadas)
  [Mycroft] montar pacote Sherlock
  [Sherlock] validação metodológica monolítica (validacao_inicial)
  [Mycroft] avaliar Sherlock (Stranger Room, até 2 rodadas)
  [Mycroft] consolidação final → relatorio_preliminar_*.md
→ verify-output (Motor de Saída)
→ Fase de Entrega (Mycroft mapeia dados → Motor de Entrega gera entregáveis → Mycroft QA)
→ seal
```

O `autorun` auto-resolve pausas de alerta crítico e completude (modo não-assistido
para execução noturna) e, ao final, aciona a Fase de Entrega automaticamente.
Para antes do `seal` — chancela humana de manhã.

---

## 4. Calibrações aplicadas (auditoria sistemática 2026-06-03)

A auditoria comparou o contrato projetado com o comportamento real de cada agente
e calibrou os prompts onde havia desvio. Registro completo em `docs/auditoria_agentes/`.

### Watson
- `soul.md` — "Prevenção de Interceptação de Segurança (ChatTCU)": mascaramento de
  PII, não-transcrição de dados brutos, síntese de conteúdo.
- `skills.md` — formato numérico estrito para contadores de cabeçalho
  (`**Alertas CRITICA:** N` deve ser inteiro, nunca prosa).
- `heartbeat.md` — restrições ativas na seção `consolidar_watson`.

### Sherlock
- `agents/heartbeat.py` — mapeamento `"validacao_inicial"` corrigido de `"verificar_ponto"`.
  Causa raiz do NV-GLOBAL-01: Sherlock recebia instrução `UM_PONTO_POR_CHAMADA` mas era
  chamado monoliticamente.
- `heartbeat.md` — adicionada seção `# Heartbeat de Sherlock — validacao_inicial`.
- `soul.md` — exceção de trace em 1ª pessoa + "Prevenção de Interceptação de Segurança".
- `skills.md` — seção 10.10 renomeada de "Decisões da Stranger Room" para
  "Deliberações Internas do Ciclo" (impessoalidade no output externo).

### Mycroft
- `agent.md` — modelo atualizado para `gpt-5.5-thinking`.
- `soul.md` — "Prevenção de Interceptação de Segurança (ChatTCU)".

### Irene
- `agent.md` — modelo atualizado para `gpt-5.5-thinking`.
- `heartbeat.md` — passo 1/2 atualizados para busca correta do catálogo.

---

## 5. Correções pós-ciclo noturno (2026-06-04)

Identificadas e corrigidas após análise do ciclo `MOD_010_A1_20260604T013158Z`:

### RN truncada (causa de veredicto NAO_VERIFICÁVEL)
`contexto_metodologico.py`: `_MAX_CHARS_METODOLOGIA` aumentado de **20k → 80k**.
A `Metodologia_Foco` (13.7k) era selecionada primeiro (ordem alfabética), esgotando
o orçamento antes da `RegraDeNegocio_Modulo10_Pessoa_Fisica_v1_2.md` (28.5k).
Resultado: apenas 6.3k de 28.5k chars da RN chegavam ao Sherlock. Corrigido:
toda a RN + metodologia chegam com 39k chars de margem.

### Motor de Saída — 3 causas de vazamento
1. `runtime.yaml` — adicionados `"Stranger Room"` (sem apóstrofo), `"MC_decisao"`,
   `"MC_consolidado"`, `"watson_consolidado"`, `"sherlock_consolidado"` aos padrões
   e substituições.
2. `skills.md` Sherlock — seção 10.10 renomeada (ver acima).
3. `motor_saida.py` — adicionada **Etapa 2.5**: remove referências `[arquivo_interno.md]`
   *antes* do split de filename, que as preservava de propósito.
   Padrão: `\[[A-Za-z_][A-Za-z0-9_]*\.md\]` — só snake_case, não captura citações legítimas.

### Inventário e protocolo de recebimento
`agents/file_prep.py` — `ARQUIVOS_SEMPRE_ANALISE` allowlist libera
`protocolo_recebimento.md` e `inventario.xlsx` para análise dos agentes, mesmo quando
o diretório estaria em `DIRS_IGNORADOS`.

**Validação:** bench pipeline `--limit 3` → 10/10 OK, `doc_modulo=80000c`.

---

## 6. Atividade 2 — Revalidação (implementada)

`motors/motor_start.py` + `orchestrator/orchestrator.py` + `agents/mycroft.py`:
- `_resolver_ciclo_anterior()` encontra o ciclo A1 mais recente em ENCERRADO_CHANCELADO.
- `_copiar_historico_a1()` copia artefatos do A1 para `_historico/` do novo ciclo.
- Watson recebe instrução de confronto com o histórico A1.
- Mycroft classifica cada inconsistência anterior como Resolvida/Justificada/Em aberto/Nova.

Testes: `tests/integration/test_ciclo_atividade2.py`.

---

## 7. Painel de acompanhamento local (`diogenes report`)

Equivalente ao LangSmith, 100% local (governança: dados fiscais não saem da infra TCU).
Lê artefatos já gravados em disco sem chamar nenhum modelo de linguagem.

```bash
diogenes report --cycle <id>                    # Markdown no terminal
diogenes report --cycle <id> --format html      # HTML no browser (abre automaticamente)
diogenes report --cycle <id> --format html -o ~/report.html  # salva em arquivo
```

**Live update:** `EventLogger.log()` regenera `report.html` no `cycle_dir/` após cada
evento (best-effort, nunca interrompe o ciclo). O HTML inclui `<meta http-equiv="refresh"
content="10">` enquanto o ciclo não é terminal — o browser atualiza sozinho.

**Conteúdo do painel:**
- Cards de agentes com avatares (Irene, Watson, Mycroft, Sherlock) — métricas individuais
- Timeline de fases com duração
- Tabela de chamadas LLM por agente (tokens prompt/completion, resposta média)
- Motor de Saída, Stranger Room, output final

Fontes: `_runtime/events.jsonl` + `_runtime/llm_calls.jsonl` + `audit_index.csv` +
`stranger_room/`.

Novo módulo: `src/diogenes/reports/` (cycle_report.py · render_markdown.py · render_html.py).
16 testes em `tests/unit/test_report.py`.

---

## 8. Fase de Entrega — entregáveis institucionais (`diogenes deliver`)

Etapa pós-ciclo que transforma os artefatos do ciclo nos documentos do padrão
GT Reforma Tributária. Roda após o Motor de Saída (excursão a partir de
`AGUARDANDO_CHANCELA_LESTRADE`) e também automaticamente ao final do `autorun`.

**Modelo híbrido (decisão de projeto):** Mycroft é o dono.
1. `Mycroft.mapear_dados_modulo` (LLM) localiza, na planilha principal, **onde** estão
   os dados (aba/célula/intervalo) e redige a narrativa — **nunca escreve números**.
   Grava `output/entrega_mapa_extracao.json` (esquema em `delivery/MAPA_EXTRACAO.md`).
2. **Motor de Entrega** (determinístico, sem LLM — espelha o Motor de Saída) lê os
   **valores exatos** das células via openpyxl e gera, em `output/entrega/`:
   `Dashboard.html`, `Apendice_Modulo*.docx`, `Relatorio_Narrativo/Consolidado/Pre_Atendimento_*.docx`,
   `ficha_sintese_*.{html,pdf,png}` + `entrega_manifesto.json`.
3. `Mycroft.avaliar_entrega` (LLM) faz o QA de aderência ao padrão e ao módulo
   (`APROVADO | REQUER_AJUSTE`).

```bash
diogenes deliver --cycle <id>              # com mapeamento + QA do Mycroft (LLM)
diogenes deliver --cycle <id> --no-qa      # só geração determinística
diogenes deliver --cycle <id> --no-assets  # pula PDF/PNG da ficha (sem Playwright)
```

**Esquema canônico módulo-agnóstico** (`PacoteEntrega` em `models.py`) — escala para os
18+ módulos sem driver por módulo. **Geradores TCU vendorizados** em
`delivery/vendor/tcu/` (cópias de `01-BIBLIOTECAS_UTILITARIAS/`, nunca referenciadas via
OneDrive em runtime — ver `VENDOR.md`).

**Dependências** (já no `pyproject`): `python-docx`, `matplotlib`, `playwright`.
Passo extra de install obrigatório: **`python -m playwright install chromium`**.

Novo módulo: `src/diogenes/delivery/` + `motors/motor_entrega.py` +
`orchestrator/entrega.py`. 11 testes em `tests/unit/test_motor_entrega.py`.

---

## 9. Bancada de testes (`diogenes bench`)

| Comando | O que faz |
|---|---|
| `diogenes bench smoke` | Testa conectividade ChatTCU |
| `diogenes bench validate-models` | Valida modelos do `agents_spec.yaml` |
| `diogenes bench preview <agente> --call-type <ct> --prompt "..."` | Monta prompt exato sem chamar LLM (custo zero) |
| `diogenes bench call <agente> --call-type <ct> --fixture <path>` | Chamada LLM isolada — 1 agente, 1 arquivo |
| `diogenes bench pipeline <módulo> --delivery <pasta> [--limit N] [--timeout S]` | Pipeline completo com `_audit.json` |

**Fallback de corpus:** `bench pipeline` herda `DIOGENES_CORPUS_JURIDICO_DIR` do `.env`
quando `--legal-corpus` não é passado. Antes retornava sempre `corpus_juridico=0c`.

Resultado de referência pós-correções:
`bench pipeline MOD_010 --limit 3 --timeout 600` → **10/10 OK, ✅ SUCESSO**
`doc_modulo=80000c` (RN completa) · `corpus_juridico>0c` (com `.env` configurado)

---

## 10. Suite de testes

| Resultado | Quantidade |
|---|---|
| Total coletados | **217** |
| Passed | **216** |
| Skipped | 1 (`test_docx_fallback_docling_se_invalido` — `docling` não instalado no Mac) |
| Failed | 0 |

```bash
cd diogenes && pytest tests/ -q   # ~3s
```

---

## 11. Provider LLM — governança crítica

**ChatTCU é o ÚNICO provider permitido em produção.** Dados fiscais do TC 015.848/2025-6
não podem trafegar por serviços externos. `get_llm_client()` em `llm/base.py` é o guardião.

| Provider | Uso |
|---|---|
| `chattcu` | Produção obrigatória — autenticação MSAL (browser na 1ª execução) |
| `azure` | Alternativo institucional |
| `openrouter` | Bloqueado em produção; permitido apenas em testes pytest com mock |

**LangSmith e qualquer SaaS de observabilidade externo são vetados** pela mesma razão:
prompts e outputs contêm dados fiscais do TC 015.848/2025-6. Usar `diogenes report` local.

---

## 12. Estrutura de código

```
src/diogenes/
  agents/       — watson.py, sherlock.py, mycroft.py + heartbeat.py + file_prep.py
                  (mycroft: + mapear_dados_modulo / avaliar_entrega na Fase de Entrega)
  bench/        — core.py + pipeline.py + prompt_builder.py
                  (pipeline herda DIOGENES_CORPUS_JURIDICO_DIR do .env)
  cli/          — app.py + commands/ (start, confirm-manifest, autorun, report, deliver, bench/, …)
  config.py     — get_config() com @lru_cache — ÚNICO ponto de config
  delivery/     — Fase de Entrega (NOVO): schema (em models), parsing, extractor (openpyxl),
                  dashboard, builders, pacote + vendor/tcu/ (geradores TCU vendorizados)
  irene.py      — wrapper pipeline Irene C1-C5
  llm/          — base.py + chattcu.py + openrouter.py + azure_foundry.py
  models.py     — TODOS os dataclasses de domínio (+ PacoteEntrega / MotorEntregaReport)
  motors/       — motor_start.py + motor_saida.py + motor_entrega.py (NOVO, determinístico)
  orchestrator/ — orchestrator.py + states.py + stranger_room.py + events.py + entrega.py (NOVO)
                  (EventLogger atualiza report.html após cada evento)
  persistence/  — audit_index.py + manifest.py + workspace.py + delivery.py
  reports/      — cycle_report.py + render_markdown.py + render_html.py
```

---

## 13. Máquina de estados (CycleState)

19 estados implementados:
`PREPARADO` → `AGUARDANDO_CONFIRMACAO_MANIFESTO` → `VERIFICANDO_EXISTENCIA` →
`AGUARDANDO_IRENE` → `IRENE_CONCLUIDA` → `EM_EXECUCAO_WATSON` → … →
`AGUARDANDO_VERIFICACAO_SAIDA` → `AGUARDANDO_CHANCELA_LESTRADE` → `ENCERRADO_CHANCELADO`

Fase de Entrega (excursão a partir de `AGUARDANDO_CHANCELA_LESTRADE`, não altera o
caminho do seal): `EM_EXECUCAO_ENTREGA` ⇄ `AGUARDANDO_AJUSTE_ENTREGA` → volta à chancela.

---

## 14. Próximo passo recomendado

Executar novo ciclo `autorun` completo com as correções aplicadas (RN completa,
Motor de Saída limpo, corpus jurídico ativo). O browser abre sozinho com o painel ao vivo:

```bash
cd diogenes
# pré-voo: renovar token MSAL e ativar role PIM
diogenes bench smoke

caffeinate -i diogenes autorun \
  --module MOD_010 --activity 1 \
  --delivery /Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/workspace/_teste_inputs/MOD_010_Pessoa_Fisica \
  2>&1 | tee ~/diogenes_MOD010_$(date +%Y%m%d_%H%M%S).log

# manhã: chancelar
diogenes seal --cycle MOD_010_A1_<ts>
```

Após chancelado, rodar Atividade 2 (revalidação) usando o ciclo A1 como histórico.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Atualizado em 2026-06-04 — pós-ciclo noturno MOD_010, painel de acompanhamento e Fase de Entrega*
