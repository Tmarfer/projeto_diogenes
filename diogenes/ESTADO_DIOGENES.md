# ESTADO DO PROJETO DIÓGENES
## Snapshot para onboarding do Claude Code
**Data:** 2026-05-30
**Executor:** Diagnóstico automático — Claude Code (claude-sonnet-4-6)
**Repositório:** `/Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/diogenes`

---

## 1. Versão e identidade

| Campo | Valor |
|---|---|
| Versão do pacote | 0.1.0 |
| Python requerido | >=3.11 (executando 3.13.13) |
| Último sprint concluído | Ciclo completo Watson→Sherlock→Mycroft + Motor de Saída (Bloco 4 do SDD) |
| Fase piloto ativa | B (modelos baratos — openrouter) |

---

## 2. Suite de testes

| Resultado | Quantidade |
|---|---|
| Total | 88 |
| Passed | 88 |
| Failed | 0 |
| Skipped | 0 |
| Erros de import | 0 |

Suite 100% verde. Tempo de execução: ~1.80s.

---

## 3. Módulos implementados

### Infraestrutura

| Módulo | Arquivo | Status | Linhas |
|---|---|---|---|
| Motor de Start | `motors/motor_start.py` | IMPLEMENTADO | 190 |
| Motor de Saída | `motors/motor_saida.py` | IMPLEMENTADO | 243 |
| Orquestrador | `orchestrator/orchestrator.py` | IMPLEMENTADO | 386 |
| Stranger's Room | `orchestrator/stranger_room.py` | IMPLEMENTADO | 142 |
| Estados (CycleState) | `orchestrator/states.py` | IMPLEMENTADO | 101 |
| Eventos | `orchestrator/events.py` | IMPLEMENTADO | 27 |
| Audit Index | `persistence/audit_index.py` | IMPLEMENTADO | 141 |
| Manifest | `persistence/manifest.py` | IMPLEMENTADO | 104 |
| Workspace | `persistence/workspace.py` | IMPLEMENTADO | 63 |
| LLM Client (OpenRouter) | `llm/openrouter.py` | IMPLEMENTADO | 252 |
| LLM Client (Azure Foundry) | `llm/azure_foundry.py` | IMPLEMENTADO | 33 |
| LLM Base | `llm/base.py` | IMPLEMENTADO | 22 |
| Config | `config.py` | IMPLEMENTADO | 184 |
| Models / Domain | `models.py` | IMPLEMENTADO | 225 |
| File Prep | `agents/file_prep.py` | IMPLEMENTADO | 88 |
| Heartbeat loader | `agents/heartbeat.py` | IMPLEMENTADO | 107 |
| CLI app | `cli/app.py` | IMPLEMENTADO | 62 |
| CLI display | `cli/display.py` | IMPLEMENTADO | 103 |

Utilitários menores (< 20 linhas, considerados infraestrutura):
- `llm/call_id.py` — geração de ID de chamada
- `llm/exceptions.py` — exceções LLM
- `llm/seed.py` — seed reprodutível
- `orchestrator/exceptions.py` — exceções do orquestrador

### Agentes

| Agente | Arquivo | Soul | Skills | Heartbeat | Agent | Linhas |
|---|---|---|---|---|---|---|
| Watson | `agents/watson.py` | S | S | S | S | 326 |
| Sherlock | `agents/sherlock.py` | S | S | S | S | 186 |
| Mycroft | `agents/mycroft.py` | S | S | S | S | 318 |

Todos os agentes possuem os 4 documentos de definição em `docs/agentes/{watson,sherlock,mycroft}/`.

---

## 4. Máquina de estados (CycleState)

Estados presentes no código (`orchestrator/states.py`):

