# Irene Adler — Contrato Projetado × Montado × Real

**Tipo:** biblioteca Python (não agente LLM puro — só o estágio C4 chama LLM).
**Invocador:** `src/diogenes/irene.py` (`executar_irene`) + `src/diogenes/irene_chattcu.py` (adaptador C4/ChatTCU).
**Definição:** `docs/agentes/irene/{soul,skills,agent,heartbeat}.md`.
**Baseline real:** ciclo `MOD_010_A1_20260602T202655Z` (`irene_catalog.yaml`, versão 1.3.1).

---

## Pipeline projetado (C1–C5)

| Estágio | Função projetada (soul/skills) | Implementação real (`irene.py`) |
|---------|-------------------------------|---------------------------------|
| C1 Manifesto | valida existência/integridade dos arquivos; para e reporta se faltar | `c1.executar()`; exceção → `IRENE_ERRO_FATAL` |
| C2 Profiling | perfila cada aba (dimensões, fórmulas, vínculos, totalizadores) | `c2.executar(inventario)` |
| C3 Amostragem | fidedignidade CSV↔XLSX, tolerância 1e-6 | `c3.executar(perfis, config)`; **MCP Excel forçadamente desabilitado → fallback openpyxl** |
| C4 Semântica | classifica papel de cada aba via LLM (só metadados, sem dados fiscais) | `c4.executar(...)`; roteado por `patch_c4_para_chattcu` |
| C5 Artefatos | consolida 5 artefatos + recomendação | `c5.executar(...)` |

**Gate (skills.md):** `APROVADO` score≥0.95 · `ALERTA` 0.65–0.95 · `BLOQUEADO` <0.65 **ou falha em aba `resultado_final`**.
**Estados de retorno:** `IRENE_APROVADO|ALERTA|BLOQUEADO|ERRO_FATAL`. Qualquer exceção em C1–C5 → `ERRO_FATAL` (orquestrador → `ABORTADO_FALHA_AGENTE`).

## Artefatos projetados × reais

| Projetado (`agent.md`) | Real (run baseline) |
|------------------------|---------------------|
| `irene_catalog.yaml` (contrato com Watson) | ✅ gerado; copiado p/ `cycles/{id}/irene_catalog.yaml` |
| `irene_confidence.md`, `irene_formulas.md`, `irene_extrato_*.md`, `irene_execution.log` | ✅ caminhos presentes nas métricas de retorno |

## 11 papéis reconhecidos (skills.md)
`resultado_final` · `resultado_intermediario` · `base_bruta` · `base_classificada` · `base_tratada` · `memoria_de_calculo` · `validacao_comparativa` · `tabela_mapeamento` · `matriz_parametrica` · `aba_auxiliar` · `nao_classificado` — **todos observados no run** (exceto `nao_classificado`, que não ocorreu).

## Limites constitucionais aplicáveis
- **Art. 4** — não inicia sozinha; acionada pelo Orquestrador sob instrução de Mycroft (`call_type acionar_irene`).
- **Limite de escopo (soul/skills, verbatim):** "Irene **não** analisa a correção dos valores fiscais — isso é Watson. Irene **não** valida a metodologia CBS — isso é Sherlock. Irene **não** emite opinião sobre a qualidade do cálculo da RFB. Irene **não** acessa dados sigilosos via LLM — apenas metadados estruturais."

## Estrutura do output real (`irene_catalog.yaml`)
Por aba: `papel`, `confianca_papel`, `score_fidedignidade`, `requer_revisao_humana`,
`tem_formulas`, `candidata_totalizador`, `flags_atencao[]`, `colunas_detalhadas[]`
(com `tipo_fisico`, `tipo_semantico`, `confianca_tipo`, nulos, distintos, soma/média).
Cabeçalho: `versao_irene: 1.3.1`, `score_consolidado: 0.9529`, `recomendacao: APROVADO`.
