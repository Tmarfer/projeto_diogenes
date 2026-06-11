# Gabarito — Inconsistências Plantadas no MOD_SINT_001

> **Uso restrito — fora do alcance dos agentes.**  
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.  
> Criado em 2026-06-09 a partir de auditoria completa de `scratch/gerar_massa_teste.py`.

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_001 |
| Empresas | Siderúrgica Alfa Ltda (CNPJ 12.345.678/0001-90) e Alimentar Beta S.A. (CNPJ 98.765.432/0001-10) |
| Período | Jan–Jun/2025 |
| Arquivos no pacote | 28 (26 analísáveis + inventário + protocolo de recebimento) |
| Inconsistências primárias plantadas | 4 (INC-01 a INC-04) |
| Inconsistências latentes | 2 (INC-05, INC-06 — presentes nos dados, sem sinalização explícita) |
| Ocorrências correctas (não devem ser marcadas) | 6 (ver seção "Verdadeiros negativos") |

---

## Inconsistências primárias (INC-01 a INC-04)

Estes 4 itens estão explicitamente sinalizados na tabela `divergencias_identificadas.xlsx`
e em `Planilha_Verificacao_MOD_SINT_001.xlsx`. São a **base de pontuação de MET-04 e MET-05**.

---

### INC-01 — CBS sobre locação de bem móvel questionada pela RFB (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Empresa | Alimentar Beta S.A. — CNPJ 98.765.432/0001-10 |
| Competência | 04/2025 |
| Valor declarado (CBS) | R$ 4.455,00 (9,9% × R$ 45.000,00) |
| Valor esperado RFB | R$ 0,00 — RFB não reconhece CBS sobre locação de bem móvel |
| Diferença | R$ 4.455,00 (contribuinte tributou o que a RFB nega) |
| Norma violada | LC 214/2025, Art. 71 — incidência CBS sobre locação (interpretação controversa) |
| Referência no corpus | `divergencias_identificadas.xlsx` linha 4 (DIV-04); `Planilha_Verificacao_MOD_SINT_001.xlsx` V-05 (CRÍTICO); `notas_fiscais_amostra.txt` NF-e 000004; `receita_bruta_empresa_B.xlsx` competência 04/2025; `memoria_calculo_CBS.xlsx` Empresa B 04/2025 |
| Agente primário | Sherlock (classificação normativa) |
| Agente secundário | Watson (verificação numérica: CBS declarada ≠ CBS esperada segundo RFB) |

**O que o agente deve fazer:**
- Watson: detectar que `divergencias_identificadas.xlsx` coluna "Valor RFB (R$)" = 0,00 para esta linha enquanto "Valor Declarado (R$)" = 4.455,00; confirmar o montante nas NF-e.
- Sherlock: classificar como CRÍTICO e citar `LC 214/2025, Art. 71`; referenciar a Solução de Consulta COSIT pendente como elemento de incerteza normativa.

---

### INC-02 — Redução setorial combustíveis sem comprovação de enquadramento NCM/ICMS-ST (Art. 39)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** (pode ser elevada a CRÍTICO se ausência documental for confirmada) |
| Empresa | Siderúrgica Alfa Ltda — CNPJ 12.345.678/0001-90 |
| Competência | 06/2025 |
| CBS declarada (com redução) | R$ 65.288,32 (alíquota efetiva 5,544% = 9,9% × 0,56) |
| CBS calculada pela RFB (sem redução) | R$ 116.622,00 (alíquota 9,9%) |
| Diferença | R$ 51.333,68 — 44,0% de divergência |
| Norma aplicada pelo contribuinte | LC 214/2025, Art. 39 — redução setorial combustíveis derivados de petróleo (fator 44%) |
| Risco de não-enquadramento | NCM 2710.12.59 precisa estar sujeito a ICMS-ST para que o Art. 39 se aplique; o pacote não contém comprovação |
| Referência no corpus | `divergencias_identificadas.xlsx` linha 1 (DIV-01, risco ALTO); `Planilha_Verificacao_MOD_SINT_001.xlsx` V-02 (ALTO); `reducoes_setoriais.xlsx` linha 1; `receita_bruta_empresa_A.xlsx` competência 06/2025; `memoria_calculo_CBS.xlsx` Empresa A 06/2025 |
| Agente primário | Sherlock (verificar enquadramento NCM × ICMS-ST e validade do fator 44%) |
| Agente secundário | Watson (verificar inconsistência entre alíquota efetiva 5,544% em `reducoes_setoriais` e alíquota 9,9% implícita na tabela de referência para GERAL) |

