# Agent — Mycroft Holmes
## Auditor Chefe | DVA-CBS | Projeto Diógenes

---

## Identificação

```yaml
agent_id: mycroft
agent_role: auditor_chefe
agent_formal_name: "Mycroft Holmes"
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
```

---

## Parâmetros de modelo

```yaml
model_preferencial: claude-sonnet-4-6
# Justificativa: Mycroft não processa os documentos do pacote RFB diretamente —
# ele avalia os outputs estruturados de Watson e Sherlock, integra resultados
# e produz documentos de orquestração. O Sonnet é suficiente para raciocínio
# de integração e síntese sobre outputs já estruturados.
# Pode ser sobrescrito pelo agents_spec.yaml do ciclo.

model_excecao: claude-opus-4-6
# Usado exclusivamente na chamada `consolidar`, onde Mycroft precisa integrar
# todo o histórico do ciclo (outputs de Watson + rodadas de revisão + outputs
# de Sherlock + rodadas de revisão) em uma posição consolidada coerente.
# O volume e a heterogeneidade dos inputs nessa chamada justificam o Opus.

temperatura: 0.2
# Justificativa: Mycroft exerce julgamento — uma atividade que requer
# alguma flexibilidade contextual para formular a crítica mais relevante
# (não a primeira que aparece) e para sintetizar posições heterogêneas em
# linguagem coerente. Temperatura ligeiramente maior que Watson e Sherlock
# é apropriada para funções de síntese e julgamento.

max_tokens_padrao: 32768
# Fase B/D — elimina truncagem em avaliações longas, críticas e consolidar.
# Valor efetivo lido de agents_spec.yaml::agentes.mycroft.max_tokens (runtime).

max_tokens_consolidar: 32768
# Unificado com max_tokens_padrao — sem distinção por call_type no runtime.

timeout_segundos: 90
```

---

## Tools disponíveis no piloto

```yaml
tools: []
# Nenhuma tool disponível no piloto local.
# Mycroft recebe os outputs dos agentes já carregados no contexto pelo invocador.
# O invocador é responsável por carregar no contexto de cada chamada de Mycroft
# exatamente os arquivos necessários àquele call_type específico — não o pacote
# completo do ciclo em toda chamada.
```

---

## Composição do prompt por call_type

```yaml
system_prompt:
  - conteudo: soul.md        # identidade permanente
  - conteudo: skills.md      # templates e critérios por call_type

# O user_prompt varia significativamente por call_type.
# O invocador monta o contexto mínimo necessário para cada chamada.
```

### `definir_tasks_watson`

```yaml
user_prompt:
  - conteudo: heartbeat.md[definir_tasks_watson]
  - conteudo: manifesto_abertura.md
  - conteudo: briefing_modulo.md
  - conteudo: inventario_etapa1.md       # inventário físico da Etapa 1
  - conteudo: regras_etapa2.md           # artefatos de validação aprovados na Etapa 2
  # NÃO inclui os arquivos do pacote RFB — Mycroft não os analisa (Artigo 5)
  # O invocador lista os caminhos dos arquivos no manifesto para que Watson os acesse
output: MC_tasks_watson.md
```

### `mapear_pontos`

```yaml
# Acionado após aprovação de watson_consolidado.md, antes do primeiro verificar_ponto de Sherlock.
model_override: claude-sonnet-4-6   # leitura de análises estruturadas; Sonnet suficiente

user_prompt:
  - conteudo: heartbeat.md[mapear_pontos]
  - conteudo: [apendice_metodologico_completo]  # Apêndice correspondente ao módulo
  - conteudo: watson_consolidado.md              # para identificar quais arquivos têm info relevante
  - conteudo: watson_analise_*.md               # para confirmar o conteúdo de cada análise
  # NÃO inclui arquivos originais do pacote RFB

output: MC_mapa_pontos.md
```

### `avaliar_agente` (Watson)

```yaml
user_prompt:
  - conteudo: heartbeat.md[avaliar_agente]
  - conteudo: MC_tasks_watson.md
  - conteudo: watson_consolidado.md | watson_resposta_r1.md   # o output atual a avaliar
  - conteudo: watson_registro_decisao.md                      # sempre — mapa dos julgamentos
  - conteudo: [watson_trace_arquivo.md]    # APENAS se resultado=CRITICA E Mycroft questiona
                                           # conclusão de arquivo específico E trace existe
output_r0: MC_avaliacao_watson_r0.md
output_r1: MC_avaliacao_watson_r1.md
```

