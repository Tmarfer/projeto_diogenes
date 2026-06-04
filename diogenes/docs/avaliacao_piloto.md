# Avaliação Qualitativa do Piloto — Diógenes

> **Processo:** TC 015.848/2025-6 | DVA-CBS | SecexContas/TCU
> **Documento exigido por:** PRD Bloco 6.3 (Critérios Qualitativos CA-QUA) e 6.5.
> **Natureza:** avaliação humana documentada. Os veredictos abaixo **só são válidos
> quando preenchidos por Lestrade** (auditor humano) sobre execução real de ciclo.
> **Estado em 2026-06-03:** scaffold preparado; veredictos pendentes de execução +
> avaliação humana. As linhas de "Evidência" apontam onde o material será encontrado.

---

## Como preencher

Para cada critério: registrar **data**, **ciclo avaliado** (`cycle_id`), **observações
específicas** (com caminhos de arquivos do `workspace/cycles/{id}/`) e **veredicto**
(POSITIVO / NEGATIVO / PARCIAL). O piloto exige **≥ 6 dos 7** com veredicto positivo
(PRD 6.5).

> **Pré-requisito comum:** restaurar o módulo sintético `MOD_SINT_001` em
> `workspace/input/MOD_SINT_001/` (com o gabarito de inconsistências mantido **fora**
> do alcance dos agentes) e executar ao menos um ciclo A1 + um ciclo A2 com modelos
> da fase ativa (ChatTCU `gpt-5.5-thinking`).

---

## CA-QUA-01 — Detecção de inconsistências (≥ 70%)

- **Ciclo avaliado:** `__________`
- **Evidência:** `output/relatorio_*.md` vs. gabarito de inconsistências do MOD_SINT_001
- **Observações:** _________________________________________________
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO

## CA-QUA-02 — Relatório institucional, impessoal, classificação coerente

- **Ciclo avaliado:** `__________`
- **Evidência:** `output/relatorio_*.md` (pós Motor de Saída) — verificar ausência de marcas internas
- **Observações:** _________________________________________________
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO

## CA-QUA-03 — Stranger's Room como deliberação real

- **Ciclo avaliado:** `__________`
- **Evidência:** `stranger_room/{watson_integridade,sherlock_validacao}/0*_*.md` em sequência
- **Observações:** críticas de Mycroft objetivas e localizadas? respostas fundamentadas? _____
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO

## CA-QUA-04 — Relatório Final (A2) usa o histórico do A1

- **Ciclo avaliado (A2):** `__________` | **Ciclo de origem (A1):** `__________`
- **Evidência:** `_historico/relatorio_anterior.md` + `output/relatorio_final_*.md`;
  conferir classificação de cada inconsistência prévia (Resolvida / Justificada / Em aberto / Nova)
- **Observações:** _________________________________________________
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO
  > Suporte técnico implementado e testado nesta sessão (`test_ciclo_atividade2.py`):
  > o Motor de Start herda o histórico e Mycroft o incorpora. Falta a avaliação humana
  > do **conteúdo** produzido sobre material real.

## CA-QUA-05 — Mycroft em dilemas interpretativos (Art. 10)

- **Ciclo avaliado:** `__________`
- **Evidência:** `99_decisao_final.md` das fases; campo de dilemas no `audit_index.csv`
- **Observações:** _________________________________________________
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO

## CA-QUA-06 — Reconstrução por auditor externo

- **Avaliador (não participou da execução):** `__________`
- **Evidência:** árvore completa de `workspace/cycles/{id}/` (incl. `_runtime/`)
- **Observações:** foi possível reconstruir o "porquê" de cada decisão por leitura direta? _____
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO

## CA-QUA-07 — Utilidade prática sobre material real (Fase D, MOD_010)

- **Ciclo avaliado:** `__________`
- **Evidência:** `output/relatorio_preliminar_MOD_010_*.md`
- **Observações:** _________________________________________________
- **Veredicto:** ☐ POSITIVO ☐ PARCIAL ☐ NEGATIVO
  > Critério sensível (único sobre material real do TCU). Não invalida o piloto se
  > não atendido, mas sinaliza necessidade de mais maturação (PRD 6.5).

---

## Síntese

| Critério | Veredicto | Data |
|---|---|---|
| CA-QUA-01 | ☐ | |
| CA-QUA-02 | ☐ | |
| CA-QUA-03 | ☐ | |
| CA-QUA-04 | ☐ | |
| CA-QUA-05 | ☐ | |
| CA-QUA-06 | ☐ | |
| CA-QUA-07 | ☐ | |

**Positivos:** ____ / 7 (mínimo exigido: 6) — PRD 6.5

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