**O que o agente deve fazer:**
- Watson: identificar que `reducoes_setoriais.xlsx` mostra CBS com redução = R$ 65.288,32, mas `divergencias_identificadas.xlsx` aponta CBS RFB = R$ 116.622,00; quantificar diferença.
- Sherlock: citar `LC 214/2025, Art. 39`; exigir comprovação de sujeição ao ICMS-ST para NCM 2710.12.59; apontar ausência de documentação no pacote como elemento de risco.

---

### INC-03 — Alíquota reduzida serviços de saúde sem comprovação de enquadramento (Art. 44)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Empresa | Alimentar Beta S.A. — CNPJ 98.765.432/0001-10 |
| Competência | 03/2025 |
| CBS declarada (com redução 50%) | R$ 9.405,00 (alíquota efetiva 4,95%) |
| CBS calculada pela RFB (sem redução) | R$ 18.810,00 (alíquota 9,9%) |
| Diferença | R$ 9.405,00 — 50,0% de divergência |
| Norma aplicada pelo contribuinte | LC 214/2025, Art. 44 — alíquota reduzida para serviços de saúde humana (fator 0,5) |
| Risco de não-enquadramento | Art. 44 exige prestação por profissional habilitado por conselho de classe; serviços administrativos hospitalares NÃO se enquadram; o pacote não documenta a natureza exata do serviço prestado |
| Referência no corpus | `divergencias_identificadas.xlsx` linha 2 (DIV-02, risco ALTO); `Planilha_Verificacao_MOD_SINT_001.xlsx` V-07 (ALTO); `reducoes_setoriais.xlsx` linha 2; `nfe_emitidas_empresa_B.xlsx` linha 3 (alíquota 4,95%); `receita_bruta_empresa_B.xlsx` competência 03/2025; `Metodologia_CBS_PF.md` seção 5.3 |
| Agente primário | Sherlock (verificar condição de enquadramento Art. 44) |
| Agente secundário | Watson (verificar que a alíquota 4,95% aplicada na NF-e diverge da alíquota padrão de 9,9%; confirmar com `reducoes_setoriais`) |

**O que o agente deve fazer:**
- Watson: identificar alíquota 4,95% na NF-e Empresa B mar/2025; contrastar com alíquota padrão 9,9%; quantificar a diferença.
- Sherlock: citar `LC 214/2025, Art. 44`; apontar que a alíquota reduzida exige prestação por profissional de saúde habilitado e que o pacote não comprova esse enquadramento.

---

### INC-04 — Crédito de transporte aproveitado parcialmente sem justificativa (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Empresa | Siderúrgica Alfa Ltda — CNPJ 12.345.678/0001-90 |
| Período | Jan/2025 |
| Crédito disponível | R$ 11.760,00 (PIS R$ 2.100,00 + COFINS R$ 9.660,00) |
| Crédito aproveitado | R$ 5.000,00 (42,5% do disponível) |
| Saldo não aproveitado | R$ 6.760,00 — sem justificativa no pacote |
| Norma | LC 214/2025, Art. 54 §3° II — crédito de transporte de insumos na transição |
| Referência no corpus | `creditos_pis_cofins.xlsx` linha 3; `divergencias_identificadas.xlsx` linha 3 (DIV-03, risco MÉDIO) |
| Agente primário | Watson (integridade técnica: saldo creditório não aproveitado) |
| Agente secundário | Sherlock (questionar ausência de documentação justificando o aproveitamento parcial) |

**O que o agente deve fazer:**
- Watson: identificar que `creditos_pis_cofins.xlsx` mostra Aproveitado = R$ 5.000,00 para crédito com Total = R$ 11.760,00; calcular Saldo = R$ 6.760,00; sinalizar ausência de justificativa.
- Sherlock: citar `LC 214/2025, Art. 54 §3° II`; questionar se o aproveitamento parcial decorre de limitação de caixa, estratégia fiscal ou erro; recomendar documentação.

---

## Inconsistências latentes (INC-05 e INC-06)

Estes itens estão presentes nos dados mas **sem sinalização explícita** no corpus. Sua detecção demonstra profundidade analítica acima do mínimo esperado. Não penalizam MET-05 (falsos positivos) se detectados, pois têm fundamento real nos dados.

### INC-05 — Reclassificação de frete de exportação como tributável (questionável)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | Baixo a ATENÇÃO (questionamento metodológico) |
| Empresa | Siderúrgica Alfa Ltda |
| Referência | `base_calculo_ajustada.xlsx` linha 2: Nota Débito NF-e 000003, R$ 18.000,00, CBS R$ 1.782,00 |
| Questão | A NF-e 000003 é exportação imune (CFOP 7101); o frete internacional reclassificado deveria também ser imune (LC 214/2025, Art. 12 §1°) |
| Detecção esperada | Watson ou Sherlock podem questionar; não consta na tabela de divergências |

