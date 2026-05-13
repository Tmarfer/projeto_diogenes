# Regras de Negócio Aplicáveis — MOD_SINT_001
## DVA-CBS | TC 015.848/2025-6 | Serviços de TI

Este documento consolida as regras de negócio que Watson deve verificar na análise de integridade
e que Sherlock deve confrontar com a metodologia homologada.

---

## RN-01: Escopo de Contribuintes

**Regra:** Apenas contribuintes com EFD-Contribuições do exercício 2025 entregue (ind_mov = 1)
e com receita bruta positiva (vl_rec_brt > 0) devem compor a base.

**Base legal:** LC 214/2025, Art. 7º, §1º; IN RFB nº 2.119/2022, Art. 3º.

**Verificação obrigatória:** O script SQL deve conter filtro `AND e.ind_mov = 1 AND e.vl_rec_brt > 0`.

---

## RN-02: CNAEs Cobertos

**Regra:** O módulo cobre exclusivamente os CNAEs 6201-5/00, 6202-3/00, 6203-1/00 e 6209-1/00.

**Base legal:** Portaria COSIT nº 45/2025, Anexo I, Tabela 3 (Serviços de TI).

**Verificação obrigatória:** Todos os CNAEs listados no script devem ser exatamente os quatro acima.
Nenhum outro CNAE deve ser incluído sem justificativa formal.

---

## RN-03: Fórmula da Alíquota de Referência

**Regra:** `Alíquota_Ref = (Σ CBS_Apurada / Σ BC_Total) × 100`

A alíquota deve ser calculada como **razão das somas** (não média das alíquotas individuais).

**Base legal:** Nota Técnica COSIT nº 08/2025, Seção 4.2.

**Verificação obrigatória:** O cálculo deve usar `SUM(cbs_total_anual) / SUM(bc_total_anual)`,
não `AVG(aliquota_efetiva_anual)`.

---

## RN-04: Exclusão do Simples Nacional

**Regra:** Contribuintes do Simples Nacional **não** devem integrar a base.
A filtragem é implícita pelo uso exclusivo do EFD-Contribuições (que não é entregue por optantes
do Simples Nacional).

**Base legal:** LC 123/2006, Art. 13, §1º, XIII; LC 214/2025, Art. 120.

---

## RN-05: Critério de Outlier

**Regra:** O critério de exclusão de outliers é `|z_score| > 3` onde
`z_score = (aliquota_empresa - media) / desvio_padrao`.

**Base legal:** Nota Técnica COSIT nº 08/2025, Seção 4.4 (padronização metodológica).

**Verificação obrigatória:** A contagem de outliers declarada (147) deve ser reproduzível
pelo script SQL e notebook com os mesmos parâmetros.

---

## RN-06: Câmbio para Receita em Moeda Estrangeira

**Regra:** Receitas em moeda estrangeira são convertidas pela **PTAX de venda do último dia útil
do mês de competência** (Banco Central do Brasil).

**Base legal:** IN RFB nº 2.119/2022, Art. 7º, §3º.

**Limitação declarada:** A metodologia utiliza PTAX fim de mês (não média mensal),
conforme registrado na Ata de Reunião de Entrega (Limitação L4).

---

## RN-07: Estratificação por Porte

**Regra:** O porte é definido conforme critério do Simples Nacional, mesmo para empresas
não optantes:
- ME: faturamento anual ≤ R$ 360.000
- EPP: R$ 360.000 < faturamento ≤ R$ 4.800.000
- Outros: faturamento > R$ 4.800.000

**Base legal:** LC 123/2006, Art. 3º (aplicação analógica para fins de estratificação).

---

*Documento de regras de negócio elaborado pelo GT Reforma Tributária para fins de piloto*  
*TC 015.848/2025-6 | Uso interno restrito*