### `avaliar_agente` (Sherlock)

```yaml
user_prompt:
  - conteudo: heartbeat.md[avaliar_agente]
  - conteudo: MC_pacote_sherlock.md
  - conteudo: sherlock_consolidado.md | sherlock_resposta_r1.md   # o output atual a avaliar
  - conteudo: sherlock_registro_decisao.md                        # sempre — mapa dos julgamentos
  - conteudo: [sherlock_trace_ponto_n.md]  # APENAS se resultado=CRITICA E Mycroft questiona
                                           # classificação de ponto específico E trace existe
output_r0: MC_avaliacao_sherlock_r0.md
output_r1: MC_avaliacao_sherlock_r1.md
# Não existe r2 — após resposta_r2 o call_type é fixar_decisao
```

### `fixar_decisao`

```yaml
# Acionado apenas após resposta_r2 do agente.
# O invocador chega aqui quando MC_avaliacao_[agente]_r1.md tem resultado=CRITICA.
user_prompt:
  - conteudo: heartbeat.md[fixar_decisao]
  - conteudo: [output_inicial_agente]           # analise_inicial ou validacao_inicial
  - conteudo: [output_resposta_r1]
  - conteudo: [output_resposta_r2]
  - conteudo: MC_avaliacao_[agente]_r0.md       # crítica da rodada 0
  - conteudo: MC_avaliacao_[agente]_r1.md       # crítica da rodada 1
output_watson: MC_decisao_watson.md
output_sherlock: MC_decisao_sherlock.md
```

### `montar_pacote_sherlock`

```yaml
user_prompt:
  - conteudo: heartbeat.md[montar_pacote_sherlock]
  - conteudo: manifesto_abertura.md
  - conteudo: 01_watson_analise_inicial.md
  - conteudo: 02_watson_resposta_r1.md          # se existir
  - conteudo: 03_watson_resposta_r2.md          # se existir
  - conteudo: MC_avaliacao_watson_r0.md | MC_avaliacao_watson_r1.md | MC_decisao_watson.md
  # O arquivo de resultado efetivo de Watson: avaliacao_r0 (se aprovado de imediato),
  # avaliacao_r1 (se aprovado após uma rodada), ou MC_decisao_watson (se houve fixar_decisao)
output: MC_pacote_sherlock.md
```

### `consolidar`

```yaml
model_override: claude-opus-4-6
user_prompt:
  - conteudo: heartbeat.md[consolidar]
  - conteudo: manifesto_abertura.md
  - conteudo: MC_pacote_sherlock.md
  - conteudo: 04_sherlock_validacao_inicial.md
  - conteudo: 05_sherlock_resposta_r1.md        # se existir
  - conteudo: 06_sherlock_resposta_r2.md        # se existir
  - conteudo: MC_aprovado_sherlock.md | MC_decisao_sherlock.md
output: MC_consolidado.md
```

---

## Limites constitucionais em linguagem técnica

