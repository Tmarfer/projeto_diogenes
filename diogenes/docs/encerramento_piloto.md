# Encerramento do Piloto — Diógenes

> **Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU
> **Documento exigido por:** PRD Bloco 6.5 — gatilho da transição à fase pós-piloto (Bloco 9).
> **Data:** 2026-06-03
> **Status:** **DRAFT — encerramento condicionado.** Os critérios automatizáveis estão
> atendidos e evidenciados; os critérios de **execução real** e **avaliação humana**
> permanecem pendentes. Este documento só vira chancela final quando Lestrade preencher
> as pendências e firmar o veredicto.

---

## 1. Condição de conclusão (PRD 6.5)

O piloto conclui quando, cumulativamente:
- **todos** os CA-FUN-01..10 atendidos;
- **todos** os CA-OPE-01..10 atendidos;
- **≥ 6 dos 7** CA-QUA com avaliação humana positiva (`docs/avaliacao_piloto.md`).

**Veredicto atual:** ❌ ainda não concluído — ver pendências na §4.

---

## 2. Critérios atendidos (com evidência)

Referência detalhada: `docs/AUDITORIA_CONFORMIDADE_PRD.md`.

### Funcionais
- **CA-FUN-02** ✅ Atividade 2 (revalidação) herda `previous_cycle_id` e incorpora o
  histórico do ciclo anterior. Evidência: `motors/motor_start.py` (`_resolver_ciclo_anterior`,
  `_copiar_historico_a1`), `orchestrator.py` (`_carregar_historico_a1`),
  `agents/mycroft.py::consolidar(historico_a1=...)`; testes em
  `tests/integration/test_ciclo_atividade2.py` (2 passando).
- **CA-FUN-04 / 05** ✅ Motor de Saída detecta marcas e não gera falso positivo em termos
  genéricos. Evidência: `motors/motor_saida.py` + testes de unidade.
- **CA-FUN-06** ✅ Retomada após alerta crítico (`proceed`). Evidência: `orchestrator.retomar_apos_alerta`.
- **CA-FUN-07** ✅ Aborto com razão e preservação do diretório. Evidência: `cli/commands/abort.py`.
- **CA-FUN-08** ✅ Falha graciosa com mensagem acionável. Evidência: exceções tipadas em `motors/`/`orchestrator/`.
- **CA-FUN-09** ✅ `status`/`list`/`show` fiéis ao índice.

### Operacionais
- **CA-OPE-01..04, 06** ✅ Índice íntegro (escrita atômica), diretório preservado,
  originais intocados (verificação de hash na cópia), sem sobrescrita (Stranger's Room imutável),
  cronologia coerente. Evidência: `persistence/audit_index.py`, `motors/motor_start.py`.
- **CA-OPE-09** ✅ README com instalação e operação básica.

### Suíte de testes
- **188 testes passando** (1 falha de ambiente: `docling` não instalado neste host —
  dependência opcional do fallback de `.docx`, sem impacto no núcleo).

---

## 3. Implementações desta sessão (2026-06-03)

1. **Atividade 2 completa** (RF-MS-05, RF-MY-08, CA-FUN-02):
   - `motor_start`: resolve o A1 encerrado mais recente, grava `previous_cycle_id`
     no manifesto e no `audit_index`, e copia o histórico (`relatorio_anterior.md`,
     decisões finais de Watson/Sherlock, `PROVENIENCIA.md`) para `cycles/{id}/_historico/`.
   - `orchestrator`: injeta o histórico nas tasks de Watson (confronto obrigatório) e
     emite o evento `REVALIDACAO_HISTORICO_INJETADO`.
   - `mycroft.consolidar`: incorpora o histórico ao Relatório Final, classificando cada
     inconsistência anterior segundo a resposta da RFB.
   - Cobertura: `tests/integration/test_ciclo_atividade2.py`.
2. **Auditoria de conformidade** RF/RNF/CA: `docs/AUDITORIA_CONFORMIDADE_PRD.md`.
3. **Scaffold de avaliação qualitativa:** `docs/avaliacao_piloto.md`.

---

## 4. Pendências para a chancela final (responsável: Lestrade)

| # | Pendência | Critérios | Ação |
|---|---|---|---|
| 1 | Restaurar `MOD_SINT_001` + gabarito de inconsistências no workspace | CA-FUN-01/03, CA-QUA-01..06 | recuperar do repositório de artefatos do piloto |
| 2 | Executar A1 do sintético **3× consecutivas** | CA-FUN-01 | `diogenes autorun --module MOD_SINT_001 --activity 1` |
| 3 | Forçar 2 rodadas da Stranger's Room em ≥1 fase | CA-FUN-03 | módulo com inconsistência controversa |
| 4 | Executar A2 (revalidação) do sintético | CA-QUA-04 | `diogenes start --module MOD_SINT_001 --activity 2` |
| 5 | Executar A1 real sobre **MOD_010** (Fase D) | CA-FUN-10, CA-QUA-07 | `diogenes autorun --module MOD_010 --activity 1` |
| 6 | Preencher os 7 veredictos de `avaliacao_piloto.md` | CA-QUA-01..07 | avaliação humana documentada |
| 7 | Medir cobertura `pytest --cov` ≥ 70% (não-agente) | CA-OPE-10 | `pytest --cov=diogenes` |
| 8 | Validar operação sob OneDrive e em ≥2 ambientes | CA-OPE-07/08 | execução ambiental |

### Lacunas de implementação (opcionais para o piloto, ver auditoria §4)
- **RNF-REPR-03** — subcomando de re-execução de ciclo concluído (não implementado).
- **RNF-CUST-01 / CA-OPE-05** — agregação de custo/tokens por ciclo no índice
  (campo existe, fica `0.00`; ChatTCU = custo institucional zero).

---

## 5. Veredicto final

☐ **PILOTO CONCLUÍDO** — todos os CA-FUN/CA-OPE atendidos e ≥6/7 CA-QUA positivos.

☑ **PILOTO EM ENCERRAMENTO CONDICIONADO** — núcleo implementado e auditado;
execução real e avaliação humana pendentes (§4).

**Chancela de Lestrade:** `__________________________`  **Data:** `____________`

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
