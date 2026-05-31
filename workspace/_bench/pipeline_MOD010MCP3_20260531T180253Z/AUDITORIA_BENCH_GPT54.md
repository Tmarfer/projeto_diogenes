# AUDITORIA COMPLETA — Pipeline de Bancada com gpt-5.4-thinking

**Data:** 2026-05-31 15:02–15:22 (UTC-3)
**Pipeline ID:** BENCH_PIPELINE_MOD010MCP3_20260531T180253Z
**Módulo:** MOD010MCP3 (AUX_MOD_10 PF - execução.xlsx + 5 CSVs)
**Modelo:** gpt-5.4-thinking (override em todos os agentes)
**TC:** 015.848/2025-6 | DVA-CBS | TCU SecexContas

---

## 1. RESUMO EXECUTIVO

| Métrica | Valor |
|---------|-------|
| **Status** | ✅ 12/12 SUCESSO |
| **Duração total** | 1200.2s (20 min) |
| **Tokens input** | 123,074 |
| **Tokens output** | 80,251 |
| **Tokens total** | 203,325 |
| **Custo referência** | USD 1.51 |
| **Erros** | 0 |
| **HTTP 500** | 0 |
| **Timeouts** | 0 |

### Comparativo com execuções anteriores

| Run | Modelo | Duração | Success | Erros | Tokens |
|-----|--------|---------|---------|-------|--------|
| Orquestrador oficial (ciclo 16h) | Mixed (Sonnet+Gemini+GPT) | 16+ horas | Parcial | Múltiplos | ~220K |
| Bench #1 (agents_spec) | Mixed | 914s | 3/12 (25%) | 9 | 9K+15K |
| Bench #2 (gemini-flash) | gemini-3.1-flash-lite | 211s | 10/12 (83%) | 2 | 8K+80K |
| **Bench #3 (gpt-5.4)** | **gpt-5.4-thinking** | **1200s** | **12/12 (100%)** | **0** | **123K+80K** |

**Conclusão:** gpt-5.4-thinking é o ÚNICO modelo que completou 12/12 passos sem NENHUM erro.
Tempo maior (20min vs 3.5min do gemini) é compensado pela confiabilidade total e qualidade superior.

---

## 2. TABELA DE PASSOS DETALHADA

| # | Passo | Agente | Duração | Input tok | Output tok | Custo ref | System chars | User chars |
|---|-------|--------|---------|-----------|------------|-----------|-------------|------------|
| 1 | irene_catalog | mycroft | 95.3s | 8,851 | 4,938 | $0.096 | 16,636 | 11,211 |
| 2 | mycroft_tasks | mycroft | 47.9s | 6,180 | 2,882 | $0.059 | 16,636 | 3,441 |
| 3 | watson_analise_01 | watson | 166.2s | 10,791 | 11,957 | $0.206 | 16,002 | 13,714 |
| 4 | watson_analise_02 | watson | 174.9s | 7,170 | 13,897 | $0.226 | 16,002 | 6,591 |
| 5 | watson_analise_03 | watson | 132.6s | 6,192 | 8,639 | $0.145 | 16,002 | 3,230 |
| 6 | watson_analise_04 | watson | 143.5s | 6,216 | 9,270 | $0.155 | 16,002 | 3,238 |
| 7 | watson_analise_05 | watson | 110.8s | 5,930 | 6,997 | $0.120 | 16,002 | 2,516 |
| 8 | watson_consolidar | watson | 162.3s | 25,424 | 13,624 | $0.268 | 10,943 | 81,472 |
| 9 | mycroft_avaliar | mycroft | 48.6s | 12,208 | 2,275 | $0.065 | 13,970 | 26,089 |
| 10 | sherlock_validacao | sherlock | 29.4s | 13,956 | 1,215 | $0.053 | 18,019 | 29,143 |
| 11 | mycroft_avaliar_sherlock | mycroft | 50.3s | 5,355 | 2,705 | $0.054 | 13,970 | 2,989 |
| 12 | mycroft_consolidar | mycroft | 38.3s | 14,801 | 1,852 | $0.065 | 15,827 | 34,989 |

### Distribuição por agente

