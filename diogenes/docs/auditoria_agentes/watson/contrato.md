# Watson Agent — Contrato Projetado × Montado × Real

**Tipo:** Invocador de Agente LLM sequencial/paralelo.
**Invocador:** `src/diogenes/agents/watson.py` (`WatsonAgent`) + `src/diogenes/agents/file_prep.py` (`preparar_arquivo`).
**Definição:** `docs/agentes/watson/{soul,skills,agent,heartbeat}.md`.
**Baseline real:** ciclo `MOD_010_A1_20260602T202655Z`.

---

## 1. Mapeamento de Call Types e Parâmetros

| Call Type | Objetivo do Prompt | Modelo Projetado (`agent.md`) | Modelo Real no Ciclo | Injetado no User Prompt | Arquivo de Output Real |
|:---|:---|:---|:---|:---|:---|
| `analise_inicial` | Analisar a integridade de um único arquivo isoladamente | `claude-opus-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [analise_arquivo] + `MC_tasks_watson.md` + Conteúdo do arquivo | `watson_analise_{nome}.md` + `watson_trace_{nome}.md` (opcional) |
| `consolidar_watson` | Sintetizar análises isoladas e mapear cadeia produtiva | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [consolidar_watson] + `MC_tasks_watson.md` + Lista de outputs de análise isolada | `watson_consolidado.md` + `watson_registro_decisao.md` |
| `validacao_planilha_rn` | Validar quantitativamente a planilha de regras de negócio | N/D (opcional) | `gpt-5.5-thinking` | `heartbeat.md` [validacao_planilha_rn] + `MC_tasks_watson.md` + Planilha + Outputs isolados | `watson_planilha_rn.md` |
| `resposta_r1` / `r2` | Responder questionamentos de Mycroft na Stranger Room | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [resposta_r*] + Output anterior + Crítica Mycroft + Trace (se aplicável) | `watson_resposta_r*.md` |

---

## 2. Limites Constitucionais e Regras Hard

| Artigo / Regra | Definição no `soul.md` / `agent.md` | Implementação no Código (`watson.py`) | Validação no Ciclo Real |
|:---|:---|:---|:---|
| **Artigo 6 (Integridade Apenas)** | Watson nunca emite juízos metodológicos. Não usa termos como "Atendido", "Divergência", "Conforme metodologia", etc. Usa apenas a escala: `CRITICA`, `ALTA`, `MEDIA`, `BAIXA`. | A função `_parsear_output` extrai apenas os alertas e suas severidades locais. | **Pendente de calibração:** Verificar se Watson vazou taxonomias metodológicas nas análises ou no consolidado. |
| **Artigo 4 (Mandato de Invocação)** | Watson nunca inicia tarefas por conta própria. Executa as tasks delegadas por Mycroft. | O orquestrador monta `MC_tasks_watson.md` e invoca `WatsonAgent.analisar_arquivo` sequencialmente. | **Confirmado:** Watson agiu estritamente sob delegação. |
| **Artigo 13 (Isolamento de Diretório)** | Opera exclusivamente sobre as cópias geradas no diretório de trabalho isolado. | O `preparar_arquivo` lê caminhos locais sob o diretório do ciclo. | **Confirmado.** |
| **Artigo 14 (Impessoalidade)** | Redação em 3ª pessoa e impessoal (exceto traces). Assinatura ao final apenas para rastreabilidade. | `watson_analise_*.md` e `watson_consolidado.md` seguem templates formais e assinam com cargo. | **Confirmado.** |
| **Exceção do Trace** | O trace (`watson_trace_*.md`) usa 1ª pessoa. É uso interno e nunca vai ao GT. | Traces são gerados opcionalmente e mantidos na subpasta `_runtime/` (não no output final). | **Confirmado.** |
| **Limite de Rodadas** | Watson responde a no máximo 2 rodadas na Stranger Room (`resposta_r1` e `resposta_r2`). | O orquestrador limita o loop a 2 iterações e falha se houver tentativa de 3ª rodada. | **Confirmado.** |
