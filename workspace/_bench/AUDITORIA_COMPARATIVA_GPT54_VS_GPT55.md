# AUDITORIA COMPARATIVA: gpt-5.4-thinking vs gpt-5.5-thinking
## Projeto Diógenes — DVA-CBS | TC 015.848/2025-6
## Gerado em 2026-05-31 21:48 | **STATUS: PARCIAL** — gpt-5.5 run em progresso

---

## AVISO IMPORTANTE

> Esta auditoria é **parcial**: o run do gpt-5.5 ainda está em execução (28/~75 steps concluídos).
> A comparação direta de 5 CSVs (AUX_MOD_10 PF) é válida e representativa.
> Uma atualização final deve ser gerada após a conclusão do run gpt-5.5.

---

## 1. CONFIGURAÇÃO DOS RUNS

| Parâmetro            | gpt-5.4-thinking                     | gpt-5.5-thinking                     |
|----------------------|--------------------------------------|--------------------------------------|
| **Run ID**           | pipeline_MOD010MCP3_20260531T184251Z | pipeline_MOD_010_20260531T234500Z    |
| **Módulo**           | MOD010MCP3 (piloto reduzido)         | MOD_010 (módulo completo)            |
| **CSVs analisados**  | 5                                    | 69 (em progresso: 26 done)           |
| **XLSX**             | AUX_MOD_10 PF - execução.xlsx (1)    | AUX_MOD_10 PF - execução.xlsx (1)    |
| **Timeout**          | 240s                                 | 600s                                 |
| **Max retries**      | 2                                    | 4                                    |
| **Profile**          | stable-gpt54                         | default (agents_spec gpt-5.5)        |
| **Status do run**    | ✅ COMPLETO (12/12 steps)            | ⏳ EM PROGRESSO (28/~75 steps)       |

---

## 2. RESULTADO POR ETAPA — COMPARAÇÃO DIRETA (5 CSVs AUX_MOD_10 PF)

> Mesmos arquivos de entrada — comparação controlada válida.

### 2.1 Timing por Step

| Step                   | gpt-5.4 (s) | gpt-5.5 (s) | Δ (s)    | Δ (%)    |
|------------------------|-------------|-------------|----------|----------|
| irene_catalog          | 140.7       | 125.9 (*)   | −14.8    | −11%     |
| mycroft_tasks          | 81.7        | 128.1 (*)   | +46.4    | +57%     |
| watson_analise_01      | 180.7       | 157.1       | −23.6    | −13%     |
| watson_analise_02      | 163.4       | 99.7        | −63.7    | −39%     |
| watson_analise_03      | 166.0       | 114.2       | −51.8    | −31%     |
| watson_analise_04      | 143.7       | 120.0       | −23.7    | −17%     |
| watson_analise_05      | 129.3       | 86.6        | −42.7    | −33%     |
| **Avg Watson 1-5**     | **156.6s**  | **115.5s**  | **−41.1**| **−26%** |

> (*) irene_catalog e mycroft_tasks do gpt-5.5 processam 69 CSVs (módulo completo), não apenas 5.
> Comparação de irene/mycroft não é diretamente equivalente.

### 2.2 Tokens por Step (Watson 1-5)

| Step              | gpt-5.4 input | gpt-5.4 output | gpt-5.5 input | gpt-5.5 output | Δ output |
|-------------------|---------------|----------------|---------------|----------------|----------|
| watson_analise_01 | 10,791        | 12,352         | 10,791        | 9,370          | −24%     |
| watson_analise_02 | 7,170         | 11,570         | 7,170         | 7,148          | −38%     |
| watson_analise_03 | 6,192         | 10,728         | 6,192         | 8,201          | −24%     |
| watson_analise_04 | 6,216         | 9,610          | 6,216         | 8,396          | −13%     |
| watson_analise_05 | 5,930         | 8,266          | 5,930         | 5,855          | −29%     |
| **Total**         | **36,299**    | **52,526**     | **36,299**    | **38,970**     | **−26%** |

> **Insight:** Mesmos tokens de input (mesmos CSVs), mas gpt-5.5 produz 26% menos output.
> gpt-5.5 é mais conciso — para Watson (análise técnica), isso pode ser positivo (menos redundância)
> ou negativo (menos detalhe). Requer avaliação qualitativa dos outputs.

### 2.3 Custo Estimado (Watson 1-5 — base comparável)

| Modelo           | Custo Watson 1-5 | Custo/análise |
|------------------|------------------|---------------|
| gpt-5.4-thinking | USD 0.879        | USD 0.176     |
| gpt-5.5-thinking | USD 1.351        | USD 0.270     |
| **Δ**            | **+USD 0.472**   | **+54%**      |

