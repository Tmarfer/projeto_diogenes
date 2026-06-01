# Auditoria Comparativa — GPT-5.4 Thinking vs GPT-5.5 Thinking

**Escopo:** execução completa da bancada `MOD_010`, com 69 CSVs e 11 XLSX.  
**Referência GPT-5.4:** `workspace/_bench/pipeline_MOD_010_20260531T191437Z`  
**Referência GPT-5.5:** `workspace/_bench/pipeline_MOD_010_20260531T234500Z`  
**Data da auditoria:** 2026-05-31

## Conclusão Executiva

O `gpt-5.5-thinking` foi superior nesta comparação prática. Ele foi mais rápido, produziu consolidação Watson utilizável, permitiu uma crítica Mycroft substantiva e deixou uma trilha final mais acionável para desenvolvimento.

O `gpt-5.4-thinking` teve sucesso de API, mas a qualidade do produto final ficou comprometida: o arquivo `04_watson_consolidado.md` saiu vazio, duas análises individuais vieram como recusa padrão e o Mycroft seguinte não conseguiu avaliar a consolidação Watson por falta de conteúdo efetivo.

O custo do `gpt-5.5-thinking` foi aproximadamente o dobro do `gpt-5.4-thinking`. Ainda assim, para bancada completa do `MOD_010`, o ganho de qualidade compensou: a execução 5.5 gerou material auditável; a 5.4, nesta rodada completa, não gerou uma consolidação Watson aproveitável.

Ambas as execuções terminaram sem emissão válida de `MC_consolidado.md`. Isso não deve ser lido apenas como falha de modelo: a etapa Sherlock continuou limitada pela ausência do pacote metodológico/protocolar completo exigido para validação final.

## Observação De Comparabilidade

A comparação não é perfeitamente controlada:

| Item | GPT-5.4 | GPT-5.5 |
| --- | ---: | ---: |
| Diretório | `pipeline_MOD_010_20260531T191437Z` | `pipeline_MOD_010_20260531T234500Z` |
| Perfil | `stable-gpt54` | `default` com `agents_spec.yaml` alterado |
| Modelo | `gpt-5.4-thinking` | `gpt-5.5-thinking` |
| Timeout | 600s | 600s |
| Retries | 2 | 1 |
| Sherlock | `freeform_aux_only` | protocolar |
| Escopo | 69 CSVs + 11 XLSX | 69 CSVs + 11 XLSX |

Essa diferença favorece uma leitura prudente: o resultado mostra que, nas condições reais dessas duas rodadas, o GPT-5.5 performou melhor. Para uma comparação estritamente científica, seria recomendável rodar ambos com o mesmo perfil, mesmos retries e mesmo modo Sherlock.

## Desempenho

| Métrica | GPT-5.4 | GPT-5.5 | Diferença |
| --- | ---: | ---: | ---: |
| Duração total | 10.775,2s | 8.908,3s | -1.866,9s |
| Duração total aproximada | 2h59m35s | 2h28m28s | -31m07s |
| Variação de tempo | base | -17,3% | melhor no 5.5 |
| Input tokens | 5.153.642 | 5.706.253 | +552.611 |
| Output tokens | 641.824 | 563.256 | -78.568 |
| Total tokens | 5.795.466 | 6.269.509 | +474.043 |
| Variação total de tokens | base | +8,2% | maior no 5.5 |
| Custo estimado | US$ 22,51 | US$ 45,43 | +US$ 22,92 |
| Variação de custo | base | +101,8% | mais caro no 5.5 |

Preços de referência usados pela bancada:

| Modelo | Input | Output |
| --- | ---: | ---: |
| `gpt-5.4-thinking` | US$ 2,50 / 1M tokens | US$ 15,00 / 1M tokens |
| `gpt-5.5-thinking` | US$ 5,00 / 1M tokens | US$ 30,00 / 1M tokens |

## Desempenho Watson

| Métrica Watson | GPT-5.4 | GPT-5.5 | Leitura |
| --- | ---: | ---: | --- |
| Média por análise individual | 147,0s | 120,6s | 5.5 foi 18,0% mais rápido |
| Mediana por análise individual | 142,9s | 116,0s | 5.5 foi 18,8% mais rápido |
| Média de output tokens por arquivo | 8.877 | 7.570 | 5.5 gerou menos saída por análise |
| Mediana de output tokens por arquivo | 8.501 | 7.453 | 5.5 foi mais contido |

