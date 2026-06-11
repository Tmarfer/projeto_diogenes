# Gabarito — Inconsistências Plantadas no MOD_SINT_DOCX

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py`: fontes `.txt` em
> `scripts/massa_fontes/MOD_SINT_DOCX/` → DOCX nativo em `{workspace}/_fontes_originais/MOD_SINT_DOCX/`
> → **`.md` convertido** por `scripts/converter_md.py` (input do módulo).

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_DOCX — homologação da fidelidade da conversão docx→md (fluxo pré-Validação) |
| Arquivos analisáveis | 3 `.md` convertidos de DOCX (+ protocolo + inventário) |
| Inconsistências plantadas | 2 (INC-DOCX-01, INC-DOCX-02) |
| Verdadeiros negativos | `nota_medicamentos.md` + crédito energia integral |

## Inconsistências plantadas

### INC-DOCX-01 — Redução combustíveis com comprovação NCM/ICMS-ST dispensada (Art. 39)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `parecer_reducao_combustiveis.md` (convertido de `.docx`) |
| Valores | CBS com redução R$ 65.288,32 vs. sem redução R$ 116.622,00 (Alfa, 06/2024) |
| Norma | LC 214/2025, Art. 39 |
| Detecção esperada | O parecer declara a dispensa da comprovação de sujeição ao ICMS-ST; Sherlock exige o enquadramento documental do NCM 2710.12.59. |

### INC-DOCX-02 — Aproveitamento parcial de crédito sem justificativa (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `memorando_creditos_transicao.md` (convertido de `.docx`) |
| Valores | Disponível R$ 11.760,00 / aproveitado R$ 5.000,00 / saldo R$ 6.760,00 (Alfa, Jan/2024) |
| Norma | LC 214/2025, Art. 54 §3° II |
| Detecção esperada | Watson quantifica o saldo; o memorando declara a ausência de documento de justificativa. |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `nota_medicamentos.md` — CBS 0,00 NCM 3003.90.89 | Isenção correta, Anvisa confirmado | LC 214/2025, Art. 44 + Anexo VII |
| `memorando_creditos_transicao.md` — energia elétrica | Aproveitamento integral documentado | LC 214/2025, Art. 54 |

## Pontuação

- **MET-04 (detecção, meta ≥70%):** 2 pontos; aprovado = 2/2 detectados com arquivo + quantificação + artigo.
- **MET-05 (falsos positivos, meta <15%):** FP / (FP + TP) × 100.
- **MET-07 (fundamentação, meta ≥1,5):** artigo correto (1) + LC 214/2025 (1) + Acórdão 2833/2025 (bônus 1).
- **Critério extra de fidelidade:** valores plantados íntegros no `.md` convertido (R$ 65.288,32; R$ 116.622,00; R$ 11.760,00; R$ 5.000,00; R$ 6.760,00) — perda na conversão reprova o conversor, não os agentes.

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| — | — | — | — | — | — | — |

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