### INC-06 — Crédito de arrendamento de máquinas aproveitado parcialmente (Art. 54 §4°)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | Baixo |
| Empresa | Alimentar Beta S.A. |
| Referência | `creditos_pis_cofins.xlsx` linha 5: Disponível R$ 5.040,00 / Aproveitado R$ 2.500,00 / Saldo R$ 2.540,00 |
| Questão | 49,6% do crédito não aproveitado sem justificativa — similar ao INC-04 |
| Detecção esperada | Pode ser detectada por Watson; bônus analítico |

---

## Verdadeiros negativos (não devem ser marcados como inconsistência)

Os itens abaixo são **corretos** e sua marcação como inconsistência conta como falso positivo (impacta MET-05).

| Item | Empresa | Justificativa | Norma |
|------|---------|---------------|-------|
| Exportações com CBS = R$ 0,00 | Alfa (03/2025) | Imunidade constitucional correta | LC 214/2025, Art. 12 §1° |
| Alimentos básicos com CBS = R$ 0,00 | Beta (01, 04, 06/2025) | Alíquota zero — lista Anexo I (NCMs 1006.30.21, 0702.00.00, 0401.10.10) | LC 214/2025, Art. 47 |
| Medicamentos com CBS = R$ 0,00 | Beta (02/2025) | Isenção — Anexo VII (NCM 3003.90.89, Anvisa confirmado) | LC 214/2025, Art. 44 + Anexo VII |
| Créditos PIS/COFINS totalmente aproveitados (Alfa dez/2024) | Alfa | Aproveitamento integral documentado | LC 214/2025, Art. 54 §2° e §3° I |
| Créditos PIS/COFINS totalmente aproveitados (Beta dez/2024) | Beta | Aproveitamento integral documentado | LC 214/2025, Art. 54 §5° |
| Nota Crédito NF-e 000001 (devolução) | Alfa | Redução legítima de base por devolução parcial | Prática contábil padrão |

---

## Tabela de pontuação para MET-04 e MET-05

### MET-04 — Taxa de detecção (meta: ≥70%)

Pontuação máxima: 4 pontos (INC-01 a INC-04). Aprovado ≥70% = ≥ 3 de 4 detecções corretas.

| ID | Descrição curta | Pontos | Watson detectou? | Sherlock classificou? |
|----|-----------------|--------|------------------|-----------------------|
| INC-01 | CBS locação bem móvel Beta (CRÍTICO) | 1 | ☐ | ☐ |
| INC-02 | Redução combustível sem comprovação (ATENÇÃO) | 1 | ☐ | ☐ |
| INC-03 | Alíquota reduzida saúde sem enquadramento (ATENÇÃO) | 1 | ☐ | ☐ |
| INC-04 | Crédito transporte parcial sem justificativa (ATENÇÃO) | 1 | ☐ | ☐ |
| **Total** | | **4** | | |

**Como pontuar:** marcar ☑ se o agente (Watson ou Sherlock) mencionou a inconsistência com:
- Identificação do arquivo e competência/linha corretos
- Quantificação do valor em divergência
- Para INC-01, INC-02, INC-03: alguma referência à LC 214/2025 ou ao artigo relevante

**MET-04 =** (total de ☑ em "Watson detectou?" + "Sherlock classificou?") / 8 × 100%  
Ou, simplificado: nº de INC detectados (qualquer agente) / 4 × 100%.

### MET-05 — Taxa de falsos positivos (meta: <15%)

Contar alertas emitidos pelos agentes que **não** correspondem a nenhum dos 6 INC acima.
Calcular: FP / (FP + TP) × 100. Aprovado < 15%.

### MET-06 — Qualidade da classificação semântica

Avaliação humana (Lestrade) sobre cada INC detectado:

| Critério | Excelente | Adequado | Insuficiente |
|----------|-----------|----------|--------------|
| Severidade correta | Exatamente CRÍTICO/ATENÇÃO como aqui | 1 nível de diferença | > 1 nível |
| Arquivo/célula corretos | Arquivo e competência corretos | Apenas arquivo | Nem arquivo |
| Quantificação | Valor em R$ correto | Estimativa dentro de 10% | Sem valor |

### MET-07 — Qualidade da fundamentação normativa (meta-alvo da Onda 2)

