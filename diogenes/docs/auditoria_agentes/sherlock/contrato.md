# Sherlock Agent — Contrato Projetado × Montado × Real

**Tipo:** Invocador de Agente LLM para Validação Metodológica.
**Invocador:** `src/diogenes/agents/sherlock.py` (`SherlockAgent`).
**Definição:** `docs/agentes/sherlock/{soul,skills,agent,heartbeat}.md`.
**Baseline real:** ciclo `MOD_010_A1_20260602T202655Z`.

---

## 1. Mapeamento de Call Types e Parâmetros

| Call Type | Objetivo do Prompt | Modelo Projetado (`agent.md`) | Modelo Real no Ciclo | Injetado no User Prompt | Arquivo de Output Real |
|:---|:---|:---|:---|:---|:---|
| `validacao_inicial` | Validar a aderência metodológica dos pontos individualmente | `claude-opus-4-6` (reexecutável per-point) | `gpt-5.5-thinking` | `heartbeat.md` [verificar_ponto] (via mapeamento) + Pacote Sherlock (síntese de Mycroft, watson_apresentacao, metodologia, corpus) | `01_apresentacao.md` (no consolidado final, via intermédio de output_pontos) |
| `validacao_planilha_rn_sherlock` | Validar a Planilha de Verificação sob perspectiva metodológica | Opcional / Não especificado | `gpt-5.5-thinking` | `heartbeat.md` [validacao_planilha_rn_sherlock] + Pacote Sherlock + `watson_planilha_rn.md` | `sherlock_planilha_rn.md` (no _runtime, opcional) |
| `consolidar_sherlock` | Consolidar pontos da Fase 1, análise sistêmica e relatório de 11 seções | `claude-opus-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [consolidar_sherlock] + quadro consolidado + `watson_consolidado.md` | `sherlock_consolidado.md` + `sherlock_registro_decisao.md` + `sherlock_ocorrencias.json` |
| `resposta_r1` / `r2` | Responder questionamentos de Mycroft na Stranger Room | `claude-opus-4-6` | `gpt-5.5-thinking` | `heartbeat.md` [resposta_r*] + Output anterior + Crítica Mycroft + Ponto relevante | `sherlock_resposta_r*.md` |

---

## 2. Limites Constitucionais e Regras Hard

| Artigo / Regra | Definição no `soul.md` / `agent.md` | Implementação no Código (`sherlock.py`) | Validação no Ciclo Real |
|:---|:---|:---|:---|
| **Artigo 7 (Camada 1 a 3 Apenas)** | Sherlock não analisa integridade estrutural (fórmulas, scripts brutos). Parte dos dados de Watson. Toda classificação cita dispositivo metodológico. | O invocador passa as análises do Watson (`watson_apresentacao`) em vez de arquivos brutos. | **Confirmado:** Sherlock focou estritamente na metodologia. |
| **Citação de Dispositivo Obrigatória** | Toda classificação (Atendido, Divergência, etc.) deve vir acompanhada da citação no formato definido no `skills.md`. | O parser verifica se o output possui classificações associadas a dispositivos legais ou metodológicos. | **Confirmado:** O output de baseline e R1 contêm citações precisas no formato. |
| **Artigo 4 (Mandato de Invocação)** | Sherlock age sob delegação de Mycroft sobre o pacote integrado local. | O orquestrador invoca os métodos sob controle da máquina de estados do ciclo. | **Confirmado.** |
| **Artigo 14 (Impessoalidade)** | Redação em 3ª pessoa e impessoal. Nome ou persona "Sherlock Holmes" apenas na assinatura final. | Os outputs do consolidado e respostas seguem templates impessoais. | **Confirmado:** 1 vazamento do termo "Sherlock" detectado no baseline foi higienizado e corrigido. |
| **Limite de Rodadas** | Sherlock responde a no máximo 2 rodadas na Stranger Room (`resposta_r1` e `resposta_r2`). | O orquestrador limita o loop a 2 iterações. | **Confirmado.** |
| **Dilema Não Arbitrário (Artigo 10)** | Dilemas equilibrados não são decididos arbitrariamente; são reportados para Mycroft. | Sherlock possui seções para registrar dilemas e contadores parseados pelo invocador. | **Confirmado.** |
| **Um Ponto Por Chamada (UM_PONTO_POR_CHAMADA)** | Em `verificar_ponto`, o invocador injeta exatamente um ponto por chamada. Sherlock não verifica múltiplos pontos. | **DIVERGÊNCIA CRÍTICA:** O orquestrador faz uma única chamada de `validar()` passando o pacote inteiro com todas as metodologias e sem mapa de pontos delimitado. | **Violado pela Orquestração:** Isso causou a recusa de análise por Sherlock e a consequente emissão de zero pontos válidos. |