| Agente | Chamadas | Tempo total | Tokens input | Tokens output | Custo ref |
|--------|----------|-------------|-------------|---------------|-----------|
| Watson | 6 | 890.3s (74%) | 61,723 | 64,384 | $1.12 |
| Mycroft | 5 | 280.4s (23%) | 47,395 | 14,652 | $0.34 |
| Sherlock | 1 | 29.4s (2%) | 13,956 | 1,215 | $0.05 |

---

## 3. ANÁLISE DE QUALIDADE DOS OUTPUTS

### 3.1 Watson — Análise de integridade (EXCELENTE)
- **5/5 CSVs analisados** com profundidade adequada
- Identificou 31 alertas (5 CRÍTICA, 9 ALTA, 15 MÉDIA, 2 BAIXA)
- Mapeou cadeia de produção cross-file com 9 elos identificados
- Consolidação de 26K chars com inventário tabular completo
- Registro de decisão sobre severidades e bifurcações analíticas
- **Ponto forte:** análise numérica detalhada com verificação de totalizadores

### 3.2 Mycroft — Coordenação (EXCELENTE)
- Tasks Watson: definição estruturada com premissas globais e restrições operacionais
- Avaliação Watson: identificou fragilidade na fundamentação da severidade CRÍTICA
- Emitiu "CRITICA" (pedir revisão) ao invés de aprovação cega — comportamento correto
- Consolidação final: corretamente recusou emitir MC_consolidado sem sherlock_consolidado
- **Ponto forte:** rigor procedimental (não aprova sem fundamentação completa)

### 3.3 Sherlock — Validação metodológica (CORRETO, mas limitado)
- Corretamente recusou emitir classificação sem MC_mapa_pontos.md e Apêndice metodológico
- Registrou premissas globais identificáveis (ano-base 2023/2024)
- Identificou limitação material (ausência de insumos mínimos)
- **Nota:** esse comportamento é ESPERADO no bench — Sherlock precisa do pacote metodológico completo que não existe no MOD010MCP3 de teste

### 3.4 Achado material do ciclo
Watson identificou risco na relação entre:
- Retração/variação das bases de cálculo
- Arrecadação estimada
- Créditos (especialmente no produtor rural)
- Uso de preço médio ANP como deflator para volume de combustível

Isso confirma o achado da execução anterior (teste MCP com chattcu_complete).

---

## 4. ERROS CATALOGADOS

### 4.1 Nesta execução (gpt-5.4-thinking)
**ZERO erros.** Todas as 12 chamadas completaram com sucesso.

### 4.2 Histórico de erros (execuções anteriores)

| Erro | Modelo | Causa raiz | Solução |
|------|--------|-----------|---------|
| Read timeout 120s | Claude 4.6 Sonnet | Modelo saturado/indisponível no ChatTCU | Override para gpt-5.4-thinking |
| HTTP 500 intermitente | gemini-3.1-flash-lite | Saturação temporária do backend Gemini | Retry ou override |
| Prompt 55K chars timeout | Todos (via orquestrador) | soul+agent+heartbeat+skills = 55K | Prompts reduzidos (soul+section ≈ 12K) |
| MSAL token failure | Todos (orquestrador) | Token expirado + rede instável | Lazy auth + retry |

### 4.3 Padrões identificados
1. **Claude 4.6 Sonnet**: não confiável no ChatTCU atual (100% timeout)
2. **gemini-3.1-flash-lite**: rápido mas instável (~20% HTTP 500)
3. **gpt-5.4-thinking**: lento mas 100% confiável (melhor trade-off)
4. **Prompts reduzidos**: funcionam perfeitamente (~12K vs 55K)

---

## 5. MÉTRICAS DE PERFORMANCE

### Latência por tipo de chamada
- Watson análise individual: 110-175s (média 146s)
- Watson consolidação: 162s (user_prompt grande: 81K chars)
- Mycroft avaliação: 48-50s
- Mycroft consolidação: 38s
- Sherlock validação: 29s (mais rápido — user_prompt menor)

### Throughput
- Tokens/segundo (output): 66.9 tok/s
- Chars/segundo (output): ~120 chars/s

### Eficiência de prompt
- System prompt médio: 15.3K chars
- User prompt médio: 18.2K chars (exceto consolidação Watson: 81K)
- Ratio output/input: 0.65 (65% dos tokens de input viram output)

---