```yaml
restricoes_hard:

  - id: ART5_SEM_ANALISE_DIRETA
    descricao: >
      Mycroft não analisa os arquivos do pacote RFB diretamente.
      O invocador não deve injetar os arquivos do pacote no contexto das
      chamadas de Mycroft — apenas os outputs dos agentes e os documentos
      de orquestração (manifesto, briefing, MC_ files).
      Exceção: o manifesto lista os caminhos dos arquivos do pacote para
      que Mycroft possa referenciar esses caminhos ao montar as tasks de Watson.
    violacao_detectavel: >
      Contexto de Mycroft contendo conteúdo de planilha xlsx, código SQL
      ou código Python do pacote RFB injetado diretamente.

  - id: UMA_CRITICA_POR_RODADA
    descricao: >
      Mycroft formula exatamente uma crítica por chamada avaliar_agente
      que resulte em questionamento. Uma crítica. Uma localização. Um argumento.
      O invocador não deve re-acionar avaliar_agente para o mesmo agente na
      mesma fase sem que o agente tenha respondido à crítica anterior.
    violacao_detectavel: >
      Output de MC_critica contendo mais de um ponto questionado distinto.

  - id: ART3_SEQUENCIALIDADE
    descricao: >
      O invocador garante que Watson e Sherlock nunca são acionados
      simultaneamente. O workflow do invocador deve ser estritamente linear:
      Mycroft define tasks → Watson executa → Mycroft avalia → [rodadas] →
      Mycroft monta pacote → Sherlock executa → Mycroft avalia → [rodadas] →
      Mycroft consolida → Lestrade chancela.
    violacao_detectavel: >
      Chamadas paralelas a watson e sherlock no mesmo ciclo no log do invocador.

  - id: LIMITE_RODADAS_ABS
    descricao: >
      Máximo de duas rodadas de revisão por agente por fase.
      Após MC_critica_[agente]_r2, o próximo passo obrigatório é
      fixar_decisao — não uma terceira avaliação.
    violacao_detectavel: >
      Existência de MC_critica_[agente]_r3 no diretório do ciclo.

  - id: ART14_TERCEIRA_PESSOA
    descricao: >
      Todo output de Mycroft é em terceira pessoa, impessoal.
      "Mycroft" ou "Mycroft Holmes" não aparece no corpo dos documentos —
      apenas na assinatura final.
    violacao_detectavel: >
      Ocorrência de "Mycroft avaliou", "Mycroft considera" no corpo do
      output fora da seção de assinatura.
```

---

## Outputs por call_type — convenção de nomenclatura

```yaml
# Prefixo MC_ identifica todos os arquivos produzidos por Mycroft.
# Isso resolve qualquer colisão com a numeração sequencial de Watson e Sherlock.

mycroft_outputs:
  - MC_tasks_watson.md                   # sempre
  - MC_avaliacao_watson_r0.md            # avaliação do watson_consolidado
  - MC_avaliacao_watson_r1.md            # avaliação da watson_resposta_r1 — se houver
  - MC_decisao_watson.md                 # se houve watson_resposta_r2 (fixar_decisao)
  - MC_alerta_critico_lestrade.md        # se watson_consolidado tem alertas CRITICA
  - MC_mapa_pontos.md                    # sempre, antes de Sherlock iniciar
  - MC_pacote_sherlock.md                # sempre
  - MC_avaliacao_sherlock_r0.md          # avaliação do sherlock_consolidado
  - MC_avaliacao_sherlock_r1.md          # avaliação da sherlock_resposta_r1 — se houver
  - MC_decisao_sherlock.md               # se houve sherlock_resposta_r2 (fixar_decisao)
  - MC_consolidado.md                    # sempre

# Todos os arquivos são gravados em:
# MOD_XXX/ANALISE/{timestamp_ciclo}/
```

---

## Notas de design

**Por que Sonnet para Mycroft e Opus para Watson/Sherlock em chamadas iniciais?**
Aparentemente contraintuitivo — o Auditor Chefe usando modelo menor. A razão: Watson e Sherlock processam volumes grandes de documentos heterogêneos e precisam de raciocínio analítico extenso sobre conteúdo que nunca viram. Mycroft processa outputs estruturados que seguem templates conhecidos e formula julgamentos localizados. A síntese de outputs estruturados é tarefa onde o Sonnet performa muito bem, com latência e custo menores. A exceção do Opus para `consolidar` existe porque nessa chamada Mycroft precisa integrar o histórico completo do ciclo — um contexto que pode ser extenso e heterogêneo.

**Por que temperatura 0.2 e não 0.1?**
A crítica ideal não é a primeira que o modelo encontra — é a mais relevante para o avanço do ciclo. Uma temperatura ligeiramente maior que a dos agentes executores favorece que Mycroft escolha o ponto de maior impacto entre os candidatos, em vez de fixar na primeira inconsistência detectada.

**Por que o invocador não injeta os arquivos do pacote no contexto de Mycroft?**
Artigo 5 da Constituição. Se os arquivos do pacote estão no contexto de Mycroft, o modelo pode — e provavelmente irá — analisar diretamente, violando o limite constitucional. A garantia é arquitetural: o invocador simplesmente não injeta esses arquivos. Mycroft avalia outputs, não documentos fonte.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Documento de parâmetros de runtime — uso interno restrito*
