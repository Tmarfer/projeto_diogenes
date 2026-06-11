# Gabarito — Inconsistências Plantadas no MOD_SINT_MD

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py` a partir de
> `scripts/massa_fontes/MOD_SINT_MD/` (arquivos `.md` nativos, copiados direto).

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_MD — homologação do caminho texto puro (teto 60k chars) |
| Arquivos analisáveis | 4 documentos `.md` (+ protocolo + inventário) |
| Inconsistências plantadas | 3 (INC-MD-01 a INC-MD-03) |
| Verdadeiros negativos | `nota_exportacoes.md` + seções 2 e 3 da metodologia + crédito energia |

## Inconsistências plantadas

### INC-MD-01 — Metodologia inclui locação de bem móvel na base sem ressalva (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Arquivo | `metodologia_apuracao.md` — seção 1 "Base de incidência" |
| Valores | Base R$ 45.000,00 → CBS R$ 4.455,00 (Empresa B, 04/2024) |
| Norma | LC 214/2025, Art. 71 |
| Detecção esperada | Sherlock identifica que a metodologia declarada inclui locação de bem móvel na base sem registrar a controvérsia normativa; cita o Art. 71. |

### INC-MD-02 — Nota técnica dispensa comprovação NCM/ICMS-ST para redução combustíveis (Art. 39)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `nota_tecnica_reducoes.md` — "comprovação ... **dispensada pela equipe**" |
| Valores | CBS com redução R$ 65.288,32 vs. sem redução R$ 116.622,00 (Alfa, 06/2024) |
| Norma | LC 214/2025, Art. 39 |
| Detecção esperada | A dispensa explícita de comprovação é a pista direta; Sherlock aponta que o Art. 39 exige sujeição ao ICMS-ST. |

### INC-MD-03 — Aproveitamento parcial de crédito sem justificativa (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `nota_tecnica_creditos.md` — tabela do crédito de transporte |
| Valores | Disponível R$ 11.760,00 / aproveitado R$ 5.000,00 / saldo R$ 6.760,00 (Alfa, Jan/2024) |
| Norma | LC 214/2025, Art. 54 §3° II |
| Detecção esperada | Watson quantifica o saldo; o próprio texto declara a ausência de justificativa. |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `nota_exportacoes.md` — exportações CBS 0,00 | Imunidade correta | LC 214/2025, Art. 12 §1° |
| `metodologia_apuracao.md` seções 2 e 3 | Exportações e alimentos tratados corretamente | Art. 12 §1° e Art. 47 |
| `nota_tecnica_creditos.md` — energia elétrica | Aproveitamento integral documentado | LC 214/2025, Art. 54 |

## Pontuação

- **MET-04 (detecção, meta ≥70%):** 3 pontos; aprovado ≥ 2/3 com arquivo + quantificação + artigo.
- **MET-05 (falsos positivos, meta <15%):** FP / (FP + TP) × 100.
- **MET-07 (fundamentação, meta ≥1,5):** artigo correto (1) + LC 214/2025 (1) + Acórdão 2833/2025 (bônus 1).

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| — | — | — | — | — | — | — |

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