O GPT-5.5 foi mais eficiente no trecho Watson: menor tempo médio, menor mediana e menor volume médio de output por arquivo. O ponto importante é que a redução de output não degradou a consolidação; ao contrário, a consolidação 5.5 foi materialmente melhor.

## Confiabilidade Operacional

| Item | GPT-5.4 | GPT-5.5 | Avaliação |
| --- | ---: | ---: | --- |
| Sucesso de API | 76/76 | 76/76 | empate |
| `all_success` | `true` | `true` | empate formal |
| `api_success` | `true` | `true` | empate formal |
| Retries observados | 0 | 1 | 5.5 recuperou um HTTP 502 |
| Etapas OK com 0 tokens | 3 | 1 | melhor no 5.5 |
| Recusas explícitas | 2 | 1 | melhor no 5.5 |
| Consolidação Watson vazia | sim | não | vantagem crítica do 5.5 |
| Consolidação Watson utilizável | não | sim | vantagem crítica do 5.5 |
| Limitação Sherlock | sim | sim | limitação de fluxo/pacote |
| MC final emitido | não | não | empate formal |

O ponto decisivo não está no `api_success`, pois ambos passaram pela API. O ponto decisivo está na validade semântica dos artefatos produzidos. A execução GPT-5.4 aparenta sucesso operacional, mas falha como produto de auditoria porque a consolidação Watson ficou vazia. A execução GPT-5.5 teve uma falha transitória HTTP 502 em `watson_analise_47`, recuperada no retry, e ainda assim produziu artefatos de melhor qualidade.

## Achados Da Execução GPT-5.4

### Pontos positivos

- Completou formalmente todas as chamadas da bancada.
- Processou o escopo completo de 69 CSVs e 11 XLSX.
- Não registrou erro HTTP terminal.
- Sherlock e Mycroft final registraram limitações metodológicas em vez de forçar conclusão indevida.

### Problemas relevantes

- `04_watson_consolidado.md` ficou vazio.
- `watson_consolidar` aparece como etapa OK, mas com `0` input tokens e `0` output tokens.
- Duas análises individuais Watson retornaram recusa padrão:
  - `03_watson_04_aux_mod_10_pf_execucao__aux_mod_10_3.csv.md`
  - `03_watson_68_produtor_rural_pf__matriz_de_incidencia_.md`
- Mycroft não conseguiu avaliar a consolidação Watson porque o conteúdo consolidado não estava efetivamente disponível.
- O relatório final corretamente notificou impossibilidade de emissão do `MC_consolidado.md`.

### Leitura qualitativa

A execução GPT-5.4 teve aparência de sucesso de pipeline, mas não entregou uma consolidação Watson auditável. Para comparação de resultados, isso enfraquece bastante a rodada 5.4: ela serve como evidência de desempenho e de comportamento da bancada, mas não como baseline robusto de qualidade analítica final.

## Achados Da Execução GPT-5.5

### Pontos positivos

- Completou formalmente todas as chamadas da bancada.
- Processou o mesmo escopo completo de 69 CSVs e 11 XLSX.
- Foi 17,3% mais rápido no tempo total.
- Foi aproximadamente 18% mais rápido nas análises individuais Watson.
- Produziu `04_watson_consolidado.md` real, com 34.645 caracteres e 536 linhas.
- Watson consolidado declarou 68 análises estruturadas recebidas em 69 arquivos.
- A consolidação mapeou inventário com 69 linhas e totais de severidade:
  - Críticos: 110
  - Altos: 98
  - Médios: 184
  - Baixos: 39
- Mycroft conseguiu fazer crítica substantiva sobre a decisão Watson, especialmente sobre calibração de severidade crítica.
- Sherlock protocolar recusou validação plena por falta de insumos metodológicos, o que é comportamento prudente.
- Mycroft final identificou problema formal na assinatura do Sherlock, mostrando capacidade de auditoria de forma além de conteúdo.

### Problemas relevantes

- Uma análise individual Watson retornou recusa padrão:
  - `03_watson_11_demais_pessoas_fisicas__consumo_final_co.md`
- Houve um HTTP 502 transitório em `watson_analise_47`, recuperado no retry.
- A execução usou Sherlock protocolar, então não é diretamente comparável ao modo `freeform_aux_only` usado no GPT-5.4.
- O custo estimado foi cerca de 2,02 vezes maior.
- O relatório final continuou impedindo emissão de `MC_consolidado.md`, por ausência de pacote metodológico completo e pendências críticas.

### Leitura qualitativa