| Estado | Valor |
|---|---|
| PREPARADO | `"PREPARADO"` |
| AGUARDANDO_CONFIRMACAO_MANIFESTO | `"AGUARDANDO_CONFIRMACAO_MANIFESTO"` |
| EM_EXECUCAO_WATSON | `"EM_EXECUCAO_WATSON"` |
| AGUARDANDO_REVISAO_MYCROFT_WATSON | `"AGUARDANDO_REVISAO_MYCROFT_WATSON"` |
| AGUARDANDO_DECISAO_LESTRADE_ALERTA | `"AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO"` |
| EM_EXECUCAO_SHERLOCK | `"EM_EXECUCAO_SHERLOCK"` |
| AGUARDANDO_REVISAO_MYCROFT_SHERLOCK | `"AGUARDANDO_REVISAO_MYCROFT_SHERLOCK"` |
| AGUARDANDO_COMPLETUDE | `"AGUARDANDO_COMPLETUDE"` |
| AGUARDANDO_VERIFICACAO_SAIDA | `"AGUARDANDO_VERIFICACAO_SAIDA"` |
| AGUARDANDO_CHANCELA_LESTRADE | `"AGUARDANDO_CHANCELA_LESTRADE"` |
| ENCERRADO_CHANCELADO | `"ENCERRADO_CHANCELADO"` |
| PAUSADO_LESTRADE | `"PAUSADO_LESTRADE"` |
| ABORTADO_FALHA_AGENTE | `"ABORTADO_FALHA_AGENTE"` |
| ABORTADO_LESTRADE | `"ABORTADO_LESTRADE"` |

**Total: 14 estados.** O `runtime.yaml` espelha os mesmos 14 estados.

Estados que precisarão ser adicionados para integração do Irene:
- [ ] `VERIFICANDO_EXISTENCIA` — Mycroft verifica se ciclo anterior existe para o módulo
- [ ] `AGUARDANDO_IRENE` — Irene em execução (verificação documental externa)
- [ ] `IRENE_CONCLUIDA` — resultado da Irene disponível, aguardando consumo pelo Orquestrador

---

## 5. Provider LLM atual

| Campo | Valor |
|---|---|
| Provider | OpenRouter |
| base_url | `https://openrouter.ai/api/v1` |
| Modelo Mycroft | `meta-llama/llama-4-maverick` (Fase B) |
| Modelo Watson | `google/gemini-2.5-flash-lite` (Fase B) |
| Modelo Sherlock | `deepseek/deepseek-v4-flash` (Fase B) |
| Temperatura Mycroft | 0.0 |
| Temperatura Watson | 0.0 |
| Temperatura Sherlock | 0.1 |
| Teto custo/ciclo | USD 5.00 |
| Seed base | 42 |
| API key configurada | NÃO — `.env` não encontrado no repositório |

> **Atenção:** o arquivo `.env` não está presente. O `.env.example` está disponível.
> Para executar o sistema é necessário criar `.env` com `DIOGENES_LLM_API_KEY` e `DIOGENES_WORKSPACE`.

---

## 6. Colunas do audit_index.csv

```
cycle_id, module_id, activity, status,
opened_at_utc, ended_at_utc,
is_sigilo_module, previous_cycle_id,
watson_rodadas, sherlock_rodadas,
mycroft_overruled_watson, mycroft_overruled_sherlock,
watson_critical_alerts_count, sherlock_dilemmas_count,
motor_saida_invocado_at_utc, motor_saida_occurrences, motor_saida_decision,
lestrade_seal_at_utc, output_filename, output_hash,
custo_total_usd, tokens_mycroft, tokens_watson, tokens_sherlock,
ambiente, diogenes_version, git_commit
```

**Total: 27 colunas.** Sem coluna de rastreamento para Irene ainda.

---

## 7. CLI — subcomandos disponíveis

```
diogenes init              — Inicializa workspace (cria estrutura + audit_index.csv)
diogenes start             — Abre novo ciclo (Motor de Start)
diogenes confirm-manifest  — Confirma manifesto e aciona Orquestrador
diogenes status            — Exibe estado atual de um ciclo
diogenes list              — Lista ciclos no audit_index.csv
diogenes proceed           — Autoriza prosseguimento após alerta crítico de Watson
diogenes pause             — Pausa ciclo após alerta crítico
diogenes resume            — Retoma ciclo pausado por Lestrade
diogenes abort             — Aborta ciclo por decisão de Lestrade
diogenes verify-output     — Aciona Motor de Saída (verificação do documento)
diogenes seal              — Chancela final de Lestrade
diogenes show              — Exibe arquivos da Stranger's Room de um ciclo
```