Para cada INC detectado que foi **também classificado com fundamentação normativa**, verificar:

| Critério | Pontos |
|----------|--------|
| Cita o artigo correto da LC 214/2025 | 1 |
| Menciona o número da lei (LC 214/2025) | 1 |
| Menciona Acórdão 2833/2025-Plenário ou TC 015.848/2025-6 | 1 (bônus) |

MET-07 = média de pontos por INC detectado (máx. 2, bônus 3).
**Linha de base** (antes da Onda 2): registrar o MET-07 do próximo ciclo A1.
**Meta da Onda 2:** MET-07 ≥ 1,5 pontos médios em cada INC detectado.

---

## Notas para o avaliador

1. **INC-01 é o mais importante**: é o único CRÍTICO, envolve uma controvérsia normativa real e exige
   que Sherlock classifique corretamente com base no Art. 71. Falhar este item é o principal sinal de
   necessidade de calibração do Sherlock.

2. **INC-02 e INC-03 testam enquadramento de regimes especiais**: a chave é que o agente exija
   comprovação, não apenas aceite o regime declarado. Se Sherlock apenas diz "redução aplicada corretamente"
   sem questionar a ausência de documentação, é sinal de prompt insuficiente.

3. **INC-04 é o teste de integridade técnica do Watson**: o saldo creditório não utilizado está
   explicitamente na tabela — Watson deve detectar sem apoio de Sherlock.

4. **Os verdadeiros negativos são essenciais para MET-05**: exportações zeradas e alíquotas zero
   para alimentos/medicamentos são corretos. Agentes bem calibrados NÃO devem flagá-los.

5. **Atenção ao INC-01 na direção da divergência**: diferente de INC-02/03 (onde o contribuinte
   pagou menos que o RFB espera), no INC-01 o contribuinte pagou CBS mas a RFB não reconhece a
   obrigação — o risco é de pagamento indevido ou interpretação equivocada, não de sonegação.

---

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| MOD_SINT_001_A1_20260610T095227Z | 2026-06-10 | gpt-5.5-thinking (Onda 2/3, commit 4df6b9e) | **área 4/4 (100%)** · quantificação 2/4 (50%) | **~60% FP (reprova <15%)** | **~2,1 (aprova ≥1,5)** | Baseline. Ver análise abaixo. |
| MOD_SINT_001_A1_20260610T133554Z | 2026-06-10 | gpt-5.5-thinking (Onda 4, commit 17691ef) | — | — | — | **INVÁLIDO p/ Sherlock:** 4 timeouts (600s) → fallback determinístico, 1 ocorrência global NV. Watson OK (V-05/V-07 quantificados). Motivou timeout 1500s. |
| MOD_SINT_001_A1_20260610T164820Z | 2026-06-10 | gpt-5.5-thinking (Onda 4 + timeout 1500s) | área 4/4 (100%) · quantificação 2/4 (50%) | ~60% FP (reprova) | ~2,0 (aprova) | Sherlock via LLM, sem fallback. Ver análise abaixo. |

### Análise do ciclo pós-Onda 4 (20260610T164820Z)

**Sherlock rodou inteiro via LLM** (2 chamadas, 231s/212s — o timeout 1500s resolveu) e emitiu
10 ocorrências, todas fundamentadas. Motor de Saída: **documento LIMPO** (142 marcas → 0 — a
correção 1 da Onda 4 funcionou). Ciclo em ~80 min (vs ~137 min).

| INC | Evidência no ciclo | Veredito |
|-----|--------------------|----------|
| INC-01 (locação Art. 71) | Watson W001-005: V-05 "esperado R$ 4.455,00 e encontrado R$ 0,00" ✅; Sherlock S010 cita Art. 71 mas agrega locação+combustíveis+saúde em 1 ocorrência NV/Médio | Detectado e quantificado; **subclassificado** (sem CRÍTICO individual) |
| INC-02 (combustível Art. 39) | S004 cita arts. 39/44/47/48 **e** "V-02 referencia R$ 65.288,32" | **Melhor vinculação número↔norma do ciclo** (ganho da Onda 4 Passo 5b); severidade CRÍTICO (+1 nível vs gabarito) |
| INC-03 (saúde Art. 44) | Watson V-07 "encontrado em dobro do esperado" ✅; S010 exige "habilitação profissional" e "segregação de serviços administrativos de hospitais" (condição exata do gabarito) | Área+norma corretas; valores R$ 9.405/18.810 não sobrevivem ao relatório |
| INC-04 (crédito Art. 54) | S005-AP "Créditos sem chave operacional formal — LC 214/2025, Art. 54" | Área+norma; sem os valores R$ 11.760/5.000/6.760 |

