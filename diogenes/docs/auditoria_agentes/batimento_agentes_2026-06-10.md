---
documento: Batimento Agentes — Docs (soul/skills/heartbeat/agent) × Implementação
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
data: 2026-06-10
uso: Interno Restrito
escopo: Mycroft, Irene, Watson, Sherlock — call_types, prompts, requisitos PRD (RF-MY/WA/SH)
---

# Batimento Agentes × Implementação — 2026-06-10

Reconciliação de 3 vias por agente: **agents_spec.yaml** (parâmetros) × **invocador Python**
(`agents/{agente}.py` + Orquestrador) × **heartbeat.md/skills.md** (seções e templates),
confrontada com os requisitos do PRD (RF-MY-01..08, RF-WA-01..10, RF-SH-01..08).

Legenda: ✅ conforme · 🔧 corrigido nesta sessão · 📝 doc ajustada nesta sessão.

---

## 1. Mycroft (Auditor Chefe)

| Call_type / item | Heartbeat | Método Python | Veredito |
|---|---|---|---|
| `definir_tasks_watson` | ✓ | `definir_tasks_watson()` + catálogo Irene | ✅ (RF-MY-01) |
| `avaliar_agente` | ✓ (compartilhada) | `avaliar_watson()` / `avaliar_sherlock()` | ✅ (RF-MY-03/04) |
| `fixar_decisao` | ✓ (compartilhada) | `fixar_decisao_watson()` / `_sherlock()` | ✅ (RF-MY-05/06) |
| `montar_pacote_sherlock` | ✓ | `montar_pacote_sherlock()` (+ metodologia + corpus) | ✅ (RF-SH-01) |
| `consolidar` | ✓ | `consolidar()` (A1/A2, histórico) | ✅ (RF-MY-07/08) |
| `mapear_dados_modulo` / `avaliar_entrega` / `redigir_apendice` | ✓ | ✓ (Fase de Entrega) | ✅ 🔧 mapeamento explícito no `CALL_TYPE_TO_SECTION` |
| `mapear_pontos` | ✓ seção | **sem método/uso** | 📝 marcada como reservada ao modo per-ponto (produção é monolítica); CLAUDE.md corrigido |
| `acionar_irene` | ✓ seção (decisão LLM) | decisão **determinística** no Orquestrador | 📝 nota de execução delegada (Artigo 5); critérios alinhados aos implementados |
| `max_tokens` | spec: 16384 | hardcoded 16384 no `_montar_call` | 🔧 agora lê `spec.max_tokens` |
| `seed_base` (RNF-REPR-02) | spec: 42 | hardcoded `calcular_seed(42, …)` | 🔧 injetado via construtor a partir de `cfg.agentes.seed_base` |

**RF-MY-02 (não analisa arquivos):** ✅ — nenhum file_prep/parsing em mycroft.py; entradas
são outputs de agentes e metadados.

## 2. Irene (Catalogação C1–C5)

| Item | Doc | Implementação | Veredito |
|---|---|---|---|
| Acionamento como biblioteca (não LLM) | heartbeat intro | `executar_irene()` em `irene.py` | ✅ 📝 intro atualizada (decisão determinística) |
| Decisão EXECUTAR/REUTILIZAR | heartbeat: 4 critérios | `verificar_catalogo_existente()`: existe + `versao >= 1.3.0` | 📝 critérios da doc alinhados aos implementados (atividade/flag Lestrade não são verificados — Lestrade força reprocessamento removendo o catálogo) |
| **Catálogo reutilizado chega a Mycroft** | implícito | **BUG: no caminho de reuso o catálogo não era copiado para `cycles/{id}/irene_catalog.yaml`** — `definir_tasks_watson` declarava "Catálogo: Não" mesmo com reuso | 🔧 `copiar_catalogo_para_ciclo()` agora também no caminho de reuso |
| IRENE_BLOQUEADO não fatal / ERRO_FATAL aborta | INTEGRACAO §5.1 | ✓ orquestrador | ✅ |

## 3. Watson (Integridade Técnica)

