# Conformidade — Motor de Start (RF-MS)

> PRD Bloco 3.1 (linhas 182-198) vs. `src/diogenes/motors/motor_start.py`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped
> Semente: `docs/AUDITORIA_CONFORMIDADE_PRD.md` (2026-06-03)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-MS-01 | Recebe módulo + atividade como parâmetros | Conforme | `motor_start.py:111` `run(module_id, activity)`; CLI `start --module --activity`; `test_motor_start.py` | — | — | — |
| RF-MS-02 | Verifica presença dos inputs por atividade; A2 exige A1 encerrado | Conforme | `motor_start.py:220` `_verificar_inputs`; `:237` `_resolver_ciclo_anterior` | — | — | — |
| RF-MS-03 | SHA-256 por arquivo, registrado no manifesto | Conforme | `motor_start.py:41` `_sha256_file`; `:49` `_sha256_package` | — | — | — |
| RF-MS-04 | Cycle ID `{MOD}_A{ATIV}_{TIMESTAMP_UTC}`, colisão barrada | Conforme | `motor_start.py:75` `_generate_cycle_id` | — | — | — |
| RF-MS-05 | Manifesto Markdown com id, módulo, atividade, timestamps, inputs+hashes, sala de sigilo, ciclo anterior | Conforme | `persistence/manifest.py` `write_manifesto`; A2 grava `previous_cycle_id` (coberto por `test_ciclo_atividade2.py`) | — | — | — |
| RF-MS-06 | Cria `workspace/cycles/{id}/` com estrutura padronizada | Conforme | `persistence/workspace.py` `criar_estrutura_ciclo` (inputs/ stranger_room/ output/) | — | — | — |
| RF-MS-07 | Copia inputs preservando originais; verifica integridade da cópia | Conforme | `motor_start.py` cópia + `CopyIntegrityError`; originais RFB intocados (invariante CLAUDE.md §6) | — | — | — |
| RF-MS-08 | Exibe caminho do manifesto e aguarda confirmação explícita | Conforme | `cli/commands/start.py` exibe caminho; transição só via `confirm-manifest` | — | — | — |
| RF-MS-09 | Registra abertura no `audit_index.csv` com status `PREPARADO` | Conforme | `audit_index.py:33` `add_cycle`; `test_audit_index.py` | — | — | — |

**Síntese:** 9/9 Conforme. Componente estável; nenhuma ação de refatoração necessária.

**Nota:** o Motor de Start ganhou na Fase de Entrega a captura de `git_commit` (`motor_start.py:54`) e versões de pacote (`:67`) no manifesto — atende também RNF-REPR-04/05 (ver `10_rnf.md`).
