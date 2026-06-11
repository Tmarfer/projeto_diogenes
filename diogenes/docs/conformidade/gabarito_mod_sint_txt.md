# Gabarito — Inconsistências Plantadas no MOD_SINT_TXT

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py`: fontes `.txt` em
> `scripts/massa_fontes/MOD_SINT_TXT/` → nativo em `{workspace}/_fontes_originais/MOD_SINT_TXT/`
> → **`.md` convertido** por `scripts/converter_md.py` (input do módulo).

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_TXT — homologação da fidelidade da conversão txt→md (fluxo pré-Validação) |
| Arquivos analisáveis | 3 `.md` convertidos de TXT (+ protocolo + inventário) |
| Inconsistências plantadas | 2 (INC-TXT-01, INC-TXT-02) |
| Verdadeiros negativos | `registro_exportacoes_alfa.md` + crédito energia integral |

## Inconsistências plantadas

### INC-TXT-01 — CBS sobre locação de bem móvel tributada integralmente (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Arquivo | `registro_locacao_beta.md` (convertido de `.txt`) |
| Valores | Base R$ 45.000,00 → CBS R$ 4.455,00 (Beta, 04/2024) |
| Norma | LC 214/2025, Art. 71 |
| Detecção esperada | O registro declara tributação integral "sem ressalva quanto ao entendimento da Receita Federal". |

### INC-TXT-02 — Aproveitamento parcial de crédito sem justificativa (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `registro_creditos_alfa.md` (convertido de `.txt`) |
| Valores | Disponível R$ 11.760,00 / aproveitado R$ 5.000,00 / saldo R$ 6.760,00 (Alfa, Jan/2024) |
| Norma | LC 214/2025, Art. 54 §3° II |
| Detecção esperada | O registro declara o lançamento "sem documento de justificativa". |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `registro_exportacoes_alfa.md` — CBS 0,00 em CFOP 7101 | Imunidade correta | LC 214/2025, Art. 12 §1° |
| `registro_creditos_alfa.md` — energia elétrica | Aproveitamento integral documentado | LC 214/2025, Art. 54 |

## Pontuação

- **MET-04 (detecção, meta ≥70%):** 2 pontos; aprovado = 2/2 detectados com arquivo + quantificação + artigo.
- **MET-05 (falsos positivos, meta <15%):** FP / (FP + TP) × 100.
- **MET-07 (fundamentação, meta ≥1,5):** artigo correto (1) + LC 214/2025 (1) + Acórdão 2833/2025 (bônus 1).
- **Critério extra de fidelidade:** valores plantados íntegros no `.md` convertido (R$ 4.455,00; R$ 11.760,00; R$ 6.760,00).

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| — | — | — | — | — | — | — |

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