**MET-05 (~60%, reprova) — composição do FP:** S001 (anos-base 2025 vs 2023/2024 — **artefato
do corpus sintético**, ver nota abaixo), S009 (consequência de falha técnica — ver nota), S002/S003/
S006/S008 genéricas de rastreabilidade. **Nenhum verdadeiro negativo foi flagado** (exportações
imunes e alíquota zero não viraram ocorrência — ganho da Onda 4 Passo 5c/8f).

**Notas de contexto (não são erro de calibração):**
1. **S001 (anos-base):** a massa sintética é datada Jan–Jun/2025 enquanto a metodologia fixa
   anos-base 2023/2024. Tecnicamente o Sherlock está certo. Opções: re-datar a massa para
   2023/2024 ou aceitar S001 como ocorrência esperada do módulo (não pontuar como FP).
2. **S009 (arquivo não analisado):** o ChatTCU devolveu 2xx com resposta vazia na análise de
   `receita_bruta_empresa_A.xlsx` (0 tokens, 82,7s); o ciclo degradou graciosamente, mas perdeu
   1/28 análises. Corrigido em `llm/chattcu.py` (resposta vazia agora faz retry).

**Pendência de calibração (próxima onda de prompt):** a quantificação plantada ainda se perde
entre Watson e o relatório final (2/4), e o Sherlock agrega os 3 pontos controvertidos numa
única ocorrência NV em vez de classificá-los individualmente (INC-01 deveria ser CRÍTICO próprio).

### Análise do baseline 2026-06-10

**MET-04 — detecção (meta ≥70%):** as 4 áreas/artigos foram tocadas (Art. 71, 39, 44, 54) — **o corpus jurídico funcionou**. Mas só 2 de 4 tiveram o valor plantado quantificado:

| INC | Área detectada | Valor quantificado | Severidade | Veredito |
|-----|----------------|--------------------|-----------|----------|
| INC-01 (locação Art. 71) | ✅ S006 + V-05 (Watson achou R$ 4.455 vs R$ 0) | ✅ via Planilha Verificação | ❌ ALERTA (gabarito: CRÍTICO) | Detectado, **subclassificado e não vinculado** |
| INC-02 (combustível Art. 39) | ✅ S007 CRÍTICO | ❌ R$ 65.288/116.622 ausentes | ⬆ CRÍTICO (gabarito: ATENÇÃO) | Área certa, **sem números** |
| INC-03 (saúde Art. 44) | ✅ S008 + V-07 (Watson achou R$ 9.405 vs R$ 18.810) | ✅ via Planilha Verificação | ✅ ALERTA≈ATENÇÃO | **Melhor detecção** |
| INC-04 (crédito Art. 54) | ✅ S005 CRÍTICO genérico | ❌ R$ 5.000/11.760/6.760 ausentes | ⬆ CRÍTICO | Área certa, **sem números** |

**MET-05 — falsos positivos (meta <15%):** 15 ocorrências Sherlock; ~9 são genéricas ("sem parametrização rastreável", "cadeia não reprodutível", "CBS líquida inconsistente"). S003 marca exportações zeradas como problema — mas elas são **verdadeiro negativo** (imunidade Art. 12 §1° correta). FP ≈ 60% → reprova.

**MET-07 — fundamentação (meta ≥1,5):** **toda** ocorrência tem `fundamento_violado` com LC 214/2025 + artigo; várias citam Acórdão 2833/2025. Média ≈ 2,1 → aprova. **Este é o ganho da Onda 2.**

**Achado central (causa-raiz da qualidade):** Watson e Sherlock produzem **dois fluxos paralelos não vinculados** — Watson acha os números (via Planilha de Verificação: "esperado X, encontrado Y") mas sem o sentido de negócio; Sherlock acha a norma (via corpus: "locação Art. 71") mas sem os números de Watson. Eles deveriam **convergir**: "o R$ 4.455 de CBS sobre locação (V-05) viola interpretação do Art. 71 — CRÍTICO". Em vez disso ficam separados, e a quantificação se perde no relatório final (nenhum dos valores plantados sobrevive em `relatorio_preliminar`).

**Impessoalidade (MET-09):** 142 marcas internas (vs 31/33 nos ciclos pré-Onda 2) — a maioria são citações a `` `watson_consolidado.md` `` / `` `sherlock_consolidado.md` `` em crase no corpo do relatório. As narrativas mais ricas da Onda 2 fizeram os agentes citarem os arquivos de trabalho internos com mais frequência.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*  
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