A execução GPT-5.5 foi muito mais útil como bancada de desenvolvimento. Mesmo sem chegar a um `MC_consolidado.md` final, ela gerou uma cadeia de artefatos que permite discutir severidade, rastreabilidade, limitações protocolar-metodológicas e próximos ajustes do pipeline.

## Comparação Dos Resultados Finais

| Etapa | GPT-5.4 | GPT-5.5 | Vencedor prático |
| --- | --- | --- | --- |
| Irene/preparação | executado | executado | empate |
| Mycroft tarefas | executado | executado | empate |
| Watson individuais | majoritariamente executado, 2 recusas | majoritariamente executado, 1 recusa | GPT-5.5 |
| Watson consolidado | vazio | consolidado real | GPT-5.5 |
| Mycroft decisão Watson | não conseguiu avaliar por falta de conteúdo | crítica substantiva da severidade e rastreabilidade | GPT-5.5 |
| Sherlock | limitação AUX-only | limitação protocolar por falta de pacote | depende do objetivo |
| Mycroft decisão Sherlock | crítica metodológica | crítica metodológica + achado formal de assinatura | GPT-5.5 |
| Relatório final | impede emissão por falta de Watson/Sherlock consolidado | impede emissão com pendências acionáveis | GPT-5.5 |

## Interpretação Técnica

O GPT-5.5 não apenas rodou mais rápido; ele sustentou melhor o trabalho de síntese. A diferença central está em `04_watson_consolidado.md`: no 5.4, a etapa crítica de consolidação ficou vazia; no 5.5, virou um artefato estruturado com inventário, alertas e limitações explícitas.

Isso muda a natureza da rodada. Com GPT-5.4, a auditoria posterior fica obrigada a discutir ausência de saída. Com GPT-5.5, a auditoria consegue discutir a qualidade da análise: severidade, rastreabilidade, suficiência de insumos e aderência protocolar.

O GPT-5.5 também reduziu o output médio por arquivo Watson, o que sugere maior concisão. Como a consolidação final saiu melhor, essa concisão parece ter sido produtiva, não empobrecimento.

## Limitações Da Bancada

As duas rodadas ainda não provam a capacidade de emissão final do `MC_consolidado.md`, porque Sherlock não recebeu o pacote completo exigido para validação protocolar.

Faltaram ou não estavam suficientemente integrados ao fluxo final:

- `MC_mapa_pontos.md`;
- apêndice protocolar completo;
- análises individuais relevantes entregues a Sherlock no formato esperado;
- material consolidado Sherlock esperado pelo relatório final;
- JSON/artefatos finais exigidos pelo fluxo de fechamento.

Portanto, a conclusão correta não é “GPT-5.5 resolve o fluxo inteiro”. A conclusão correta é: “GPT-5.5 gera artefatos intermediários muito melhores nesta bancada completa e deixa os bloqueios restantes mais claros”.

## Recomendações

1. Usar `gpt-5.5-thinking` como modelo preferencial para bancadas completas do `MOD_010`, quando o custo for aceitável.
2. Manter `gpt-5.4-thinking` como alternativa econômica apenas para recortes menores ou após melhorar a instrumentação de saída vazia/recusa.
3. Fazer uma comparação controlada posterior:
   - ambos com mesmo perfil;
   - mesmos retries;
   - mesmo modo Sherlock;
   - mesmo timeout;
   - mesma versão do código.
4. Tratar saídas vazias, recusa padrão e etapas com `0` tokens como anomalias semânticas da bancada, mesmo quando a chamada HTTP tiver sucesso.
5. Separar nos relatórios:
   - sucesso de API;
   - sucesso de geração;
   - validade metodológica;
   - bloqueio protocolar.
6. Fornecer a Sherlock o pacote metodológico completo antes de avaliar a qualidade do fechamento final.
7. Remover ou bloquear assinaturas/personificações em saídas protocolar-metodológicas, como observado no Sherlock da rodada GPT-5.5.

## Veredito

Para esta rodada completa do `MOD_010`, o `gpt-5.5-thinking` é o melhor candidato para continuidade. Ele custou mais, mas entregou uma execução mais rápida e, principalmente, uma cadeia de resultados muito mais aproveitável.

O `gpt-5.4-thinking` não deve ser descartado, mas a rodada completa analisada aqui não é uma boa baseline de resultado final porque a consolidação Watson ficou vazia. Antes de promovê-lo novamente para comparação de qualidade, vale corrigir a observabilidade das etapas semanticamente vazias e repetir o teste em condições controladas.
