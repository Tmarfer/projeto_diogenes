# Agent — Dr. John Watson
## Auditor de Integridade Técnica | DVA-CBS | Projeto Diógenes

---

## Identificação

```yaml
agent_id: watson
agent_role: auditor_integridade_tecnica
agent_formal_name: "Dr. John Watson"
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
```

---

## Parâmetros de modelo

```yaml
model_preferencial: claude-opus-4-6
# Justificativa: Watson analisa conteúdo técnico heterogêneo (SQL, Python,
# planilhas encadeadas) e produz análises que Mycroft precisará questionar
# com precisão. Opus garante qualidade no raciocínio analítico por arquivo.

model_fallback: claude-sonnet-4-6
# Usado para consolidar_watson e para respostas, onde o escopo
# é mais delimitado (análises já estruturadas como input).

temperatura: 0.1
max_tokens_analise_arquivo: 4000
# Suficiente para análise de um arquivo por vez. Contexto pequeno e focado.

max_tokens_consolidar: 6000
# A consolidação integra múltiplos watson_analise_*.md — precisa de
# espaço para a cadeia de produção cross-file.

timeout_segundos: 90
```

---

## Composição do prompt por call_type

```yaml
system_prompt:                          # igual em todas as chamadas
  - conteudo: soul.md
  - conteudo: skills.md

# O user_prompt varia por call_type:
```

### `analise_arquivo`

```yaml
user_prompt:
  - conteudo: heartbeat.md[analise_arquivo]
  - conteudo: MC_tasks_watson.md              # contexto do ciclo e instruções de Mycroft
  - conteudo: [um_arquivo_do_pacote]          # exatamente um arquivo por chamada
  - meta_invocador:
      proximo_id_alerta: "W008-001"           # injetado pelo invocador, atualizado após cada chamada

output_analise: "watson_analise_{nome_arquivo_sem_ext}.md"
output_trace:   "watson_trace_{nome_arquivo_sem_ext}.md"   # apenas se Watson decidir produzir

# O invocador lê o campo "Último ID de alerta usado" do output
# e o injeta como "Próximo ID de alerta disponível" na chamada seguinte.
```

### `consolidar_watson`

```yaml
model_override: claude-sonnet-4-6      # análises já estruturadas; Sonnet suficiente

user_prompt:
  - conteudo: heartbeat.md[consolidar_watson]
  - conteudo: MC_tasks_watson.md
  - conteudo: watson_analise_*.md      # todos os arquivos de análise produzidos na Fase 1
  # NÃO inclui os arquivos originais do pacote RFB

output: "watson_consolidado.md"
```

### `resposta_r1`

```yaml
user_prompt:
  - conteudo: heartbeat.md[resposta_r1]
  - conteudo: watson_consolidado.md
  - conteudo: MC_avaliacao_watson_r0.md          # avaliação de Mycroft (resultado=CRITICA)
  - conteudo: [watson_trace_arquivo_relevante.md] # injetado pelo invocador SE Mycroft
                                                  # questionou conclusão de arquivo específico
                                                  # e trace existe para esse arquivo

output: "watson_resposta_r1.md"
```

### `resposta_r2`

```yaml
user_prompt:
  - conteudo: heartbeat.md[resposta_r2]
  - conteudo: watson_consolidado.md
  - conteudo: watson_resposta_r1.md
  - conteudo: MC_avaliacao_watson_r0.md
  - conteudo: MC_avaliacao_watson_r1.md
  - conteudo: [watson_trace_arquivo_relevante.md] # se aplicável

output: "watson_resposta_r2.md"
```

---

## Limites constitucionais em linguagem técnica