## 6. RECOMENDAÇÕES PARA PRÓXIMA ITERAÇÃO

### 6.1 Modelo de produção
**Recomendação:** usar gpt-5.4-thinking para Watson e Mycroft, manter para Sherlock.
- Não usar Claude 4.6 Sonnet no ChatTCU até resolver instabilidade
- gemini-3.1-flash-lite como fallback rápido (aceitar ~20% retry)
- Para produção: considerar timeout 200s (Watson #2 atingiu 175s)

### 6.2 Pipeline de bancada
- Adicionar retry (max_retries=2) para absorver HTTP 500 intermitentes
- Adicionar opção `--skip-on-error` para continuar pipeline mesmo com falha
- Adicionar `--timeout-watson` separado (Watson precisa mais que Mycroft)

### 6.3 Sherlock
- Para testes reais, precisa receber MC_mapa_pontos.md e Apêndice metodológico
- Criar fixture de pacote metodológico mínimo para bench testing
- Considerar modo "free-form" onde Sherlock analisa sem protocolo rígido

### 6.4 Watson
- Timeout Watson deveria ser 200s+ (2 chamadas ficaram acima de 160s)
- Considerar paralelismo Watson (análises são independentes entre si)
- Consolidação Watson é o passo mais caro (25K input + 81K user prompt)

### 6.5 Mycroft
- Funcionou rapidamente (38-50s) — prompt mais curto, resposta concisa
- Comportamento de "CRITICA + pedir revisão" é desejado
- Para bench, considerar ciclo Watson→Mycroft→Watson(R1)→Mycroft(aceitar)

### 6.6 Próximos testes
1. Rodar com 2 retries para eliminar HTTP 500 do gemini
2. Testar com o XLSX completo (11 planilhas) usando sample mode
3. Criar fixture MC_mapa_pontos para exercitar Sherlock plenamente
4. Testar ciclo de revisão (Watson R1 após crítica do Mycroft)

---

## 7. ARTEFATOS GERADOS

```
workspace/_bench/pipeline_MOD010MCP3_20260531T180253Z/
├── 01_irene_catalog.md           (10 KB) — Classificação de abas
├── 02_mycroft_tasks.md           (10 KB) — MC_tasks_watson.md
├── 03_watson_01_...aux_mod_10.csv.md    (17 KB) — Análise principal
├── 03_watson_02_...aux_mod_10_1.csv.md  (18 KB) — Análise auxiliar 1
├── 03_watson_03_...aux_mod_10_2.csv.md  (16 KB) — Análise auxiliar 2
├── 03_watson_04_...aux_mod_10_3.csv.md  (18 KB) — Análise auxiliar 3
├── 03_watson_05_...aux_mod_10_4.csv.md  (14 KB) — Análise auxiliar 4
├── 04_watson_consolidado.md      (27 KB) — Consolidação de integridade
├── 05_mycroft_decisao_watson.md   (3 KB) — Avaliação com CRITICA
├── 06_sherlock_validacao.md       (3 KB) — Impedimento por insumos
├── 07_mycroft_decisao_sherlock.md (3 KB) — Avaliação da limitação
├── 08_relatorio_final.md          (3 KB) — Impedimento de consolidação
├── _audit.json                    (5 KB) — Metadados máquina
├── _audit_report.md               (2 KB) — Relatório tabular auto-gerado
├── _runtime/llm_calls.jsonl              — Log de todas as chamadas
└── AUDITORIA_BENCH_GPT54.md             — Este documento
```

---

## 8. CHECKLIST DE VERIFICAÇÃO

- [x] Pipeline completo executado (12/12 steps)
- [x] Zero erros na execução
- [x] Todos os CSVs analisados individualmente
- [x] Consolidação Watson com cadeia cross-file
- [x] Mycroft avaliou Watson com rigor (CRITICA emitida)
- [x] Sherlock corretamente identificou falta de insumos
- [x] Mycroft recusou consolidar sem sherlock_consolidado
- [x] Auditoria completa gerada
- [x] Comparativo com execuções anteriores documentado
- [x] Erros catalogados com causa raiz
- [x] Recomendações para próxima iteração

---

*Auditoria gerada em 2026-05-31T18:22Z | DVA-CBS | TC 015.848/2025-6*
*Pipeline de Bancada v1.0 | Projeto Diógenes*
