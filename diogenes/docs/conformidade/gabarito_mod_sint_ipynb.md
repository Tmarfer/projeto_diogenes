# Gabarito — Inconsistências Plantadas no MOD_SINT_IPYNB

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py` a partir de
> `scripts/massa_fontes/MOD_SINT_IPYNB/` (fontes `.py` com separador `# %%`).

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_IPYNB — homologação do parser de notebooks (`nbformat`, só code cells, teto 80k) |
| Arquivos analisáveis | 3 notebooks `.ipynb` (+ protocolo + inventário) |
| Inconsistências plantadas | 3 (INC-NB-01 a INC-NB-03) |
| Verdadeiros negativos | exportações imunes + alimentos alíquota zero |
| Particularidades | O parser descarta outputs e markdown — as pistas estão em código e comentários |

## Inconsistências plantadas

### INC-NB-01 — CBS sobre locação de bem móvel na memória de cálculo (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Arquivo | `memoria_calculo_cbs.ipynb` — célula `cbs_locacao = ... * ALIQUOTA_CBS` |
| Valores | Base R$ 45.000,00 → CBS R$ 4.455,00 (Empresa B, 04/2024) |
| Norma | LC 214/2025, Art. 71 |
| Detecção esperada | Watson lê o cálculo e o comentário "sem ressalva de entendimento divergente"; Sherlock classifica CRÍTICO. |

### INC-NB-02 — Alíquota reduzida saúde sobre receita não segregada (Art. 44)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `memoria_calculo_cbs.ipynb` — célula `cbs_saude = ... * 0.5` |
| Valores | CBS declarada R$ 9.405,00 vs. sem redução R$ 18.810,00 (Beta, 03/2024) |
| Norma | LC 214/2025, Art. 44 — exige profissional habilitado; serviços administrativos hospitalares não se enquadram |
| Detecção esperada | O comentário "sem segregar serviços administrativos hospitalares" é a pista; Sherlock exige comprovação de enquadramento. |

### INC-NB-03 — Crédito de transição truncado por teto operacional (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `creditos_transicao.ipynb` — `min(disponivel, TETO_APROVEITAMENTO)` |
| Valores | Disponível R$ 11.760,00 / aproveitado R$ 5.000,00 / saldo R$ 6.760,00 (Alfa, Jan/2024) |
| Norma | LC 214/2025, Art. 54 §3° II |
| Detecção esperada | Watson identifica o teto sem justificativa documental. |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `conferencia_exportacoes.ipynb` — CBS 0,00 em CFOP 7101 | Imunidade correta | LC 214/2025, Art. 12 §1° |
| `memoria_calculo_cbs.ipynb` — alimentos básicos CBS 0,00 | Alíquota zero, Anexo I | LC 214/2025, Art. 47 |
| `creditos_transicao.ipynb` — energia elétrica integral | Aproveitamento integral documentado | LC 214/2025, Art. 54 |

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