**Total: 12 subcomandos — todos implementados.** Nenhum placeholder.

---

## 8. Mycroft — call_types implementados

| call_type | Fase | Descrição |
|---|---|---|
| `definir_tasks_watson` | Watson | Mapeia arquivos e prioridades |
| `avaliar_agente` | Watson/Sherlock | Revisão da resposta do agente |
| `fixar_decisao` | Watson | Decisão final Watson |
| `montar_pacote_sherlock` | Sherlock | Prepara pacote de entrada para Sherlock |
| `avaliar_sherlock` | Sherlock | Revisão da validação metodológica |
| `fixar_decisao_sherlock` | Sherlock | Decisão final Sherlock |
| `consolidar` | Consolidação | Relatório final consolidado |

**Ausente:** `acionar_irene` / `verificar_existencia` — necessário para integração do Irene.

---

## 9. Irene — estado da integração

| Verificação | Status |
|---|---|
| `executar_irene()` no Orquestrador | AUSENTE |
| Estados `AGUARDANDO_IRENE` no CycleState | AUSENTE |
| Estado `VERIFICANDO_EXISTENCIA` no CycleState | AUSENTE |
| Estado `IRENE_CONCLUIDA` no CycleState | AUSENTE |
| Call_type `acionar_irene` no Mycroft heartbeat | AUSENTE |
| Referência a Irene no SDD atual | AUSENTE (SDD v0.1 não menciona Irene) |
| Pacote `irene` instalado no venv | NÃO INSTALADO |
| Variáveis `IRENE_*` no `.env` | AUSENTES (`.env` inexistente) |
| Coluna `irene_*` no audit_index | AUSENTE |

**Conclusão: Irene completamente ausente do código. Integração parte do zero.**

---

## 10. O que falta para a integração do Irene

Com base no diagnóstico, as ações necessárias em ordem lógica:

1. **Instalar pacote Irene** — `pip install irene==1.3.1` e adicionar ao `pyproject.toml`
2. **Adicionar estados ao CycleState** — `VERIFICANDO_EXISTENCIA`, `AGUARDANDO_IRENE`, `IRENE_CONCLUIDA` em `orchestrator/states.py`
3. **Atualizar TRANSICOES_VALIDAS** — definir grafo de transições para os novos estados
4. **Adicionar variáveis de ambiente** — `IRENE_*` no `.env.example` e em `config.py`
5. **Implementar `executar_irene()`** no `orchestrator/orchestrator.py` — acionar Irene após Sherlock
6. **Adicionar call_type `acionar_irene`** no `agents/mycroft.py` + seção correspondente em `docs/agentes/mycroft/heartbeat.md`
7. **Estender audit_index** — adicionar colunas `irene_invocada_at_utc`, `irene_resultado` em `models.py` (AUDIT_INDEX_COLUMNS)
8. **Atualizar `runtime.yaml`** — acrescentar novos estados à lista `ciclo.estados`
9. **Escrever testes** — unitários para os novos estados e integração para o fluxo Irene
10. **Atualizar CLI se necessário** — verificar se algum novo subcomando de controle da Irene é requerido

---

## 11. Divergências identificadas em relação ao SDD v0.1

| Item | SDD v0.1 | Código atual |
|---|---|---|
| Irene | Não mencionada | Não implementada — integração é sprint futuro |
| Colunas audit_index para Irene | N/A | Ausentes |
| Estados da máquina Irene | N/A | Ausentes |

Nenhuma divergência estrutural encontrada entre o SDD v0.1 e o código implementado. O código está alinhado com o SDD na sua versão atual. A integração do Irene está além do escopo do SDD v0.1 e requer documento próprio (INTEGRACAO_DIOGENES.md).

---

## 12. Próximo passo recomendado

Ler o `INTEGRACAO_DIOGENES.md` e implementar os estados `VERIFICANDO_EXISTENCIA`, `AGUARDANDO_IRENE` e `IRENE_CONCLUIDA` em `orchestrator/states.py` — esse é o ponto de ancoragem de toda a integração.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Documento gerado automaticamente pelo diagnóstico de estado — 2026-05-30*
