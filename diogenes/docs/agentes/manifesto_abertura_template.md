# Template — Manifesto de Abertura
## Motor de Start | DVA-CBS | Projeto Diógenes

---

*Este template é preenchido pelo Motor de Start e confirmado por Lestrade antes de qualquer acionamento de Mycroft. O campo `prioridades_analise` é o único campo preenchido manualmente por Lestrade — todos os demais são gerados automaticamente pelo Motor de Start a partir do inventário físico do pacote recebido.*

---

```markdown
# Manifesto de Abertura
**Processo:** TC 015.848/2025-6
**Módulo:** [ex.: MOD_008_Simples_Nacional]
**Identificador:** [ex.: MOD_008]
**Atividade:** [ex.: Atividade 1 — Validação de Módulo]
**Ciclo:** [ex.: Ciclo 1]
**Timestamp de abertura:** [ISO 8601, ex.: 2026-05-09T09:14:00-03:00]
**Sala de Sigilo:** [Sim | Não]
**Hash de integridade do pacote:** [SHA-256 do diretório ENTREGA/ completo]

---

## Arquivos Recebidos

| Arquivo | Formato | Tamanho | Hash SHA-256 | Caminho ANALISE/ |
|---------|---------|---------|--------------|-----------------|
| [nome] | [ext] | [bytes] | [hash] | [caminho] |
| ... | ... | ... | ... | ... |

**Total de arquivos:** [n]
**Inventário declarado pela RFB:** [Conforme | Divergente — ver observação]
**Observação:** [se divergente: descrição da divergência entre inventário declarado e recebido]

---

## Prioridades de Análise

*Campo preenchido por Lestrade. Define a ordem de prioridade dos documentos para Watson, do mais para o menos crítico para o resultado do módulo. O Motor de Start gera a lista de arquivos; Lestrade define a ordem e o critério.*

**Critério de priorização:**
[Uma linha descrevendo o raciocínio de Lestrade para esta ordenação.
Ex.: "Script principal de extração e planilha de resultado agregado são o núcleo do cálculo deste módulo; documentação de referência é auxiliar e pode ser processada por último."]

**Ordem de prioridade:**

| Prioridade | Arquivo | Tipo | Justificativa |
|-----------|---------|------|---------------|
| 1 | [nome_arquivo.ext] | [Script SQL / Notebook Python / Planilha / Documentação / Outro] | [uma linha] |
| 2 | [nome_arquivo.ext] | [tipo] | [uma linha] |
| 3 | [nome_arquivo.ext] | [tipo] | [uma linha] |
| ... | ... | ... | ... |

*Arquivos não listados explicitamente são processados por Watson na ordem padrão (documentação → scripts → planilhas) após os priorizados acima.*

**Fallback:** Se este campo estiver vazio ou marcado como `[não preenchido]`, Mycroft aplica a ordem padrão: documentação de referência → scripts SQL → notebooks Python → planilhas de resultado → outros.

---

## Condições Especiais

**Alertas de Lestrade:**
[Observações que Lestrade considera relevantes para o ciclo antes de Mycroft iniciar.
Ex.: "RFB informou que o script principal foi atualizado em relação à versão anterior — atenção especial para diferenças."
Se nenhuma: "Nenhuma condição especial identificada."]

---

## Confirmação de Lestrade

**Status:** [CONFIRMADO | PENDENTE]
**Timestamp de confirmação:** [ISO 8601]
**Lestrade aciona Mycroft:** [Sim — após confirmação acima]
```

---

## Instruções de preenchimento do campo `prioridades_analise`

**Quem preenche:** Lestrade, manualmente, antes de confirmar o manifesto.

**Quando preencher:** Sempre que o pacote contiver mais de cinco arquivos, ou sempre que Lestrade identificar que o módulo tem documentos de importância claramente desigual para o resultado do cálculo.

**Como priorizar:**

A ordem correta é do mais crítico para o menos crítico para o resultado final do módulo — não necessariamente a ordem da cadeia de produção. O critério orientador:

1. O script ou planilha cujo resultado vai diretamente para o cálculo da alíquota de referência deste módulo tem prioridade máxima.
2. Os scripts de extração que alimentam esse resultado têm segunda prioridade.
3. Scripts de transformação intermediária têm terceira prioridade.
4. Documentação de referência e arquivos auxiliares têm prioridade mínima.

Para módulos simples ou com poucos arquivos, o campo pode ser deixado em branco — Mycroft aplica o fallback de ordem padrão, que é adequado para a maioria dos casos.

**O que este campo não faz:**

Não define o que Watson deve concluir. Não orienta Watson sobre conformidade metodológica. Define apenas a ordem em que os arquivos entram no contexto — garantindo que os documentos mais críticos sejam processados quando a atenção do modelo está em seu pico, antes de eventual saturação em módulos muito grandes.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Template de documento de orquestração — uso interno restrito*
