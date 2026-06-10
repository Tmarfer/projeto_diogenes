# Conformidade — Stranger's Room (RF-SR)

> PRD Bloco 3.6 (linhas 294-304) vs. `src/diogenes/orchestrator/stranger_room.py`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-SR-01 | Subdiretório por fase em `stranger_room/` | Conforme | `stranger_room/{watson_integridade,sherlock_validacao}/`; constantes `FASE_WATSON`/`FASE_SHERLOCK` | — | — | — |
| RF-SR-02 | Nomes numerados `01_apresentacao` … `99_decisao_final` | Conforme | `stranger_room.py:140` `_path_para`; `test_stranger_room.py` | — | — | — |
| RF-SR-03 | Frontmatter YAML mínimo (cycle_id, phase, author, role, round, timestamp, hash) | Conforme | `stranger_room.py:110` `_escrever` + `:146` `_calcular_hash`; `StrangerRoomFile` em `models.py` | — | — | — |
| RF-SR-04 | Escrita única; sem sobrescrita/edição/remoção | Conforme | `StrangerRoomWriteError` guarda a imutabilidade (Art. 11); invariante CLAUDE.md §4 | — | — | — |
| RF-SR-05 | Leitura sequencial reconstrói a deliberação completa | Conforme | `stranger_room.py:95` `listar_arquivos_fase` + `:99` `validar_fase_completa`; CA-QUA-03 valida qualitativamente | — | — | — |
| RF-SR-06 | Metadados agregados da fase no `audit_index.csv` | Conforme | `audit_index.py:118` `update_watson_metadata`, `:127` `update_sherlock_metadata` | — | — | — |

**Síntese:** 6/6 Conforme. Componente fechado e protegido por invariante — **não tocar nas Ondas 1-3** (qualquer mudança de formato exigiria versionamento novo do protocolo).