| Call_type | Heartbeat | Método | Veredito |
|---|---|---|---|
| `analise_inicial` → seção `analise_arquivo` | ✓ (mapeado no loader) | `analisar_arquivo()` por arquivo, perfis do Motor de Perfilamento, checkpoint por ciclo | ✅ (RF-WA-01/03/04/05/08) |
| `consolidar_watson` | ✓ | `consolidar()` — críticos = max(LLM, Σ individuais) | ✅ (RF-WA-09/10) |
| `validacao_planilha_rn` | ✓ | `validacao_planilha_rn()` condicional ao manifesto | ✅ |
| `resposta_r1`/`r2` | ✓ | `responder_critica()` | ✅ |
| `seed_base` | spec | hardcoded 42 (4 call-sites) | 🔧 via construtor |

**RF-WA-02 (não interpreta metodologia):** ✅ — metodologia não entra nos prompts de Watson.
**RF-WA-07 (análises além do literal):** ✅ — seções de padrões/anomalias no skills.md.

## 4. Sherlock (Validação Metodológica)

| Call_type | Heartbeat | Método | Veredito |
|---|---|---|---|
| `validacao_inicial` (monolítico) | ✓ | `validar(pacote)` | ✅ (RF-SH-01..04, 07, 08) |
| `verificar_ponto` (per-ponto) | ✓ seção | **sem uso em produção** (reservado bancada) | 📝 nota de status na seção; CLAUDE.md e comentário do orquestrador corrigidos |
| `validacao_planilha_rn_sherlock` | ✓ | ✓ condicional | ✅ |
| `consolidar_sherlock` | ✓ (11 seções + JSON §11 + 8f) | `consolidar()` + `_verificar_completude_sherlock` | ✅ |
| `resposta_r1`/`r2` | ✓ | `responder_critica()` | ✅ (RF-SH-05 via dilemas) |
| `seed_base` | spec | hardcoded 42 | 🔧 via construtor |

### 🔴 Achado principal do batimento — calibrações mortas em produção

As calibrações da Onda 4 e pós-SQL-v2 (Passos **5b** ancoragem ao fato, **5c** natureza da
ocorrência/controle de FP, **5d** gradação de severidade) viviam **somente na seção
`verificar_ponto`** — que NÃO é injetada na produção (o modo ativo é o monolítico
`validacao_inicial`). Só o controle do 8f (em `consolidar_sherlock`) estava ativo. Isso
explica a recaída do ciclo SQL v2 (sistêmica S009 como CRITICO e INC-SQL-01 rebaixado a NV)
apesar das calibrações "aplicadas".

**🔧 Correção:** os três controles foram portados para o protocolo monolítico como Passos
**4e/4f/4g** de `validacao_inicial` (+ restrições ativas). Regra operacional registrada nas
duas seções: *calibrações novas devem ser aplicadas nas duas seções* (monolítica e per-ponto).

---

## Correções de código desta sessão (resumo)

1. `orchestrator/orchestrator.py` — catálogo Irene reutilizado agora é copiado para o ciclo.
2. `agents/{mycroft,watson,sherlock}.py` — `seed_base` injetado do `agents_spec.yaml`
   (RNF-REPR-02); default 42 preservado para testes/bancada.
3. `agents/mycroft.py` — `max_tokens` lido do spec (contrato `agents_spec.yaml` restaurado).
4. `agents/heartbeat.py` — mapeamentos explícitos da Fase de Entrega + inventário comentado
   das seções sem call_type ativo.
5. `orchestrator/orchestrator.py` — comentário da fase Sherlock corrigido (monolítico).

## Correções de documentação desta sessão (resumo)

6. `sherlock/heartbeat.md` — Passos 4e/4f/4g no protocolo monolítico; notas de status em
   `verificar_ponto`.
7. `mycroft/heartbeat.md` — notas de status em `mapear_pontos` (reservado) e `acionar_irene`
   (execução determinística delegada).
8. `irene/heartbeat.md` — intro alinhada à execução determinística.
9. `CLAUDE.md` — fluxo do ciclo corrigido (Sherlock monolítico; mapear_pontos reservado).

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