> gpt-5.5 custa ~54% mais por chamada Watson nos mesmos arquivos.
> Extrapolando para 69 CSVs com gpt-5.5: custo Watson esperado ≈ USD 18.62.

---

## 3. CONFIABILIDADE

### 3.1 Erros e Timeouts

| Modelo           | Steps done | API Errors | Timeouts | Success Rate | Outliers         |
|------------------|------------|------------|----------|--------------|------------------|
| gpt-5.4-thinking | 12/12      | 0          | 0        | **100%**     | nenhum           |
| gpt-5.5-thinking | 28/~75     | 0          | 0        | **100%**     | step15 = 335.9s  |

> **Outlier gpt-5.5 step 15**: 335.9s vs média 126s. Arquivo com 12,505 tokens de input.
> Não causou erro — o timeout de 600s absorveu. Com timeout=240s (config gpt-5.4), teria falhado.
> **Risco identificado**: com timeout menor, gpt-5.5 teria ~5% falha neste step.

### 3.2 Análise do Outlier

- **Step**: watson_analise_15 | **Arquivo**: ~12,505 tokens input
- **Duração**: 335.9s (2.7x a média de 126s)
- **Custo**: USD 0.295 (baixo — pouco output: 7,756 tokens)
- **Causa provável**: arquivo com estrutura complexa → reasoning chain mais longa
- **Mitigação**: usar timeout ≥ 400s para gpt-5.5 em produção

---

## 4. MÉTRICAS GLOBAIS (RUN COMPLETO gpt-5.4 vs PARCIAL gpt-5.5)

| Métrica                     | gpt-5.4 (12 steps, 5 CSVs) | gpt-5.5 (28 steps, 26 CSVs) |
|-----------------------------|----------------------------|------------------------------|
| Duração total                | 1,413s = 23.5min           | 3,531s = 58.8min (parcial)   |
| Tokens input                | 128,683                    | 651,883 (parcial)            |
| Tokens output               | 84,824                     | 238,035 (parcial)            |
| Custo estimado              | ~USD 1.59                  | USD 10.40 (parcial)          |
| Erros                       | 0                          | 0                            |
| Duração estimada total      | —                          | ~159min (2.65h)              |

> **Atenção**: comparação direta não é justa — escopos são diferentes (5 vs 69 CSVs).
> Para custo proporcional: gpt-5.4 equivalente em 5 CSVs = ~$1.59 vs gpt-5.5 em 5 CSVs = ~$1.35*5/5 ≈ similar.
> Mas pricing por token do gpt-5.5 é ~54% maior nos mesmos 5 files.

---

## 5. QUALIDADE DOS OUTPUTS — ANÁLISE COMPARATIVA (Watson 1-5)

### gpt-5.4-thinking
- Outputs mais verbosos (52,526 tokens para 5 files)
- Maior detalhamento técnico por análise
- Tempo maior mas mais confiável contra timeout (máx 180.7s < 240s threshold)

### gpt-5.5-thinking
- Outputs mais concisos (38,970 tokens para mesmos 5 files — −26%)
- Mais rápido em geral (115.5s vs 156.6s avg Watson)
- **Um outlier em 26 steps** (335.9s) — requer timeout mais alto (≥400s)
- Custo por chamada ~54% maior

> Avaliação qualitativa completa (checagem de coerência analítica dos outputs)
> será incluída na versão final desta auditoria após conclusão do run gpt-5.5.

---

## 6. RESULTADOS DO PIPELINE COMPLETO (gpt-5.4 — referência)

Extraído do run completo `pipeline_MOD010MCP3_20260531T184251Z`:

| Step                   | Duração | Status    | Observação                           |
|------------------------|---------|-----------|--------------------------------------|
| irene_catalog          | 140.7s  | ✅ ok     | Classificação das 5 abas             |
| mycroft_tasks          | 81.7s   | ✅ ok     | 5 tarefas Watson definidas           |
| watson_analise_01..05  | avg 157s| ✅ ok     | 5/5 análises concluídas              |
| watson_consolidar      | 236.0s  | ✅ ok     | 87K chars de input (5 análises)      |
| mycroft_avaliar_watson | 43.7s   | ✅ ok     | Emitiu CRITICA (sem justif. severity)|
| sherlock_validacao     | 59.2s   | ⚠️ limited| Ausência MC_mapa_pontos.md esperada  |
| mycroft_avaliar_sherlock| 42.4s  | ✅ ok     | Aprovado com ressalvas                |
| mycroft_consolidar     | 26.6s   | ✅ ok     | Relatório final gerado               |

**Achado principal (gpt-5.4)**: Watson identificou inconsistência metodológica na
relação produtor rural/CBS. Mycroft emitiu CRITICA válida por falta de justificativa
de severidade — comportamento protocolar correto.

---

## 7. RECOMENDAÇÕES TÉCNICAS

