# Conformidade — Persistência (RF-PE)

> PRD Bloco 3.8 (linhas 326-352) vs. `src/diogenes/persistence/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-PE-01 | Workspace configurável via `DIOGENES_WORKSPACE` | Conforme | `config.py` (único ponto de leitura); `persistence/workspace.py` | — | — | — |
| RF-PE-02 | Estrutura interna especificada (input/, cycles/{id}/…, audit_index.csv) | Conforme | `workspace.py` cria a estrutura; `diogenes init` | — | — | — |
| RF-PE-03 | `audit_index.csv` índice único e cronológico com colunas mínimas | Evoluído | Schema **superset** (31+ colunas, `AUDIT_INDEX_COLUMNS`): campos do PRD + tokens/custo/Irene/entrega (`audit_index.py:142` `update_entrega`) | — | — | — |
| RF-PE-04 | Append-only para inserção; atômico para atualização | Conforme | `audit_index.py:159` `_write_atomic` (mkstemp + replace); `test_audit_index.py` cobre idempotência | — | — | — |
| RF-PE-05 | Compatível com sync OneDrive/Drive/Dropbox | Conforme | Sem lock files; `pathlib`; nomes sem caracteres problemáticos | CA-OPE-07 (operação sob OneDrive ativo) ainda não verificado em ambiente real | P3 | — |
| RF-PE-06 | Diretório de ciclo encerrado preservado integralmente | Conforme | Sem rotina de limpeza/compactação no código | — | — | — |

**Síntese:** 5 Conforme, 1 Evoluído (superset benigno). Componente estável.
