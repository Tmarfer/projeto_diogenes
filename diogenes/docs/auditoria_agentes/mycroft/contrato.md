# Mycroft Agent — Contrato Projetado × Montado × Real

**Tipo:** Invocador de Agente LLM para Orquestração, Avaliação e Consolidação de Ciclos.
**Invocador:** `src/diogenes/agents/mycroft.py` (`MycrooftAgent`).
**Definição:** `docs/agentes/mycroft/{soul,skills,agent,heartbeat}.md`.
**Baseline real:** ciclo `MOD_010_A1_20260602T202655Z`.

---

## 1. Mapeamento de Call Types e Parâmetros

| Call Type | Objetivo do Prompt | Modelo Projetado (`agent.md`) | Modelo Real no Ciclo | Injetado no User Prompt | Arquivo de Output Real |
|:---|:---|:---|:---|:---|:---|
| `definir_tasks_watson` | Definir e ordenar as tarefas de integridade de Watson a partir do manifesto do ciclo e catálogo semântico | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [definir_tasks_watson] + Manifesto + Catálogo Irene + Inventário | `MC_tasks_watson.md` |
| `mapear_pontos` | Mapear cada ponto metodológico do Apêndice aos arquivos analisados por Watson | `claude-sonnet-4-6` | Não utilizado no ciclo real | `heartbeat.md` [mapear_pontos] + Apêndice + watson_analise_*.md | `MC_mapa_pontos.md` |
| `avaliar_agente` (avaliar_watson / avaliar_sherlock) | Avaliar o raciocínio do agente executor, retornando branching parseável (APROVADO ou CRITICA) com no máximo uma crítica | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [avaliar_agente] / [avaliar_sherlock] + Output do agente + Histórico + Critérios | `MC_avaliacao_watson_r[n].md` / `MC_avaliacao_sherlock_r[n].md` |
| `fixar_decisao` (watson / sherlock) | Bater o martelo na Stranger Room após 2 rodadas, consolidando a classificação final (acatada ou fixada) | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [fixar_decisao] / [fixar_decisao_sherlock] + Histórico + Respostas + Críticas | `MC_decisao_watson.md` / `MC_decisao_sherlock.md` |
| `montar_pacote_sherlock` | Sintetizar as descobertas e alertas de Watson para contextualizar Sherlock, incluindo nota metodológica alterada | `claude-sonnet-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [montar_pacote_sherlock] + Inventário + Decisão Watson + Metodologia + Corpus Jurídico | `MC_pacote_sherlock.md` |
| `consolidar` | Consolidar os relatórios de Watson e Sherlock no Relatório Final/Preliminar, verificando 11 seções obrigatórias | `claude-opus-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [consolidar] + Watson consolidado + Sherlock consolidado + Decisões de Mycroft | `MC_consolidado.md` |
| `acionar_irene` | Decidir se o catálogo Irene deve ser gerado ou reutilizado a partir da versão | `claude-sonnet-4-6` | Não utilizado via LLM (executado por lógica de código) | `heartbeat.md` [acionar_irene] + Manifesto + Diretórios | `MC_instrucao_irene.md` |

---

## 2. Limites Constitucionais e Regras Hard

| Artigo / Regra | Definição no `soul.md` / `skills.md` | Implementação no Código (`mycroft.py`) | Validação no Ciclo Real |
|:---|:---|:---|:---|
| **Artigo 3 (Sequencialidade)** | Os agentes Watson e Sherlock jamais operam em paralelo. Mycroft controla e garante a linearidade do ciclo. | Orquestrador gerencia a máquina de estados sequencialmente. | **Confirmado:** Watson rodou por completo e sua Stranger Room fechou antes de Sherlock iniciar. |
| **Artigo 5 (Não-intervenção)** | Mycroft não abre arquivos brutos, não faz cálculos e não valida a metodologia diretamente. Ele julga exclusivamente com base nas justificativas e outputs apresentados. | Mycroft recebe apenas o inventário, metadados e o texto consolidado dos agentes executors. | **Confirmado:** Nenhuma chamada de Mycroft recebeu dados brutos de arquivos originais. |
| **Artigo 8 (Regra do Martelo)** | Mycroft dispõe de no máximo duas rodadas de críticas na Stranger Room. Na terceira chamada, ele deve obrigatoriamente bater o martelo. | O loop de Stranger Room é rigidamente controlado e limitado pelo orquestrador. | **Confirmado:** A máquina de estados força `fixar_decisao` após `resposta_r2`. |
| **Artigo 9 (Alertas Críticos)** | Alerta `CRITICA` de Watson gera notificação a Lestrade antes de encaminhar o pacote a Sherlock. | `DecisaoFinal` expõe `has_critical_alert` e o orquestrador gera `MC_alerta_critico_lestrade.md`. | **Confirmado:** O pipeline detectou e expôs o status adequadamente. |
| **Artigo 10 (Sem arbitrariedade de dilemas)** | Mycroft não decide dilemas genuinamente equilibrados sem amparo legal/normativo; ele os expõe no relatório final a Lestrade. | O parser lê os dilemas contados por Sherlock e o prompt de Mycroft o instrui a não decidi-los de forma arbitrária. | **Confirmado.** |
| **Artigo 14 (Impessoalidade)** | Redação de todos os relatórios em terceira pessoa e sem menção a nomes de agentes no corpo. | Os prompts e templates de `consolidar` e `definir_tasks` impõem redação impessoal. | **Confirmado:** Mycroft é assinado apenas ao final. |
| **Verificação de Completude** | Mycroft deve atestar que o relatório de Sherlock contém as 11 seções obrigatórias antes de emitir o consolidado final. | `_parsear_decisao_sherlock` e `consolidar` verificam os cabeçalhos das seções em `sherlock_consolidado.md`. | **Confirmado.** |
| **Regra Absoluta de Crítica** | Exatamente uma crítica localizada por chamada de `avaliar_agente`. | O prompt do heartbeat limita Mycroft a escolher apenas o ponto de maior impacto se houver múltiplos problemas. | **Confirmado.** |