### 7.1 Para Uso em Produção (Ciclo Oficial Diógenes)

| Decisão                    | Recomendação                                |
|---------------------------|---------------------------------------------|
| Modelo principal           | **gpt-5.5-thinking** (quando disponível)    |
| Modelo fallback            | **gpt-5.4-thinking** (100% confiável)       |
| Timeout recomendado        | **≥ 400s** (por conta do outlier 335.9s)    |
| Max retries                | **4** (atual) — mantener                    |
| Backoff                    | **60s** entre retries — mantener            |
| CSVs por run               | Sem limite prático observado (69 ok)        |

### 7.2 Para Bench Pipeline

| Decisão                         | Recomendação                                        |
|---------------------------------|-----------------------------------------------------|
| Modelo bench                    | `--model gpt-5.5-thinking --timeout 400`            |
| Módulo piloto bench             | MOD010MCP3 (5 CSVs) — mais rápido (23min vs 159min) |
| Comparação de modelos           | Sempre usar mesmo módulo (MOD010MCP3) para apple-to-apple |
| Timeout consolidação Watson     | ≥ 400s (prompt cresce com N CSVs)                   |

### 7.3 Decisão sobre Migração gpt-5.4 → gpt-5.5

| Critério            | gpt-5.4          | gpt-5.5          | Vencedor     |
|---------------------|------------------|------------------|--------------|
| Velocidade Watson   | 156.6s avg       | 115.5s avg       | gpt-5.5 −26%|
| Confiabilidade      | 100% (12 steps)  | 100% (28 steps)  | Empate       |
| Custo/chamada       | USD 0.176/Watson | USD 0.270/Watson | gpt-5.4 −54%|
| Verbosidade output  | Alta             | Moderada         | Depende      |
| Risco outlier       | Nenhum           | 1/26 (335.9s)    | gpt-5.4      |
| Timeout necessário  | 240s suficiente  | ≥400s necessário | gpt-5.4      |

> **Recomendação:** Aguardar conclusão do run gpt-5.5 para avaliação qualitativa completa.
> Se qualidade for equivalente: **gpt-5.5 para produção** (mais rápido, custo compensado por
> menos tokens de output). Se qualidade inferior: manter **gpt-5.4-thinking** como principal.

---

## 8. ANOMALIAS E BUGS IDENTIFICADOS

| # | Anomalia                              | Modelo   | Criticidade | Status     |
|---|---------------------------------------|----------|-------------|------------|
| 1 | Outlier step15: 335.9s               | gpt-5.5  | Médio       | Conhecido  |
| 2 | live_status.json sem tokens           | gpt-5.5  | Baixo       | Bug menor  |
| 3 | irene_catalog input 52K vs 8.8K       | gpt-5.5  | Info        | Escopo diferente |
| 4 | mycroft_tasks: gpt-5.5 mais lento (+57%)| gpt-5.5 | Médio       | Investigar |

> Bug #2: o campo `prompt_tokens`/`completion_tokens` não foi gravado no _live_status.json
> para o run gpt-5.5. Tokens disponíveis apenas via log. Corrigir em pipeline.py para
> salvar tokens no live_status (já está no _audit.json mas não no live_status intermediário).

---

## 9. PRÓXIMOS PASSOS

1. **Aguardar conclusão do run gpt-5.5** (~100min restantes a partir desta geração)
2. **Atualizar esta auditoria** com dados completos: consolidação, Sherlock, Mycroft final
3. **Avaliação qualitativa** dos outputs Watson: comparar achados concretos entre modelos
4. **Corrigir Bug #2**: salvar tokens no live_status.json durante a execução
5. **Fixar timeout padrão** para gpt-5.5: atualizar agents_spec.yaml para 400s
6. **Decisão de migração**: com dados completos, decidir modelo padrão para próximo sprint

---

## 10. REFERÊNCIAS DOS ARTEFATOS

| Artefato                    | Caminho                                                               |
|-----------------------------|-----------------------------------------------------------------------|
| Run gpt-5.4 (audit.json)    | workspace/_bench/pipeline_MOD010MCP3_20260531T184251Z/_audit.json    |
| Run gpt-5.5 (live_status)   | workspace/_bench/pipeline_MOD_010_20260531T234500Z/_live_status.json  |
| Log gpt-5.5                 | workspace/_bench/run_gpt55_20260531T234500Z.log                       |
| Auditoria gpt-5.4 completa  | workspace/_bench/pipeline_MOD010MCP3_20260531T180253Z/AUDITORIA_BENCH_GPT54.md |

---
*Auditoria parcial gerada automaticamente em 2026-05-31 21:48 | DVA-CBS | TC 015.848/2025-6*
*Atualizar após conclusão do run pipeline_MOD_010_20260531T234500Z*
