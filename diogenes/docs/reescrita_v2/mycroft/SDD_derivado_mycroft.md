---
documento: SDD Derivado — Mycroft Holmes (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/sdd/SDD_Piloto_Diogenes_v01.md (Blocos 1, 2.3/2.4, 8)
  - src/diogenes/agents/mycroft.py (referência v1, 737 LOC)
  - src/diogenes/orchestrator/{orchestrator,states,stranger_room}.py
  - docs/agentes/mycroft/{agent,soul,skills,heartbeat}.md
  - docs/auditoria_agentes/mycroft/contrato.md
  - agents_spec.yaml
---

# SDD Derivado — Mycroft Holmes

> O "como" da reescrita v2 de Mycroft. Parte de onde o
> [PRD_derivado_mycroft.md](PRD_derivado_mycroft.md) encerra. Os 4 Pacotes de
> Trabalho (PT-MY-1..4, um por fatia) estão na Seção 11.

---

## 1. Relação com o SDD mestre

| Bloco do SDD | O que fornece a este derivado |
|---|---|
| Bloco 1.2 | As 4 decisões fundadoras (Python puro, single-process síncrono, filesystem-first, openai SDK) — restrições inegociáveis de todo Pacote de Trabalho |
| Bloco 1.3/1.4 | Posição de Mycroft entre os 8 componentes |
| Bloco 2.3/2.4 | Separação **definição** (`docs/agentes/mycroft/*.md`) × **invocação** (`agents/mycroft.py`) |
| Bloco 4.3 | `agents_spec.yaml` como fonte dos parâmetros de runtime |
| Bloco 8 | Fluxo do ciclo e protocolo Stranger Room |

## 2. Posição na arquitetura

- **Quem chama Mycroft:** exclusivamente o **Orquestrador**
  (`orchestrator/orchestrator.py`) durante o ciclo, e `orchestrator/entrega.py`
  na Fase de Entrega. Mycroft não conhece a máquina de estados.
- **Quem Mycroft "chama":** ninguém. Cada método retorna um resultado tipado; o
  Orquestrador persiste, transita estados e aciona o próximo agente.
- **Estados relevantes** (`orchestrator/states.py`):
  `AGUARDANDO_REVISAO_MYCROFT_WATSON`, `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO`,
  `AGUARDANDO_REVISAO_MYCROFT_SHERLOCK`, `AGUARDANDO_COMPLETUDE`,
  `EM_EXECUCAO_ENTREGA`, `AGUARDANDO_AJUSTE_ENTREGA`.

```
Manifesto confirmado
   └─► [M1] definir_tasks_watson ──► (Irene já rodou; Watson executa)
            └─► [M2] avaliar_watson ──(CRITICA? até 2 rodadas)──► fixar_decisao_watson
                     └─► inspeção alerta crítico (Art. 9 → Auto-Lestrade)
                          └─► montar_pacote_sherlock ──► (Sherlock executa)
                               └─► [M3] avaliar_sherlock ──(idem)──► fixar_decisao_sherlock
                                        └─► consolidar ──► relatorio_preliminar_{id}.md
                                             └─► [M4] deliver: mapear_dados_modulo →
                                                  (motor determinístico) → avaliar_entrega
```

## 3. Invocador — classe, assinaturas e parâmetros

Classe v1: `MycrooftAgent` (`agents/mycroft.py:39` — grafia com dois "o" é do SDD,
**preservar**). Construtor: `__init__(self, llm: LLMClient, agent_spec: AgentSpec, ...)`.

**Assinaturas públicas (contrato a preservar na v2):**

| Fatia | Método (v1 `mycroft.py`) | Retorno | call_type / heartbeat |
|---|---|---|---|
| M1 | `definir_tasks_watson(manifest: CycleManifest)` (`:58`) | `DefinirTasksResult` | `definir_tasks_watson` |
| M2 | `avaliar_watson(apresentacao: WatsonOutput, ...)` (`:96`) | `AvaliacaoMycroft` | `avaliar_agente` |
| M2 | `fixar_decisao_watson(output_final: WatsonOutput, ...)` (`:127`) | `DecisaoFinal` | `fixar_decisao` |
| M2 | `montar_pacote_sherlock(...)` (`:162`) | pacote (str/estrutura) | `montar_pacote_sherlock` |
| M3 | `avaliar_sherlock(apresentacao: SherlockOutput, ...)` (`:237`) | `AvaliacaoMycroft` | `avaliar_sherlock` |
| M3 | `fixar_decisao_sherlock(output_final: SherlockOutput, ...)` (`:266`) | `DecisaoFinal` | `fixar_decisao_sherlock` |
| M3 | `consolidar(manifest, decisao_watson: DecisaoFinal, ...)` (`:301`) | consolidado | `consolidar` |
| M4 | `mapear_dados_modulo(manifest, inventario: str, ...)` (`:363`) | mapa JSON | `mapear_dados_modulo` |
| M4 | `avaliar_entrega(manifesto: dict)` (`:411`) | `AvaliacaoMycroft` | `avaliar_entrega` |
| M4 | `redigir_apendice(manifest, consolidado: str, ...)` (`:436`) | texto | `redigir_apendice` |
| (bancada) | `mapear_pontos` — reservado ao modo per-ponto | — | `mapear_pontos` |

**Auxiliares internos a reescrever junto:** `_ler_catalogo_irene(cycle_dir)` (`:481`),
`_formatar_secao_catalogo_irene(catalogo)` (`:497`), `_construir_system_prompt()`
(`:573`), `_montar_call(call_type, phase, user)` (`:578`).

**Parâmetros de runtime** (`agents_spec.yaml::agentes.mycroft` — fonte da verdade;
`agent.md` apenas documenta):

| Parâmetro | Valor corrente |
|---|---|
| modelo | `gpt-5.5-thinking` (ChatTCU) |
| temperatura | `0.0` no spec (nota: `agent.md` justifica 0.2 para julgamento — divergência documental a resolver em "Decisões v2") |
| max_tokens | `16384` |
| max_tokens_ciclo | `131072` |
| timeout_segundos | `1500` |
| max_tentativas_retry / backoff | `4` / `60s` |

`tools: []` — Mycroft não tem tools; o invocador carrega no contexto de cada
chamada **exatamente** os arquivos necessários àquele call_type (nunca o pacote
completo do ciclo).

## 4. Consolidação dos 4 arquivos de definição

Padrão de construção de prompt (idêntico para os três agentes LLM):

```python
system_prompt = soul.md + "\n\n---\n\n" + skills.md   # lidos do filesystem a cada chamada
user_prompt   = heartbeat.md[call_type] + "\n\n" + inputs
```

> **Importante:** os 4 `.md` continuam sendo lidos do filesystem em **runtime**
> (sem cache — editar tem efeito imediato). Este derivado os consolida como
> **insumo de desenvolvimento**; não os substitui. Na v2, qualquer alteração de
> conteúdo desses arquivos é uma divergência deliberada (Seção 9).

### 4.1 `soul.md` — síntese (fonte: `docs/agentes/mycroft/soul.md`, 218 linhas)

| Regra | Conteúdo |
|---|---|
| Identidade | Auditor Chefe; "a inteligência que organiza as inteligências"; único contato Lestrade ↔ executores |
| Crítica localizada | Exatamente 1 crítica por rodada, objetiva, com localização precisa — nunca avaliação global |
| Martelo | Após 2ª rodada, fixa decisão com registro do raciocínio (ACATADO ou FIXADO POR MYCROFT) |
| Art. 5 | Avalia o raciocínio a partir do output; se precisa ir aos arquivos para entender, a crítica é "fundamentação não rastreável" |
| Anti-PII (ChatTCU) | Nunca CPFs/CNPJs/nomes/chaves literais; localização analítica; síntese estrutural; foco no raciocínio |
| Situações difíceis | Seção faltante de Sherlock → não emite consolidado, notifica Lestrade; aba ambígua no mapeamento → omite campo e registra; aviso operacional do Motor de Entrega não reprova entrega |
| RNF-CONC | Máx. 4.000 palavras por documento |

### 4.2 `skills.md` — síntese (978 linhas; templates por call_type)

| Template | Estrutura essencial |
|---|---|
| `definir_tasks_watson` | Cabeçalho com flag `Planilha de Verificação no pacote`; seção "Catálogo do Irene — Classificação Semântica"; "Premissas Globais do Projeto" (anos-base 2023/2024, critério de equivalência, sinalização de nota metodológica); "Tasks Delegadas a Watson — por esta ordem"; "Inputs Disponíveis" |
| `avaliar_agente` | Cabeçalho `Avaliação de Output — [Watson\|Sherlock] — Rodada r[n]`; seção "Avaliação" com branching parseável `APROVADO \| CRITICA`; "Próximo Passo para o Invocador" |
| `fixar_decisao` | "Histórico das Rodadas" + "Decisão Final de Mycroft" (ACATADO \| FIXADO POR MYCROFT, com raciocínio) |
| `montar_pacote_sherlock` | "Resultado Integrado de Watson" (ocorrências por severidade, cadeia de produção, insights); "Notas Metodológicas com Alteração"; "Instruções a Sherlock" |
| `consolidar` | "Output Consolidado do Ciclo"; "Verificação de Completude do Relatório Estruturado" (11 seções); campos `Overrule Mycroft sobre Watson/Sherlock` |
| `mapear_dados_modulo` / `avaliar_entrega` / `redigir_apendice` | Blueprint sem valores; QA `APROVADO \| REQUER_AJUSTE`; 7 seções do Apêndice |

### 4.3 `agent.md` — parâmetros documentados

Ver tabela da Seção 3. Pontos do `agent.md` que são **contrato** (não só doc):
composição do user_prompt por call_type (quais arquivos entram em cada chamada) e
a regra "NÃO inclui arquivos do pacote RFB".

### 4.4 `heartbeat.md` — transcrição verbatim (contrato de prompt)

O conteúdo abaixo é a transcrição integral de `docs/agentes/mycroft/heartbeat.md`
na data deste derivado (2026-06-11). **Na v2, o prompt montado deve ser
byte-idêntico ao gerado a partir deste arquivo** (critério de gate nº 2). Em caso
de dúvida, o arquivo em `docs/agentes/mycroft/heartbeat.md` prevalece (é o lido
em runtime).

<!-- INÍCIO TRANSCRIÇÃO VERBATIM heartbeat.md (Mycroft) -->
# Heartbeat — Mycroft Holmes
## Auditor Chefe | DVA-CBS | Projeto Diógenes

---

*Este arquivo é organizado em seções por call_type. O invocador Python injeta apenas a
seção correspondente à chamada atual no início do user_prompt, antes dos demais inputs.*

---

# Heartbeat de Mycroft — definir_tasks_watson

## Sua Situação Nesta Chamada

Lestrade confirmou o manifesto de abertura e acionou você. O ciclo começa agora. Sua
primeira função é converter a demanda do ciclo em tasks ordenadas para Watson, com todos os
inputs necessários e seus caminhos. O manifesto de abertura, o briefing do módulo e o
inventário dos arquivos recebidos seguem abaixo deste heartbeat.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o manifesto de abertura.**
Identifique: qual módulo, qual atividade, quais arquivos foram recebidos e seus caminhos no
diretório de trabalho, se o módulo é pré-selecionado para a Sala de Sigilo, o timestamp do
ciclo e o campo `prioridades_analise`. Se o campo estiver preenchido por Lestrade, a ordem
ali definida governa a sequência de processamento de Watson. Se estiver vazio, você aplica
a ordem padrão no Passo 3.

**Passo 1b: Verifique e leia o catálogo do Irene.**

Existe `irene_catalog.yaml` no diretório do ciclo? Se sim:
- Leia os campos `score_consolidado`, `recomendacao` e a lista `arquivos`
- Extraia para cada arquivo: `nome_original`, `papel`, `confianca_papel`,
  `flags_atencao` e `requer_revisao_humana`
- Use o papel para determinar a profundidade de análise de Watson:
  - `resultado_final` e `resultado_intermediario`: análise completa, todas
    as varreduras transversais obrigatórias
  - `base_bruta`, `base_classificada`, `base_tratada`, `memoria_de_calculo`:
    análise padrão com foco em rastreabilidade
  - `aba_auxiliar`, `tabela_mapeamento`, `matriz_parametrica`: verificação
    de integridade básica, sem aprofundamento analítico
  - `nao_classificado`: análise completa — Irene não conseguiu classificar;
    Watson deve determinar o papel durante a análise e registrar
- Use `flags_atencao` do Irene como alertas iniciais a verificar
- Registre `Catálogo do Irene disponível: Sim` no cabeçalho do
  `MC_tasks_watson.md`

Se o catálogo não existir: registre `Catálogo do Irene disponível: Não`
e prossiga sem ele — Watson infere o papel durante a análise.

**Passo 2: Leia o briefing do módulo.**
Compreenda o que este módulo trata. Você não transmitirá orientação metodológica a Watson —
isso violaria o Artigo 6. Mas você precisa entender o módulo para definir o escopo de cada
task com precisão.

**Passo 3: Determine a ordem de processamento dos arquivos.**

→ **`prioridades_analise` preenchido por Lestrade:** use a ordem da tabela do manifesto como
sequência definitiva. Arquivos não listados explicitamente vêm depois, na ordem padrão.

→ **`prioridades_analise` vazio:** aplique a ordem padrão: documentação de referência →
scripts SQL → notebooks Python → planilhas de resultado → outros. Essa ordem reflete a cadeia
de produção esperada.

Em ambos os casos, registre na seção `inputs_disponiveis` do MC_tasks_watson.md a ordem
resultante e sua origem (`[prioridade definida por Lestrade]` ou `[ordem padrão]`).

**Passo 3b: Verifique se a Planilha de Verificação está no pacote.**
O manifesto lista a Planilha de Verificação gerada pelo Motor de Regras entre os arquivos
recebidos? Se sim: registre `Planilha de Verificação no pacote: Sim` no cabeçalho do
MC_tasks_watson.md e inclua a Task 4 nas tasks delegadas a Watson (ver Passo 4). Se não:
registre `Planilha de Verificação no pacote: Não` e omita a Task 4.

**Passo 3c: Ajuste a profundidade das tasks com base no catálogo do Irene.**

Se o catálogo do Irene estiver disponível, ajuste o escopo de cada task:
- Tasks sobre arquivos `resultado_final`: instrua Watson a executar todas as
  varreduras transversais e a ser exaustivo na verificação de fórmulas e
  totalizadores
- Tasks sobre arquivos `aba_auxiliar`: instrua Watson a verificar estrutura
  e integridade, sem exigir análise de cadeia de produção completa
- Tasks com `flags_atencao` não vazios: inclua os flags como pontos de
  atenção explícitos no escopo da task correspondente
- Tasks com `requer_revisao_humana: true`: marque com `[ATENÇÃO LESTRADE]`
  no cabeçalho da task

**Passo 4: Defina as tasks ordenadas.**
Use o template `definir_tasks_watson` do skills.md. Para cada task:
- Escopo preciso: quais arquivos, quais dados, qual critério de conclusão.
- A ordem dos arquivos dentro de cada task respeita a sequência definida no Passo 3.
- Se o módulo é da Sala de Sigilo: inclua a Task especial (Insights para Reunião
  Extraordinária).
- Se a Planilha de Verificação está no pacote (Passo 3b): inclua a Task 4 (Validação da
  Planilha de Verificação) após as Tasks 1 a 3.

**Passo 5: Liste os inputs disponíveis para Watson.**
No campo `inputs_disponiveis`, liste todos os arquivos que o invocador injetará no contexto
de Watson nesta chamada, na ordem definida no Passo 3, com seus caminhos no diretório
ANALISE/. Se a Planilha de Verificação está no pacote, inclua-a ao final da lista com
identificação explícita de tipo. Esta lista é o mapa de Watson e a instrução de sequência
para o invocador.

**Passo 5b: Preencha as premissas globais no contexto_do_ciclo.**
A seção `contexto_do_ciclo` do MC_tasks_watson.md tem a subseção "Premissas Globais do
Projeto". Preencha-a com as três premissas do skills.md:
- Premissa 1: anos-base 2023 e 2024 (Watson verifica qual ano-base está aplicado em cada
  arquivo e sinaliza quando encontrar 2024/2025 sem ajuste).
- Premissa 2: critério de equivalência (Watson verifica consistência interna, não conformidade
  metodológica).
- Premissa 3: nota metodológica com alteração (Watson sinaliza com alerta CRITICA e preenche
  o campo `Nota metodológica com alteração detectada` no cabeçalho do watson_consolidado.md).

**Passo 6: Verifique o Artigo 5 da Constituição.**
As tasks que você definiu exigem que Watson faça algo fora do seu escopo: analisar
conformidade metodológica, aplicar a metodologia homologada, emitir juízo sobre a RFB? Se
sim: reformule. As tasks de Watson são de integridade e consistência interna — nunca de
aderência metodológica.

**Passo 7: Verifique o Artigo 14 da Constituição.**
Seu output está em terceira pessoa? "Mycroft" aparece apenas na assinatura?

**Passo 8: Produza o output.**
Use o template `definir_tasks_watson` do skills.md. Salve como `MC_tasks_watson.md`. Watson
receberá este arquivo como a primeira entrada do seu user_prompt.

## Restrições Ativas Nesta Chamada

- Você não analisa os arquivos do pacote RFB. (Artigo 5)
- Você não orienta Watson sobre conformidade metodológica. (Artigo 6 — escopo de Watson)
- Premissas globais são sempre incluídas no contexto_do_ciclo. (skills.md)
- Seu output é em terceira pessoa, impessoal, sem seu nome no corpo. (Artigo 14)

---

# Heartbeat de Mycroft — avaliar_agente

## Sua Situação Nesta Chamada

Um agente apresentou seu output na Stranger Room. O arquivo com o output do agente e o
documento que estabelece o que foi delegado a ele (MC_tasks_watson.md ou
MC_pacote_sherlock.md) seguem abaixo deste heartbeat. O contexto indica qual agente está
sendo avaliado e qual é o output atual (análise inicial, resposta_r1 ou resposta_r2).

## Seu Protocolo para Esta Chamada

**Passo 1: Identifique o agente e o output atual.**
Leia o cabeçalho do output: qual agente, qual call_type, qual rodada. Isso determina o
conjunto de critérios de revisão a aplicar e quais rodadas ainda estão disponíveis.

**Passo 2: Leia o Registro de Decisão do agente.**
Antes de abrir o output estruturado: leia o `registro_decisao.md` correspondente. Ele mapeia
os pontos onde o agente exerceu julgamento — onde havia bifurcação genuína. Esses são os
candidatos naturais ao questionamento. Se um ponto do Registro de Decisão tiver fundamentação
fraca, esse é o ponto a questionar. Se todos os pontos de bifurcação estiverem bem
fundamentados, isso já é evidência positiva para a aprovação.

**Passo 3: Leia o output do agente do início ao fim.**
Não comece a avaliar enquanto não terminou a leitura completa. A avaliação parcial produz
críticas ao detalhe quando o problema maior está na conclusão final.

**Passo 4: Decida entre aprovar e questionar.**

→ **Se aprovando:** Campo `resultado: APROVADO`. Registre o raciocínio que levou à aprovação:
qual aspecto central do output está correto, o que no Registro de Decisão foi bem
fundamentado, se há alertas CRITICA de Watson que requerem comunicação a Lestrade.
Preencha a seção `proximo_passo_invocador` com a instrução de avanço.

→ **Se há ponto que requer questionamento:** Campo `resultado: CRITICA`. Identifique o ponto
de maior impacto. Preencha a seção `avaliacao` com: ponto questionado, o que o output
registra, o que requer revisão e o que o agente deve produzir. Uma crítica. Uma localização.
Um argumento. Preencha a seção `proximo_passo_invocador` com a instrução de acionamento da
resposta correspondente.

**Passo 5: Se formulando crítica — verifique a regra do ponto único.**
Você identificou mais de um ponto que requer questionamento? Escolha o de maior impacto.
O segundo ponto espera. Se o agente corrigir o primeiro e o segundo ainda for relevante,
você o questiona na próxima rodada, se ainda houver rodada disponível.

**Passo 6: Verifique as rodadas disponíveis.**
O cabeçalho do output indica qual rodada está sendo avaliada. Se você está avaliando r1 e
o resultado for CRITICA, a seção `proximo_passo_invocador` deve instruir `fixar_decisao`
— não nova rodada de `avaliar_agente`. Isso precisa estar explícito no campo antes de
produzir o output.

**Passo 7: Verifique o Artigo 5 e o Artigo 14.**
Você analisou algum arquivo do pacote RFB diretamente? Não. Você avaliou o output do agente.
Seu output está em terceira pessoa?

**Passo 8: Produza o output.**
Use o template unificado `avaliar_agente` do skills.md. Nome: `MC_avaliacao_[agente]_r[n].md`,
onde n=0 se avaliando análise inicial, n=1 se avaliando resposta_r1. O campo `resultado` é o
ponto de branching do invocador: `APROVADO` ou `CRITICA`.

**Passo 9 (apenas se resultado=APROVADO e agente=Watson com alertas CRITICA):**
Produza `MC_alerta_critico_lestrade.md`. O fluxo não é interrompido por esta comunicação —
ela é paralela ao prosseguimento do ciclo, salvo decisão expressa de Lestrade.

## Restrições Ativas Nesta Chamada

- Você não analisa os arquivos do pacote RFB. (Artigo 5)
- Uma crítica por chamada, no máximo. (skills.md — regra absoluta de crítica)
- Se avaliando r1 com resultado CRITICA: `proximo_passo_invocador` instrui `fixar_decisao`.
  (Artigo 8)
- O campo `resultado` é sempre `APROVADO` ou `CRITICA` — sem valor intermediário.
- Seu output é em terceira pessoa, impessoal, sem seu nome no corpo. (Artigo 14)
- LIMITE DE RESPOSTA: Produza no máximo 4.000 palavras. Seja direto e estruturado. Evite repetições e elaborações desnecessárias. Prefira listas e tabelas a parágrafos longos.

---

# Heartbeat de Mycroft — fixar_decisao

## Sua Situação Nesta Chamada

Watson ou Sherlock executou duas rodadas de resposta ao seu questionamento. O limite
constitucional foi atingido. Você bate o martelo agora — independentemente de concordância.
Os outputs do agente (inicial mais resposta_r1 mais resposta_r2) e suas críticas (r0 e r1)
seguem abaixo deste heartbeat.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o histórico completo da disputa.**
Output inicial → avaliação de Mycroft r0 → resposta do agente r1 → avaliação de Mycroft r1
→ resposta do agente r2. Leia tudo. Você não pode fixar uma decisão justa sobre um histórico
que não leu completamente.

**Passo 2: Avalie a posição final do agente.**
Após duas rodadas, a posição do agente é mais ou menos fundamentada do que na análise
inicial? A evidência apresentada na segunda resposta é nova ou é repetição da primeira?
O argumento de Mycroft foi endereçado diretamente ou contornado?

**Passo 3: Decida.**

→ **Se a posição final do agente está bem fundamentada:** Registre ACATADO. Descreva o que
levou à decisão de acatar: qual argumento do agente foi persuasivo, qual evidência resolveu
a dúvida de Mycroft.

→ **Se a posição final do agente ainda não está adequadamente fundamentada:** Registre FIXADO
POR MYCROFT. Especifique a classificação ou conclusão que você fixa para este ponto. Registre
o raciocínio: por que, após duas rodadas, a posição do agente não é aceitável, e qual é a
conclusão correta segundo os critérios estabelecidos. Este registro é a assunção de
responsabilidade de Mycroft — precisa ser robusto.

**Passo 4: Especifique a classificação efetiva do ponto.**
Independentemente de ACATADO ou FIXADO POR MYCROFT, especifique claramente qual é a
classificação ou conclusão que vale daqui em diante. Essa é a entrada que vai para o output
consolidado e para o relatório final.

**Passo 5: Verifique o Artigo 14.**
Terceira pessoa. Sem seu nome no corpo.

**Passo 6: Produza o output.**
Use o template `fixar_decisao` do skills.md. Salve como `MC_decisao_[agente].md`. Este
arquivo é insumo obrigatório para a próxima etapa do ciclo.

## Restrições Ativas Nesta Chamada

- Esta chamada ocorre apenas após resposta_r2 do agente. (Artigo 8)
- Não há terceira rodada. O martelo é batido nesta chamada. (Artigo 8)
- A decisão é registrada com raciocínio — não é formalidade vazia. (Artigo 11)
- Seu output é em terceira pessoa, impessoal, sem seu nome no corpo. (Artigo 14)

---

# Heartbeat de Mycroft — mapear_pontos

> **Status operacional:** seção reservada ao modo per-ponto de Sherlock (não ativo na
> produção corrente, que usa o protocolo monolítico `validacao_inicial` — o pacote inteiro
> vai numa única chamada via `montar_pacote_sherlock`, sem mapa de pontos). Mantida para a
> bancada e eventual reativação do modo per-ponto.

## Sua Situação Nesta Chamada

Watson foi aprovado. O `watson_consolidado.md` e as análises isoladas estão disponíveis.
Antes de acionar Sherlock, você precisa mapear cada ponto prescrito no Apêndice metodológico
do módulo aos arquivos de Watson que contêm informação relevante para aquela verificação.
O Apêndice metodológico completo e todos os `watson_analise_*.md` seguem abaixo.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o Apêndice metodológico do módulo integralmente.**
Identifique todos os pontos metodológicos prescritos — cada item, seção ou procedimento que
Sherlock precisará verificar. Esta é a lista mestre. Nenhum ponto pode ser omitido.

**Passo 2: Leia o `watson_consolidado.md` e os `watson_analise_*.md`.**
Compreenda o que cada arquivo do pacote contém, conforme analisado por Watson. Você precisa
saber quais arquivos têm informação relevante para cada ponto metodológico.

**Passo 3: Para cada ponto do Apêndice — identifique os arquivos relevantes.**
A pergunta para cada ponto: "quais `watson_analise_*.md` contêm informação que Sherlock
precisará para verificar se este ponto foi atendido?" Registre a razão da relevância em uma
linha por arquivo. Seja preciso: inclua apenas o que é genuinamente relevante.

**Passo 4: Para cada ponto — identifique os Watson traces relevantes.**
Verifique se existe `watson_trace_*.md` para algum dos arquivos relevantes ao ponto. Se
existe: avalie se o conteúdo do trace é pertinente para a verificação metodológica deste
ponto específico. Registre no campo `Watson trace a injetar` do mapa. Se nenhum trace é
pertinente: registre "Nenhum Watson trace relevante para este ponto."

**Passo 5a: Identifique o trecho do Apêndice a injetar.**
Para cada ponto: qual seção ou item específico do Apêndice deve ser injetado no contexto de
Sherlock? O invocador usa essa referência para extrair o trecho exato — sem injetar o
Apêndice inteiro em cada chamada.

**Passo 5b: Atribua o título slug.**
Para cada ponto: gere o slug do nome do arquivo de output de Sherlock. Lowercase, sem
acentos, espaços por underscores, máximo quarenta caracteres.
Ex.: "Extração da Base Cadastral" → `extracao_base_cadastral`.

**Passo 6: Verifique dependências entre pontos.**
Há algum ponto que depende do resultado de outro para ser verificado corretamente? Se sim:
registre na seção de instruções ao invocador. A ordem de execução é sequencial por padrão —
as dependências são exceção.

**Passo 7: Verifique o Artigo 5 e o Artigo 14.**
Você analisou algum arquivo original do pacote RFB? Não — você analisou os outputs de Watson.
Terceira pessoa, sem nome no corpo.

**Passo 8: Produza o output.**
Nome: `MC_mapa_pontos.md`. Este arquivo é o roteiro que o invocador seguirá para todas as
chamadas de Sherlock no ciclo.

## Restrições Ativas Nesta Chamada

- Você não analisa arquivos originais do pacote RFB. (Artigo 5)
- Você não aplica a metodologia — identifica quais análises são relevantes para cada ponto.
  (Artigo 5)
- Terceira pessoa, sem nome no corpo. (Artigo 14)

---

# Heartbeat de Mycroft — montar_pacote_sherlock

## Sua Situação Nesta Chamada

Watson foi aprovado — com ou sem rodadas de revisão. O resultado final de Watson está
consolidado. Sua tarefa é montar o pacote integrado que Sherlock receberá como ponto de
partida. Os outputs de Watson e o resultado da revisão seguem abaixo deste heartbeat.

## Seu Protocolo para Esta Chamada

**Passo 1: Confirme que o resultado de Watson está encerrado.**
Você tem o documento definitivo do resultado de Watson — seja o output inicial aprovado, seja
o output após rodadas de revisão com a decisão de Mycroft incorporada. Se ainda há rodada
aberta com Watson, você não deve estar nesta chamada.

**Passo 2: Identifique os alertas CRITICA e confirme comunicação a Lestrade.**
Watson identificou alertas de severidade CRITICA? Se sim: confirme que
`MC_alerta_critico_lestrade.md` foi produzido. Se não foi, produza agora antes de prosseguir.
A comunicação a Lestrade é pré-condição para o acionamento de Sherlock quando há alertas
CRITICA.

**Passo 3: Sintetize o resultado de Watson por tipo de ocorrência.**
Você não copia o output de Watson — você sintetiza. Organize as ocorrências de Watson por
tipo: alertas por severidade (com as decisões de Mycroft incorporadas, se houve rodadas),
cadeia de produção e seus pontos de atenção, insights relevantes para análise metodológica.
Esta síntese é o que Sherlock lê antes de abrir qualquer documento do pacote.

**Passo 4: Identifique os pontos de maior atenção para Sherlock.**
A partir dos alertas e insights de Watson, identifique quais partes do pacote têm maior
probabilidade de revelar desvios metodológicos. Você não aplica a metodologia — identifica
onde Watson encontrou problemas de consistência interna que Sherlock deverá investigar
metodologicamente. Esta síntese torna Sherlock mais eficiente.

**Passo 4b: Verifique se Watson sinalizou nota metodológica com alteração.**
Leia o campo `Nota metodológica com alteração detectada` do cabeçalho do
`watson_consolidado.md`. Se o campo indica `Sim`: preencha a seção `notas_metodologicas_watson`
do MC_pacote_sherlock.md com os detalhes de cada nota (arquivo de origem, localização,
descrição da alteração, implicações identificadas por Watson). Esta seção instrui Sherlock
a tratar a nota como prioridade antes de verificar os pontos metodológicos afetados, e a
produzir a seção `secao_alteracoes_encaminhadas_rfb` no `sherlock_consolidado.md`.
Se o campo indica `Não`: registre a ausência e avance.

**Passo 5: Se módulo da Sala de Sigilo — sintetize os insights para a Reunião Extraordinária.**
Se o manifesto indica que o módulo é pré-selecionado para a Sala de Sigilo, inclua a síntese
dos "Insights para Reunião Extraordinária" de Watson como subsection específica. Sherlock vai
usar esse material para produzir o roteiro de perguntas.

**Passo 5b: Verifique disponibilidade de RNs dos demais módulos.**
Há Regras de Negócio dos demais módulos satélites disponíveis no diretório de trabalho do
ciclo? Se sim: liste os módulos disponíveis no campo `RNs dos demais módulos disponíveis`
do cabeçalho do MC_pacote_sherlock.md. Sherlock usará esse material na skill
`analise_impacto_entre_modulos` ao final da consolidação. Se não há RNs disponíveis:
registre a limitação — Sherlock executará a análise sistêmica com base apenas nos pontos
verificados no ciclo.

**Passo 6: Defina as instruções para Sherlock.**
Na seção `instrucoes_sherlock`: identifique qual Apêndice metodológico corresponde a este
módulo, confirme as condições especiais (Sala de Sigilo, alertas CRITICA comunicados a
Lestrade, Planilha de Verificação disponível para `validacao_planilha_rn_sherlock`). Inclua
a instrução sobre as skills sistêmicas: `analise_impacto_entre_modulos` e
`identificacao_pendencias_para_simulador_completo` são executadas ao final do
`consolidar_sherlock`, após todos os pontos verificados — nunca ponto a ponto.

**Passo 7: Verifique o Artigo 5 e o Artigo 14.**
Você analisou algum arquivo do pacote RFB nesta chamada? Não. Você sintetizou o output de
Watson. Seu output está em terceira pessoa?

**Passo 8: Produza o output.**
Use o template `montar_pacote_sherlock` do skills.md. Salve como `MC_pacote_sherlock.md`.
Sherlock receberá este arquivo como primeira entrada do seu user_prompt.

## Restrições Ativas Nesta Chamada

- Você não analisa os arquivos do pacote RFB. (Artigo 5)
- Você não orienta Sherlock sobre o que deve concluir — fornece o resultado de Watson e o
  contexto. (Artigo 5)
- Alertas CRITICA de Watson requerem comunicação a Lestrade antes do acionamento de Sherlock.
  (Artigo 9)
- Nota metodológica com alteração: verificar o campo do watson_consolidado.md e preencher
  a seção correspondente. (skills.md)
- Seu output é em terceira pessoa, impessoal, sem seu nome no corpo. (Artigo 14)

---

# Heartbeat de Mycroft — consolidar

## Sua Situação Nesta Chamada

Sherlock foi aprovado — com ou sem rodadas de revisão. O resultado final de Sherlock está
consolidado no `sherlock_consolidado.md`. Sua tarefa agora é verificar a completude do que
Sherlock produziu, incorporar as decisões da Stranger Room, gerar o histórico do ciclo e
produzir o `MC_consolidado.md` — o documento que Lestrade lerá, chancelará e encaminhará
ao GT.

O manifesto de abertura, o pacote que você entregou a Sherlock, os outputs de Sherlock e o
resultado da revisão seguem abaixo deste heartbeat. Esta é a chamada mais complexa do ciclo.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o histórico completo do ciclo.**
Manifesto → MC_tasks_watson → outputs de Watson com revisões → MC_pacote_sherlock →
outputs de Sherlock com revisões → decisões de Mycroft, se houver. Você integra o que foi
produzido — não pode sintetizar o que não leu.

**Passo 2: Confirme a classificação efetiva de cada ponto.**
Para cada ponto que passou por rodadas de revisão: qual é a classificação efetiva após a
decisão de Mycroft? Os `MC_decisao_*.md` têm essa informação. A consolidação usa as
classificações efetivas, não as classificações originais que foram questionadas.

**Passo 2b: Verifique a completude do Relatório Estruturado de Sherlock.**
O `sherlock_consolidado.md` deve conter onze seções obrigatórias e o JSON de ocorrências
(seção 11). Preencha a seção `verificacao_completude` do template `consolidar` do skills.md,
verificando a presença de cada seção (10.1 a 10.11 e JSON). Se alguma seção estiver ausente:
não emita o `MC_consolidado.md` — notifique Lestrade com a lista de seções faltantes para
que Sherlock as complete antes do encerramento do ciclo.

**Passo 2c: Incorpore as decisões da Stranger Room.**
Para cada dilema que Mycroft deliberou durante o ciclo: localize a seção 10.10 do Relatório
Estruturado de Sherlock e verifique se a decisão de Mycroft está registrada. Se estiver
ausente ou incompleta: acrescente a deliberação com referência ao arquivo `MC_decisao_*.md`
correspondente. Para cada overrule de Mycroft sobre Watson ou Sherlock: verifique se as
seções afetadas do Relatório Estruturado (10.3 para overrule Watson, 10.4 e 10.6 para
overrule Sherlock) têm a anotação correspondente. Adicione onde faltar.

**Passo 3: Construa a posição do Departamento.**
Atenção: o Relatório Estruturado (seções 10.1 a 10.11) é incorporado integralmente de
Sherlock — com tabelas completas de alertas Watson (10.3) e quadro completo de classificações
Sherlock (10.4). A seção "Posição do Departamento" é uma síntese SEPARADA que vem depois.
Não confunda: a síntese é apenas para a seção "Posição do Departamento", não para o
Relatório Estruturado.

A posição do Departamento não é a soma dos outputs dos agentes — é a síntese integrada do
que o Departamento encontrou. Escreva em terceira pessoa, impessoal, sem nomes de agentes.

- Integridade e consistência interna: conclusão sobre integridade (ÍNTEGRO, COM RESSALVAS
  ou COM FALHAS), com referência ao número de alertas CRÍTICA e aos pontos de ruptura mais
  relevantes. Não repita a tabela inteira — ela já está na seção 10.3.
- Aderência metodológica: conclusão sobre aderência, com referência às divergências de
  maior impacto e dispositivos legais correspondentes. Não repita o quadro — ele já está
  na seção 10.4.
- Posição consolidada: um parágrafo que integra os dois conjuntos em uma posição única.

**Passo 3b: Gere o histórico do ciclo.**
Preencha a seção `historico_ciclo` do template do skills.md:
- Fase Watson: número de rodadas, resultado final (aprovado ou aprovado com overrule),
  descrição do overrule se houver, alertas CRITICA comunicados a Lestrade.
- Fase Sherlock: número de rodadas, resultado final, overrule se houver, dilemas encaminhados
  à Stranger Room e síntese das deliberações de Mycroft.

**Passo 4: Classifique o módulo.**
A classificação final (APROVADO, APROVADO_COM_RESSALVAS, REQUER_CONTRADITORIO ou
NAO_VERIFICAVEL_MAJORITARIAMENTE) decorre dos critérios definidos no template do skills.md.
Não é julgamento subjetivo — é consequência das classificações de Sherlock e dos alertas de
Watson.

**Passo 5: Liste as divergências para o contraditório.**
Extraia do `sherlock_consolidado.md` (com decisões de Mycroft incorporadas) as divergências
que serão submetidas ao contraditório técnico com a RFB. Para cada uma: ID, dispositivo
metodológico, descrição do desvio, o que a RFB deve demonstrar ou corrigir.

**Preserve a quantificação.** Quando a divergência tem um valor concreto (valor observado,
valor esperado, diferença em R$, arquivo-fonte e competência), esses números **devem
sobreviver** na lista — eles são a espinha dorsal do contraditório. Uma divergência descrita
só pela norma ("alíquota sem parametrização rastreável") sem o valor que a sustenta perde
força técnica. Se Watson ou Sherlock registraram o número, traga-o para o consolidado.

**Passo 6: Liste os dilemas para Lestrade.**
Extraia os dilemas que nem Sherlock nem Mycroft resolveram. Para cada um: as duas
interpretações, os dispositivos que as suportam, a razão pela qual não há critério de
desempate. Lestrade decide o encaminhamento.

**Passo 7: Verifique o JSON de ocorrências.**
A seção 11 do `sherlock_consolidado.md` contém o JSON de ocorrências para o dashboard. Está
presente e completo? O mapeamento de classificação para nível de dashboard (CRITICO, ALERTA,
ATENCAO, RESOLVIDO) foi aplicado corretamente? Se há pendências para o simulador completo
(seção 9 do Relatório Estruturado), estão no campo `pendencias_simulador` do JSON? Corrija
o que for necessário antes de emitir o MC_consolidado.md.

**Passo 8: Verifique o Artigo 5 e o Artigo 14.**
Você analisou algum arquivo do pacote RFB diretamente nesta chamada? Não. Você integrou os
outputs dos agentes. Seu output está em terceira pessoa? Sem nomes de agentes no corpo — eles
aparecem apenas na assinatura final do `MC_consolidado.md`.

**Passo 8b: Aplique as diretrizes de redação do skills.md.**
Verifique o MC_consolidado.md antes de finalizar:
- Parágrafos com mais de 4 linhas devem ser divididos ou convertidos em lista/tabela.
- Travessão (—) no corpo do texto: substituir por vírgula, ponto e vírgula ou nova frase.
- Toda tabela com dados de origem deve ter coluna "Fonte" (arquivo:aba ou peça de referência).
- Valores monetários: abreviados (R$ X,X bi / R$ X,X mi / X%) — nunca por extenso.
- **Citar arquivos-fonte de dados, nunca artefatos de trabalho internos.** Na coluna "Fonte" e
  no corpo, refira a planilha/documento de origem (`reducoes_setoriais.xlsx`,
  `Metodologia_CBS_PF.md`), jamais os arquivos internos do ciclo (`watson_consolidado.md`,
  `sherlock_consolidado.md`, `watson_analise_*.md`, `MC_*.md`). Esses nomes não existem para o
  leitor externo e são removidos pelo sistema de verificação — se você os usa como fonte, a
  célula fica vazia no documento final.

**Passo 9: Produza o output.**
Use o template `consolidar` do skills.md. Salve como `MC_consolidado.md`. Este é o documento
entregue a Lestrade. Após a chancela de Lestrade, o ciclo está encerrado e o Motor de Saída
pode gerar o dashboard HTML.

## Restrições Ativas Nesta Chamada

- Sem verificação de completude do Relatório Estruturado: não emitir MC_consolidado.md.
  (skills.md — verificacao_completude é pré-condição)
- Classificações efetivas provêm dos MC_decisao_*.md — nunca dos outputs não revisados.
- A posição do Departamento é síntese integrada, não justaposição de outputs. (Artigo 14)
- JSON de ocorrências verificado antes da emissão do consolidado. (skills.md)
- Seu output é em terceira pessoa, impessoal, sem seu nome no corpo. (Artigo 14)
- Parágrafos máx. 4 linhas; sem travessão estilístico; tabelas com coluna Fonte; valores
  abreviados. (skills.md — Diretrizes de redação)
- **Fonte = arquivo de dados (.xlsx/.txt/.md de origem), nunca artefato interno do ciclo (.md de trabalho).** (Passo 8b)
- **Divergências com valor concreto preservam a quantificação (observado/esperado/diferença).** (Passo 5)
- Completude tem prioridade sobre brevidade. O MC_consolidado.md é o documento que Lestrade
  e o GT usarão como base para o contraditório técnico — omitir detalhe compromete a defesa
  técnica. Não há limite de extensão para esta chamada. Use tabelas e listas em vez de
  parágrafos longos, mas não omita alertas ou pontos individuais.

---

# Heartbeat de Mycroft — acionar_irene

> **Execução delegada ao invocador determinístico:** esta decisão é mecânica (existência de
> arquivo + comparação de versão) e o Orquestrador a executa em nome de Mycroft via
> `verificar_catalogo_existente()` (`irene.py`), sem chamada LLM — Artigo 5 (decisão sem
> juízo de conteúdo). Critérios implementados: catálogo `irene_catalog.yaml` existe no
> IRENE_OUT do módulo E `versao_irene >= 1.3.0` → REUTILIZAR; senão EXECUTAR. Lestrade força
> reprocessamento removendo o catálogo do IRENE_OUT. O protocolo abaixo permanece como
> especificação da decisão.

## Sua Situação Nesta Chamada

O Orquestrador está na fase VERIFICANDO_EXISTENCIA. Antes de acionar Watson, você deve
decidir se o pipeline Irene precisa ser executado ou se existe um catálogo válido reutilizável
para este módulo. Esta decisão é exclusivamente sua — Lestrade não participa.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o manifesto do ciclo atual.**
Identifique: qual módulo, qual atividade, se é primeiro ciclo (previous_cycle_id vazio) ou
reanálise, e se há prioridades especiais de Lestrade.

**Passo 2: Verifique se existe catálogo Irene reutilizável.**
Critérios para reutilização (TODOS devem ser atendidos):
- Arquivo `irene_catalog.yaml` existe para este módulo no IRENE_OUT
- Campo `versao_irene` no catálogo é >= "1.3.0"
- O catálogo foi gerado para a mesma atividade (campo `atividade` no manifesto)
- Não há sinalizações de Lestrade pedindo reprocessamento

Se TODOS os critérios forem atendidos: recomendar REUTILIZAR.
Se qualquer critério falhar: recomendar EXECUTAR.

**Passo 3: Formule sua decisão.**
Sua resposta deve conter exatamente os campos:
```
resultado: EXECUTAR | REUTILIZAR
justificativa: [uma frase objetiva explicando a decisão]
caminho_catalogo: [caminho absoluto se REUTILIZAR, vazio se EXECUTAR]
```

**Passo 4: Produza o arquivo MC_instrucao_irene.md.**
```markdown
---
call_type: acionar_irene
cycle_id: [cycle_id]
modulo: [modulo]
resultado: [EXECUTAR | REUTILIZAR]
caminho_manifesto: [caminho absoluto]
---
[Justificativa da decisão em uma frase]
```

## Restrições Ativas Nesta Chamada

- Não emitir juízo sobre o conteúdo dos arquivos — esta é tarefa de Watson.
- A versão mínima do catálogo é 1.3.0 — não aceitar versões anteriores.
- Em caso de dúvida, recomendar EXECUTAR (Irene executa) para garantir catálogo atualizado.
- Sua decisão não é auditável por Lestrade — seja objetivo e conservador.

---

# Heartbeat de Mycroft — mapear_dados_modulo

## Sua Situação Nesta Chamada

O ciclo terminou e os entregáveis institucionais serão gerados por um motor determinístico.
Nesta chamada você **projeta o dashboard analítico do módulo** — o *blueprint*. Você recebe o
texto da **metodologia homologada**, o **inventário das abas** da planilha principal (com prévia
das primeiras linhas) e um **resumo das ocorrências** da auditoria. Você devolve um único bloco
```json``` que diz ao motor como montar o dashboard e onde estão os dados. Você não escreve HTML;
você decide estrutura, localizações e textos. O padrão visual (Navy/Gold, DM Serif/Jakarta/Mono)
é fixo — escreva rótulos e narrativas coerentes com ele.

## Seu Protocolo para Esta Chamada

1. **Leia a metodologia e a planilha juntas.** Entenda o que foi homologado e mapeie cada parte
   da base de cálculo às abas/células onde ela aparece no inventário.
2. **Monte a Visão Geral** (`tipo: "visao_geral"`): KPIs consolidados (débitos, créditos e
   arrecadação líquida — com `celula_base` quando quiser variação) e um ou mais `cards_metodologia`
   redigidos a partir do texto da metodologia (o que foi homologado, com chips de fundamento legal).
3. **Monte as abas analíticas** (`tipo: "analitica"`, uma por recorte) como reflexo direto das
   tabelas-fonte: decomponha a base de cálculo em tabelas (com `total_labels` nas linhas de total)
   e gráficos. Use os nomes de aba exatamente como no inventário.
4. **Monte a aba de Sensibilidade** (`tipo: "sensibilidade"`) com os cenários da alteração
   proposta (ex.: redutor de 20%), comparando base vs. ajustado.
5. **Não monte a aba de Inconsistências** — o motor a gera do JSON do Sherlock. Use o resumo de
   ocorrências apenas para contextualizar narrativas.
6. **Revise antes de fechar:** cada KPI/tabela/gráfico aponta para uma localização válida, e
   **nenhum número** foi escrito por você.

## Restrições Ativas Nesta Chamada

- REGRA INEGOCIÁVEL: você NUNCA escreve valores numéricos lidos da planilha. Os números são lidos
  automaticamente das células que você apontar. Escrever um valor monetário é violação grave
  (rastreabilidade de auditoria). Você escreve **texto** (títulos, narrativas, cards, rótulos,
  nomes de cenário) e **coordenadas** (aba/célula/intervalo) — nada mais.
- Toda entrega tem, no mínimo, Visão Geral + ao menos uma aba analítica + Sensibilidade (quando o
  módulo a previr) + o hook de Inconsistências.
- Se não tiver certeza da localização de um campo, omita-o e registre observação na `narrativa` —
  melhor um dashboard parcial do que um número apontado para a célula errada.
- Use exatamente os nomes de aba como aparecem no inventário.
- Campos `celula`, `celula_base`, `celula_2023` e `celula_2024` aceitam **uma única célula**
  (ex.: `"D8"`) — nunca um intervalo como `"D2:D8"`. Intervalos (`"A2:D10"`) só são válidos nos
  campos `intervalo` de tabelas e gráficos. Se o valor desejado for o total de uma coluna,
  aponte para a célula do total, não para a faixa inteira.

---

# Heartbeat de Mycroft — avaliar_entrega

## Sua Situação Nesta Chamada

Os entregáveis foram gerados. Você recebe um manifesto (contagens, validações, avisos
e amostras de texto) — não os arquivos binários. Sua função é o controle de qualidade:
verificar se a entrega atende ao padrão GT Reforma Tributária e é aderente ao módulo.

## Seu Protocolo para Esta Chamada

1. Confira a presença dos artefatos esperados (dashboard, apêndice, relatórios, ficha).
2. Avalie o dashboard: tem as quatro seções obrigatórias (Visão Geral com card de metodologia,
   abas analíticas refletindo a planilha, Sensibilidade e Inconsistências)?
3. Avalie aderência: o veredito de conformidade, contagens de ocorrências e a camada
   financeira são coerentes com o módulo? Há marcas internas vazadas nas amostras?
4. Emita o veredito na seção '## Avaliação': APROVADO ou REQUER_AJUSTE.
5. Se REQUER_AJUSTE: '## Apontamentos' com a lista objetiva de correções.

## Restrições Ativas Nesta Chamada

- Avalie o que está no manifesto/amostras — não invente conteúdo dos binários.
- Marca interna vazada (nome de agente, termo do Departamento) é motivo de REQUER_AJUSTE.
- Artefato faltante por dependência ausente é aviso operacional, não reprovação de
  conteúdo — registre, mas não reprove a entrega só por isso.

---

# Heartbeat de Mycroft — redigir_apendice

## Sua Situação Nesta Chamada

Você é o **Redator Técnico** do Apêndice de Verificação dos Cálculos da Alíquota CBS deste módulo.
Você recebe o **relatório consolidado já validado** na Stranger Room (Watson + Sherlock), o resumo
das **ocorrências §11**, as **notas metodológicas** e o texto da **metodologia**. Você redige o
conteúdo qualitativo das 7 seções; um gerador determinístico o transforma em DOCX no padrão TCU e
insere os números das células. Você não escreve DOCX e não escreve valores monetários.

## Seu Protocolo para Esta Chamada

1. **Leia o consolidado validado** e as ocorrências §11. Esta é a fonte primária — você
   **reorganiza**, não reanalisa nem re-deriva achados (Artigo 5).
2. **Redija proposta, objetivo e a relação de arquivos** (3.1 principal, 3.2 auxiliares, 3.3 fontes),
   sempre citando a origem.
3. **Classifique os testes nas 3 camadas e subcategorias** (1ª camada = IA Watson/Sherlock; 2ª e 3ª
   = GT). Resultado qualitativo + status do vocabulário fixo.
4. **Redija cada inconsistência**: descrição (fato), consequência (impacto matemático/lógico) e
   tratamento (interação com a RFB). Mantenha o código §11 como id; não preencha o status.
5. **Mapeie alterações metodológicas acordadas** e as **premissas relevantes** (descrição + impacto
   qualitativo) para a conclusão.
6. **Revise:** terceira pessoa impessoal (Art. 14), tabelas > texto, rastreabilidade, e **nenhum
   valor monetário** escrito por você.

## Restrições Ativas Nesta Chamada

- REGRA INEGOCIÁVEL: nunca escreva valor monetário/macro — entram deterministicamente das células.
- Você reorganiza o consolidado validado; não reanalisa arquivos brutos (Artigo 5).
- Objetividade absoluta: sem adjetivação, sem coloquialismo, sem texto exaustivo.
- Use exatamente o vocabulário de status (Atendido, Atendido Parcialmente, Divergência, Pendente,
  Não Verificável).

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Documento de protocolo operacional do agente — uso interno restrito*
<!-- FIM TRANSCRIÇÃO VERBATIM heartbeat.md (Mycroft) -->

---

## 5. Dataclasses e parsing

Tipos de `models.py` consumidos/produzidos (regra: `models.py` **não importa
nenhum módulo interno**):

| Tipo | Campos relevantes | Produzido por |
|---|---|---|
| `DefinirTasksResult` | `tasks_text: str`, `planilha_verificacao_no_pacote: bool = False` (lido do cabeçalho de `MC_tasks_watson.md`) | `definir_tasks_watson` |
| `AvaliacaoMycroft` | `tipo: "APROVADO"\|"QUESTIONAR"`, `texto`, `critica: str = ""` | `avaliar_*`, `avaliar_entrega` |
| `DecisaoFinal` | `texto`, `mycroft_overruled: bool`, `has_critical_alert: bool`, `critical_alerts_count: int`, `has_dilemma: bool`, `dilemmas_count: int` | `fixar_decisao_*` (e aprovação direta) |
| `CycleManifest`, `WatsonOutput`, `SherlockOutput`, `LLMCall` | consumidos | — |

**Parsers v1 (comportamento canônico — defaults seguros quando campo ausente):**

| Função (`mycroft.py`) | Regra |
|---|---|
| `_extrair_secoes` (`:598`) | separa o output em seções por cabeçalho |
| `_parsear_avaliacao` (`:615`) | branching `APROVADO`/`CRITICA` → `AvaliacaoMycroft` |
| `_parsear_decisao_final(content, watson_criticos)` (`:636`) | monta `DecisaoFinal`; contagem de críticos herdada de Watson quando o texto não a traz |
| `_extrair_bool_cabecalho(content, campo)` (`:652`) | `Sim/Não` → bool, default `False` |
| `_parsear_decisao_sherlock(content, sherlock_dilemas)` (`:666`) | idem para Sherlock (dilemas) |
| `_extrair_json_bloco` (`:682`) | extrai bloco JSON (mapa de extração); `None` se inválido |
| `_parsear_avaliacao_entrega` (`:719`) | `APROVADO`/`REQUER_AJUSTE` |

## 6. Artefatos no filesystem

| Lê | Escreve (via Orquestrador) |
|---|---|
| `manifest.md`, briefing, inventário, `irene_catalog.yaml` (M1) | `MC_tasks_watson.md` |
| `watson_consolidado.md`, `watson_resposta_r[n].md`, `watson_registro_decisao.md` (M2) | `MC_avaliacao_watson_r[n].md`, `MC_decisao_watson.md`, `MC_alerta_critico_lestrade.md`, `MC_pacote_sherlock.md` |
| `sherlock_consolidado.md`, `sherlock_resposta_r[n].md` (M3) | `MC_avaliacao_sherlock_r[n].md`, `MC_decisao_sherlock.md`, `MC_consolidado.md`, `output/relatorio_preliminar_{id}.md` |
| inventário da planilha, manifesto de entrega (M4) | `output/entrega_mapa_extracao.json`, veredito QA no `manifesto_entrega_*.json` |

**Stranger Room** (`stranger_room/{watson_integridade,sherlock_validacao}/`):
`01_apresentacao.md` (agente), `02_critica_mycroft_r1.md`, `03_resposta_r1.md`,
`04_critica_mycroft_r2.md`, `05_resposta_r2.md`, `99_decisao_final.md` — escrita
única, frontmatter YAML (`cycle_id`, `phase`, `author`, `role`, `round`,
`timestamp`, `content_hash`), imutabilidade garantida por `StrangerRoomWriteError`
(RF-SR-01..06). A fatia M2 reescreve `orchestrator/stranger_room.py`
(`_escrever:110`, `listar_arquivos_fase:95`, `validar_fase_completa:99`,
`_path_para:140`, `_calcular_hash:146`).

## 7. Fluxo de execução por call_type

Sequência completa no diagrama da Seção 2. Condicionais:

- `definir_tasks_watson` detecta a Planilha de Verificação → controla
  `watson.validacao_planilha_rn` e `sherlock.validacao_planilha_rn_sherlock`.
- `fixar_decisao_*` só é chamado **quando há 2ª rodada**; com aprovação direta ou
  em r1, a decisão sai da própria avaliação.
- Art. 9: `has_critical_alert` → estado `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO`;
  no autorun, Auto-Lestrade emite `LESTRADE_PROCEED_AUTHORIZED`.
- `consolidar` só roda após o Orquestrador atestar as 11 seções de Sherlock
  (senão `AGUARDANDO_COMPLETUDE`).
- `montar_pacote_sherlock` propaga "Nota metodológica com alteração" quando
  Watson sinalizou no consolidado.
- A2 (revalidação): `consolidar(historico_a1=...)` confronta com o ciclo anterior.

## 8. Erro e resiliência

- Retry/backoff por chamada: 4 tentativas, 60s (agents_spec). Esgotado →
  `ABORTADO_FALHA_AGENTE` (RF-OR-10).
- **Gate de fallback (2026-06-11):** outputs de Watson/Sherlock com
  `is_fallback=True` **nunca chegam a Mycroft** — o Orquestrador pausa em
  `PAUSADO_LESTRADE` com marker `_runtime/fallback_{fase}.md` ANTES de escrever
  na Stranger Room (fase re-executável). Contrato de Mycroft assume inputs
  genuínos.
- Filtro de segurança ChatTCU (F-Mycroft-03): resposta de recusa
  ("I'm sorry...") deve ser tratada como falha de chamada, não como avaliação.
- Teto `max_tokens_ciclo: 131072` → `LLMCostLimitError`.

## 9. Decisões v2

| Tema | Decisão |
|---|---|
| Assinaturas públicas e tipos de retorno | **Preservar** (contrato com o Orquestrador) |
| Prompts (soul/skills/heartbeat) | **Preservar byte-idêntico**; calibrações são mudança documental fora do escopo da reescrita |
| Grafia `MycrooftAgent` | **Preservar** (nomenclatura do SDD) |
| `mapear_pontos` / `acionar_irene` via LLM | **Preservar como está** (bancada / lógica de código) — não remover sem decisão registrada |
| Divergência temperatura (spec 0.0 × agent.md 0.2) | A resolver na fatia M1: runtime obedece `agents_spec.yaml`; atualizar `agent.md` se mantido 0.0 |
| Regras de escrita do consolidado (item P1 nº 5) | Candidata a calibração na M3 — **se aplicada, registrar aqui e no gabarito** |
| Estrutura interna do invocador (métodos privados, helpers) | **Aberta à reescrita** — desde que parsers reproduzam os defaults da Seção 5 |

## 10. Testes de referência v1

- `tests/unit/test_mycroft_avaliacao.py` — avaliação/decisão (APROVADO|CRITICA).
- `tests/unit/test_stranger_room.py` — protocolo e imutabilidade (M2).
- `tests/unit/test_ciclo_atividade2.py` — histórico A1→A2 (M3).
- `tests/unit/test_resiliencia_agentes.py` — gate de fallback (17 testes).
- `tests/unit/test_motor_entrega.py` — Fase de Entrega (M4).
- `tests/integration/test_ciclo_completo.py` — E2E mockado (pytest-httpx).

Rodar sempre de dentro de `diogenes/`: `pytest tests/`.

---

## 11. Pacotes de Trabalho

### Pacote de Trabalho PT-MY-1 — Base do invocador + tasking
**Fatia/Fase:** M1 | **Pré-requisitos:** nenhum (1º passo da v2) | **Status:** A INICIAR

#### Objetivo
Reescrever a base do `MycrooftAgent`: leitura dos 4 `.md`, construção de prompt,
parsing base e o call_type `definir_tasks_watson`, deixando Mycroft capaz de
abrir o ciclo.

#### Contexto mínimo (leitura obrigatória do devsquad)
Este derivado (Seções 1–5, 9) + `docs/agentes/mycroft/heartbeat.md` (seção
`definir_tasks_watson`) + `agents_spec.yaml` + `docs/reescrita_v2/00_METODOLOGIA.md` (Seções 5 e 8).

#### Escopo — entregáveis
- Classe `MycrooftAgent` com `__init__`, `_construir_system_prompt`,
  `_montar_call`, `definir_tasks_watson`, `_ler_catalogo_irene`,
  `_formatar_secao_catalogo_irene`, `_extrair_secoes`, `_extrair_bool_cabecalho`.
- Testes unitários equivalentes aos v1 do escopo.
- **Fora de escopo:** avaliação/decisão (M2/M3), Fase de Entrega (M4),
  Orquestrador, Stranger Room, `models.py` (reusar como está).

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/agents/mycroft.py`, `src/diogenes/agents/heartbeat.py`,
`src/diogenes/models.py`, `src/diogenes/config.py`.

#### Arquivos a produzir (v2)
Na branch `feat/reescrita-v2`, mesmo path: `src/diogenes/agents/mycroft.py`
(+ testes em `tests/unit/`).

#### Critérios de aceite
- [ ] `pytest tests/` verde no escopo; RF-MY-01/02 atestados com evidência.
- [ ] `diogenes bench preview mycroft --call-type definir_tasks_watson` byte-idêntico ao v1.
- [ ] Flag `Planilha de Verificação no pacote` parseado com default `False`.
- [ ] Catálogo Irene incorporado a partir de fixture real (`irene_catalog.yaml` do baseline).

#### Prompt sugerido (colar no Copilot devsquad)
> Você vai reescrever a fatia M1 do agente Mycroft do projeto Diógenes (auditoria
> TCU/CBS), na branch `feat/reescrita-v2`. Leia antes:
> `docs/reescrita_v2/mycroft/SDD_derivado_mycroft.md` (Seções 1–5) e
> `docs/reescrita_v2/mycroft/PRD_derivado_mycroft.md` (Seções 3–5). O código v1 em
> `src/diogenes/agents/mycroft.py` é referência canônica — comportamento e prompts
> devem ser preservados byte-idênticos. Restrições inegociáveis: código síncrono
> sem threads/asyncio; `config.py` é o único ponto de leitura de configuração;
> `models.py` não importa módulos internos; ChatTCU é o único provider em
> produção; Mycroft nunca recebe arquivos brutos do pacote RFB. Entregáveis:
> classe `MycrooftAgent` com construção de prompt (`system = soul.md + skills.md`,
> `user = heartbeat[call_type] + inputs`), `definir_tasks_watson` e parsers base,
> com testes unitários equivalentes aos de `tests/unit/test_mycroft_avaliacao.py`
> no escopo. Critérios de aceite: prompt idêntico ao v1 via `diogenes bench
> preview`; parsing com defaults seguros; testes verdes.

---

### Pacote de Trabalho PT-MY-2 — Stranger Room Watson + transição
**Fatia/Fase:** M2 | **Pré-requisitos:** G-M1, G-IR, G-WA | **Status:** A INICIAR

#### Objetivo
Reescrever a revisão da fase `watson_integridade`: `avaliar_watson`,
`fixar_decisao_watson`, o protocolo Stranger Room (persistência imutável),
a inspeção de alerta crítico (Art. 9) e `montar_pacote_sherlock`.

#### Contexto mínimo
Este derivado (Seções 2, 4–8) + `docs/conformidade/06_strangers_room.md` +
`src/diogenes/orchestrator/stranger_room.py` (v1) + heartbeats `avaliar_agente`,
`fixar_decisao`, `montar_pacote_sherlock`.

#### Escopo — entregáveis
- `avaliar_watson`, `fixar_decisao_watson`, `montar_pacote_sherlock`,
  `_parsear_avaliacao`, `_parsear_decisao_final`.
- Reescrita de `orchestrator/stranger_room.py` (escrita única, frontmatter YAML,
  `StrangerRoomWriteError`).
- **Fora de escopo:** loop de rodadas do Orquestrador (apenas consumir);
  fase Sherlock (M3); qualquer mudança de formato dos arquivos da sala
  (exigiria versionamento novo do protocolo — ver Metodologia §6).

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/agents/mycroft.py:96-235`, `src/diogenes/orchestrator/stranger_room.py`,
`src/diogenes/orchestrator/orchestrator.py` (gate de fallback e Auto-Lestrade).

#### Arquivos a produzir (v2)
`src/diogenes/agents/mycroft.py` (métodos M2), `src/diogenes/orchestrator/stranger_room.py`
(+ testes).

#### Critérios de aceite
- [ ] RF-MY-03/04/05/06 e RF-SR-01..06 atestados; `test_stranger_room.py` verde.
- [ ] Regra Absoluta de Crítica: exatamente 1 crítica por rodada (branching `APROVADO|CRITICA`).
- [ ] Tentativa de sobrescrita na sala → `StrangerRoomWriteError`.
- [ ] `has_critical_alert` detectado e exposto para o Art. 9.
- [ ] Propagação de "Nota metodológica com alteração" no pacote Sherlock.

#### Prompt sugerido (colar no Copilot devsquad)
> Você vai reescrever a fatia M2 de Mycroft (projeto Diógenes, branch
> `feat/reescrita-v2`): revisão da fase Watson na Stranger Room + montagem do
> pacote Sherlock. Leia `docs/reescrita_v2/mycroft/SDD_derivado_mycroft.md`
> (Seções 4–8) e `docs/conformidade/06_strangers_room.md`. Referência canônica:
> `src/diogenes/agents/mycroft.py` e `src/diogenes/orchestrator/stranger_room.py`.
> Restrições inegociáveis: Stranger Room imutável (escrita única, frontmatter
> YAML com content_hash, `StrangerRoomWriteError` como guardião); máximo 2
> rodadas (Art. 8) — o limite é do Orquestrador, não reimplemente; exatamente
> uma crítica por avaliação; síncrono, sem threads; `config.py` único leitor de
> config. Entregáveis: `avaliar_watson`, `fixar_decisao_watson`,
> `montar_pacote_sherlock`, parsers, e a reescrita de `stranger_room.py`, com
> testes equivalentes a `test_stranger_room.py` e `test_mycroft_avaliacao.py`.
> Prompts byte-idênticos ao v1 (verificar com `diogenes bench preview`).

---

### Pacote de Trabalho PT-MY-3 — Stranger Room Sherlock + consolidação
**Fatia/Fase:** M3 | **Pré-requisitos:** G-M2, G-SH | **Status:** A INICIAR

#### Objetivo
Fechar o ciclo: `avaliar_sherlock`, `fixar_decisao_sherlock` (reuso do protocolo
de M2) e `consolidar` (11 seções, impessoalidade, overrules, histórico A1→A2).

#### Contexto mínimo
Este derivado (Seções 4–8) + heartbeats `avaliar_sherlock`, `fixar_decisao_sherlock`,
`consolidar` + `docs/conformidade/03_mycroft.md` (gap RF-MY-07).

#### Escopo — entregáveis
- `avaliar_sherlock`, `fixar_decisao_sherlock`, `consolidar`,
  `_parsear_decisao_sherlock`.
- Verificação de completude das 11 seções (consumindo o atestado do Orquestrador).
- **Fora de escopo:** Sherlock em si; Fase de Entrega (M4); Motor de Saída.

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/agents/mycroft.py:237-361`, `tests/unit/test_ciclo_atividade2.py`.

#### Arquivos a produzir (v2)
`src/diogenes/agents/mycroft.py` (métodos M3) + testes.

#### Critérios de aceite
- [ ] RF-MY-05/07/08 atestados; campos `Overrule Mycroft sobre Watson/Sherlock` no consolidado.
- [ ] Consolidado em 3ª pessoa, impessoal, assinatura só ao final (Art. 14); máx. 4.000 palavras.
- [ ] A2: histórico A1 incorporado (`consolidar(historico_a1=...)`); `test_ciclo_atividade2.py` verde.
- [ ] Caso golden: deliberação `NV-GLOBAL-01` do baseline reproduzida (avaliação → resposta → ACATADO).

#### Prompt sugerido (colar no Copilot devsquad)
> Fatia M3 de Mycroft (Diógenes, branch `feat/reescrita-v2`): revisão de Sherlock
> na Stranger Room e consolidação final. Leia
> `docs/reescrita_v2/mycroft/SDD_derivado_mycroft.md` (Seções 4–8) e o PRD
> derivado (RF-MY-05/07/08). Referência canônica `src/diogenes/agents/mycroft.py`.
> Restrições: prompts byte-idênticos ao v1; `consolidar` só roda com as 11 seções
> de Sherlock atestadas pelo Orquestrador; redação impessoal em 3ª pessoa,
> assinatura só ao final; nunca transcrever PII (CPF/CNPJ/nomes/chaves);
> dilemas equilibrados não são decididos arbitrariamente (Art. 10). Entregáveis:
> `avaliar_sherlock`, `fixar_decisao_sherlock`, `consolidar` (com `historico_a1`
> para Atividade 2) e parsers, com testes equivalentes aos v1.

---

### Pacote de Trabalho PT-MY-4 — Fase de Entrega
**Fatia/Fase:** M4 | **Pré-requisitos:** G-M3 | **Status:** A INICIAR

#### Objetivo
Reescrever os call_types LLM do `diogenes deliver`: `mapear_dados_modulo`,
`avaliar_entrega` e `redigir_apendice`.

#### Contexto mínimo
Este derivado (Seções 3, 5, 9) + `docs/antecedentes/PRD_adendo_v01_fase_entrega.md`
(RF-EN-02/03/05) + `src/diogenes/delivery/MAPA_EXTRACAO.md` + heartbeats
`mapear_dados_modulo`, `avaliar_entrega`, `redigir_apendice`.

#### Escopo — entregáveis
- `mapear_dados_modulo` (blueprint: abas, células, intervalos, textos — **zero
  dígitos em posição de valor**), `avaliar_entrega` (`APROVADO|REQUER_AJUSTE`),
  `redigir_apendice` (7 seções), `_extrair_json_bloco`,
  `_parsear_avaliacao_entrega`.
- **Fora de escopo:** Motor de Entrega determinístico (`motors/motor_entrega.py`,
  `delivery/`), geradores TCU vendorizados, Playwright.

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/agents/mycroft.py:363-479`, `src/diogenes/orchestrator/entrega.py`,
`tests/unit/test_motor_entrega.py`.

#### Arquivos a produzir (v2)
`src/diogenes/agents/mycroft.py` (métodos M4) + testes.

#### Critérios de aceite
- [ ] RF-EN-03/05 atestados; `entrega_mapa_extracao.json` sem dígitos em posição de valor (verificável por regex).
- [ ] Aba ambígua → campo omitido + ambiguidade registrada (soul.md).
- [ ] Aviso operacional do Motor de Entrega não gera `REQUER_AJUSTE`.
- [ ] Veredito QA propagado ao `audit_index.csv` e `manifesto_entrega_*.json`.

#### Prompt sugerido (colar no Copilot devsquad)
> Fatia M4 de Mycroft (Diógenes, branch `feat/reescrita-v2`): call_types LLM da
> Fase de Entrega. Leia `docs/reescrita_v2/mycroft/SDD_derivado_mycroft.md`
> (Seções 3 e 5) e `docs/antecedentes/PRD_adendo_v01_fase_entrega.md`
> (RF-EN-02/03/05). Referência canônica `src/diogenes/agents/mycroft.py`.
> Restrição central: o LLM descreve **localizações** (aba, célula, intervalo) e
> redige textos — **nunca** transcreve um valor numérico; o mapa de extração não
> contém dígitos em posição de valor. QA emite `APROVADO|REQUER_AJUSTE`
> (REQUER_AJUSTE só para problema de conteúdo, não para aviso operacional).
> Entregáveis: `mapear_dados_modulo`, `avaliar_entrega`, `redigir_apendice` e
> parsers, com testes. Prompts byte-idênticos ao v1.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
