# Auditoria — Pipeline de Bancada

**Pipeline:** BENCH_PIPELINE_MOD010MCP3_20260531T180253Z
**Módulo:** MOD010MCP3
**Início:** 2026-05-31T18:02:53.051022+00:00
**Fim:** 2026-05-31T18:22:53.288182+00:00
**Duração total:** 1200.2s
**Tokens input:** 123,074
**Tokens output:** 80,251
**Status:** ✅ Completo

## Passos

| # | Passo | Agente | Modelo | Duração | Tokens | Status |
|---|-------|--------|--------|---------|--------|--------|
| 1 | irene_catalog | mycroft | gpt-5.4-thinking | 95.3s | 8851+4938 | ✅ |
| 2 | mycroft_tasks | mycroft | gpt-5.4-thinking | 47.9s | 6180+2882 | ✅ |
| 3 | watson_analise_01 | watson | gpt-5.4-thinking | 166.3s | 10791+11957 | ✅ |
| 4 | watson_analise_02 | watson | gpt-5.4-thinking | 174.9s | 7170+13897 | ✅ |
| 5 | watson_analise_03 | watson | gpt-5.4-thinking | 132.6s | 6192+8639 | ✅ |
| 6 | watson_analise_04 | watson | gpt-5.4-thinking | 143.5s | 6216+9270 | ✅ |
| 7 | watson_analise_05 | watson | gpt-5.4-thinking | 110.8s | 5930+6997 | ✅ |
| 8 | watson_consolidar | watson | gpt-5.4-thinking | 162.3s | 25424+13624 | ✅ |
| 9 | mycroft_avaliar_watson | mycroft | gpt-5.4-thinking | 48.6s | 12208+2275 | ✅ |
| 10 | sherlock_validacao | sherlock | gpt-5.4-thinking | 29.4s | 13956+1215 | ✅ |
| 11 | mycroft_avaliar_sherlock | mycroft | gpt-5.4-thinking | 50.3s | 5355+2705 | ✅ |
| 12 | mycroft_consolidar | mycroft | gpt-5.4-thinking | 38.3s | 14801+1852 | ✅ |

---
*Gerado em 2026-05-31T18:22:53.289239+00:00*