# Briefing do Módulo MOD_SINT_001
## GT Reforma Tributária | DVA-CBS | TC 015.848/2025-6

**Módulo:** MOD_SINT_001 — Apuração da Alíquota de Referência CBS / Serviços de TI  
**Prioridade:** Alta (setor com maior volume de contribuintes na faixa EPP)  
**Prazo do GT:** 2026-05-15  

---

## O que este módulo analisa

O setor de **Tecnologia da Informação** representa o segundo maior segmento em número de contribuintes
da CBS (após o comércio varejista) e o quinto em arrecadação potencial. A alíquota de referência
calculada neste módulo (8,77%) será utilizada como:

1. **Referência de comparação** para auditoria dos recolhimentos mensais dos contribuintes
2. **Parâmetro de calibração** do sistema de seleção de fiscalização da CBS
3. **Insumo para o relatório consolidado** de alíquotas de referência por setor (TC 015.848/2025-6)

---

## Pontos de atenção para a equipe DVA-CBS

### Integridade (Watson)

- Verificar se a **cadeia de produção de dados** está completamente documentada:
  EFD → SQL → notebook → planilha (deve ser rastreável sem lacunas)
- Verificar se a **fórmula da alíquota** usa razão das somas (não média das alíquotas):
  vide RN-03 do documento de regras de negócio
- Verificar **consistência numérica**: soma das partes na aba `Por_Porte` deve bater com totais
  da aba `Resultado_Final`
- Verificar se a **contagem de empresas após exclusão de outliers** (88.487) é reproduzível
  pelo script SQL e notebook

### Metodologia (Sherlock)

- Verificar conformidade com **LC 214/2025, Art. 7º** (base de cálculo da CBS)
- Verificar se a **exclusão do Simples Nacional** está corretamente fundamentada (RN-04)
- Verificar se o critério de **outlier (±3σ)** está documentado e alinhado com NT COSIT nº 08/2025
- Verificar se a **limitação do câmbio** (PTAX fim de mês vs. média mensal) foi adequadamente
  declarada e seu impacto estimado

### Questão aberta para Lestrade

A nota técnica NT COSIT nº 12/2026 (que fundamenta a exclusão dos 147 outliers) não foi
entregue junto com os artefatos — foi prometida para 2026-04-22 conforme Ata de Reunião.
Se não recebida até o início da validação, Watson deve registrar como **alerta de integridade
documental** e Sherlock deve classificar como **ponto de verificação pendente**.

---

*Briefing elaborado pelo GT Reforma Tributária | TC 015.848/2025-6 | Uso interno restrito*
