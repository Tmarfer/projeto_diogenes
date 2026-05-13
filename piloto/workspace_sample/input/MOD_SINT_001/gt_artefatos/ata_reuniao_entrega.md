# Ata de Reunião de Entrega — MOD_SINT_001
## GT Reforma Tributária / DVA-CBS | TC 015.848/2025-6

**Data:** 2026-04-15  
**Hora:** 14h00 – 16h30 (BRT)  
**Local:** Sala de Reuniões Virtual — Microsoft Teams  
**Modalidade:** Videoconferência  

---

## Participantes

| Nome | Cargo | Órgão | Papel |
|------|-------|-------|-------|
| Rodrigo Ferreira Lima | Auditor Fiscal | RFB/COSIT | Entregador (RFB) |
| Ana Paula Guimarães | Analista Tributária | RFB/COFIS | Apoio técnico |
| Carlos Eduardo Mota | Auditor Federal | TCU/SecexContas | Receptor (GT) |
| Fernanda Alves Costa | Técnica de Controle | TCU/SecexContas | Receptor (GT) |
| [Sistema Diógenes] | Agente Automatizado | TCU/DVA-CBS | Observador passivo |

---

## Pauta

1. Entrega formal dos artefatos do Módulo MOD_SINT_001
2. Esclarecimentos metodológicos
3. Confirmação do escopo e limitações declaradas
4. Próximos passos

---

## 1. Entrega Formal dos Artefatos

O Sr. Rodrigo Lima apresentou os quatro artefatos que compõem a entrega:

- `descricao_metodologica.md` — documentação completa da metodologia, incluindo fontes, cadeia de produção, fórmulas e verificações internas
- `planilha_cbs.xlsx` — consolidação final com três abas: `Dados_Brutos`, `Por_Porte` e `Resultado_Final`
- `script_extracao.sql` — script ETL utilizado na extração e filtragem inicial dos dados do EFD-Contribuições
- `notebook_transform.ipynb` — código Python para transformação, cruzamento e validação dos dados

O Sr. Carlos Mota confirmou o recebimento de todos os artefatos e registrou o hash SHA-256 do pacote no sistema de controle do GT.

---

## 2. Esclarecimentos Metodológicos

**Pergunta (GT — Fernanda Costa):** A alíquota calculada de 8,77% inclui ou exclui os contribuintes do Simples Nacional?

**Resposta (RFB — Rodrigo Lima):** **Exclui.** Os optantes pelo Simples Nacional recolhem CBS por regime diferenciado (alíquota unificada do Simples) e não possuem EFD-Contribuições. A base analisada cobre exclusivamente contribuintes sob regime de lucro real, lucro presumido e lucro arbitrado.

**Pergunta (GT — Carlos Mota):** A dedução de créditos de insumos do IBS foi considerada no cálculo da BC?

**Resposta (RFB — Rodrigo Lima):** **Não.** A base de cálculo aqui apurada refere-se à BC bruta da CBS, antes de qualquer crédito do IBS. A metodologia de dedução de créditos está prevista para entrega separada no MOD_010.

**Pergunta (GT — Fernanda Costa):** Os 147 outliers excluídos foram investigados individualmente?

**Resposta (RFB — Ana Paula Guimarães):** Sim. Dos 147:
- 34 foram resolvidos como erro de preenchimento da EFD (retificadora enviada)
- 113 apresentaram comportamento atípico confirmado (ex.: recolhimentos irregulares, encerramento tardio, liminar judicial suspendendo CBS)

A exclusão foi formalizada em nota técnica interna da COSIT (NT COSIT nº 12/2026, de 2026-03-20, disponível para consulta mediante solicitação formal).

---

## 3. Confirmação de Escopo e Limitações

O Sr. Carlos Mota leu em voz alta as limitações declaradas na Seção 5 da descrição metodológica. A RFB confirmou todas as limitações sem ressalvas adicionais.

**Limitação adicional registrada em reunião (não constava da descrição):** A Sra. Ana Paula informou que o cruzamento com dados de câmbio (PTAX) utilizou a cotação do último dia útil de cada mês, não a média mensal. O impacto estimado é inferior a 0,05 pp na alíquota de referência, dentro da margem de erro declarada.

A Sra. Fernanda Costa registrou esta limitação adicional no sistema de controle do GT como "Limitação L4 — Critério de câmbio (PTAX fim de mês vs. média mensal)".

---

## 4. Próximos Passos

| Ação | Responsável | Prazo |
|------|-------------|-------|
| Encaminhar NT COSIT nº 12/2026 ao GT | RFB/Rodrigo Lima | 2026-04-22 |
| Iniciar validação DVA-CBS (Atividade 1) | GT/Carlos Mota | 2026-04-16 |
| Retificação da EFD dos 34 casos resolvidos | RFB/Ana Paula | 2026-05-30 |

---

## Encerramento

Reunião encerrada às 16h30. Ata lavrada por Fernanda Alves Costa e validada por Carlos Eduardo Mota.

A entrega foi registrada no sistema de controle do GT em 2026-04-15T16:35:00-03:00.

---

*Ata de reunião sintética elaborada para fins de piloto do DVA-CBS | TC 015.848/2025-6*