```yaml
restricoes_hard:

  - id: ART6_INTEGRIDADE_APENAS
    descricao: >
      Watson não emite classificações de aderência metodológica.
      Categorias Atendido, Divergência etc. são exclusivas de Sherlock.
      Watson usa apenas CRITICA, ALTA, MEDIA, BAIXA.
    violacao_detectavel: >
      Output contendo "Atendido", "Divergência metodológica",
      "conforme a metodologia", "em desacordo com o Acórdão".

  - id: UM_ARQUIVO_POR_CHAMADA
    descricao: >
      Em analise_arquivo, o invocador injeta exatamente um arquivo do pacote.
      Watson não analisa múltiplos arquivos originais em uma única chamada
      de analise_arquivo.
    violacao_detectavel: >
      Múltiplos arquivos originais do pacote RFB injetados em uma
      única chamada de analise_arquivo.

  - id: CONSOLIDACAO_SEM_ORIGINAIS
    descricao: >
      Em consolidar_watson, o invocador não injeta os arquivos originais
      do pacote. Watson consolida a partir das análises isoladas.
    violacao_detectavel: >
      Arquivos xlsx, sql ou ipynb do pacote RFB injetados em chamada
      de consolidar_watson.

  - id: TRACE_EXCECAO_ART14
    descricao: >
      O trace usa primeira pessoa — exceção explícita ao Artigo 14,
      documentada no skills.md. O trace nunca é entregável ao GT e
      nunca passa pelo Motor de Saída.
    violacao_detectavel: >
      Arquivo watson_trace_*.md referenciado em MC_consolidado.md
      ou em qualquer produto destinado ao GT.

  - id: ART14_EXCETO_TRACE
    descricao: >
      Todos os documentos de Watson exceto o trace são em terceira
      pessoa, impessoal, sem nome do agente no corpo.
    violacao_detectavel: >
      Primeira pessoa em watson_analise_*.md, watson_consolidado.md,
      watson_resposta_*.md.

  - id: LIMITE_RODADAS
    descricao: >
      Watson responde no máximo duas vezes a questionamentos de Mycroft.
      O invocador não gera call_type resposta_r3 ou superior.
    violacao_detectavel: >
      Existência de watson_resposta_r3.md no diretório do ciclo.
```

---

## Convenções de nomenclatura

```yaml
watson_outputs:
  # Fase 1 — por arquivo:
  - "watson_analise_{nome_arquivo_sem_ext}.md"    # sempre
  - "watson_trace_{nome_arquivo_sem_ext}.md"      # opcional, decisão de Watson

  # Fase 2 — consolidação:
  - "watson_consolidado.md"                        # sempre
  - "watson_registro_decisao.md"                   # sempre (com n=0 se sem bifurcações)

  # Respostas a Mycroft:
  - "watson_resposta_r1.md"                        # se Mycroft questionar
  - "watson_resposta_r2.md"                        # se Mycroft questionar segunda vez

# Todos os arquivos gravados em:
# MOD_XXX/ANALISE/{timestamp_ciclo}/
```

---

## Notas de design

**Por que Opus para `analise_arquivo` e Sonnet para `consolidar_watson`?**
A análise isolada exige leitura profunda de conteúdo técnico não estruturado (SQL, Python, planilhas complexas). A consolidação recebe apenas .md estruturados e executa raciocínio de integração — território do Sonnet.

**Por que o contador de ID é responsabilidade do invocador?**
Watson processa um arquivo por vez em contextos isolados — não tem memória do ciclo anterior. O invocador é o único componente que persiste estado entre chamadas, e o ID sequencial global é exatamente esse tipo de estado. O cabeçalho do output (`Último ID de alerta usado`) é a interface de comunicação entre Watson e o invocador para manutenção do contador.

**Por que o trace é decisão de Watson, não do invocador?**
Watson é o único que sabe, no momento da análise, se o raciocínio que levou a uma conclusão é suficientemente não óbvio para merecer registro. O invocador não tem essa informação antes da análise. Watson declara a decisão no cabeçalho (`Trace produzido: Sim/Não`) para que o invocador saiba o que procurar após a chamada.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Documento de parâmetros de runtime — uso interno restrito*
