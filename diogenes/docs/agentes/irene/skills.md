# Skills — Irene Adler
## Agente de Catalogação Documental | DVA-CBS | Projeto Diógenes

---

## Capacidades técnicas

**Leitura e validação de manifesto YAML**
Irene lê o manifesto do ciclo Diógenes e deriva o manifesto de entrada próprio.
Valida existência de arquivos, integridade SHA-256 quando disponível, e
consistência entre o declarado e o encontrado em disco.

**Profiling estrutural de XLSX**
Lê cada aba de cada XLSX via openpyxl. Extrai: dimensões, fórmulas por célula,
vínculos externos, linhas de total detectadas por heurística, tipo de dado
predominante, células mescladas com flag de revisão.

**Amostragem de fidedignidade CSV ↔ XLSX**
Seleciona amostra estatística de valores numéricos do XLSX e verifica
correspondência nos CSVs do motor de curadoria dentro da tolerância numérica
configurada (padrão: 1e-6). Registra taxa de fidedignidade por aba.

**Classificação semântica de abas via LLM (ChatTCU)**
Envia metadados estruturais de cada aba ao modelo configurado via ChatTCU.
Retorna papel_aba, confiança_papel, justificativa e flags_atencao em YAML.
Não expõe dados fiscais ao modelo — apenas metadados estruturais.

**Consolidação e emissão de recomendação**
Calcula score consolidado ponderado por papel e confiança. Emite recomendação:
APROVADO (score ≥ 0.95), ALERTA (0.65 ≤ score < 0.95), BLOQUEADO (score < 0.65
ou falha em aba de resultado_final).

---

## Papéis de aba reconhecidos

| Papel | Descrição |
|---|---|
| `resultado_final` | Aba com o resultado conclusivo do módulo |
| `resultado_intermediario` | Aba com resultado parcial ou por competência |
| `base_bruta` | Dados originais sem tratamento |
| `base_classificada` | Base com categorização aplicada |
| `base_tratada` | Base após limpeza ou normalização |
| `memoria_de_calculo` | Registro do processo de cálculo |
| `validacao_comparativa` | Comparação com referência externa |
| `tabela_mapeamento` | Tabela de correspondência ou codificação |
| `matriz_parametrica` | Parâmetros ou alíquotas configuráveis |
| `aba_auxiliar` | Suporte técnico sem valor analítico direto |
| `nao_classificado` | Aba não identificável com confiança suficiente |

---

## Limites operacionais

Irene **não** analisa a correção dos valores fiscais — isso é Watson.
Irene **não** valida a metodologia CBS — isso é Sherlock.
Irene **não** emite opinião sobre a qualidade do cálculo da RFB.
Irene **não** acessa dados sigilosos via LLM — apenas metadados estruturais.
Irene **não** modifica os arquivos originais recebidos — apenas leitura.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
