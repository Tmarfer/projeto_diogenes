# Gabarito — Inconsistências Plantadas no MOD_SINT_PDF

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py`: fontes `.txt` em
> `scripts/massa_fontes/MOD_SINT_PDF/` → PDF nativo em `{workspace}/_fontes_originais/MOD_SINT_PDF/`
> → **`.md` convertido** por `scripts/converter_md.py` (input do módulo).

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_PDF — homologação da fidelidade da conversão pdf→md (fluxo pré-Validação) |
| Arquivos analisáveis | 3 `.md` convertidos de PDF (+ protocolo + inventário) |
| Inconsistências plantadas | 2 (INC-PDF-01, INC-PDF-02) |
| Verdadeiros negativos | `nota_alimentos_basicos.md` |
| Particularidades | O input que os agentes veem é o `.md` com frontmatter de rastreabilidade (arquivo original, SHA-256). A detecção valida que a inconsistência **sobreviveu à conversão**. |

## Inconsistências plantadas

### INC-PDF-01 — CBS sobre locação de bem móvel tributada integralmente (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Arquivo | `relatorio_apuracao_beta.md` (convertido de `relatorio_apuracao_beta.pdf`) |
| Valores | Base R$ 45.000,00 → CBS R$ 4.455,00 (Beta, 04/2024) |
| Norma | LC 214/2025, Art. 71 |
| Detecção esperada | A seção "OBSERVACOES DA CONTABILIDADE" declara tributação integral sem ressalva do entendimento da RFB. |

### INC-PDF-02 — Alíquota reduzida saúde sem comprovação de habilitação (Art. 44)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `parecer_aliquota_saude.md` (convertido de `parecer_aliquota_saude.pdf`) |
| Valores | CBS declarada R$ 9.405,00 vs. sem redução R$ 18.810,00 (Beta, 03/2024) |
| Norma | LC 214/2025, Art. 44 |
| Detecção esperada | O parecer declara que a comprovação de profissional habilitado foi "considerada desnecessária" e que serviços administrativos hospitalares foram incluídos — dupla violação do enquadramento. |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `nota_alimentos_basicos.md` — CBS 0,00 NCMs do Anexo I | Alíquota zero correta, conferida nota a nota | LC 214/2025, Art. 47 |
| `relatorio_apuracao_beta.md` — serviços administrativos R$ 2.970,00 | Tributação padrão 9,9% correta | — |

## Pontuação

- **MET-04 (detecção, meta ≥70%):** 2 pontos; aprovado = 2/2 detectados com arquivo + quantificação + artigo.
- **MET-05 (falsos positivos, meta <15%):** FP / (FP + TP) × 100.
- **MET-07 (fundamentação, meta ≥1,5):** artigo correto (1) + LC 214/2025 (1) + Acórdão 2833/2025 (bônus 1).
- **Critério extra de fidelidade:** os valores monetários plantados devem aparecer ÍNTEGROS no `.md` convertido (R$ 4.455,00; R$ 9.405,00; R$ 18.810,00) — perda na conversão reprova o conversor, não os agentes.

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| — | — | — | — | — | — | — |

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
