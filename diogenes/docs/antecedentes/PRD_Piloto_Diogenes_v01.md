---
documento: PRD — Piloto Diógenes Local
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
grupo_de_trabalho: GT Reforma Tributária
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-05-07
uso: Interno Restrito
documentos_antecedentes:
  - dva_cbs_completo_v03.docx (Arquitetura Conceitual do Departamento)
  - GT_CBS_Estrategia_Integrada_Validacao.docx (Estratégia Integrada do GT)
---

# **PRD — Piloto Diógenes Local**
## Departamento de Validação Assistida da CBS

> **Status:** Documento de Trabalho Interno em sua primeira versão consolidada (v0.1).
> **Escopo:** fase de validação operacional do Departamento em ambiente local ou VPS particular, com modelos servidos via OpenRouter, antes de qualquer migração para infraestrutura institucional.
> **Documentos antecedentes:** `dva_cbs_completo_v03.docx` (arquitetura conceitual do Departamento) e `GT_CBS_Estrategia_Integrada_Validacao.docx` (estratégia integrada do GT). Este PRD não substitui esses documentos — deriva deles.

---

## **Sumário**

- [Bloco 1 — Contexto e Objetivo do Piloto](#bloco-1--contexto-e-objetivo-do-piloto)
- [Bloco 2 — Casos de Uso Prioritários](#bloco-2--casos-de-uso-prioritários)
- [Bloco 3 — Requisitos Funcionais](#bloco-3--requisitos-funcionais)
- [Bloco 4 — Requisitos Não Funcionais](#bloco-4--requisitos-não-funcionais)
- [Bloco 5 — Restrições e Premissas](#bloco-5--restrições-e-premissas)
- [Bloco 6 — Critérios de Aceitação](#bloco-6--critérios-de-aceitação)
- [Bloco 7 — Métricas e Benchmarking de Modelos](#bloco-7--métricas-e-benchmarking-de-modelos)
- [Bloco 8 — Roadmap do Piloto](#bloco-8--roadmap-do-piloto)
- [Bloco 9 — Evolução Pós-Piloto](#bloco-9--evolução-pós-piloto)
- [Bloco 10 — Glossário e Referências](#bloco-10--glossário-e-referências)

---

# **Bloco 1 — Contexto e Objetivo do Piloto**

## **1.1 Por Que um Piloto antes da Implementação em Foundry**

A arquitetura conceitual do Departamento de Validação Assistida foi consolidada em três documentos institucionais que descrevem, com profundidade, o mandato do trabalho, os agentes que o executam, as atividades operacionais, as camadas de validação e a Constituição que rege o funcionamento interno. Esses documentos estabelecem o que o Departamento é, faz e entrega. O passo seguinte — transformar essa arquitetura em sistema executável — não pode ser dado em produção pela primeira vez.

A razão é estrutural, não técnica. O Departamento opera sobre dados que fundamentarão o cálculo da alíquota de referência da CBS, parâmetro central de uma reforma tributária de magnitude histórica. A primeira execução do sistema sobre material da Receita Federal do Brasil precisa ocorrer com a confiança de que a arquitetura é executável, de que os componentes operam como descritos na Constituição, de que o Motor de Start abre ciclos corretamente, de que a Stranger's Room produz os artefatos de revisão esperados, de que o Motor de Saída efetivamente remove as marcas dos agentes antes da chancela final. Essa confiança não vem de revisão de código nem de testes unitários: vem de rodadas reais sobre material que se comporta como o material real, em um ambiente que pode falhar sem custo institucional.

O piloto também tem segunda função, igualmente importante: permitir benchmarking honesto de modelos sem comprometimento orçamentário ou político. A escolha definitiva dos modelos que cada agente utilizará na produção depende de comparação empírica entre opções concretas, sob carga representativa, com medição de custo, latência e qualidade. Essa comparação só faz sentido com o sistema rodando — não sobre slides ou suposições. Rodar localmente com OpenRouter, sob orçamento controlado e individual, permite essa exploração com liberdade que um ambiente institucional desde o início não permitiria.

Há ainda terceira razão, de natureza prática: a liberação do Azure AI Foundry pelo Departamento de TI e pela Auditoria Interna do TCU envolve aprovações que tomam tempo, e o desenvolvimento da arquitetura não pode ficar bloqueado até que essas aprovações se concretizem. O piloto local desacopla a construção do sistema da disponibilidade da infraestrutura institucional. Quando o Foundry estiver liberado, o sistema já estará maduro o suficiente para migrar com baixo risco — bastará trocar o cliente de LLM, conforme previsto no SDD.

## **1.2 Critérios de Sucesso do Piloto**

O piloto é considerado bem-sucedido quando, cumulativamente, as seguintes condições forem observadas.

Primeiro, **execução ponta a ponta sem quebra**. O ciclo completo da Atividade 1 (Validação de Módulo) deve executar três vezes consecutivas sobre um módulo sintético, com Motor de Start gerando manifesto correto, agentes operando em sequência sem paralelismo, Stranger's Room produzindo arquivos de revisão íntegros, Motor de Saída filtrando marcas dos agentes, audit_index.csv recebendo o registro do ciclo. Erros de runtime, perda de trace ou falha em qualquer Human-in-the-Gate descumprem este critério.

Segundo, **rastreabilidade auditável por inspeção humana direta**. Um auditor que abra o diretório de trabalho do ciclo deve conseguir reconstruir, lendo apenas os arquivos Markdown produzidos, todo o raciocínio do Departamento: o que foi recebido, o que cada agente analisou, quais críticas Mycroft levantou, como elas foram respondidas, qual posição final foi adotada e com que fundamentação. Sem necessidade de logs de aplicação, sem necessidade de banco de dados auxiliar, sem ferramentas externas. A leitura humana direta é o teste.

Terceiro, **execução do ciclo de revalidação**. A Atividade 2 (Revalidação de Módulo) deve executar sobre o mesmo módulo sintético depois que uma resposta simulada da RFB for produzida, demonstrando que o sistema preserva e utiliza o histórico do ciclo anterior corretamente.

Quarto, **mensuração de custo e latência**. O sistema deve registrar, ao final de cada ciclo, o custo total em USD pago ao OpenRouter, o número de tokens consumidos por agente, a latência de cada chamada e a duração total do ciclo. Esses dados alimentam o benchmark de modelos previsto na Fase B.

Quinto, **avaliação humana qualitativa positiva**. Os relatórios produzidos ao final de pelo menos uma execução com modelos não-free devem passar por avaliação humana, e essa avaliação deve confirmar que o conteúdo tem utilidade técnica real — que o relatório encontrou as inconsistências propositais inseridas no módulo sintético, que a fundamentação metodológica está coerente, que a linguagem é institucional e impessoal conforme a Constituição.

Sexto, **portabilidade demonstrada**. O sistema deve rodar, sem alteração de código além de configuração, em três ambientes: máquina local com OneDrive sincronizado, VPS particular sem OneDrive, e ambiente de teste simulando a estrutura de diretórios prevista para Azure. A simples troca de variáveis de ambiente e do `runtime.yaml` deve ser suficiente.

A não satisfação de qualquer um desses critérios indica trabalho pendente antes da declaração de piloto concluído.

## **1.3 Escopo Fora do Piloto**

A delimitação do que não entra no piloto é tão importante quanto a delimitação do que entra, porque protege o foco e impede que o esforço se dilua em frentes que pertencem a fases posteriores.

**Atividades 3, 4 e 5 ficam fora.** As atividades exclusivas dos módulos selecionados para a Sala de Sigilo — produção do roteiro de perguntas para a reunião extraordinária, produção do roteiro de testes para execução em campo, validação ad hoc dos dados coletados em campo — não são exercitadas no piloto. Elas dependem de interações com o GT Reforma Tributária e com a infraestrutura da RFB que não fazem sentido replicar em ambiente local. Quando a arquitetura estiver validada para as Atividades 1 e 2, a extensão para 3, 4 e 5 é incremental, não estrutural.

**Os 17 módulos da CBS ficam fora.** O piloto opera sobre um módulo sintético na Fase A e Fase B, e sobre o MOD_010 (Pessoa Física) na Fase D, esta última quando a arquitetura já estiver suficientemente madura. Os demais 16 módulos pertencem à operação contínua do Departamento e ficam fora do escopo de validação inicial.

**Integração com Azure, Foundry e infraestrutura institucional do TCU fica fora.** O piloto roda exclusivamente em máquina pessoal ou VPS particular, com modelos servidos via OpenRouter. A migração para Azure AI Foundry é prevista no SDD como caminho evolutivo, mas não é exercitada nesta fase. Tampouco há integração com sistemas internos do TCU, com o ambiente do GT, com sistemas da RFB ou com qualquer base institucional.

**Anonimização de dados sensíveis fica fora.** Não há, no piloto, dados reais sob sigilo fiscal sendo processados. O módulo sintético é fabricado com dados fictícios; o MOD_010 utilizado na Fase D, embora derivado de material real entregue pela RFB, contém dados que já foram tratados pelo GT Reforma Tributária para o piloto de validação concluído anteriormente, e a análise no Departamento não envolve manipulação de dados pessoais identificáveis. A engenharia de anonimização que será exigida em produção, especialmente para os módulos da Sala de Sigilo, não é exercitada nesta fase.

**Interface gráfica e ambiente multiusuário ficam fora.** O Departamento, no piloto, é operado via linha de comando por um único auditor — o próprio desenvolvedor exercendo o papel de Lestrade — em um único processo, sem concorrência, sem múltiplas sessões simultâneas, sem dashboard. As funções de orquestração, leitura de manifesto, chancela de outputs e disparo de ciclo são exercidas via comandos Typer documentados no SDD.

**Geração final dos relatórios em docx no padrão Design System v5 fica parcialmente fora.** O piloto produz outputs em Markdown estruturado, com os campos institucionais corretos. A conversão final para docx no padrão TCU pode ser feita pelo motor gerador de documentos já existente no projeto maior — mas a integração refinada com esse motor não é critério de sucesso do piloto. Validar a integração com o motor de docx é tarefa pós-piloto.

**Persistência em banco de dados, mensageria e indexação avançada ficam fora.** O sistema é integralmente filesystem-first: arquivos Markdown, CSV de índice, manifestos em Markdown. Vetorização semântica de traces, busca full-text indexada, dashboards analíticos sobre o histórico de ciclos — tudo isso é evolução pós-piloto e não entra agora.

---

# **Bloco 2 — Casos de Uso Prioritários**

## **2.1 Lógica de Seleção dos Casos de Uso**

O piloto não exercita o universo completo das atividades do Departamento. A seleção dos casos de uso é orientada por dois critérios convergentes: a Constituição precisa ser exercida em seus pontos mais carregados de regra, e a arquitetura técnica precisa ser estressada nos pontos onde uma falha silenciosa teria consequência institucional.

A Atividade 1, por se aplicar a todos os 17 módulos e por concentrar a totalidade do fluxo interno do Departamento — Motor de Start, Mycroft delegando, Watson analisando, Stranger's Room operando, Sherlock validando, Stranger's Room operando novamente, Mycroft consolidando, Motor de Saída filtrando, Lestrade chancelando — é o caso de uso central. Validá-la equivale a validar o coração do Departamento.

A Atividade 2, por replicar a estrutura da Atividade 1 com input adicional e exigir que o sistema preserve e utilize corretamente o histórico do ciclo anterior, é o caso de uso que comprova rastreabilidade entre ciclos do mesmo módulo. Sem ela, não há demonstração de que o sistema funciona ao longo do tempo, apenas em uma execução isolada.

O terceiro caso de uso, derivado dos dois primeiros mas tratado com peso próprio, é o protocolo da Stranger's Room com duas rodadas de revisão completas. A Constituição estabelece, no Artigo 8, que Mycroft pode questionar e o agente questionado dispõe de duas rodadas para corrigir ou sustentar sua posição. O caso natural é Mycroft acatar de primeira; o caso difícil é Mycroft refutar, o agente sustentar com nova evidência, Mycroft refutar de novo, o agente fixar a posição na segunda rodada. Esse caminho precisa ser exercitado deliberadamente, não esperado por acaso. O módulo sintético é construído com inconsistências cuja interpretação admite controvérsia, justamente para forçar a Stranger's Room ao seu uso pleno.

As Atividades 3, 4 e 5 ficam fora do piloto, conforme já registrado no Bloco 1.

## **2.2 Caso de Uso 1 — Atividade 1 sobre Módulo Sintético**

**Ator humano:** Lestrade (auditor exercendo o papel de Human-in-the-Gate, no piloto representado pelo próprio desenvolvedor).

**Objetivo:** executar o ciclo completo de validação inicial sobre um módulo sintético construído para o piloto, produzindo o Relatório Preliminar de Análise do Módulo conforme Atividade 1 da Constituição.

**Pré-condições.** O diretório `workspace/input/MOD_SINT_001/` contém os documentos do módulo sintético: planilhas com cálculos da CBS hipotética, scripts SQL de extração, notebook Python de transformação, documento metodológico do módulo, briefing do GT, atas e transcrições de reunião fictícias. O `audit_index.csv` está em estado consistente, sem ciclo aberto pendente. As variáveis de ambiente necessárias estão carregadas, com `OPENROUTER_API_KEY` válido e saldo positivo.

**Fluxo principal.** Lestrade dispara `diogenes start --module MOD_SINT_001 --activity 1` na linha de comando. O Motor de Start verifica a presença de todos os inputs nos diretórios corretos, calcula hash SHA-256 de cada arquivo, gera o manifesto de abertura do ciclo em Markdown registrando módulo, atividade, arquivos encontrados, caminhos, hashes e timestamp de início, e copia todos os arquivos para o diretório de trabalho isolado do ciclo. O Motor exibe o caminho do manifesto e aguarda confirmação. Lestrade lê o manifesto e confirma com `diogenes confirm-manifest`. O sistema registra a confirmação e aciona Mycroft.

Mycroft lê o manifesto, confirma internamente e inicia a execução. Define as tasks ordenadas de Watson, encaminhando-as com todos os inputs e caminhos. O sistema chama Watson uma única vez, com o pacote completo. Watson analisa os documentos em profundidade, produz relatório graduado com alertas de severidade diferenciada, registra o raciocínio que o levou a cada conclusão e escreve o resultado no diretório da Stranger's Room do ciclo, na fase `watson_integridade`, como arquivo `01_apresentacao.md`.

Mycroft lê o output de Watson, avalia, e segue um de dois caminhos. Se julga o output suficiente, escreve `99_decisao_final.md` na fase `watson_integridade` aprovando sem revisão e prossegue. Se julga necessária revisão, escreve `02_critica_mycroft_r1.md` com os pontos questionados, e o sistema reativa Watson com o pacote original mais a crítica. Watson responde em `03_resposta_r1.md`. Mycroft avalia novamente. Pode acatar e fixar `99_decisao_final.md`, ou refutar uma segunda vez em `04_critica_mycroft_r2.md`, recebendo a resposta final em `05_resposta_r2.md`. Após a segunda rodada, Mycroft fixa a decisão em `99_decisao_final.md` independentemente da concordância com Watson — o Artigo 8 da Constituição é absoluto sobre o limite.

Antes de prosseguir para Sherlock, Mycroft inspeciona a decisão final consolidada à procura de alertas de severidade crítica. Se houver pelo menos um, o sistema notifica Lestrade via console, registrando a comunicação no trace, e aguarda. Lestrade pode autorizar prosseguimento com `diogenes proceed` ou interromper com `diogenes pause`. O fluxo prossegue por padrão se Lestrade não interromper expressamente.

Mycroft então monta o pacote integrado para Sherlock — composto pelo inventário, pelos documentos entregues, pela decisão final de Watson e pelo briefing do módulo — e o sistema chama Sherlock. Sherlock aplica a metodologia homologada sobre o pacote, aponta o que está conforme, o que diverge e o que não é possível verificar, registra fundamentação explícita para cada posição e escreve o resultado na Stranger's Room na fase `sherlock_validacao`, como `01_apresentacao.md`. O protocolo de revisão de Mycroft sobre Sherlock é idêntico ao aplicado sobre Watson, com mesmo limite de duas rodadas e mesma estrutura de arquivos.

Encerrada a Stranger's Room de Sherlock, Mycroft consolida o output final do ciclo: o Relatório Preliminar de Análise do Módulo MOD_SINT_001, com a fase identificada como "Após Reunião de Entrega Inicial". O documento é gerado em Markdown estruturado no diretório `workspace/cycles/{cycle_id}/output/`. Mycroft entrega o relatório a Lestrade.

Lestrade aciona o Motor de Saída via `diogenes verify-output`. O Motor varre o documento procurando ocorrências dos nomes dos agentes (Mycroft, Watson, Sherlock, Lestrade, e variações), referências aos cargos formais que possam ter vazado para o corpo do texto, e marcas internas do Departamento (referências a Stranger's Room, audit_index, traces internos). Apresenta um relatório de verificação com todas as ocorrências detectadas. Em caso de ocorrências, o sistema interrompe o fluxo e exige decisão de Lestrade — corrigir manualmente, retornar a Mycroft para reprodução do output, ou aceitar com justificativa registrada. Em caso de zero ocorrências, o Motor confirma a limpeza e habilita a chancela final.

Lestrade chancela o output com `diogenes seal --cycle {cycle_id}`. O sistema registra a chancela no audit_index.csv com timestamp, módulo, atividade, agentes envolvidos, status final, hash do documento de saída, e marca o ciclo como encerrado. O diretório de trabalho do ciclo é preservado integralmente. O documento de saída fica disponível em `workspace/cycles/{cycle_id}/output/relatorio_preliminar.md` para entrega externa.

**Pós-condições.** O `audit_index.csv` registra um novo ciclo encerrado para o MOD_SINT_001 com atividade 1. O diretório de trabalho do ciclo está preservado, com manifesto, cópias dos inputs, traces da Stranger's Room de ambas as fases, decisões finais e relatório consolidado. Nenhum arquivo do diretório original de input foi alterado.

**Fluxos alternativos.** Watson encontra arquivo que não consegue analisar — registra a ocorrência na decisão final e segue com os demais arquivos, conforme Bloco 3 da arquitetura conceitual. Sherlock identifica dúvida genuinamente equilibrada sobre interpretação metodológica — registra o dilema na decisão final, apresenta a Mycroft, e se Mycroft também não resolve, o ponto vai consolidado no relatório ordinário, conforme Artigo 10 da Constituição. Falha de chamada à API do OpenRouter por timeout ou erro 5xx — o sistema executa retry conforme política do `agent.md` (máximo duas tentativas com backoff), e se persistir, escreve trace de falha, notifica Lestrade e aborta o ciclo deixando o estado pausado para análise. Lestrade aborta o ciclo manualmente em qualquer ponto via `diogenes abort` — o sistema marca o ciclo como abortado no audit_index.csv com timestamp e razão, preserva o diretório de trabalho e libera o sistema para novo ciclo.

**Critérios de aceitação específicos.** O ciclo executa em tempo razoável (target inicial: trinta minutos com modelos free, dez minutos com modelos baratos, ajustável conforme benchmark). Todos os arquivos previstos da Stranger's Room estão presentes ao final, com timestamps coerentes e conteúdo legível por leitura humana direta. O Relatório Preliminar é redigido em terceira pessoa, sem nome dos agentes no corpo, com assinatura ao final identificando o agente responsável (Mycroft, no caso de output consolidado) e o cargo formal. O audit_index.csv reflete o ciclo encerrado.

## **2.3 Caso de Uso 2 — Atividade 2 (Revalidação) sobre o Mesmo Módulo**

**Ator humano:** Lestrade.

**Objetivo:** executar o ciclo de revalidação sobre o MOD_SINT_001 após uma resposta simulada da RFB ter sido produzida e organizada por simulação do GT, demonstrando que o sistema preserva o histórico do ciclo anterior e o utiliza corretamente como base de comparação.

**Pré-condições.** O ciclo da Atividade 1 sobre o MOD_SINT_001 foi concluído e chancelado, registrado no audit_index.csv. Existe, em `workspace/input/MOD_SINT_001/resposta_rfb_simulada/`, um pacote de resposta da RFB construído sinteticamente: planilhas corrigidas, scripts revisados, justificativas formais para inconsistências não corrigidas. O pacote chega organizado por simulação do GT, conforme previsto no Bloco 4 da arquitetura conceitual.

**Fluxo principal.** Lestrade dispara `diogenes start --module MOD_SINT_001 --activity 2`. O Motor de Start verifica a presença do pacote de resposta nos diretórios corretos, gera novo manifesto de abertura referenciando o ciclo anterior — incluindo o cycle_id da Atividade 1 e o caminho dos artefatos preservados — e copia o pacote de resposta e os outputs completos da Atividade 1 (relatório preliminar, traces da Stranger's Room, decisões finais) para o novo diretório de trabalho. O manifesto declara explicitamente os inputs herdados e os inputs novos.

Lestrade confirma o manifesto. Mycroft confirma internamente e inicia. A execução interna replica a estrutura da Atividade 1, com diferença substantiva: Watson recebe instrução explícita de confrontar os documentos novos ou corrigidos com o que foi analisado na Atividade 1, identificando o que mudou, o que foi corrigido, o que permanece inconsistente. A Stranger's Room de Watson opera nesse novo registro analítico. Mycroft revisa, integra, encaminha a Sherlock. Sherlock valida as correções e justificativas da RFB contra a metodologia homologada, aponta o que foi resolvido, o que foi justificado de forma aceitável, o que permanece em aberto e o que gerou nova inconsistência. A Stranger's Room de Sherlock opera com esse novo registro.

Mycroft consolida o Relatório Final de Análise do Módulo, que difere do Relatório Preliminar em estrutura: incorpora o histórico completo do módulo, posicionando lado a lado o que foi identificado na Atividade 1, o que a RFB respondeu, o que foi aceito e o que permanece como inconsistência. O documento é gerado em `workspace/cycles/{cycle_id_atividade_2}/output/relatorio_final.md`.

O Motor de Saída opera nos mesmos termos da Atividade 1. Lestrade chancela. O ciclo é registrado no audit_index.csv com referência ao ciclo da Atividade 1.

**Pós-condições.** O audit_index.csv registra dois ciclos para o MOD_SINT_001 — Atividade 1 e Atividade 2 —, ambos encerrados. O diretório de trabalho do segundo ciclo preserva os artefatos do primeiro como inputs, sem duplicação física desnecessária (o sistema utiliza referências de caminho, não cópias redundantes, para os outputs do ciclo anterior).

**Critérios de aceitação específicos.** O Relatório Final referencia explicitamente, em seu corpo, as inconsistências identificadas no Relatório Preliminar, demonstrando que o sistema utilizou o histórico. As correções da RFB são classificadas com clareza: aceita, justificada de forma aceitável, em aberto, ou nova inconsistência. A leitura comparativa do Relatório Preliminar e do Relatório Final permite reconstruir o diálogo técnico completo entre o Departamento e a RFB simulada, sem necessidade de consulta a outros artefatos.

## **2.4 Caso de Uso 3 — Stranger's Room com Duas Rodadas Completas**

**Ator humano:** Lestrade.

**Objetivo:** demonstrar que o protocolo de revisão de Mycroft sobre os agentes executores opera plenamente quando o caso exige, com duas rodadas completas de crítica e resposta sendo exercidas, e a decisão final sendo fixada por Mycroft após o esgotamento do limite constitucional.

Esse caso de uso não é executado em separado — ele é forçado dentro da execução do Caso de Uso 1, mediante construção deliberada do módulo sintético. O módulo MOD_SINT_001 é fabricado com pelo menos duas inconsistências cuja interpretação é genuinamente controversa, projetadas para que o output inicial de Watson ou de Sherlock contenha posições que Mycroft tenderá a questionar. A controvérsia precisa ser real, não fabricada artificialmente: deve haver fundamento técnico para a posição inicial do agente, e fundamento técnico para a contraposição de Mycroft. O objetivo é exercitar o protocolo de revisão sob carga real de raciocínio, não simular um diálogo predefinido.

**Critérios de aceitação específicos.** Em pelo menos uma das fases (`watson_integridade` ou `sherlock_validacao`) do Caso de Uso 1, o diretório da Stranger's Room contém os arquivos `01_apresentacao.md`, `02_critica_mycroft_r1.md`, `03_resposta_r1.md`, `04_critica_mycroft_r2.md`, `05_resposta_r2.md` e `99_decisao_final.md`, todos com conteúdo substantivo e timestamps coerentes. A leitura sequencial desses seis arquivos lê como uma transcrição literária de duas rodadas de discussão técnica. A decisão final de Mycroft é fundamentada — seja acatando a posição do agente, seja fixando posição diversa — e cita explicitamente a discussão das duas rodadas. Em caso de fixação de posição diversa da defendida pelo agente, a decisão final deixa registrado o ponto e a fundamentação, e essa controvérsia resolvida por Mycroft eventualmente migra para o Relatório Preliminar como inconsistência classificada.

A execução do Caso de Uso 3 dentro do Caso de Uso 1 não tem disparo separado nem comando próprio. É observada e aceita conforme os critérios acima. Caso o módulo sintético, construído originalmente com inconsistências controversas, não consiga forçar duas rodadas em pelo menos uma fase, o módulo é refeito com inconsistências mais polêmicas. A não exercitação plena do protocolo de duas rodadas, em pelo menos uma execução do piloto, descumpre o critério geral de sucesso registrado no Bloco 1.

---

# **Bloco 3 — Requisitos Funcionais**

## **3.1 Lógica da Estrutura de Requisitos**

Os requisitos funcionais do piloto são enunciados na ordem do fluxo operacional do Departamento, não na ordem de complexidade ou de relevância arquitetural. A razão é prática: cada requisito amarra-se a um componente concreto do sistema, e o fluxo operacional é a sequência mais natural de leitura tanto para quem implementa quanto para quem audita posteriormente o cumprimento.

Cada requisito é identificado por código no formato `RF-{COMPONENTE}-{NÚMERO}`, onde o componente é uma sigla curta (`MS` para Motor de Start, `OR` para Orquestrador, `MY`/`WA`/`SH` para os agentes, `SR` para Stranger's Room, `MV` para Motor de Saída, `PE` para Persistência, `CL` para CLI). A numeração é sequencial dentro de cada componente. Esse esquema permite que o SDD, ao mapear componentes para módulos de código, referencie diretamente os requisitos atendidos por cada módulo.

A redação adota tom prescritivo: cada requisito declara o que o sistema deve fazer, não como deve fazê-lo. As decisões de implementação ficam para o SDD. Quando um requisito tem natureza condicional ou depende de configuração, isso é explicitado.

## **3.2 Motor de Start (RF-MS)**

O Motor de Start é o componente que abre cada ciclo do Departamento. Sua função é estabelecer, de forma rastreável e isolada, o ambiente de trabalho para a execução que se seguirá.

**RF-MS-01.** O Motor de Start deve receber, como parâmetros de invocação, o identificador do módulo a ser processado e o código da atividade a ser executada (1 para Validação de Módulo, 2 para Revalidação de Módulo).

**RF-MS-02.** O Motor de Start deve verificar a presença de todos os inputs esperados nos diretórios de origem, conforme a atividade invocada. Para a Atividade 1, os inputs incluem inventário e metadados da Etapa 2.1, regras de negócio e documentos derivados da Etapa 2.2, atas e transcrições da Etapa 2.3, briefing do módulo e os documentos entregues pela RFB. Para a Atividade 2, os inputs incluem o pacote de resposta da RFB, o output completo do ciclo da Atividade 1 do mesmo módulo e os artefatos originais necessários ao confronto. A ausência de qualquer input esperado interrompe o Motor com mensagem explícita identificando o que falta e em que diretório era esperado.

**RF-MS-03.** O Motor de Start deve calcular o hash SHA-256 de cada arquivo de input, registrando o hash no manifesto de abertura para fins de rastreabilidade e detecção de alteração não autorizada.

**RF-MS-04.** O Motor de Start deve gerar um identificador único de ciclo no formato `{MOD_ID}_A{ATIVIDADE}_{TIMESTAMP_UTC}`, onde o timestamp utiliza o padrão ISO 8601 compactado (`YYYYMMDDTHHMMSSZ`). O identificador deve ser único em todo o histórico do Departamento.

**RF-MS-05.** O Motor de Start deve gerar o manifesto de abertura do ciclo em formato Markdown, contendo no mínimo: identificador do ciclo, identificador do módulo, código e nome da atividade, timestamp de abertura em UTC e em fuso local, lista completa de arquivos de input com caminhos absolutos de origem e hashes SHA-256, indicação se o módulo está pré-selecionado para análise na Sala de Sigilo, e referência ao ciclo anterior quando se tratar de Atividade 2. O manifesto é gravado em `workspace/cycles/{cycle_id}/manifest.md`.

**RF-MS-06.** O Motor de Start deve criar o diretório de trabalho isolado do ciclo em `workspace/cycles/{cycle_id}/`, com a estrutura interna padronizada: subdiretórios `inputs/` para as cópias dos arquivos de origem, `stranger_room/` para os artefatos de revisão, `output/` para o produto final do ciclo, e o arquivo `manifest.md` na raiz do diretório do ciclo.

**RF-MS-07.** O Motor de Start deve copiar todos os arquivos de input para o subdiretório `inputs/` do diretório de trabalho do ciclo, preservando a estrutura de pastas de origem quando existir. Os arquivos originais nos diretórios de origem não devem ser alterados em nenhuma hipótese, conforme Artigo 13 da Constituição.

**RF-MS-08.** O Motor de Start deve, ao concluir a preparação, exibir no console o caminho absoluto do manifesto gerado e aguardar confirmação explícita de Lestrade antes de qualquer próximo passo. A confirmação se dá por comando CLI dedicado, conforme RF-CL-03. Sem confirmação, o ciclo permanece em estado preparado mas inativo, e nenhum agente é acionado.

**RF-MS-09.** O Motor de Start deve registrar a abertura do ciclo no `audit_index.csv` com status inicial `PREPARADO`, atualizado posteriormente conforme o ciclo evolui.

## **3.3 Orquestrador (RF-OR)**

O Orquestrador é o componente que conduz a sequência interna do ciclo após a confirmação de Lestrade. Não confundir com Mycroft: o Orquestrador é infraestrutura, Mycroft é o agente de modelo de linguagem que toma decisões dentro dessa infraestrutura. O Orquestrador chama Mycroft, persiste seus outputs, encadeia as fases do ciclo conforme as decisões de Mycroft, e assegura que a sequencialidade exigida pela Constituição seja tecnicamente garantida.

**RF-OR-01.** O Orquestrador deve garantir, por construção, que apenas um agente esteja em execução em cada momento. Não há paralelismo entre agentes em nenhuma fase do ciclo. A garantia é estrutural: o Orquestrador opera em fluxo sequencial síncrono dentro de um único processo, sem concorrência.

**RF-OR-02.** O Orquestrador deve, ao receber a confirmação de Lestrade sobre o manifesto, ler o manifesto, validá-lo internamente quanto à completude dos campos obrigatórios, instanciar Mycroft com o pacote completo de inputs e aguardar o retorno de Mycroft com a definição das tasks ordenadas para Watson.

**RF-OR-03.** O Orquestrador deve executar as tasks ordenadas por Mycroft, na sequência por ele definida, sem reordenação automática, sem inclusão de tasks não previstas pelo Mycroft, e sem omissão de tasks por ele declaradas. A autoridade de definição das tasks é exclusiva de Mycroft, conforme Artigo 4 da Constituição.

**RF-OR-04.** O Orquestrador deve, ao receber o output de Watson, persistir o resultado na fase correspondente da Stranger's Room e invocar Mycroft para revisão. Se Mycroft questiona, o Orquestrador reativa Watson com o pacote original mais a crítica de Mycroft, recebendo a resposta. O Orquestrador deve aplicar o limite de duas rodadas estabelecido pelo Artigo 8 da Constituição: após a segunda rodada, qualquer nova chamada a Watson na mesma fase é tecnicamente impedida pelo Orquestrador, e Mycroft é forçado a fixar a decisão final.

**RF-OR-05.** O Orquestrador deve, após a fixação da decisão final de Mycroft sobre Watson, inspecionar a decisão à procura de marcação de alerta de severidade crítica. Em caso positivo, o Orquestrador deve emitir notificação a Lestrade no console, registrar a notificação no trace do ciclo, e aguardar resposta explícita de Lestrade — autorização para prosseguir ou pausa do ciclo. O fluxo prossegue por padrão se Lestrade não interromper expressamente, conforme Artigo 9 da Constituição.

**RF-OR-06.** O Orquestrador deve, autorizado o prosseguimento, montar o pacote integrado para Sherlock — composto pelo inventário, pelos documentos entregues pela RFB, pela decisão final de Mycroft sobre Watson, pela análise consolidada de Watson e pelo briefing do módulo — e invocar Sherlock.

**RF-OR-07.** O Orquestrador deve aplicar à fase `sherlock_validacao` o mesmo protocolo de Stranger's Room aplicado à fase `watson_integridade`: persistência do output inicial, revisão por Mycroft, limite de duas rodadas, fixação de decisão final por Mycroft.

**RF-OR-08.** O Orquestrador deve, encerradas ambas as fases, invocar Mycroft para a consolidação final do output do ciclo. Mycroft produz, com base nas decisões finais das duas fases, o documento consolidado correspondente à atividade — Relatório Preliminar de Análise para a Atividade 1, Relatório Final de Análise para a Atividade 2 — e o entrega ao Orquestrador.

**RF-OR-09.** O Orquestrador deve persistir o documento consolidado em `workspace/cycles/{cycle_id}/output/`, atualizar o status do ciclo no `audit_index.csv` para `AGUARDANDO_VERIFICACAO_SAIDA`, e exibir no console o caminho do output gerado, aguardando o acionamento do Motor de Saída por Lestrade.

**RF-OR-10.** O Orquestrador deve, em caso de falha em qualquer chamada a um agente — timeout, erro de provider, resposta malformada — aplicar a política de retry definida no `agent.md` do agente em questão. Esgotada a política, o Orquestrador deve registrar a falha em trace dedicado, atualizar o status do ciclo para `ABORTADO_FALHA_AGENTE`, notificar Lestrade no console com o detalhamento da falha, e encerrar o processo do ciclo sem corromper o estado do `audit_index.csv`. O diretório de trabalho do ciclo é preservado para análise posterior.

**RF-OR-11.** O Orquestrador deve, em todas as transições de fase, atualizar o status do ciclo no `audit_index.csv` com o estado correspondente, conforme a tabela de estados definida no SDD.

## **3.4 Mycroft (RF-MY)**

Mycroft é o agente que orquestra as decisões internas do ciclo. Sua função técnica é receber pacotes, definir tasks, revisar outputs dos demais agentes, decidir sobre questionamentos, e consolidar o produto final.

**RF-MY-01.** Mycroft deve, ao ser instanciado pelo Orquestrador no início do ciclo, ler o manifesto, internalizar o contexto do módulo e da atividade, e produzir a definição das tasks ordenadas a serem encaminhadas a Watson. A definição inclui, no mínimo, a lista de arquivos a serem analisados, a sequência de análise sugerida, e as instruções específicas que devem orientar Watson — sem nunca dirigir a interpretação metodológica, que pertence a Sherlock.

**RF-MY-02.** Mycroft não deve, em nenhuma circunstância, analisar arquivos diretamente, executar cálculos próprios ou aplicar regras de negócio metodológicas. A função de Mycroft é integrar, revisar, questionar e consolidar, conforme Artigo 5 da Constituição. Tecnicamente, isso se traduz na ausência, no `agent.md` de Mycroft, de tools de leitura direta de planilhas, parsing de SQL ou execução de notebooks.

**RF-MY-03.** Mycroft deve, ao receber o output de um agente executor, decidir entre três caminhos: aprovar sem revisão, registrando essa decisão como `99_decisao_final.md` com fundamentação curta; questionar, escrevendo `02_critica_mycroft_r1.md` com pontos específicos a serem corrigidos ou justificados; ou identificar inconsistência crítica imediata que justifique escalonamento a Lestrade.

**RF-MY-04.** Mycroft deve, ao questionar um agente, formular crítica objetiva, dirigida a pontos específicos do output recebido, com fundamentação técnica. Críticas vagas ou genéricas violam a função de revisão e devem ser tecnicamente detectáveis na avaliação humana dos traces.

**RF-MY-05.** Mycroft deve, após a segunda rodada de revisão de qualquer fase, fixar a decisão final independentemente de concordância ou discordância com a posição final do agente. A decisão final pode acatar a posição do agente, fixar posição diversa com fundamentação, ou registrar a controvérsia como inconsistência classificada a ser incluída no relatório consolidado, conforme Artigo 10 da Constituição.

**RF-MY-06.** Mycroft deve, ao encerrar a fase `watson_integridade`, inspecionar a decisão final à procura de alertas de severidade crítica identificados por Watson. Em caso positivo, Mycroft deve marcar explicitamente a presença do alerta crítico em campo dedicado da decisão final, de forma estruturada para que o Orquestrador detecte e dispare a notificação a Lestrade conforme RF-OR-05.

**RF-MY-07.** Mycroft deve, ao consolidar o output final do ciclo, gerar o documento conforme a atividade em curso: Relatório Preliminar de Análise do Módulo para Atividade 1, Relatório Final de Análise do Módulo para Atividade 2. O documento deve ser redigido em terceira pessoa e de forma impessoal, sem nome de agentes no corpo, com assinatura ao final identificando Mycroft como agente responsável e o cargo formal de Auditor Chefe, conforme Artigo 14 da Constituição.

**RF-MY-08.** Mycroft deve incorporar ao output final, quando se tratar de Atividade 2, o histórico explícito do ciclo da Atividade 1 do mesmo módulo: o que foi identificado preliminarmente, o que a RFB respondeu no contraditório técnico, o que foi aceito, o que permanece como inconsistência. O documento deve permitir reconstrução do diálogo técnico completo entre o Departamento e a RFB sobre o módulo.

## **3.5 Watson (RF-WA)**

Watson é o agente executor responsável pelas verificações da Camada 0 da estratégia de validação: integridade, consistência interna e coerência das transformações dos documentos entregues pela RFB.

**RF-WA-01.** Watson deve receber, do Orquestrador, o pacote de tasks ordenadas definido por Mycroft, com lista explícita dos arquivos a serem analisados e instruções específicas de análise. Watson não deve iniciar análise por iniciativa própria nem incluir arquivos não previstos nas tasks recebidas.

**RF-WA-02.** Watson não deve, em nenhuma circunstância, interpretar a metodologia homologada pelo Acórdão 2833/2025-Plenário, emitir juízo sobre conformidade metodológica ou confrontar dados com regras de negócio da CBS, conforme Artigo 6 da Constituição. Tecnicamente, isso se traduz na ausência, no `agent.md` de Watson, de injeção do documento da metodologia homologada como contexto, e na presença explícita, no prompt de sistema de Watson, da regra de não interpretação metodológica.

**RF-WA-03.** Watson deve, para cada planilha entregue, verificar se totais e subtotais fecham aritmeticamente, se células declaradas como resultado de fórmulas efetivamente correspondem ao recálculo dessas fórmulas, e se há inconsistências internas na apresentação dos dados.

**RF-WA-04.** Watson deve, para cada script SQL entregue, traduzir a consulta para linguagem natural descrevendo o que efetivamente o script executa — quais bases consulta, quais filtros aplica, quais agregações produz, qual estrutura de resultado retorna. A tradução deve ser fiel ao código, sem inferência sobre a intenção do autor.

**RF-WA-05.** Watson deve, para cada notebook Python entregue, traduzir a sequência de células executáveis para linguagem natural, descrevendo as transformações aplicadas, as bases de dados manipuladas e os resultados produzidos. A tradução deve respeitar a ordem real de execução e a presença de células condicionais ou de erro.

**RF-WA-06.** Watson deve identificar, sempre que possível, a cadeia de produção dos dados entre os documentos: qual script gerou qual dado em qual planilha, qual notebook transformou qual base, qual relatório consolida quais cálculos. Quando a cadeia não puder ser identificada por ausência de rastro, Watson deve registrar a lacuna como inconsistência.

**RF-WA-07.** Watson deve gerar análises sobre os dados que extrapolam a verificação literal: padrões observados, anomalias estatísticas, comportamentos que merecem atenção. Essas análises são insumos para Sherlock e para Mycroft, e devem ser claramente segregadas das verificações de integridade, identificadas em seção própria do output.

**RF-WA-08.** Watson deve, ao encontrar arquivo que não consegue analisar por formato desconhecido, corrupção, ou ausência de documentação técnica suficiente, registrar a ocorrência em campo dedicado do output, descrevendo o arquivo, a razão da inanalisabilidade e a tentativa realizada, e prosseguir com os demais arquivos. A inanalisabilidade não deve, por si só, abortar a análise dos demais arquivos.

**RF-WA-09.** Watson deve emitir, como output final, relatório graduado com classificação de severidade dos achados em ao menos três níveis: crítica (impede prosseguimento sem decisão expressa de Lestrade), atenção (não impede prosseguimento mas demanda registro destacado), informativa (registro padrão sem destaque). A classificação deve seguir critérios objetivos definidos no `skills.md` de Watson e ser tecnicamente detectável por inspeção do output.

**RF-WA-10.** Watson deve produzir o output em formato estruturado, com seções nomeadas e campos previsíveis, permitindo que Mycroft o consuma sem ambiguidade interpretativa e que o Orquestrador detecte mecanicamente a presença de alertas críticos. O formato exato é definido no `agent.md` e no SDD.

## **3.6 Sherlock (RF-SH)**

Sherlock é o agente executor responsável pelas verificações das Camadas 1, 2 e 3 da estratégia de validação: aderência metodológica, reprodutibilidade da extração e consistência do resultado final.

**RF-SH-01.** Sherlock deve receber, do Orquestrador, o pacote integrado por Mycroft contendo o inventário, os documentos entregues pela RFB, a decisão final de Mycroft sobre Watson, a análise consolidada de Watson e o briefing do módulo. Sherlock não deve iniciar análise sem o pacote completo nem solicitar arquivos adicionais por iniciativa própria.

**RF-SH-02.** Sherlock não deve, em nenhuma circunstância, analisar a integridade estrutural dos artefatos. Recebe o pacote já saneado por Watson e integrado por Mycroft, e opera sobre ele sem retomar verificações de Camada 0, conforme Artigo 7 da Constituição. Tecnicamente, o `agent.md` de Sherlock não inclui tools de parsing de planilhas ou tradução de SQL — essas pertencem a Watson.

**RF-SH-03.** Sherlock deve aplicar, sobre o pacote recebido, a metodologia homologada pelo Acórdão 2833/2025-Plenário correspondente ao módulo em análise. O documento da metodologia homologada deve estar acessível ao Sherlock como contexto, conforme configuração no `agent.md`.

**RF-SH-04.** Sherlock deve classificar cada ponto verificado segundo o sistema semântico estabelecido pelo Design System TCU-CBS: Atendido, Atendido Parcialmente, Divergência, Atenção, Limitação ou Não Verificável. A classificação deve ser fundamentada com referência explícita ao dispositivo metodológico correspondente.

**RF-SH-05.** Sherlock deve, ao identificar inconsistência que admita duas interpretações de peso equivalente, registrar o dilema com as duas interpretações descritas e fundamentadas, e apresentá-lo a Mycroft via Stranger's Room. Sherlock não deve resolver o dilema arbitrariamente nem omiti-lo, conforme Artigo 10 da Constituição.

**RF-SH-06.** Sherlock deve, para cálculos e testes que executar como parte de sua análise, garantir reprodutibilidade: cada cálculo deve poder ser refeito por terceiro a partir da fundamentação registrada no output. Cálculos sem rastreabilidade reprodutiva violam o Artigo 7 da Constituição.

**RF-SH-07.** Sherlock deve emitir, como output final, relatório classificado ponto a ponto, com fundamentação explícita por classificação e identificação clara dos pontos que requerem encaminhamento ao contraditório técnico com a RFB.

**RF-SH-08.** Sherlock deve produzir o output em formato estruturado equivalente ao adotado por Watson, permitindo consumo unívoco por Mycroft.

## **3.7 Stranger's Room (RF-SR)**

A Stranger's Room é o componente de persistência e protocolo dos artefatos de revisão de Mycroft sobre os agentes executores. Tecnicamente, é um diretório com convenção de nomes e um protocolo de escrita estritamente sequencial.

**RF-SR-01.** A Stranger's Room deve ser instanciada como subdiretório do diretório de trabalho do ciclo, em `workspace/cycles/{cycle_id}/stranger_room/`, organizada em subdiretórios por fase: `watson_integridade/` e `sherlock_validacao/`.

**RF-SR-02.** Os arquivos da Stranger's Room devem seguir convenção de nomes numerada e auto-explicativa, conforme estrutura: `01_apresentacao.md` para o output inicial do agente, `02_critica_mycroft_r1.md` para a primeira crítica de Mycroft (se houver), `03_resposta_r1.md` para a resposta do agente à primeira crítica, `04_critica_mycroft_r2.md` para a segunda crítica de Mycroft (se houver), `05_resposta_r2.md` para a resposta do agente à segunda crítica, e `99_decisao_final.md` para a decisão final fixada por Mycroft.

**RF-SR-03.** Cada arquivo da Stranger's Room deve conter frontmatter YAML mínimo com os campos: `cycle_id`, `phase`, `author` (Mycroft, Watson ou Sherlock), `role` (cargo formal do autor), `round` (número da rodada quando aplicável), `timestamp` (UTC ISO 8601), `content_hash` (SHA-256 do conteúdo do corpo). O corpo do arquivo é Markdown estruturado sem restrição rígida de formato, mas conformidade com o template documentado no `skills.md` do agente correspondente.

**RF-SR-04.** Os arquivos da Stranger's Room devem ser escritos uma única vez. Não há sobrescrita, não há edição, não há remoção. Em caso de erro de escrita, o sistema deve abortar a operação e registrar a falha, conforme Artigo 11 da Constituição.

**RF-SR-05.** A leitura sequencial dos arquivos da Stranger's Room de uma fase, na ordem numérica de seus prefixos, deve produzir uma transcrição coerente da deliberação técnica entre Mycroft e o agente executor, legível por inspeção humana direta sem necessidade de ferramentas auxiliares.

**RF-SR-06.** Ao final de cada fase, o sistema deve registrar no `audit_index.csv` os metadados agregados da Stranger's Room: número de rodadas executadas, presença de overrule de Mycroft sobre o agente, presença de alerta crítico (apenas para `watson_integridade`), presença de dilema interpretativo encaminhado (apenas para `sherlock_validacao`).

## **3.8 Motor de Saída (RF-MV)**

O Motor de Saída é o componente que executa a verificação peremptória exigida pelo Artigo 15 da Constituição antes da chancela final de Lestrade. Sua função é garantir que nenhum documento que saia do Departamento carregue marca interna, identificação de agente ou referência a estruturas próprias do Departamento.

**RF-MV-01.** O Motor de Saída deve ser invocado por Lestrade, mediante comando CLI dedicado, sobre o documento consolidado produzido pelo Orquestrador no diretório de output do ciclo.

**RF-MV-02.** O Motor de Saída deve varrer o documento à procura de ocorrências de: nomes próprios dos agentes (Mycroft, Watson, Sherlock, Lestrade, com variações como Holmes, John Watson, Inspetor Lestrade); cargos formais quando empregados em contexto que identifique um agente específico (a presença genérica do termo "Auditor Chefe" em contexto institucional pode ser legítima — a presença em frase como "o Auditor Chefe consolidou este relatório" não é); nomes simbólicos de estruturas internas (Stranger's Room, Sala dos Estrangeiros, Clube Diógenes, Projeto Diógenes); referências a artefatos internos (audit_index, traces, manifest, motor de start, motor de saída); identificadores técnicos do ciclo (cycle_id em formatos típicos como `MOD_010_A1_20260507T143000Z`).

**RF-MV-03.** O Motor de Saída deve gerar relatório de verificação listando todas as ocorrências detectadas, com localização precisa no documento (linha, contexto curto antes e depois) e classificação preliminar (nome de agente, cargo identificador, estrutura interna, artefato técnico, identificador de ciclo).

**RF-MV-04.** O Motor de Saída deve apresentar o relatório no console e aguardar decisão de Lestrade. Em caso de zero ocorrências, o Motor confirma a limpeza do documento e habilita a chancela final via comando CLI específico. Em caso de ocorrências, o Motor interrompe o fluxo e exige uma das três decisões de Lestrade: corrigir manualmente o documento (Lestrade edita e reinvoca o Motor), retornar a Mycroft para reprodução (Lestrade dispara comando que aciona Mycroft a regerar o output considerando a verificação), ou aceitar com justificativa registrada (Lestrade dispara comando que aceita as ocorrências detectadas, registrando justificativa no audit_index).

**RF-MV-05.** O Motor de Saída deve registrar, em todos os casos, sua execução no audit_index.csv: timestamp da invocação, quantidade de ocorrências detectadas, decisão de Lestrade, e hash do documento verificado. Esse registro é necessário para reconstruir, futuramente, o histórico de verificações e correções.

**RF-MV-06.** O Motor de Saída deve, em sua implementação inicial, operar com regras heurísticas explícitas (busca por palavras-chave, expressões regulares para identificadores) sem recurso a modelo de linguagem para a verificação. A simplicidade da implementação é virtude: o Motor de Saída é elemento crítico de governança e deve ser tecnicamente auditável por leitura direta de seu código.

## **3.9 Persistência (RF-PE)**

A persistência do Departamento é integralmente baseada em filesystem, com Markdown para conteúdo legível e CSV para índices estruturados. Não há banco de dados, não há serviço externo de armazenamento.

**RF-PE-01.** A raiz do espaço de trabalho do Departamento deve ser configurável via variável de ambiente `DIOGENES_WORKSPACE`, com valor padrão `./workspace/` relativo ao diretório do projeto. A configuração permite que a mesma instalação opere em diferentes ambientes (local, VPS, futuro Azure) sem alteração de código.

**RF-PE-02.** A estrutura interna do espaço de trabalho deve seguir a especificação:

```
workspace/
├── input/
│   └── {MOD_ID}/                       (entregas externas, intocáveis)
├── cycles/
│   └── {cycle_id}/
│       ├── manifest.md
│       ├── inputs/                     (cópias dos arquivos de input)
│       ├── stranger_room/
│       │   ├── watson_integridade/
│       │   └── sherlock_validacao/
│       └── output/
│           └── relatorio_*.md
└── audit_index.csv
```

**RF-PE-03.** O `audit_index.csv` deve ser o índice único e cronológico de todos os ciclos do Departamento, com colunas: `cycle_id`, `module_id`, `activity`, `status`, `started_at_utc`, `ended_at_utc`, `is_sigilo_module`, `previous_cycle_id` (preenchido apenas para Atividade 2), `mycroft_overruled_watson` (booleano), `mycroft_overruled_sherlock` (booleano), `watson_critical_alerts_count`, `sherlock_dilemmas_count`, `motor_saida_occurrences`, `motor_saida_decision`, `output_hash`, `lestrade_seal_at_utc`. As colunas referentes ao Motor de Saída e à chancela podem estar vazias enquanto o ciclo não atinge essas fases.

**RF-PE-04.** A escrita no `audit_index.csv` deve ser append-only para inserção de novos ciclos e atomicamente segura para atualização de status de ciclo existente. O sistema deve prevenir corrupção do arquivo em caso de interrupção abrupta — implementação via escrita em arquivo temporário e renomeação atômica.

**RF-PE-05.** Os arquivos no espaço de trabalho devem ser totalmente compatíveis com sincronização por OneDrive, Google Drive, Dropbox ou equivalentes. Isso implica: nomes de arquivo sem caracteres reservados, paths sem profundidade excessiva, ausência de arquivos de bloqueio (lock files) persistentes, ausência de arquivos com extensão ou metadados que disparem indexação automática indesejada (`.DS_Store`, `Thumbs.db` e equivalentes devem ser proativamente ignorados).

**RF-PE-06.** O sistema deve preservar integralmente o diretório de trabalho de cada ciclo encerrado, sem rotina de limpeza, compactação ou arquivamento automático. Conforme Artigo 16 da Constituição, nenhum arquivo é deletado.

## **3.10 CLI (RF-CL)**

A interface de linha de comando é o único ponto de interação humana com o sistema no piloto. Implementada via Typer, deve ser explícita, previsível e tecnicamente auditável.

**RF-CL-01.** O sistema deve expor o comando raiz `diogenes`, com subcomandos para cada operação distinta. A invocação `diogenes --help` deve listar todos os subcomandos disponíveis com descrição curta.

**RF-CL-02.** O subcomando `diogenes start --module {MOD_ID} --activity {1|2}` deve disparar o Motor de Start conforme RF-MS-01 a RF-MS-09.

**RF-CL-03.** O subcomando `diogenes confirm-manifest --cycle {cycle_id}` deve registrar a confirmação de Lestrade sobre o manifesto e disparar o Orquestrador conforme RF-OR-02.

**RF-CL-04.** O subcomando `diogenes proceed --cycle {cycle_id}` deve registrar a autorização de Lestrade para prosseguimento após notificação de alerta crítico conforme RF-OR-05.

**RF-CL-05.** O subcomando `diogenes pause --cycle {cycle_id}` deve interromper o ciclo após notificação de alerta crítico, marcar o status no `audit_index.csv` como `PAUSADO_LESTRADE` e preservar o estado para retomada.

**RF-CL-06.** O subcomando `diogenes resume --cycle {cycle_id}` deve retomar ciclo previamente pausado, retornando à fase em que foi interrompido.

**RF-CL-07.** O subcomando `diogenes verify-output --cycle {cycle_id}` deve disparar o Motor de Saída conforme RF-MV-01 a RF-MV-06.

**RF-CL-08.** O subcomando `diogenes seal --cycle {cycle_id}` deve registrar a chancela final de Lestrade no `audit_index.csv`, marcando o ciclo como `ENCERRADO_CHANCELADO`. O comando deve falhar com mensagem explícita se o Motor de Saída ainda não foi executado ou se foram detectadas ocorrências não resolvidas.

**RF-CL-09.** O subcomando `diogenes abort --cycle {cycle_id} --reason "{texto}"` deve permitir aborto manual de ciclo em qualquer estado, registrando o aborto e a razão no `audit_index.csv` e preservando o diretório de trabalho.

**RF-CL-10.** O subcomando `diogenes status --cycle {cycle_id}` deve exibir o estado atual do ciclo: fase, último arquivo da Stranger's Room escrito, próxima ação esperada, status no `audit_index.csv`.

**RF-CL-11.** O subcomando `diogenes list [--module {MOD_ID}] [--status {STATUS}]` deve listar ciclos, com filtros opcionais por módulo e por status, exibindo identificador, módulo, atividade, datas e status atual.

**RF-CL-12.** O subcomando `diogenes show --cycle {cycle_id} [--phase {watson|sherlock}]` deve exibir, formatado para leitura humana, o conteúdo da Stranger's Room do ciclo, opcionalmente filtrado por fase.

**RF-CL-13.** Todos os subcomandos devem ser idempotentes em sua natureza informativa (`status`, `list`, `show`) e seguros em sua natureza modificadora — em caso de invocação inválida, devem falhar antes de qualquer escrita, com mensagem explicando a razão da falha.

---

# **Bloco 4 — Requisitos Não Funcionais**

## **4.1 Lógica da Estrutura de Requisitos Não Funcionais**

Os requisitos não funcionais do piloto têm natureza distinta dos requisitos funcionais detalhados no Bloco 3. Enquanto aqueles enunciam o que o sistema deve fazer, estes enunciam como o sistema deve se comportar enquanto faz. Cobrem dimensões transversais — rastreabilidade, reprodutibilidade, custo, latência, portabilidade, observabilidade, segurança, manutenibilidade — que não pertencem a um componente específico mas afetam o sistema inteiro.

A relevância dos requisitos não funcionais para o Departamento é desproporcional ao que se observa em sistemas de software ordinários. Aqui, a rastreabilidade não é virtude operacional: é exigência constitucional explícita. A reprodutibilidade não é boa prática de engenharia: é critério de validade institucional do trabalho produzido. O custo, num piloto sustentado por recursos pessoais do desenvolvedor, é restrição prática que define quais experimentos são viáveis. A portabilidade não é antecipação de cenário hipotético: é compromisso operacional concreto, já que a transição de OpenRouter para Foundry está cravada como caminho evolutivo.

A nomenclatura segue o padrão `RNF-{DIMENSÃO}-{NÚMERO}`, onde a dimensão é uma sigla curta (`RAST` para rastreabilidade, `REPR` para reprodutibilidade, `CUST` para custo, `LATE` para latência, `PORT` para portabilidade, `OBSE` para observabilidade, `SEGU` para segurança e privacidade, `MANU` para manutenibilidade, `USAB` para usabilidade da CLI).

Cada requisito declara o atributo de qualidade com critério tecnicamente verificável quando possível. Quando o critério for qualitativo, a verificação dá-se por inspeção humana documentada, e isso é explicitado.

## **4.2 Rastreabilidade (RNF-RAST)**

A rastreabilidade é o atributo de qualidade mais carregado de exigência constitucional. Os Artigos 11 e 16 estabelecem registro integral, ausência de sobrescrita, ordem cronológica absoluta e preservação irrestrita de todo ciclo encerrado.

**RNF-RAST-01.** Todo raciocínio, decisão e conclusão produzidos no Departamento deve ser registrado em arquivo persistente no diretório de trabalho do ciclo. Não há decisão tomada por agente que viva apenas em memória — cada chamada de modelo e cada decisão produzida deve resultar em arquivo escrito antes da próxima chamada se iniciar.

**RNF-RAST-02.** Nenhum arquivo escrito pelo sistema durante a execução de um ciclo deve ser sobrescrito ou modificado após sua criação. Em caso de erro de escrita, a operação é abortada e a falha registrada — não há retentativa que sobrescreva o arquivo parcialmente escrito.

**RNF-RAST-03.** A nomeação de todo arquivo persistido deve permitir ordenação cronológica absoluta por nome, mediante uso consistente de prefixos numéricos sequenciais (Stranger's Room) ou timestamps em formato ISO 8601 compactado (manifesto, traces de falha, registros de eventos).

**RNF-RAST-04.** A leitura humana direta dos arquivos do diretório de trabalho de um ciclo, na ordem cronológica natural, deve permitir reconstrução completa do raciocínio do Departamento sobre o módulo. Esse critério é qualitativo e verificado por inspeção humana documentada como parte dos critérios de aceitação do piloto.

**RNF-RAST-05.** O `audit_index.csv` deve conter, ao final de cada ciclo encerrado, todas as informações necessárias para localizar e identificar o ciclo no espaço de trabalho. A integridade do arquivo é mantida por escrita atômica conforme RF-PE-04.

**RNF-RAST-06.** Toda chamada a um modelo de linguagem deve ser acompanhada de registro técnico em trace dedicado, contendo no mínimo: agente que invocou, modelo utilizado, provider, tokens enviados e recebidos, custo estimado, latência da chamada, e resposta bruta. O trace técnico fica em `workspace/cycles/{cycle_id}/_runtime/llm_calls/`, separado dos artefatos institucionais que vão para a Stranger's Room ou para o output.

**RNF-RAST-07.** O sistema deve permitir, mediante leitura do `audit_index.csv` e do diretório de trabalho de qualquer ciclo, a reconstrução completa do estado do ciclo em qualquer instante de sua execução. Não deve existir estado relevante apenas em memória do processo — toda mudança de estado é precedida de escrita persistente.

## **4.3 Reprodutibilidade (RNF-REPR)**

A reprodutibilidade é o atributo que permite que terceiros — auditores futuros, revisores institucionais, o próprio Departamento em momento posterior — refaçam o trabalho realizado sobre um módulo e obtenham resultado equivalente. No contexto do piloto, a reprodutibilidade absoluta é tecnicamente impossível, dada a natureza não determinística dos modelos de linguagem mesmo sob temperatura baixa. O que é exigível é a reprodutibilidade do procedimento e a rastreabilidade total dos parâmetros que produziram cada resultado, de modo que a divergência entre execuções possa ser explicada por fatores conhecidos e isolados.

**RNF-REPR-01.** Toda chamada a modelo deve ter registrados os parâmetros completos da invocação: prompt de sistema completo, prompt do usuário completo, modelo, temperatura, max_tokens, seed quando aplicável, e quaisquer outros parâmetros que afetem a saída. Esses parâmetros ficam no trace técnico de cada chamada.

**RNF-REPR-02.** O sistema deve, sempre que o provider de modelo permitir, fixar uma seed determinística por chamada, derivada de combinação previsível entre `cycle_id`, fase e número da chamada. A fixação de seed não garante determinismo absoluto entre providers, mas reduz substancialmente a variância dentro de um mesmo provider e permite que o investigador identifique que duas execuções partiram do mesmo ponto de aleatoriedade.

**RNF-REPR-03.** O sistema deve ser capaz de operar em modo de re-execução sobre um ciclo já concluído, lendo os parâmetros registrados no trace técnico e disparando novas chamadas idênticas aos modelos, para fins de comparação ou de re-validação. Esse modo é acionado por subcomando dedicado da CLI a ser detalhado no SDD.

**RNF-REPR-04.** A versão do código do Departamento que produziu cada ciclo deve ser registrada no manifesto de abertura, mediante hash do commit Git correspondente. Re-execuções em versões diferentes do código são identificadas como tal e não confundidas com re-execuções idênticas.

**RNF-REPR-05.** As versões dos modelos efetivamente utilizadas em cada chamada — quando o provider expõe essa informação como `system_fingerprint` ou equivalente — devem ser registradas no trace técnico. Mudanças silenciosas de versão pelo provider são detectáveis posteriormente.

## **4.4 Custo (RNF-CUST)**

O custo é restrição prática estruturante do piloto. Os recursos vêm do desenvolvedor pessoalmente, e o desperdício orçamentário em fase de validação operacional inviabiliza fases posteriores de benchmarking qualitativo.

**RNF-CUST-01.** O sistema deve registrar, ao final de cada ciclo, o custo total em USD pago aos providers de modelo, discriminado por agente, por chamada e por fase. Essa informação fica em campo dedicado do `audit_index.csv` e é detalhada nos traces técnicos.

**RNF-CUST-02.** O sistema deve permitir, mediante configuração em `runtime.yaml`, a definição de teto de custo por ciclo. Ao atingir o teto durante a execução, o sistema interrompe o ciclo com aviso explícito, registrando o estado parcial e preservando o diretório de trabalho. A retomada exige decisão expressa de Lestrade via CLI.

**RNF-CUST-03.** O custo-alvo do ciclo da Atividade 1 sobre o módulo sintético na Fase A (modelos free) é zero USD, dado o uso exclusivo de modelos sem cobrança. O custo-alvo na Fase B (modelos baratos para benchmarking) é estabelecido em até cinco USD por ciclo completo. O custo-alvo da Fase D (MOD_010 com modelos baratos) é estabelecido em até dez USD por ciclo, considerando o volume real do módulo. Esses valores são metas, não limites rígidos — divergências significativas entre o esperado e o realizado são insumo de revisão da estratégia de modelos, não causa de falha do piloto.

**RNF-CUST-04.** O `agent.md` de cada agente deve declarar limites de tokens (`max_tokens` por chamada e teto agregado por ciclo). O Orquestrador deve respeitar esses limites e abortar chamadas que os ultrapassem antes de incorrer no custo.

**RNF-CUST-05.** O sistema deve, em caso de uso de modelos free do OpenRouter, lidar graciosamente com limites de taxa e indisponibilidades intermitentes que caracterizam essa categoria de modelos. Falha por limite de taxa é registrada como falha temporária e a política de retry aplica-se. Falha persistente após esgotamento da política de retry é tratada conforme RF-OR-10.

## **4.5 Latência (RNF-LATE)**

A latência define o tempo de resposta percebido pelo operador humano. No piloto, com operação CLI síncrona e auditor humano aguardando entre fases, a latência razoável é critério de usabilidade prática. Latências excessivas tornam o piloto inviável de operar.

**RNF-LATE-01.** O ciclo completo da Atividade 1 sobre o módulo sintético, em Fase A com modelos free, deve concluir em até trinta minutos. Esse tempo inclui as duas fases da Stranger's Room com até duas rodadas cada, a consolidação final por Mycroft e a verificação pelo Motor de Saída. O tempo é medido do `diogenes confirm-manifest` até o estado pronto para chancela final.

**RNF-LATE-02.** O ciclo completo da Atividade 1 em Fase B com modelos baratos (Kimi K2, Qwen 3 Max ou DeepSeek v4) deve concluir em até quinze minutos.

**RNF-LATE-03.** A latência de cada chamada individual a modelo deve ser registrada no trace técnico. O sistema deve, ao detectar latência superior a cinco minutos em chamada individual, exibir aviso no console informando o operador de que a chamada está em andamento e o tempo decorrido, atualizando a cada minuto. Sem feedback visual, o operador não tem como distinguir lentidão legítima de travamento.

**RNF-LATE-04.** O Motor de Saída, por operar com regras heurísticas sem chamada a modelo, deve concluir sua verificação em segundos, independentemente do tamanho do documento. Latência superior a trinta segundos no Motor de Saída indica problema de implementação a ser corrigido.

**RNF-LATE-05.** Comandos da CLI de natureza informativa (`status`, `list`, `show`) devem responder em até dois segundos sob o volume típico do piloto (até cem ciclos no `audit_index.csv`).

## **4.6 Portabilidade (RNF-PORT)**

A portabilidade é compromisso explícito do piloto: o sistema precisa rodar em três ambientes sem alteração de código, apenas com configuração distinta. Esse compromisso protege a transição futura para Foundry e elimina dependências silenciosas que travariam essa transição.

**RNF-PORT-01.** O sistema deve rodar em Linux, macOS e Windows sem alteração de código. Caminhos de arquivo devem ser construídos via `pathlib.Path` em todo o código, sem concatenação manual com separadores. Nomes de arquivo escritos pelo sistema devem evitar caracteres reservados em qualquer dos três sistemas.

**RNF-PORT-02.** O sistema deve rodar em três ambientes-alvo distintos sem alteração de código: máquina local com OneDrive sincronizado, VPS particular sem OneDrive, ambiente de teste simulando estrutura prevista para Azure (volume montado em caminho configurável). A diferença entre ambientes resolve-se por variáveis de ambiente e por `runtime.yaml`.

**RNF-PORT-03.** A camada `LLMClient` deve isolar todo conhecimento sobre providers específicos. O código dos agentes, do Orquestrador e dos motores não deve conter referência direta a OpenRouter, a Foundry, a Anthropic ou a qualquer provider. A troca de provider em produção é feita exclusivamente em `agents_spec.yaml` e na seleção do cliente em ponto único do código.

**RNF-PORT-04.** Toda configuração do sistema deve estar concentrada em três arquivos: `.env` (segredos, variáveis de ambiente), `agents_spec.yaml` (mapeamento agente → modelo → provider, parâmetros de runtime), `runtime.yaml` (caminhos de workspace, limites de custo, timeouts, política de retry). O código não deve conter configuração hardcoded.

**RNF-PORT-05.** O sistema não deve depender de serviços externos além do provider de LLM e do filesystem. Não há dependência de banco de dados, fila de mensagens, cache distribuído, serviço de autenticação externa ou qualquer infraestrutura adicional.

**RNF-PORT-06.** A inicialização do sistema em ambiente novo deve poder ser feita por sequência documentada e curta: clonar repositório, criar ambiente virtual Python, instalar dependências via `pip install -e .`, copiar `.env.example` para `.env` e preencher chaves, executar `diogenes init` para criar a estrutura inicial do workspace. A documentação dessa sequência integra o `README.md` do repositório e é critério de aceitação do piloto.

## **4.7 Observabilidade (RNF-OBSE)**

A observabilidade no piloto não tem o sentido pleno que assume em sistemas distribuídos de produção. É o conjunto mínimo de capacidades que permitem ao operador humano entender, em tempo de execução e em análise posterior, o que o sistema está fazendo, o que fez, e por quê.

**RNF-OBSE-01.** O sistema deve emitir, durante a execução de um ciclo, mensagens estruturadas no console identificando a fase corrente, o agente em execução, a chamada de modelo em andamento, e a transição entre fases. As mensagens utilizam a biblioteca `rich` para formatação legível com cores semânticas conforme o Design System TCU-CBS.

**RNF-OBSE-02.** O sistema deve manter, por ciclo, log técnico estruturado em formato JSONL no diretório `workspace/cycles/{cycle_id}/_runtime/events.jsonl`. Cada linha do log é evento estruturado com timestamp UTC, tipo de evento, fase, agente, dados específicos do evento. O log permite reconstrução granular da execução para depuração.

**RNF-OBSE-03.** Os traces técnicos das chamadas a modelo, conforme RNF-RAST-06, ficam em `workspace/cycles/{cycle_id}/_runtime/llm_calls/`, com um arquivo JSON por chamada, nomeado por timestamp e contendo a invocação completa e a resposta bruta.

**RNF-OBSE-04.** O subcomando `diogenes status --cycle {cycle_id}` deve produzir relatório textual conciso do estado atual do ciclo, agregando informações do `audit_index.csv`, do log de eventos e do estado do diretório de trabalho. Em ciclo em andamento, deve indicar a fase corrente e a próxima ação esperada.

**RNF-OBSE-05.** O sistema não deve, no piloto, integrar-se a serviços externos de observabilidade (Datadog, Grafana, OpenTelemetry collectors). Toda observabilidade é local, baseada em arquivos no workspace, legível por inspeção humana direta ou por ferramentas locais simples. Essa restrição é deliberada e protege a portabilidade do piloto.

## **4.8 Segurança e Privacidade (RNF-SEGU)**

A segurança no piloto cobre dois domínios distintos: o segredo das chaves de API e a privacidade dos dados que trafegam pelo sistema. O segundo domínio é simplificado pela natureza do piloto — não há dados sob sigilo fiscal real sendo processados — mas as práticas precisam ser estabelecidas desde já porque a transição para produção em Foundry vai operar sobre material sensível.

**RNF-SEGU-01.** Chaves de API e quaisquer outros segredos devem residir exclusivamente em variáveis de ambiente, carregadas via `.env` ou via mecanismo de injeção do ambiente externo. Nenhum segredo deve ser hardcoded em código, em arquivo de configuração versionado, ou em manifesto.

**RNF-SEGU-02.** O `.env` do projeto Diógenes deve estar listado em `.gitignore` e nunca ser versionado. O arquivo `.env.example`, com chaves esperadas e valores fictícios, é versionado e serve de documentação.

**RNF-SEGU-03.** O sistema deve, ao registrar traces técnicos de chamadas a modelo, redatar automaticamente quaisquer ocorrências de segredos conhecidos. A presença acidental de chave de API em log é falha tratável por mecanismo de filtragem na escrita.

**RNF-SEGU-04.** Os dados que compõem os inputs do piloto, na Fase D com MOD_010, são dados que já foram tratados pelo GT Reforma Tributária para o piloto de validação concluído anteriormente. Não há dados pessoais identificáveis sendo manipulados pelo Departamento no piloto. Esse fato é registrado no PRD e no SDD para memória institucional, mas não exime o sistema de operar com prudência: a infraestrutura de anonimização que será exigida em produção é antecipada como evolução obrigatória pós-piloto.

**RNF-SEGU-05.** O sistema não deve, no piloto, transmitir dados a serviços externos além do provider de LLM em uso. Os providers utilizados (OpenRouter na Fase A, B e D do piloto) operam sob seus próprios termos de privacidade, e o operador deve conhecer e aceitar esses termos antes da operação. A documentação do piloto registra explicitamente os providers utilizados e onde encontrar seus termos.

**RNF-SEGU-06.** A versão de produção que operará em Azure Foundry sobre dados reais sob sigilo fiscal exigirá controles adicionais — anonimização prévia, política de retenção, isolamento de tenancy — que estão fora do escopo do piloto mas são marcados como pré-condição obrigatória da transição.

## **4.9 Manutenibilidade (RNF-MANU)**

A manutenibilidade no piloto é virtude estrutural: o sistema precisa ser legível, compreensível e modificável por outras pessoas além do desenvolvedor inicial, dado que evoluirá ao longo de anos até 2032 e provavelmente passará por múltiplas mãos.

**RNF-MANU-01.** O código deve seguir convenções padrão de Python: PEP 8 para estilo, type hints completos via `typing` ou sintaxe nativa de Python 3.11+, docstrings em formato Google ou NumPy para todas as funções públicas. Conformidade verificada por `ruff` e `mypy` em modo estrito.

**RNF-MANU-02.** O código deve ser organizado em módulos com responsabilidades estritamente delimitadas, conforme estrutura de repositório a ser detalhada no SDD. Acoplamento entre módulos via interfaces explícitas (Protocols, classes abstratas), não via importação de implementações concretas.

**RNF-MANU-03.** Dependências externas devem ser minimizadas e, quando presentes, justificadas no `pyproject.toml` por comentário ou em documento dedicado. A ausência de framework de agentes é decisão arquitetural, não omissão.

**RNF-MANU-04.** O sistema deve possuir suíte de testes automatizados cobrindo, no mínimo, os componentes críticos: Motor de Start, Motor de Saída, Orquestrador, persistência. Testes dos agentes utilizam mocks dos providers de LLM, evitando custo e flutuação. A cobertura mínima alvo é setenta por cento das linhas dos componentes não-agente.

**RNF-MANU-05.** A suíte de testes deve incluir teste de integração end-to-end que executa o ciclo completo da Atividade 1 sobre o módulo sintético com mocks de LLM retornando respostas predefinidas. Esse teste é a salvaguarda primária contra regressões na orquestração.

**RNF-MANU-06.** O `README.md` do repositório deve conter, no mínimo: descrição curta do projeto, requisitos de sistema (Python 3.11+, dependências), sequência de instalação, sequência de operação básica do piloto, ponteiros para a documentação institucional (PRD, SDD, documentos antecedentes do TCU).

**RNF-MANU-07.** A documentação institucional (PRD, SDD, documentos antecedentes) deve estar acessível no próprio repositório, em diretório `docs/`, como Markdown ou como referência aos arquivos docx originais. A separação entre código e documentação institucional é convenção, não barreira.

## **4.10 Usabilidade da CLI (RNF-USAB)**

A CLI é o único ponto de interação humana com o sistema no piloto, e sua usabilidade afeta diretamente a viabilidade prática da operação. Auditor humano frustrado com CLI confusa simplesmente abandona o piloto.

**RNF-USAB-01.** Todos os subcomandos da CLI devem ter documentação inline acessível via `--help`, com descrição da função, parâmetros aceitos, exemplos de uso e referência aos requisitos funcionais que implementam.

**RNF-USAB-02.** As mensagens de erro da CLI devem ser claras, identificar a causa do erro, e indicar a ação corretiva esperada. Mensagens de erro genéricas (`Error: failed`, `Operation aborted`) são inaceitáveis. Padrão alvo: a mensagem de erro deve permitir que o operador resolva o problema sem consultar a documentação ou o código.

**RNF-USAB-03.** A CLI deve, em comandos modificadores de estado (`start`, `proceed`, `seal`, `abort`), exibir confirmação explícita do que será executado antes da execução, permitindo cancelamento rápido em caso de invocação acidental. Exceções: comandos com `--yes` ou `--force` para uso em scripts não interativos.

**RNF-USAB-04.** A CLI deve manter consistência terminológica com a Constituição e com os documentos institucionais. Os termos "manifesto", "ciclo", "fase", "Stranger's Room", "chancela", "Motor de Start", "Motor de Saída" são empregados com o mesmo sentido em todo o sistema. Inconsistência terminológica entre documentação e CLI é falha tratável.

**RNF-USAB-05.** A formatação de saída da CLI utiliza cores e tipografia conforme o sistema cromático TCU-CBS, na medida em que a biblioteca `rich` permite. As cores semânticas de status (Atendido, Divergência, Atenção, Limitação, Não Verificável) seguem o sistema definido pelo Design System.

---

# **Bloco 5 — Restrições e Premissas**

## **5.1 Lógica da Distinção entre Restrições e Premissas**

Restrições e premissas são, em PRDs, frequentemente tratadas como sinônimos. No piloto Diógenes, a distinção é importante e deliberada: cada categoria tem natureza, origem e tratamento operacional distintos.

**Restrições** são limites externos impostos ao piloto que o desenvolvimento não pode contornar nem alterar. Vêm de decisões institucionais já tomadas (a Constituição, os documentos antecedentes do GT e do Departamento), de limitações técnicas concretas do ambiente (orçamento pessoal, ausência de infraestrutura institucional na fase do piloto), ou de marcos legais e normativos (sigilo fiscal, Acórdão 2833/2025-Plenário). Restrições são cumpridas, não negociadas.

**Premissas** são suposições que o piloto adota como verdadeiras para poder ser planejado e executado, mas que podem se revelar falsas no decorrer do trabalho. Vêm de expectativas razoáveis sobre comportamento de terceiros (estabilidade do OpenRouter, disponibilidade de modelos free, qualidade do material entregue pela RFB no MOD_010), sobre ferramentas (estabilidade das bibliotecas Python utilizadas), ou sobre o próprio ambiente operacional (disponibilidade contínua da máquina ou VPS de teste). Premissas são monitoradas, e quando se revelam falsas, exigem replanejamento.

A separação rigorosa permite que, em qualquer momento do piloto, o operador identifique se está enfrentando um limite que precisa ser respeitado ou uma suposição que precisa ser revista. A confusão entre as duas categorias produz, na prática, dois tipos de falha: tentar contornar restrições legítimas (gerando trabalho descartável e exposição institucional) ou tratar como imutáveis premissas que poderiam ser revisadas (gerando rigidez injustificada).

A nomenclatura segue o padrão `R-{NÚMERO}` para restrições e `P-{NÚMERO}` para premissas, sem subdivisão por dimensão, já que cada item é tratado individualmente.

## **5.2 Restrições**

**R-01. Conformidade integral com a Constituição do Departamento.** Os dezesseis artigos da Constituição estabelecida no Bloco 5 do documento conceitual são restrição absoluta. Nenhuma decisão de implementação do piloto pode contradizer artigo da Constituição. Em caso de aparente conflito entre uma decisão de implementação tecnicamente conveniente e um artigo constitucional, a Constituição prevalece sem exceção. Casos concretos já antecipados: a sequencialidade absoluta entre agentes (Artigo 3) impede paralelização ainda que seja tecnicamente viável; o limite de duas rodadas de revisão (Artigo 8) impede uma terceira rodada ainda que produzisse melhor resultado; a impessoalidade dos documentos (Artigo 14) impede assinatura no corpo ainda que melhorasse a leitura; a porta única de saída via Lestrade (Artigo 15) impede atalhos de automação ainda que reduzissem trabalho humano. Esses não são exemplos hipotéticos: são pressões reais que vão aparecer no desenvolvimento.

**R-02. Conformidade com a estratégia integrada de validação do GT.** O documento `GT_CBS_Estrategia_Integrada_Validacao.docx` estabelece o fluxo operacional de seis etapas, as quatro camadas de validação, os critérios de seleção de módulos para a Sala de Sigilo, o princípio Human-in-the-Gate em todos os pontos críticos, e a posição do Departamento como executor das etapas técnicas dentro de fluxo mais amplo conduzido pelo GT. O piloto não recria nem altera essa estratégia, opera sobre o recorte previsto para o Departamento.

**R-03. Conformidade com a metodologia homologada pelo Acórdão 2833/2025-Plenário.** A metodologia homologada é a única base normativa válida para análise de mérito realizada no Departamento, conforme Artigo 2 da Constituição. No piloto, isso significa que Sherlock opera tendo como referência o documento da metodologia homologada — ainda que, no módulo sintético da Fase A e Fase B, o documento de referência seja uma versão fabricada para fins de teste —, e nunca propõe metodologia alternativa nem substitui as escolhas técnicas que estão dentro do espaço que a metodologia permite.

**R-04. Operação exclusiva em ambiente local ou VPS particular.** O piloto não roda em infraestrutura institucional do TCU, da RFB ou de qualquer órgão público. A máquina é do desenvolvedor, ou VPS por ele contratada com seus próprios recursos. Nenhuma integração com sistemas internos institucionais é exercitada nesta fase.

**R-05. Provedor de modelos exclusivamente OpenRouter na fase de piloto.** Não há, no piloto, uso de Azure AI Foundry, da API direta de Anthropic, OpenAI, Google ou qualquer outro provedor que não seja OpenRouter. A escolha por OpenRouter unifica a interface de chamada e simplifica o benchmarking. A migração para Foundry é prevista como evolução pós-piloto, conforme Bloco 9.

**R-06. Orçamento pessoal do desenvolvedor para o piloto.** O custo total do piloto é arcado pelo próprio desenvolvedor. Isso impõe contenção severa nas Fases A (zero USD), B (até cinco USD por ciclo) e D (até dez USD por ciclo). A Fase C (estado-alvo Foundry) está fora do piloto e fora do orçamento pessoal.

**R-07. Ausência de banco de dados ou serviço externo de armazenamento.** O piloto opera integralmente em filesystem, com Markdown para conteúdo legível e CSV para índices estruturados, conforme RF-PE-01 a RF-PE-06. Não há SQLite, PostgreSQL, MongoDB, S3 ou qualquer outra forma de persistência além do filesystem do sistema operacional anfitrião.

**R-08. Compatibilidade com sincronização por OneDrive.** O `workspace/` do Departamento, na máquina local do desenvolvedor, está dentro de pasta sincronizada por OneDrive. A escolha de filesystem flat com Markdown é, em parte, consequência desta restrição. Nomes de arquivo, profundidade de paths e ausência de lock files persistentes seguem essa exigência conforme RF-PE-05.

**R-09. Operação por usuário único, sem concorrência.** O piloto roda em sessão única, sob operação de um único auditor (o desenvolvedor exercendo o papel de Lestrade). Não há suporte a múltiplos operadores simultâneos, múltiplas sessões concorrentes, nem mecanismo de bloqueio para acesso compartilhado. A operação multiusuário é evolução pós-piloto.

**R-10. Atividades 3, 4 e 5 fora do escopo do piloto.** As atividades exclusivas dos módulos selecionados para a Sala de Sigilo — roteiro de perguntas para reunião extraordinária, roteiro de testes para execução em campo, validação ad hoc dos dados coletados — não são exercitadas no piloto, conforme Bloco 1 do PRD. A arquitetura é construída de forma a permitir extensão para essas atividades posteriormente, sem refatoração estrutural.

*Nota qualificadora a R-10 — flexibilidade para atividades ad hoc por solicitação de Lestrade.* As cinco atividades estabelecidas no Bloco 4 do documento conceitual são as atividades centrais e previsíveis do Departamento, e o piloto não exercita atividades além das previstas. No entanto, a Constituição não fecha o catálogo de atividades possíveis em cinco itens imutáveis: o item 1.7 do documento conceitual já antecipa explicitamente que *"o Departamento poderá produzir outros tipos de produto, caso seja identificada essa necessidade no decorrer do desenvolvimento e dos testes piloto"*. A arquitetura do sistema, no piloto e na evolução posterior, preserva flexibilidade mínima para atividades ad hoc solicitadas por Lestrade dentro dos limites constitucionais — atividades que respeitem os limites de cada agente (Artigos 5, 6 e 7), sigam o princípio de delegação por Mycroft (Artigo 4), preservem a sequencialidade absoluta (Artigo 3) e a porta única de saída via Lestrade (Artigos 1 e 15). Essa flexibilidade não amplia o escopo do piloto, mas protege o Departamento contra rigidez arquitetural que impediria respostas a necessidades genuínas surgidas durante a operação.

**R-11. Suporte a um único módulo real por vez no piloto.** A Fase D do roadmap exercita o sistema sobre o MOD_010 (Pessoa Física). Os demais dezesseis módulos da CBS estão fora do escopo do piloto. O suporte ao processamento dos dezessete módulos em produção é evolução pós-piloto, conforme Bloco 9.

**R-12. Idioma português brasileiro em todos os artefatos institucionais.** Todos os documentos produzidos pelo Departamento — manifesto, traces da Stranger's Room, decisões finais, relatórios — são redigidos em português brasileiro, na norma culta, conforme regras de escrita estabelecidas no projeto. Mensagens da CLI seguem o mesmo padrão. Apenas elementos técnicos puramente internos (nomes de variáveis, identificadores de função, mensagens de log de baixo nível) podem usar inglês, e mesmo assim com critério.

**R-13. Geração de documento docx final fora do escopo principal do piloto.** A conversão dos relatórios de Markdown para docx no padrão Design System TCU-CBS v5 é responsabilidade do motor gerador de documentos já existente no projeto maior. O piloto produz Markdown estruturado conforme o que o motor consome, mas não inclui a integração refinada com o motor como critério de aceitação. A integração é tarefa pós-piloto, conforme Bloco 9.

## **5.3 Premissas**

**P-01. OpenRouter mantém disponibilidade operacional adequada durante o piloto.** Assume-se que o serviço OpenRouter estará disponível com latência razoável, taxa de erro baixa e ausência de mudanças disruptivas na API durante o período do piloto. A premissa é razoável dado o histórico de operação do serviço, mas é monitorada: indisponibilidade prolongada ou degradação significativa exige replanejamento, possivelmente com troca temporária de provedor (uso direto da API Anthropic ou OpenAI, mediante novo orçamento e adaptação da camada `LLMClient`).

**P-02. Modelos free do OpenRouter permanecem disponíveis durante a Fase A.** A Fase A do roadmap depende da existência, no catálogo do OpenRouter, de modelos com cobrança zero suficientemente capazes de executar o ciclo completo. Essa categoria oscila — modelos entram e saem do catálogo free, providers ajustam políticas. A premissa é razoável no momento do planejamento, mas a fixação da lista exata de modelos free utilizados é feita imediatamente antes do início da Fase A, consultando o catálogo vigente.

**P-03. Modelos baratos da Fase B mantêm preço e qualidade durante o benchmarking.** Os modelos previstos para a Fase B (Kimi K2.6, Qwen 3 Max, DeepSeek v4 ou equivalentes vigentes na data) têm precificação muito baixa por token e qualidade adequada para análise normativa simples. A premissa é razoável dado o estado atual do mercado, mas é monitorada: alteração significativa de preço ou retirada de catálogo de algum desses modelos exige seleção de substituto antes da Fase B.

**P-04. Bibliotecas Python da stack permanecem estáveis durante o piloto.** A stack proposta — Python 3.11+, Pydantic 2.x, httpx, Typer, Rich, python-frontmatter, PyYAML, python-docx, openpyxl, sqlparse, nbformat, pytest — é composta por bibliotecas maduras com baixo risco de breaking changes em janelas curtas. A premissa é razoável, mas a fixação de versões em `pyproject.toml` é prática obrigatória, e as versões fixadas têm compatibilidade verificada antes do início do piloto.

**P-05. Material do MOD_010 entregue pela RFB está em estado consultável e suficientemente documentado.** A Fase D depende de que o material do MOD_010 (Pessoa Física), entregue pela RFB e tratado pelo GT no piloto de validação concluído, esteja efetivamente disponível, organizado e com documentação técnica suficiente para que Watson e Sherlock possam operar sobre ele. A premissa é razoável dado o status declarado, mas a verificação concreta da disponibilidade e da qualidade do material é a primeira atividade da Fase D, antes de qualquer execução do sistema sobre ele.

**P-06. Capacidade dos modelos selecionados é suficiente para os papéis previstos.** Assume-se que os modelos das categorias previstas — modelos free na Fase A, modelos baratos na Fase B, modelos de ponta na hipotética Fase C — têm capacidade analítica suficiente para executar os papéis dos agentes (validação técnica determinística para Watson, análise normativa complexa para Sherlock, alta síntese estratégica para Mycroft). A premissa é razoável para Sherlock e Mycroft com modelos de ponta, e é exatamente o que se quer testar empiricamente para os modelos baratos. A não satisfação da premissa em qualquer combinação leva à substituição do modelo na configuração, não à mudança da arquitetura.

**P-07. Ambiente de execução do piloto permanece operacional.** A máquina local do desenvolvedor (ou a VPS particular utilizada) permanece disponível, com acesso à internet, espaço em disco suficiente para o crescimento do `workspace/` ao longo dos ciclos, e ausência de interferências de antivírus ou de políticas corporativas que afetem a operação. A premissa é razoável dado o controle do desenvolvedor sobre o ambiente, mas eventos como falha de hardware ou perda de acesso à VPS exigem replanejamento.

**P-08. O OneDrive sincroniza arquivos do `workspace/` sem corrupção ou conflito.** Assume-se que o OneDrive opera de forma estável sobre os arquivos do Departamento, sem produzir versões em conflito por sincronização tardia, sem corromper arquivos durante operações de escrita pelo sistema, sem renomear arquivos para resolução de conflitos próprios. A premissa é razoável para uso por usuário único em máquina única, e foi parcialmente protegida pelas escolhas de design (escrita atômica, ausência de lock files, paths sem profundidade excessiva). Conflitos persistentes exigem migração para diretório fora do OneDrive ou uso de VPS.

**P-09. Convenções estabelecidas no Design System TCU-CBS v5 são suficientemente estáveis durante o piloto.** O sistema cromático, as classificações semânticas de status, as regras tipográficas e demais elementos do Design System utilizados pelo piloto não passam por revisão estrutural durante a fase de validação operacional. Pequenos ajustes são absorvidos sem retrabalho significativo; revisão estrutural exigiria adaptação coordenada do piloto e do motor gerador de documentos.

**P-10. Tempo do desenvolvedor disponível para execução supervisionada do piloto.** O piloto exige presença ativa do desenvolvedor para exercer o papel de Lestrade — confirmação de manifesto, autorização de prosseguimento após alerta crítico, decisão sobre verificação do Motor de Saída, chancela final. Cada ciclo demanda atenção humana em múltiplos pontos, ainda que cada decisão consuma poucos minutos. A premissa é que o desenvolvedor tem disponibilidade para executar os ciclos previstos no roadmap dentro do horizonte temporal do piloto. Indisponibilidade prolongada estende o cronograma.

**P-11. A versão atual da Constituição e dos documentos antecedentes é estável durante o piloto.** Os documentos `dva_cbs_completo_v03.docx` e `GT_CBS_Estrategia_Integrada_Validacao.docx` são a base normativa e arquitetural sobre a qual o piloto é construído. Assume-se que esses documentos não passam por revisão substantiva durante a fase do piloto. Revisão pontual de redação é absorvida sem retrabalho; revisão estrutural — alteração de artigo da Constituição, adição ou remoção de atividade, mudança de definição de papel de agente — exige adaptação coordenada do piloto.

**P-12. Suficiência da abstração `LLMClient` para futura migração ao Foundry.** A abstração projetada para isolar o provider de LLM é suficiente para que a migração de OpenRouter para Azure AI Foundry, no estado-alvo de produção, exija apenas implementação de novo cliente concreto sem alteração do código de aplicação. A premissa é razoável dada a familiaridade entre as duas APIs (ambas seguem padrão OpenAI-compatible em larga medida), mas a confirmação só ocorre quando a implementação do `AzureFoundryClient` for efetivamente exercitada. Diferenças não antecipadas exigirão pequenas adaptações pontuais, esperadas e absorvíveis.

## **5.4 Itens Que Não São Restrições nem Premissas**

Há quatro categorias de itens que ocasionalmente aparecem em PRDs como restrições ou premissas mas que não pertencem a nenhuma das duas categorias no piloto Diógenes, e a explicitação aqui evita confusão futura.

**Decisões de design técnico.** A escolha por Python custom sem framework de agentes, por monolito sequencial single-process, pela camada `LLMClient` como abstração, pela Stranger's Room como diretório com convenção de nomes, pelo sistema cromático do Design System na CLI — todas são decisões de design tomadas no PRD com base em raciocínio técnico explícito. Não são restrições impostas externamente, nem premissas suposicionadas; são escolhas justificadas. Mudá-las exige nova decisão de design fundamentada, não simples replanejamento por revisão de premissa.

**Critérios de sucesso e aceitação.** Os critérios estabelecidos no Bloco 1 (sucesso do piloto) e nos casos de uso do Bloco 2 (aceitação dos casos de uso) são metas a serem atingidas, não condições a serem cumpridas externamente. O não atingimento de critério de sucesso indica que o piloto ainda não está concluído, não que uma restrição foi violada ou uma premissa caiu.

**Riscos identificados.** O PRD não inclui seção dedicada a riscos por escolha deliberada — os riscos relevantes estão distribuídos como premissas monitoradas, e essa abordagem é mais operacional que o registro abstrato de riscos com probabilidade e impacto típico de PRDs corporativos. Se for útil, em fase posterior, consolidar riscos em seção dedicada para apresentação institucional, isso é trabalho de comunicação, não revisão estrutural do piloto.

**Dependências externas a serem provisionadas.** Itens como obtenção de chave OpenRouter, instalação de Python na máquina, configuração de OneDrive, contratação de VPS quando aplicável — são pré-requisitos de operação que o desenvolvedor provisiona antes do início do piloto. Documentados no `README.md` do repositório, conforme RNF-MANU-06, mas não entram como restrições ou premissas no PRD.

---

# **Bloco 6 — Critérios de Aceitação**

## **6.1 Lógica da Estrutura de Critérios de Aceitação**

Os critérios de aceitação do piloto cumprem função distinta dos requisitos funcionais (Bloco 3) e não funcionais (Bloco 4). Aqueles definem o que o sistema deve fazer e como deve se comportar enquanto faz; os critérios de aceitação aqui definem o que precisa ser observado para que o piloto seja considerado concluído com sucesso e habilitado a transitar para a fase seguinte do projeto.

A diferença prática é essencial: um requisito pode estar implementado tecnicamente sem que o critério de aceitação correspondente esteja satisfeito. Um Motor de Saída pode estar codificado conforme RF-MV-01 a RF-MV-06 e ainda assim falhar em detectar uma marca de agente real no documento de teste — o requisito está cumprido em código, mas o critério de aceitação não está atingido. Os critérios de aceitação são, portanto, o teste empírico final dos requisitos, observados sob carga real ou simulada do sistema.

Os critérios são organizados em três famílias com naturezas e processos de verificação distintos. Os **funcionais** verificam, sob execução real, que o sistema cumpre os fluxos operacionais previstos nos casos de uso do Bloco 2. Os **qualitativos** verificam, por avaliação humana documentada, que os artefatos produzidos têm utilidade técnica institucional real, não apenas conformidade técnica formal. Os **operacionais** verificam, por inspeção do estado do sistema após execução, que os mecanismos de governança, rastreabilidade e preservação operam como projetado.

A nomenclatura segue o padrão `CA-{FAMÍLIA}-{NÚMERO}`, onde a família é `FUN`, `QUA` ou `OPE`. Cada critério explicita o método de verificação — execução automatizada, inspeção manual, avaliação qualitativa — e identifica o agente responsável pela verificação no contexto do piloto. Como o piloto opera com usuário único, esse agente é, na maioria dos casos, o próprio desenvolvedor exercendo papel duplo de implementador e auditor; a explicitação do papel reforça a separação funcional ainda que executada pela mesma pessoa.

## **6.2 Critérios Funcionais (CA-FUN)**

Os critérios funcionais verificam, sob execução, que o sistema completa os casos de uso previstos. A verificação dá-se por execução real do sistema, com inspeção do estado final do `workspace/`, do `audit_index.csv` e dos outputs gerados.

**CA-FUN-01.** O ciclo completo da Atividade 1 sobre o módulo sintético MOD_SINT_001 executa com sucesso pelo menos três vezes consecutivas, em sessões independentes, sem qualquer erro de runtime. Cada execução produz manifesto íntegro, fases da Stranger's Room completas, output consolidado e ciclo registrado no `audit_index.csv` como `ENCERRADO_CHANCELADO`. Verificação: execução real seguida de inspeção dos diretórios de trabalho dos três ciclos.

**CA-FUN-02.** O ciclo da Atividade 2 sobre o MOD_SINT_001 executa com sucesso após a Atividade 1 do mesmo módulo, lendo corretamente o histórico do ciclo anterior, produzindo Relatório Final que incorpora explicitamente o histórico, e registrando o ciclo no `audit_index.csv` com referência ao `previous_cycle_id` correto. Verificação: execução real seguida de inspeção do Relatório Final e do registro no índice.

**CA-FUN-03.** Em pelo menos uma das execuções da Atividade 1 sobre o MOD_SINT_001, o protocolo de duas rodadas completas da Stranger's Room é exercitado em pelo menos uma fase, com os seis arquivos da estrutura completa presentes (`01_apresentacao.md`, `02_critica_mycroft_r1.md`, `03_resposta_r1.md`, `04_critica_mycroft_r2.md`, `05_resposta_r2.md`, `99_decisao_final.md`). Verificação: inspeção do diretório `stranger_room/` do ciclo correspondente e leitura sequencial dos arquivos.

**CA-FUN-04.** O Motor de Saída detecta e bloqueia a chancela final em pelo menos um caso de teste construído deliberadamente com marcas de agente injetadas no output. Verificação: teste manual em que o desenvolvedor edita o Relatório Preliminar para inserir nome de agente e/ou referência a estrutura interna, e dispara `diogenes verify-output`; o sistema deve detectar e listar as ocorrências.

**CA-FUN-05.** O Motor de Saída habilita a chancela final quando o output está limpo, sem produzir falsos positivos sobre termos genéricos legítimos do contexto institucional (ex.: "auditor responsável" em sentido genérico não dispara alerta, "Auditor Responsável (Watson)" dispara). Verificação: execução do Motor sobre output real produzido pelo sistema, com Relatório Preliminar que segue corretamente as regras de impessoalidade da Constituição.

**CA-FUN-06.** O sistema retoma corretamente um ciclo pausado por alerta crítico de Watson, após autorização explícita de Lestrade via `diogenes proceed`, prosseguindo para Sherlock sem perda de estado. Verificação: execução real de ciclo construído para gerar alerta crítico em Watson, observação da pausa, autorização e conclusão.

**CA-FUN-07.** O sistema aborta corretamente um ciclo via `diogenes abort`, registrando o aborto e a razão no `audit_index.csv`, preservando o diretório de trabalho intacto, e liberando o sistema para novo ciclo. Verificação: execução de aborto manual em ciclo em meio à Stranger's Room de Watson, inspeção do estado pós-aborto.

**CA-FUN-08.** O sistema falha graciosamente em caso de input incompleto, ausência de variável de ambiente obrigatória, ou erro persistente de provider, com mensagem clara identificando a causa e a ação corretiva esperada. Verificação: execução de cenários de falha controlados — diretório de input com arquivo faltando, `.env` sem `OPENROUTER_API_KEY`, chave de API inválida proposital — e inspeção das mensagens emitidas.

**CA-FUN-09.** Os subcomandos informativos da CLI (`status`, `list`, `show`) operam corretamente sobre o `audit_index.csv` e o `workspace/`, exibindo informações fiéis ao estado real. Verificação: execução dos subcomandos após série de ciclos em estados diversos (encerrados, abortados, pausados), conferência da informação exibida contra o estado real dos arquivos.

**CA-FUN-10.** Na Fase D do roadmap, o ciclo da Atividade 1 sobre o MOD_010 (Pessoa Física) executa com sucesso pelo menos uma vez, produzindo Relatório Preliminar que reflete análise efetiva sobre o material entregue pela RFB. Verificação: execução real seguida de inspeção do output gerado e comparação superficial com a estrutura esperada de relatório de análise.

## **6.3 Critérios Qualitativos (CA-QUA)**

Os critérios qualitativos não têm verificação automatizável. Verificam, por avaliação humana documentada, que o sistema produz artefatos com utilidade técnica institucional real. A avaliação qualitativa é registrada em documento dedicado — uma `avaliacao_piloto.md` no diretório `docs/` do repositório — com data, ciclo avaliado, critério verificado, observações específicas e veredicto.

**CA-QUA-01.** O Relatório Preliminar produzido pelo ciclo da Atividade 1 sobre o MOD_SINT_001 (com modelos da Fase B) identifica corretamente, no mínimo, setenta por cento das inconsistências propositais inseridas na construção do módulo sintético. A verificação compara o conjunto de inconsistências detectadas com o conjunto conhecido de inconsistências inseridas (registrado em documento separado, não acessível aos agentes). Critério qualitativo: avaliação humana confirma que as inconsistências detectadas estão corretamente classificadas e fundamentadas, e que as não detectadas são compreensíveis dado o nível de capacidade dos modelos.

**CA-QUA-02.** O Relatório Preliminar é redigido em português brasileiro institucional, em terceira pessoa, sem nome de agentes no corpo, com classificação semântica conforme Design System TCU-CBS aplicada coerentemente, com fundamentação metodológica explícita por classificação. Critério qualitativo: avaliação humana confirma que a leitura do relatório por terceiro não revela traço da estrutura interna do Departamento, mantém tom institucional consistente, e permite reconstrução do raciocínio que levou a cada classificação.

**CA-QUA-03.** Os arquivos da Stranger's Room, lidos em sequência, configuram transcrição coerente de deliberação técnica entre Mycroft e o agente executor. Críticas de Mycroft são objetivas e dirigidas a pontos específicos, não vagas ou genéricas. Respostas dos agentes corrigem ou sustentam posição com fundamentação. Decisões finais de Mycroft são fundamentadas, seja acatando posição do agente ou fixando posição diversa. Critério qualitativo: avaliação humana confirma que a Stranger's Room funciona como o espaço de revisão crítica que a Constituição estabelece, não como ritual formal vazio.

**CA-QUA-04.** O Relatório Final da Atividade 2 sobre o MOD_SINT_001 demonstra uso efetivo do histórico do ciclo da Atividade 1, classificando corretamente cada inconsistência prévia conforme a resposta simulada da RFB (resolvida, justificada de forma aceitável, em aberto, nova inconsistência). A leitura comparativa do Relatório Preliminar e do Relatório Final permite reconstrução completa do diálogo técnico simulado. Critério qualitativo: avaliação humana confirma a fidelidade do histórico e a coerência da classificação.

**CA-QUA-05.** As decisões de Mycroft em casos de dilema interpretativo (Artigo 10 da Constituição) demonstram raciocínio ponderado: quando o dilema é genuíno, é registrado e encaminhado conforme o protocolo; quando o dilema admite resolução fundamentada, Mycroft a fixa com justificativa explícita. Critério qualitativo: avaliação humana confirma que Mycroft não evade dilemas reais com falsas resoluções nem fabrica dilemas em casos resolvíveis.

**CA-QUA-06.** O conjunto de traces técnicos das chamadas a modelo, em conjunto com os arquivos institucionais, permite a um auditor externo (papel exercido em simulação por colega ou pelo próprio desenvolvedor em data posterior à execução) reconstruir não apenas o que o sistema fez, mas por que cada decisão foi tomada. Critério qualitativo: avaliação humana, executada por revisor que não participou da execução do ciclo, confirma a viabilidade dessa reconstrução por leitura direta dos arquivos do `workspace/cycles/{cycle_id}/`.

**CA-QUA-07.** Na execução da Fase D sobre o MOD_010, o Relatório Preliminar produzido sobre material real demonstra que o sistema opera com utilidade prática para o trabalho do Departamento, não apenas em laboratório com módulo sintético. A avaliação compara o output produzido com o que seria esperado de análise humana sobre o mesmo material. Critério qualitativo: avaliação humana, ideal mas não obrigatoriamente conduzida em conjunto com auditor familiar com o MOD_010, confirma que o output tem valor analítico real.

## **6.4 Critérios Operacionais (CA-OPE)**

Os critérios operacionais verificam, por inspeção do estado do sistema após execução, que os mecanismos de governança, rastreabilidade e preservação previstos na Constituição e no PRD operam como projetado. A verificação é majoritariamente automatizável e parcialmente manual.

**CA-OPE-01.** Após a conclusão de cada ciclo, o `audit_index.csv` reflete o ciclo com todos os campos preenchidos conforme RF-PE-03, sem nenhuma linha corrompida, sem caracteres quebrados, sem inconsistência de tipos. Verificação: leitura programática do CSV após execução de série de ciclos, validação de tipos e completude.

**CA-OPE-02.** Após a conclusão de cada ciclo, o diretório de trabalho do ciclo (`workspace/cycles/{cycle_id}/`) está integralmente preservado, com todos os arquivos previstos presentes e nenhum arquivo adicional não esperado. A estrutura interna corresponde à especificada em RF-PE-02. Verificação: inspeção da árvore de diretórios e contagem de arquivos por subdiretório.

**CA-OPE-03.** Os arquivos originais nos diretórios `workspace/input/MOD_*/` permanecem intocados após execução de ciclos sobre eles, com hashes idênticos aos registrados no manifesto de abertura. Verificação: cálculo de hash dos arquivos de input antes e depois da execução de ciclo, conferência contra os hashes registrados.

**CA-OPE-04.** Nenhum arquivo escrito pelo sistema dentro do diretório de trabalho de um ciclo é sobrescrito ou modificado após criação. Verificação: instrumentação simples (registro de timestamps de modificação dos arquivos durante e após a execução) e inspeção pós-execução.

**CA-OPE-05.** O custo financeiro de cada ciclo está registrado no `audit_index.csv` e detalhado nos traces técnicos das chamadas individuais, com soma coerente entre o agregado e o detalhe. Verificação: cálculo programático da soma dos custos por chamada e conferência contra o valor agregado registrado para o ciclo.

**CA-OPE-06.** A sequência cronológica do `audit_index.csv` é preservada: a leitura ordenada por timestamp produz histórico coerente, sem ciclos com `started_at_utc` posterior ao `ended_at_utc`, sem ciclos com `previous_cycle_id` apontando para ciclo posterior. Verificação: leitura programática e validação de consistência cronológica.

**CA-OPE-07.** O sistema opera corretamente em ambiente com `workspace/` sincronizado por OneDrive, sem produção de arquivos `.tmp`, `.lock` ou outros artefatos que disparem conflitos de sincronização. Verificação: execução de ciclo completo em ambiente real com sincronização ativa, inspeção de artefatos não esperados.

**CA-OPE-08.** O sistema opera, sem alteração de código, em pelo menos dois dos três ambientes-alvo previstos no Bloco 4 (máquina local com OneDrive, VPS particular, ambiente simulado de Azure). A operação no terceiro ambiente é desejável mas não obrigatória para fechamento do piloto. Verificação: execução de ciclo completo em cada ambiente com configuração distinta apenas em variáveis de ambiente e `runtime.yaml`.

**CA-OPE-09.** A documentação no `README.md` do repositório permite, a um operador novo seguindo apenas o documento, instalar o sistema e executar o primeiro ciclo de teste com sucesso. Verificação: teste em ambiente limpo (máquina virtual, container, ou máquina sem o projeto previamente instalado), seguido de execução estrita das instruções do README sem consulta a outros materiais.

**CA-OPE-10.** A suíte de testes automatizados executa integralmente sem falhas no estado final do piloto, com cobertura mínima de setenta por cento das linhas dos componentes não-agente, conforme RNF-MANU-04. Verificação: execução de `pytest --cov` e inspeção do relatório de cobertura.

## **6.5 Quadro de Síntese e Critério Geral de Conclusão do Piloto**

O piloto Diógenes é considerado concluído com sucesso quando todos os critérios funcionais (CA-FUN-01 a CA-FUN-10) e operacionais (CA-OPE-01 a CA-OPE-10) estiverem atendidos, e ao menos seis dos sete critérios qualitativos (CA-QUA-01 a CA-QUA-07) tiverem avaliação humana documentada com veredicto positivo.

A flexibilidade nos critérios qualitativos reflete a natureza do objeto: avaliação qualitativa de output de modelo de linguagem é, por definição, sujeita a alguma variabilidade entre executores e contextos. Exigir unanimidade absoluta em sete avaliações qualitativas distintas, executadas potencialmente em momentos diferentes do desenvolvimento, criaria critério irrealista que poderia bloquear a conclusão do piloto por divergência menor de avaliação. A exigência de seis dos sete preserva o rigor sem cair na rigidez improdutiva.

O critério qualitativo CA-QUA-07, sobre a Fase D com MOD_010, é particularmente sensível e merece atenção: é o único critério que envolve material real do TCU sob qualquer modalidade. A não satisfação deste critério não invalida o piloto, mas tem peso diferente — sinaliza que a transição para uso institucional efetivo demanda mais maturação, possivelmente com ajustes de modelo ou de prompt antes de qualquer aplicação a outros módulos da CBS.

A documentação da satisfação dos critérios é parte do encerramento formal do piloto, registrada em documento `encerramento_piloto.md` no diretório `docs/` do repositório, com data, lista de critérios atendidos, evidências citadas (caminhos de arquivos do `workspace/`, linhas do `audit_index.csv`, trechos de avaliação qualitativa), critérios não atendidos com justificativa, e veredicto final de conclusão.

Esse documento de encerramento é, por sua vez, o gatilho para a transição à fase pós-piloto descrita no Bloco 9 do PRD. Sem ele, a transição não ocorre — não se inicia tratativa de migração para Foundry, não se contrata desenvolvimento adicional de Atividades 3, 4 e 5, não se amplia o escopo para múltiplos módulos. O documento de encerramento é a chancela final que Lestrade emite sobre o piloto inteiro, replicando, em escala maior, o protocolo que aplica ao final de cada ciclo individual.

---

# **Bloco 7 — Métricas e Benchmarking de Modelos**

## **7.1 Lógica do Benchmarking no Piloto**

O benchmarking de modelos no piloto Diógenes não é exercício acadêmico de comparação abstrata. É instrumento operacional para uma decisão concreta e definitiva: qual modelo de linguagem cada agente do Departamento utilizará quando o sistema migrar para o estado-alvo Foundry e operar sobre os módulos reais da CBS. Essa decisão tem consequências orçamentárias estruturantes — os agentes serão chamados centenas de vezes por ciclo, dezenas de ciclos por módulo, em dezessete módulos ao longo de anos —, consequências qualitativas estruturantes — a precisão da análise de Watson, a profundidade da validação metodológica de Sherlock e o discernimento de Mycroft afetam diretamente a qualidade do trabalho que fundamentará o cálculo da alíquota de referência da CBS — e consequências institucionais estruturantes — a defensabilidade externa do trabalho do Tribunal depende de que cada escolha técnica esteja lastreada em evidência empírica documentada.

Decisão dessa magnitude não pode ser tomada por intuição, por marketing dos providers, por benchmarks publicados pela própria indústria ou por preferência pessoal do desenvolvedor. Precisa ser tomada com base em medição empírica conduzida sob carga representativa do trabalho real do Departamento, com critérios objetivos definidos antes da medição, com protocolo replicável que produza evidência auditável.

O benchmarking é exercitado nas Fases B e D do roadmap (Bloco 8). A Fase B opera sobre módulo sintético com inconsistências propositais conhecidas, permitindo medição quantitativa de taxa de detecção. A Fase D opera sobre material real (MOD_010), permitindo verificação qualitativa de utilidade prática. As duas fases são complementares: a primeira mede capacidade técnica em condições controladas, a segunda confirma adequação ao trabalho institucional concreto.

A nomenclatura dos critérios e protocolos segue o padrão `BM-{NÚMERO}` para itens do protocolo de benchmark e `MET-{NÚMERO}` para métricas medidas.

## **7.2 Princípios Orientadores do Benchmarking**

Antes de descer aos modelos candidatos e ao protocolo, três princípios estruturam todo o exercício de benchmarking e merecem registro explícito.

**Princípio da carga representativa.** O benchmarking não testa modelos sobre tarefas sintéticas genéricas — perguntas de raciocínio, problemas de matemática, prompts de avaliação multiuso. Testa modelos exatamente sobre o trabalho que o Departamento precisará executar: análise de planilhas com inconsistências, tradução de SQL em linguagem natural, confronto de scripts com metodologia normativa, identificação de dilemas interpretativos. Capacidade demonstrada em outras tarefas é informação interessante mas não decisiva; capacidade demonstrada nas tarefas reais do Departamento é o critério.

**Princípio da estratificação por agente.** Watson, Sherlock e Mycroft têm perfis cognitivos distintos e exigências distintas de modelo. O modelo ideal para um agente pode ser inadequado para outro — modelo barato e veloz que serve Watson pode ser incapaz da síntese ponderada que Mycroft exige; modelo de ponta que serve Mycroft pode ser desperdício orçamentário em Watson. O benchmarking produz, portanto, três rankings independentes, um por agente, e a decisão final é configuração mista: o melhor modelo para cada papel, não um modelo único para todos.

**Princípio da reprodutibilidade do experimento.** O protocolo de benchmark é documentado de forma que terceiros possam executá-lo e obter resultados comparáveis. As inconsistências propositais inseridas no módulo sintético, os parâmetros das chamadas, os critérios de avaliação, tudo é registrado em arquivo dedicado do repositório. Sem reprodutibilidade do experimento, o resultado é opinião pessoal do desenvolvedor, não evidência defensável.

## **7.3 Modelos Candidatos por Agente**

A lista de candidatos foi consolidada conforme acordado nos ajustes do início deste PRD, considerando a estratégia em três fases e as restrições orçamentárias do piloto. A lista é fixada aqui para o protocolo do piloto, mas pode ser revisada pelo desenvolvedor antes do início da Fase B caso o catálogo do OpenRouter sofra alterações relevantes.

**Watson — perfil determinístico, custo-eficiente.** Os candidatos cobrem famílias distintas para evitar viés:

- `moonshotai/kimi-k2-0905` ou versão vigente (tendência: forte em parsing técnico estruturado)
- `qwen/qwen3-max` ou versão vigente (tendência: bom em planilhas e tabelas)
- `deepseek/deepseek-v3.2-exp` ou versão vigente (tendência: surpreendente em código)
- `anthropic/claude-haiku-4.5` (tendência: equilibrado, custo um pouco maior)

A inclusão de Haiku 4.5 como ponto de comparação fora da faixa "barata extrema" é deliberada: serve de baseline de qualidade. Se algum dos modelos mais baratos atingir qualidade comparável a Haiku 4.5, a economia compensa; se nenhum atingir, Haiku 4.5 entra como fallback de qualidade e o orçamento é renegociado.

**Sherlock — perfil de análise normativa complexa.** Mesma lógica:

- `moonshotai/kimi-k2-0905` ou equivalente vigente
- `qwen/qwen3-max` ou equivalente vigente
- `deepseek/deepseek-v3.2-exp` ou equivalente vigente
- `anthropic/claude-sonnet-4.6` (baseline de qualidade para análise normativa)

A possibilidade de testar `anthropic/claude-opus-4.7` ou `openai/gpt-5.5` em Sherlock está fora da Fase B (custo proibitivo) mas registrada como candidata para a Fase C, quando o Foundry liberar acesso institucional sem ônus pessoal.

**Mycroft — perfil de alta síntese e julgamento.** A função de Mycroft é a mais sensível ao discernimento ponderado, e o orçamento do piloto não permite testar em Mycroft os modelos de ponta que seriam ideais. A estratégia é testar os mesmos candidatos baratos das duas listas anteriores, observar criticamente se a qualidade da síntese é aceitável, e registrar para a Fase C que Mycroft é o agente cuja decisão de modelo definitivo depende mais fortemente do que se observar quando modelos de ponta puderem ser exercitados.

A configuração final esperada para a Fase C, conforme estratégia já registrada, é Kimi K2.6 em Watson, GPT-5.5 em Sherlock, Claude Opus 4.7 em Mycroft. O benchmarking do piloto serve para calibrar essa expectativa contra a realidade observada e identificar, eventualmente, configuração distinta que se mostre superior empiricamente.

## **7.4 Protocolo de Benchmark (BM)**

**BM-01.** O benchmark da Fase B opera sobre o módulo sintético MOD_SINT_001, em sua versão final estabilizada após as execuções da Fase A. O módulo deve ter, no mínimo, vinte inconsistências propositais distribuídas entre as categorias previstas: erros aritméticos em planilhas, scripts SQL com lógica divergente da declarada, notebooks Python com transformações que não correspondem à descrição metodológica, ausências documentais que impedem rastreamento de cadeia de produção de dados, casos genuinamente ambíguos que admitem duas interpretações de peso equivalente.

**BM-02.** A lista completa das inconsistências propositais é registrada em arquivo `tests/fixtures/MOD_SINT_001/inconsistencias_conhecidas.md`, com identificação única por inconsistência, categoria, localização precisa, severidade esperada (crítica, atenção, informativa), e classificação esperada (Atendido, Atendido Parcialmente, Divergência, Atenção, Limitação, Não Verificável). Esse arquivo não é acessível aos agentes em nenhuma circunstância — o sistema, em modo benchmark, garante essa segregação.

**BM-03.** Cada combinação de modelos a ser testada é definida em arquivo `bench/configs/run_{NN}.yaml`, especificando o modelo escolhido para cada agente. Exemplo de configuração:

```yaml
name: bench_03_kimi_em_todos
description: Kimi K2 em Watson, Sherlock e Mycroft
agents:
  watson:
    provider: openrouter
    model: moonshotai/kimi-k2-0905
    temperature: 0.10
  sherlock:
    provider: openrouter
    model: moonshotai/kimi-k2-0905
    temperature: 0.20
  mycroft:
    provider: openrouter
    model: moonshotai/kimi-k2-0905
    temperature: 0.25
```

**BM-04.** Para cada configuração, o ciclo da Atividade 1 sobre o MOD_SINT_001 é executado pelo menos três vezes, em sessões independentes, com timestamps espaçados em pelo menos uma hora para reduzir efeitos de cache do provider. O protocolo prevê, portanto, três execuções por configuração; configurações com variância alta entre execuções podem demandar duas execuções adicionais para amostragem mais robusta.

**BM-05.** O benchmark é rodado primeiro com as configurações homogêneas (todos os agentes com o mesmo modelo) das quatro famílias candidatas, totalizando doze execuções iniciais (quatro modelos vezes três execuções). Em seguida, com base nos resultados das homogêneas, são definidas configurações mistas a serem testadas — combinando o melhor modelo identificado para cada agente nas execuções homogêneas. A quantidade de configurações mistas é decisão tomada à vista dos resultados, mas o teto orçamentário do piloto limita a aproximadamente seis configurações mistas adicionais.

**BM-06.** Para cada execução, o sistema registra automaticamente, no `audit_index.csv` e em arquivo dedicado de benchmark `bench/results/run_{NN}_exec_{N}.json`: identificação completa da configuração, métricas conforme seção 7.5, e referências aos artefatos do ciclo (caminho do diretório de trabalho, hash do output gerado).

**BM-07.** A avaliação qualitativa de cada execução, conforme métrica MET-04, é realizada pelo desenvolvedor com auxílio do arquivo de inconsistências conhecidas, comparando o que o sistema detectou com o que foi propositalmente inserido. A avaliação é registrada em `bench/results/run_{NN}_exec_{N}_qual.md` em formato estruturado: lista das inconsistências conhecidas, marcação de cada uma como detectada/parcialmente detectada/não detectada, observações sobre falsos positivos identificados, observações sobre qualidade da fundamentação e linguagem.

**BM-08.** Após o conjunto de execuções, é produzido relatório consolidado de benchmark em `bench/results/_relatorio_consolidado.md`, integrando todas as configurações testadas, todas as execuções, todas as métricas, e apresentando o ranking final por agente com fundamentação. Esse relatório é o produto definitivo do benchmark e o insumo para a decisão de configuração da Fase C.

**BM-09.** O benchmark da Fase D, sobre o MOD_010, opera com a configuração eleita pelo benchmark da Fase B (a configuração vencedora do ranking, ou a melhor configuração mista identificada). O objetivo da Fase D não é re-benchmarking, é confirmação qualitativa de que a configuração vencedora opera adequadamente sobre material real. Caso a Fase D revele inadequação séria — qualidade muito inferior à observada na Fase B, latência ou custo divergente do esperado —, é executado mini-benchmark adicional restrito sobre o MOD_010 com candidatos alternativos identificados na Fase B.

**BM-10.** Todo o material do benchmark — configurações, resultados quantitativos, avaliações qualitativas, relatório consolidado — fica versionado no repositório em `bench/`. A reprodutibilidade do benchmark por terceiros é critério de aceitação operacional do piloto (CA-OPE adicional implícito no princípio da reprodutibilidade do experimento).

## **7.5 Métricas Medidas (MET)**

As métricas são medidas por execução individual e agregadas por configuração. A agregação é por mediana, não por média, dado o tamanho pequeno das amostras (três execuções por configuração) e a sensibilidade da média a outliers.

**MET-01. Custo financeiro total da execução.** Em USD. Soma dos custos de todas as chamadas a modelo durante o ciclo, conforme registrado pelo sistema (RNF-CUST-01). Discriminado por agente: custo de Watson, custo de Sherlock, custo de Mycroft. Critério de avaliação: configurações que excedem dez USD por execução são marcadas como inviáveis para o piloto, registradas no resultado mas excluídas do ranking.

**MET-02. Latência total da execução.** Em segundos, do `diogenes confirm-manifest` ao estado pronto para chancela final, conforme RNF-LATE-01 e RNF-LATE-02. Discriminada por fase: latência da fase Watson (incluindo Stranger's Room), latência da fase Sherlock (incluindo Stranger's Room), latência da consolidação final por Mycroft. Critério de avaliação: configurações com latência total acima de trinta minutos são marcadas como inviáveis para uso operacional contínuo.

**MET-03. Tokens consumidos.** Discriminados por agente e por chamada (input tokens, output tokens). A métrica é informativa para análise de eficiência: dois modelos podem produzir output equivalente com consumo de tokens muito distinto, e o que produz menos tokens é preferível mesmo a custo unitário ligeiramente superior. A métrica também alimenta a estimativa de custo na transição para Foundry, onde o pricing é por token.

**MET-04. Taxa de detecção de inconsistências propositais.** Calculada como número de inconsistências corretamente detectadas dividido pelo número total de inconsistências conhecidas inseridas no módulo. Discriminada por categoria: taxa de detecção em planilhas, em scripts SQL, em notebooks, em ausências documentais, em casos ambíguos. A métrica é central — modelo que detecta poucas inconsistências, mesmo barato e rápido, não serve ao Departamento. Meta indicativa para configurações aceitáveis: setenta por cento de detecção total no módulo sintético, conforme CA-QUA-01.

**MET-05. Taxa de falsos positivos.** Calculada como número de "inconsistências" reportadas pelo sistema que não correspondem a nenhuma das inconsistências conhecidas inseridas, dividido pelo número total de itens reportados. A métrica é igualmente central — modelo que aponta inconsistências inexistentes (alucina) é tão problemático quanto modelo que omite inconsistências reais, possivelmente mais, dado que cada falso positivo gera trabalho desnecessário no contraditório técnico com a RFB. Meta indicativa: abaixo de quinze por cento de falsos positivos.

**MET-06. Qualidade da classificação semântica.** Avaliação qualitativa pelo desenvolvedor: para as inconsistências corretamente detectadas, a classificação semântica aplicada (Atendido Parcialmente, Divergência, Atenção, Limitação, Não Verificável) corresponde à classificação esperada conforme registrada em `inconsistencias_conhecidas.md`? Pontuação por execução: número de classificações corretas dividido pelo número de inconsistências detectadas. A métrica avalia se o modelo entende o sistema semântico do Design System TCU-CBS, não apenas se identifica problemas.

**MET-07. Qualidade da fundamentação metodológica.** Avaliação qualitativa pelo desenvolvedor: para as inconsistências corretamente detectadas, a fundamentação registrada cita explicitamente o dispositivo da metodologia homologada correspondente, conforme exigido pelo Artigo 7 da Constituição? Pontuação por execução: número de fundamentações corretamente lastreadas dividido pelo número de inconsistências detectadas. A métrica avalia se o modelo respeita a regra constitucional de não emitir conclusão sem lastro normativo rastreável.

**MET-08. Aderência ao protocolo da Stranger's Room.** Avaliação qualitativa pelo desenvolvedor sobre a deliberação técnica registrada nos arquivos da Stranger's Room: as críticas de Mycroft são objetivas e dirigidas a pontos específicos? As respostas dos agentes corrigem ou sustentam posição com fundamentação? As decisões finais de Mycroft são fundamentadas? A leitura sequencial dos arquivos configura transcrição coerente de deliberação? Pontuação por execução em escala qualitativa de quatro níveis: ausente, formal sem profundidade, adequada, exemplar. A métrica é a tradução operacional de CA-QUA-03.

**MET-09. Aderência à impessoalidade dos documentos.** Verificação automatizada via Motor de Saída sobre o output consolidado: número de ocorrências de marcas de agente detectadas. Pontuação por execução: zero ocorrências (ideal), um a três ocorrências (corrigível por edição mínima), quatro ou mais ocorrências (modelo descumpre sistematicamente o Artigo 14 e exige ajuste de prompt ou substituição). A métrica é objetiva e tecnicamente medida.

**MET-10. Estabilidade entre execuções.** Variância entre as três execuções da mesma configuração nas métricas quantitativas (MET-01, MET-02, MET-04, MET-05). A métrica não tem alvo absoluto — alguma variância é esperada dada a natureza não determinística dos modelos —, mas configurações com variância muito alta (taxa de detecção que oscila trinta pontos percentuais entre execuções, por exemplo) são marcadas como instáveis e despriorizadas no ranking.

## **7.6 Critérios de Seleção Definitiva por Agente**

A escolha do modelo definitivo para cada agente, ao final do benchmark, segue critérios ordenados por prioridade. A ordenação é importante: dois critérios podem favorecer modelos distintos, e a ordem dita qual prevalece.

**Para Watson.** A ordem de prioridade é: (1) taxa de detecção de inconsistências propositais em planilhas e scripts (MET-04 nas categorias relevantes a Watson) — Watson precisa, antes de tudo, encontrar o que está errado; (2) baixa taxa de falsos positivos (MET-05) — Watson não pode poluir o trabalho com inconsistências inexistentes; (3) custo financeiro (MET-01) — Watson é o agente que mais consome tokens, e a economia importa estruturalmente; (4) latência (MET-02) — Watson roda no início do ciclo, latência sua afeta toda a duração; (5) estabilidade (MET-10).

**Para Sherlock.** A ordem é: (1) qualidade da fundamentação metodológica (MET-07) — Sherlock sem fundamentação rastreável viola Artigo 7 da Constituição e invalida o trabalho; (2) qualidade da classificação semântica (MET-06) — classificações erradas geram retrabalho no contraditório com a RFB; (3) taxa de detecção em casos ambíguos (parte de MET-04) — discernimento de dilemas interpretativos é o diferencial cognitivo de Sherlock; (4) baixa taxa de falsos positivos (MET-05); (5) latência (MET-02); (6) custo (MET-01) — Sherlock chama menos, tolera modelo um pouco mais caro se a qualidade compensa.

**Para Mycroft.** A ordem é: (1) aderência ao protocolo da Stranger's Room (MET-08) — Mycroft que não exerce revisão crítica é apenas overhead; (2) aderência à impessoalidade dos documentos no output consolidado (MET-09); (3) qualidade da síntese final percebida pelo desenvolvedor na leitura dos relatórios consolidados — métrica qualitativa adicional, registrada como observação no relatório consolidado de benchmark; (4) custo (MET-01) — Mycroft chama poucas vezes mas com pacotes carregados, custo absoluto pode ser alto; (5) latência (MET-02).

A configuração definitiva da Fase C é, portanto, combinação de três escolhas independentes, uma por agente. A configuração esperada (Kimi K2.6 em Watson, GPT-5.5 em Sherlock, Claude Opus 4.7 em Mycroft) é hipótese de trabalho calibrada por intuição arquitetural, e o benchmark do piloto é o exercício que confirma, refuta ou ajusta essa hipótese com evidência empírica.

## **7.7 Plano de Medição de Custo Projetado para Produção**

O benchmark do piloto tem como subproduto a estimativa de custo de operação do Departamento em produção. Essa estimativa é insumo institucional importante: o TCU precisará alocar orçamento para a operação contínua do Departamento até 2032, e a estimativa fundamentada com base em medição empírica é mais defensável que projeção abstrata.

A estimativa é calculada multiplicando o custo médio observado por ciclo (MET-01) na configuração eleita pela Fase C, pelo número estimado de ciclos por módulo na operação plena (uma Atividade 1 e uma Atividade 2 para cada um dos dezessete módulos, mais Atividades 3, 4 e 5 para os cinco módulos selecionados para a Sala de Sigilo, totalizando aproximadamente quarenta e nove ciclos), com fator de multiplicação para refletir a maior complexidade dos módulos reais em comparação ao MOD_SINT_001 (estimativa inicial: fator de duas a cinco vezes, a ser refinado pela Fase D sobre o MOD_010).

A estimativa final, com intervalo de confiança e premissas declaradas, integra o relatório consolidado do benchmark e o documento de encerramento do piloto. A precisão dessa estimativa é menos importante que a transparência das premissas que a fundamentam — qualquer revisão posterior dos modelos, da metodologia ou do escopo dos módulos altera a estimativa, e a documentação clara de como ela foi calculada permite essa atualização sem refazer todo o exercício.

---

# **Bloco 8 — Roadmap do Piloto**

## **8.1 Lógica do Roadmap em Quatro Fases**

O roadmap do piloto Diógenes organiza-se em quatro fases sequenciais, cada uma com objetivo distinto, critério de avanço explícito e produto verificável ao final. A sequência não é arbitrária: cada fase é pré-condição lógica da seguinte. Iniciar a Fase C antes de a Fase B estar concluída produziria benchmark inválido por instabilidade da implementação subjacente; iniciar a Fase D antes de a Fase B estar concluída exporia material real (ainda que tratado) a configuração de modelos não validada empiricamente. A disciplina do roadmap protege a qualidade do trabalho e a contenção orçamentária pessoal do desenvolvedor.

A duração de cada fase é estimada, não cravada. O critério de avanço é o cumprimento do objetivo da fase, não o transcurso de tempo. Uma fase pode levar mais que o estimado se necessário; não pode ser declarada concluída antes do cumprimento de seu critério, ainda que o tempo planejado já tenha esgotado.

A nomenclatura segue o padrão `FASE-{LETRA}` para identificação das fases e `MARCO-{LETRA}-{NÚMERO}` para os marcos verificáveis dentro de cada fase. Os marcos são pontos de checagem explícitos, com produto associado, que permitem ao desenvolvedor confirmar progresso real e ao auditor externo (papel exercido pelo próprio desenvolvedor em sessão dedicada de revisão) validar o avanço.

Há, antes da Fase A, uma fase preparatória — Fase 0 — que cobre o scaffolding e a construção dos artefatos de teste. Sem ela, a Fase A não tem material para operar. A Fase 0 é tratada com a mesma seriedade das fases subsequentes, ainda que seu produto seja insumo, não validação.

## **8.2 Fase 0 — Scaffolding e Construção de Artefatos de Teste**

**Objetivo.** Estabelecer a base do repositório, implementar o esqueleto da arquitetura conforme o SDD, construir o módulo sintético MOD_SINT_001 com inconsistências propositais documentadas, e preparar o ambiente operacional para as fases subsequentes.

**Duração estimada.** Quatro a seis semanas, em regime de dedicação parcial. A duração é particularmente sensível à profundidade da construção do módulo sintético, que precisa ser realista o bastante para forçar dilemas reais nos agentes.

**Produtos esperados.**

Repositório versionado com estrutura completa conforme RNF-MANU-02 e seção do SDD a ser produzida posteriormente. Esqueleto de código com todos os módulos previstos (`agents/`, `engines/`, `llm/`, `io/`, `core/`, `cli/`), Motor de Start funcional, persistência funcional (`audit_index.csv`, manifesto, diretórios de trabalho), CLI básica com subcomandos informativos e de aborto operando. Camada `LLMClient` implementada com cliente OpenRouter funcional, capaz de fazer chamada simples de teste retornando resposta válida. Suíte de testes inicial cobrindo os componentes não-agente.

Módulo sintético MOD_SINT_001 construído em `tests/fixtures/MOD_SINT_001/` ou diretório equivalente, com: planilhas Excel com cálculos da CBS hipotética, contendo erros aritméticos propositais e fórmulas com lógica divergente da declarada; scripts SQL fictícios de extração, com pelo menos um script cuja execução real difere da descrição; notebook Python fictício de transformação, com pelo menos uma transformação não documentada e pelo menos uma transformação documentada que não é executada; documento metodológico do módulo sintético, fabricado como simulação simplificada da metodologia real, com regras claras o bastante para Sherlock validar e ambíguas o bastante em pontos específicos para forçar dilemas; briefing simulado do GT; atas e transcrições fictícias de reuniões. Total de no mínimo vinte inconsistências propositais distribuídas pelas categorias previstas, registradas em `inconsistencias_conhecidas.md`.

Documentação inicial: `README.md` cobrindo instalação e operação básica conforme RNF-MANU-06, `.env.example` com chaves esperadas, documentação dos arquivos do módulo sintético, ponteiros para o PRD e o SDD.

**Marcos verificáveis.**

**MARCO-0-1.** Repositório inicializado, estrutura de diretórios criada, dependências fixadas em `pyproject.toml`, ambiente virtual operacional, suíte de testes vazia executando sem erros. Verificação: clone limpo do repositório seguido de instalação e execução de `pytest`.

**MARCO-0-2.** Camada `LLMClient` implementada e operacional. O cliente OpenRouter executa chamada simples ("hello world") contra modelo free e retorna resposta válida. Verificação: execução de script de teste em `bench/smoke_test.py`.

**MARCO-0-3.** Motor de Start, persistência e CLI básica implementados. O subcomando `diogenes start --module {ID} --activity 1` cria diretório de trabalho, gera manifesto válido e aguarda confirmação. O subcomando `diogenes confirm-manifest` registra a confirmação. Verificação: execução manual e inspeção do `workspace/`.

**MARCO-0-4.** Módulo sintético MOD_SINT_001 construído. Inconsistências propositais documentadas. Arquivo `inconsistencias_conhecidas.md` revisado para garantir que cobre todas as categorias previstas e que as inconsistências têm fundamentação técnica realista. Verificação: revisão dedicada do desenvolvedor sobre o conjunto, idealmente em sessão separada do trabalho de construção, para reduzir vieses.

**MARCO-0-5.** Documentação inicial completa. Operador novo, seguindo o `README.md`, consegue clonar, instalar e executar o smoke test. Verificação: teste em ambiente limpo conforme CA-OPE-09, ainda que executado pelo próprio desenvolvedor.

**Critério de avanço para Fase A.** Todos os cinco marcos da Fase 0 satisfeitos. Em particular, MARCO-0-4 é o gargalo prático: a qualidade do módulo sintético determina toda a utilidade das fases subsequentes.

## **8.3 Fase A — Validação de Implementação com Modelos Free**

**Objetivo.** Executar o ciclo completo da Atividade 1 sobre o módulo sintético MOD_SINT_001 ponta a ponta, sem qualquer erro de runtime, utilizando exclusivamente modelos free do OpenRouter. A qualidade do output não é critério: aceita-se qualquer resposta dos modelos, ainda que incompleta, alucinada ou superficial. O que importa é que o sistema não quebre.

**Duração estimada.** Duas a três semanas. A duração depende fortemente de quantos problemas de integração são descobertos durante as primeiras execuções — falhas de protocolo entre agentes, formatos de output incompatíveis, escapes de marcação não previstos, comportamento inesperado dos modelos free com instruções complexas.

**Produtos esperados.**

Implementação completa dos três agentes (Mycroft, Watson, Sherlock) operando no monolito sequencial, conforme requisitos funcionais do Bloco 3 do PRD. Implementação completa da Stranger's Room com protocolo de duas rodadas, ainda que na Fase A seja raramente exercitada por limitação dos modelos free. Implementação do Motor de Saída com regras heurísticas. Implementação dos demais subcomandos da CLI (`proceed`, `pause`, `resume`, `verify-output`, `seal`, `show`).

Conjunto de pelo menos três execuções consecutivas bem-sucedidas do ciclo completo da Atividade 1 sobre o MOD_SINT_001. Cada execução produz manifesto íntegro, fases da Stranger's Room completas, output consolidado, ciclo registrado no `audit_index.csv` como `ENCERRADO_CHANCELADO`. Os três ciclos ficam preservados no `workspace/cycles/` como evidência.

Conjunto adicional de execuções de cenários de falha controlada: input incompleto, chave de API inválida, aborto manual, alerta crítico forçado por construção. O sistema responde graciosamente a cada cenário, com mensagens claras e estado preservado.

**Marcos verificáveis.**

**MARCO-A-1.** Mycroft implementado. Recebe manifesto, lê inputs, define tasks ordenadas para Watson, escreve task plan em arquivo persistente. Verificação: execução com mock de Watson e inspeção do task plan gerado.

**MARCO-A-2.** Watson implementado. Recebe task plan de Mycroft, opera sobre os arquivos do MOD_SINT_001, produz output estruturado com classificação de severidade. Verificação: execução end-to-end das duas primeiras fases (até output de Watson) e inspeção do output.

**MARCO-A-3.** Stranger's Room implementada. Mycroft revisa output de Watson, escreve crítica ou aprovação direta, protocolo de duas rodadas funcional ainda que pouco exercitado. Verificação: execução até `99_decisao_final.md` da fase Watson e inspeção dos arquivos gerados.

**MARCO-A-4.** Sherlock implementado. Recebe pacote integrado de Mycroft, opera sobre os arquivos com referência à metodologia sintética, produz output classificado conforme sistema semântico. Verificação: execução end-to-end até output de Sherlock.

**MARCO-A-5.** Consolidação final por Mycroft implementada. Mycroft produz Relatório Preliminar em Markdown estruturado, em terceira pessoa, com assinatura ao final. Verificação: execução end-to-end até produção do output consolidado.

**MARCO-A-6.** Motor de Saída implementado. Detecta marcas de agente em cenário de teste construído deliberadamente. Habilita chancela quando output está limpo. Verificação: execução conforme CA-FUN-04 e CA-FUN-05.

**MARCO-A-7.** Três execuções consecutivas bem-sucedidas do ciclo completo, com critérios de CA-FUN-01 satisfeitos. Verificação: conferência dos três ciclos no `audit_index.csv` e inspeção dos diretórios de trabalho.

**Critério de avanço para Fase B.** MARCO-A-7 satisfeito. Adicionalmente, cenários de falha controlada testados conforme CA-FUN-08. O sistema é considerado "implementacionalmente válido" ao final da Fase A; o que ele produz com modelos free pode ser de qualidade muito baixa, mas o ciclo opera ponta a ponta.

## **8.4 Fase B — Benchmark com Modelos Baratos**

**Objetivo.** Executar o protocolo de benchmark detalhado no Bloco 7 sobre o módulo sintético MOD_SINT_001, com as quatro famílias de modelos candidatos identificadas, produzindo ranking empírico por agente e configuração mista vencedora. A qualidade do output passa, nesta fase, a ser critério central.

**Duração estimada.** Três a cinco semanas. A duração depende do número de configurações testadas (mínimo doze execuções homogêneas, mais até seis configurações mistas adicionais), da estabilidade dos modelos, e do tempo de avaliação qualitativa por configuração.

**Produtos esperados.**

Doze execuções iniciais com configurações homogêneas (quatro modelos, três execuções por modelo). Até seis execuções adicionais com configurações mistas, definidas após análise das homogêneas. Para cada execução, registro completo conforme BM-06 e avaliação qualitativa conforme BM-07. Relatório consolidado de benchmark em `bench/results/_relatorio_consolidado.md`, integrando todas as métricas, todas as execuções, ranking por agente e configuração eleita para a Fase D. Estimativa de custo projetado para produção, conforme seção 7.7.

A Atividade 2 sobre o MOD_SINT_001 é também exercitada na Fase B, com a configuração eleita ao final do benchmark, para validação do critério CA-FUN-02 e dos critérios qualitativos correspondentes. A resposta simulada da RFB é construída como insumo dessa execução, em diretório `tests/fixtures/MOD_SINT_001/resposta_rfb_simulada/`.

**Marcos verificáveis.**

**MARCO-B-1.** Configurações de benchmark documentadas em `bench/configs/`. Quatro configurações homogêneas iniciais escritas e revisadas. Verificação: inspeção dos arquivos.

**MARCO-B-2.** Doze execuções homogêneas concluídas. Resultados quantitativos coletados automaticamente. Avaliações qualitativas registradas. Verificação: inspeção do `audit_index.csv` (doze novos ciclos) e dos arquivos `bench/results/`.

**MARCO-B-3.** Análise das execuções homogêneas conduzida. Configurações mistas a serem testadas definidas em `bench/configs/`, com fundamentação registrada. Verificação: inspeção dos novos arquivos de configuração e do documento de fundamentação.

**MARCO-B-4.** Execuções das configurações mistas concluídas. Verificação: inspeção do `audit_index.csv` e dos arquivos `bench/results/`.

**MARCO-B-5.** Relatório consolidado de benchmark produzido. Ranking por agente fundamentado. Configuração eleita para Fase D explicitada. Estimativa de custo projetado calculada com premissas declaradas. Verificação: inspeção do relatório.

**MARCO-B-6.** Atividade 2 sobre MOD_SINT_001 executada com a configuração eleita. Critério CA-FUN-02 satisfeito. Verificação: inspeção do ciclo da Atividade 2 e do Relatório Final produzido.

**Critério de avanço para Fase C.** Todos os marcos da Fase B satisfeitos. Em particular, MARCO-B-5 é o produto institucional crítico — sem o relatório consolidado, a configuração para a Fase D fica sem fundamentação.

## **8.5 Fase C — (Reservada para o Estado-Alvo Foundry)**

**Status no escopo do piloto.** Fora.

A Fase C corresponde à execução do Departamento em estado-alvo de produção, com modelos servidos via Azure AI Foundry e a configuração esperada de Kimi K2.6 em Watson, GPT-5.5 em Sherlock e Claude Opus 4.7 em Mycroft (configuração esta sujeita a refinamento conforme resultado da Fase B). A Fase C não é exercitada no piloto pelo conjunto de razões já documentado: orçamento pessoal não suporta uso desses modelos para benchmarking; a liberação institucional do Foundry depende de aprovação de TI/Segurança que não está sob o controle do desenvolvedor; o ambiente Foundry exige integração com infraestrutura institucional que está fora do escopo do piloto.

A Fase C é registrada aqui como referência arquitetural e como destino do trabalho posterior. O critério de transição para a Fase C é o conjunto de pré-condições documentadas no Bloco 9 do PRD — encerramento formal do piloto, aprovação de TI/Segurança, alocação orçamentária institucional, treinamento operacional do Departamento.

## **8.6 Fase D — Validação Sobre Material Real (MOD_010)**

**Objetivo.** Executar o ciclo da Atividade 1 sobre o MOD_010 (Pessoa Física) com a configuração eleita ao final da Fase B, validando que o sistema opera adequadamente sobre material real entregue pela RFB e tratado pelo GT no piloto de validação concluído anteriormente. A Fase D fecha o piloto com confirmação empírica de que a arquitetura tem utilidade prática, não apenas em laboratório.

**Duração estimada.** Duas a três semanas. A duração inclui verificação inicial da disponibilidade e qualidade do material do MOD_010, possíveis ajustes de configuração ou prompt em resposta a particularidades do material real, e ciclos efetivos de execução.

**Produtos esperados.**

Verificação documentada da disponibilidade e estado do material do MOD_010, conforme P-05 do Bloco 5. Eventual ajuste de configuração de modelo em resposta ao volume ou complexidade do material real (custo unitário pode ser maior que o observado no MOD_SINT_001, exigindo eventual revisão de teto orçamentário ou troca de modelo para configuração mais econômica). Pelo menos uma execução bem-sucedida do ciclo da Atividade 1 sobre o MOD_010, satisfazendo CA-FUN-10 e CA-QUA-07. Avaliação qualitativa documentada do output produzido, idealmente em conjunto com auditor familiar com o MOD_010 (premissa não obrigatória, mas valiosa).

Caso a Fase D revele inadequação séria da configuração eleita pela Fase B sobre o material real — qualidade muito inferior, custo desproporcional, latência inaceitável — é executado mini-benchmark adicional restrito sobre o MOD_010 conforme BM-09, com até três configurações alternativas testadas. Esse mini-benchmark não invalida o relatório consolidado da Fase B; gera complemento que registra a observação e a configuração final ajustada.

**Marcos verificáveis.**

**MARCO-D-1.** Verificação do material do MOD_010 concluída. Premissa P-05 confirmada ou ajustada. Material organizado em `workspace/input/MOD_010/`. Verificação: inspeção do diretório e documento de verificação registrado em `docs/`.

**MARCO-D-2.** Primeira execução do ciclo da Atividade 1 sobre o MOD_010 com a configuração eleita pela Fase B. Verificação: inspeção do ciclo no `audit_index.csv` e do output produzido.

**MARCO-D-3.** Avaliação qualitativa do output da MARCO-D-2 documentada. Critério CA-QUA-07 satisfeito ou inadequação registrada com fundamentação. Verificação: leitura do documento de avaliação.

**MARCO-D-4.** (Condicional, apenas se MARCO-D-3 revelou inadequação.) Mini-benchmark adicional executado e relatório complementar produzido, com configuração final ajustada documentada. Verificação: inspeção dos novos ciclos e do relatório complementar.

**MARCO-D-5.** Documento de encerramento do piloto produzido em `docs/encerramento_piloto.md`, conforme protocolo descrito em 6.5. Verificação: leitura do documento de encerramento.

**Critério de conclusão do piloto.** MARCO-D-5 produzido e satisfazendo o critério geral de conclusão estabelecido em 6.5: todos os critérios funcionais e operacionais atendidos, ao menos seis dos sete critérios qualitativos com avaliação humana documentada com veredicto positivo.

## **8.7 Quadro de Síntese e Cronograma Indicativo**

A síntese do roadmap, em formato comprimido para visão de conjunto:

| Fase | Objetivo central | Produto verificável | Duração estimada |
|---|---|---|---|
| Fase 0 | Scaffolding e construção do módulo sintético | Repositório operacional + MOD_SINT_001 documentado | 4 a 6 semanas |
| Fase A | Validação de implementação com modelos free | Três execuções consecutivas bem-sucedidas | 2 a 3 semanas |
| Fase B | Benchmark com modelos baratos | Relatório consolidado de benchmark + configuração eleita | 3 a 5 semanas |
| Fase C | (Estado-alvo Foundry, fora do piloto) | — | — |
| Fase D | Validação sobre MOD_010 | Documento de encerramento do piloto | 2 a 3 semanas |

A duração total estimada do piloto, somando as quatro fases ativas (0, A, B, D), situa-se na faixa de onze a dezessete semanas em regime de dedicação parcial. A faixa larga reflete a natureza exploratória do trabalho — o tempo de descoberta de problemas durante a Fase A, em particular, é difícil de prever antes do início da implementação.

O cronograma é indicativo e não constitui compromisso institucional. A disciplina do roadmap está nos critérios de avanço entre fases, não nos prazos absolutos. Uma fase pode levar mais que o estimado e o piloto continua válido; uma fase pode ser declarada concluída antes do critério de avanço estar satisfeito e o piloto se torna inválido por construção. A primeira situação é gerenciável; a segunda, não.

A revisão do cronograma é exercício natural ao final de cada fase. O desenvolvedor, ao concluir uma fase, atualiza a estimativa das fases seguintes com base no aprendizado acumulado, e registra a revisão em log de planejamento dedicado em `docs/log_planejamento.md`. Esse registro é importante para memória institucional do projeto, não para controle externo.

---

# **Bloco 9 — Evolução Pós-Piloto**

## **9.1 Lógica e Escopo deste Bloco**

O Bloco 9 cumpre função particular no PRD: define o que está fora do piloto mas precisa ser antecipado neste documento, com clareza suficiente para que (a) o piloto seja construído de forma compatível com a evolução prevista, sem armadilhas arquiteturais que travem futuras transições; (b) o desenvolvedor e qualquer outro envolvido tenham, ao final do piloto, mapa claro do que vem a seguir e em que ordem; (c) o documento de encerramento do piloto (descrito em 6.5) possa ser lastreado em referência precisa às etapas posteriores.

A redação aqui é deliberadamente menos prescritiva que nos blocos anteriores. Os blocos 1 a 8 normatizam o piloto com requisitos verificáveis e critérios objetivos; o Bloco 9 esboça o caminho posterior com o nível de detalhe adequado a um horizonte mais longo, sujeito a revisão à medida que o piloto produz aprendizados e à medida que o contexto institucional do TCU e do GT Reforma Tributária evolui.

O Bloco 9 não substitui o PRD que será produzido para a fase de produção do Departamento. Quando a transição efetiva ocorrer, novo PRD próprio será escrito para essa fase, com requisitos funcionais e não funcionais detalhados, critérios de aceitação dimensionados à escala de produção, e roadmap próprio. O Bloco 9 do PRD do piloto é mapa, não compromisso.

A organização segue cinco eixos: a transição ao Azure AI Foundry, a extensão para as Atividades 3, 4 e 5 (Sala de Sigilo), o suporte aos demais módulos da CBS além do MOD_010, a integração com o motor gerador de documentos institucionais, e o conjunto de evoluções estruturais menores que o piloto deixa registradas como dívida a ser paga em momento posterior.

## **9.2 Eixo I — Transição ao Azure AI Foundry**

**Natureza da transição.** O piloto opera com OpenRouter como único provider de LLM. O estado-alvo de produção opera com Azure AI Foundry. A transição é, em termos de código, troca de implementação concreta da abstração `LLMClient` — operação tecnicamente trivial dadas as escolhas de design protegidas no piloto. Em termos institucionais, é processo significativo que envolve aprovação de TI/Segurança do TCU, alocação orçamentária, e estabelecimento de protocolos de operação compatíveis com a infraestrutura Azure.

**Pré-condições para a transição.** Cinco pré-condições, todas obrigatórias antes de qualquer execução do Departamento em ambiente Foundry sobre material institucional.

A primeira é o **encerramento formal do piloto** com documento de encerramento produzido conforme 6.5, satisfazendo o critério geral de conclusão. Sem encerramento formal, não há base empírica para a transição.

A segunda é a **aprovação de TI/Segurança do TCU** para uso do Foundry pelo Departamento, formalizada em documento próprio. A aprovação cobre, no mínimo: classes de modelos autorizadas, política de retenção de logs e prompts no provider, política de isolamento de dados, política de auditoria das chamadas, e responsabilidades operacionais. A elaboração desse documento de solicitação é trabalho institucional próprio, pertencente ao GT Reforma Tributária e ao próprio TCU, e deve preceder a transição.

A terceira é a **alocação orçamentária institucional**. O custo de operação do Departamento em Foundry, com Kimi K2.6, GPT-5.5 e Claude Opus 4.7 (ou configuração final que vier a ser eleita), é estimado pelo relatório consolidado da Fase B e pela validação da Fase D. A alocação cobre, no mínimo, a operação plena dos dezessete módulos com Atividades 1 e 2, e dos cinco módulos da Sala de Sigilo com Atividades 3, 4 e 5, com margem para iterações de revalidação.

A quarta é o **treinamento operacional dos auditores do GT** que exercerão o papel de Lestrade na operação plena. O piloto opera com Lestrade representado pelo desenvolvedor; em produção, o papel é exercido por auditores do GT, e a operação efetiva exige que esses auditores conheçam a CLI, o protocolo de chancela, o protocolo de verificação do Motor de Saída, o protocolo de aborto e retomada de ciclos, e o significado dos artefatos produzidos.

A quinta é a **configuração do ambiente de produção** com as decisões de infraestrutura próprias do TCU: VM Azure ou equivalente, política de backup do `workspace/`, integração com sistemas de identidade institucional para autenticação dos auditores que operam Lestrade, política de retenção de longo prazo dos diretórios de ciclos encerrados.

**Trajetória da transição.** A transição ocorre em quatro passos sequenciais, cada um com produto verificável.

Passo 1: implementação do `AzureFoundryClient` na camada `LLMClient`, seguindo a interface já estabelecida pelo `OpenRouterClient`. Esse passo é executado pelo desenvolvedor em ambiente local, com chave de teste do Foundry (idealmente disponibilizada para validação técnica antes da liberação plena), e validado por smoke test análogo ao da Fase 0 do piloto.

Passo 2: execução de smoke test em ambiente Foundry — equivalente da Fase A do piloto, mas restrito ao MOD_SINT_001 já validado. O objetivo é confirmar que o sistema opera no novo ambiente sem regressão funcional.

Passo 3: execução de revalidação no ambiente Foundry sobre o MOD_010, replicando o ciclo executado na Fase D do piloto, com a configuração definitiva (Kimi K2.6 ou modelo eleito para Watson, GPT-5.5 ou modelo eleito para Sherlock, Claude Opus 4.7 ou modelo eleito para Mycroft). O objetivo é confirmar que a configuração produz resultado pelo menos equivalente ao observado no piloto.

Passo 4: liberação para operação plena. A partir deste ponto, o Departamento opera sobre os módulos reais da CBS conforme o plano institucional do GT Reforma Tributária.

**Diferenças operacionais previstas.** Algumas diferenças entre piloto e produção são antecipadas e merecem registro para que a transição não as descubra como surpresa.

A latência observada em Foundry pode diferir significativamente da observada em OpenRouter, em qualquer direção — Foundry pode ser mais rápido por proximidade de rede e recursos dedicados, ou mais lento por overhead de auditoria e controles institucionais. A revisão dos critérios de RNF-LATE é trabalho da fase de produção.

A política de retry pode precisar de calibração diferente, dado que o Foundry tem comportamento próprio em relação a limites de taxa e a janelas de manutenção. O `agent.md` de cada agente é o ponto de ajuste, e a calibração é absorvida sem refatoração estrutural.

A operação multiusuário, ainda que não seja foco imediato da transição, é exigência natural da fase de produção. O atual desenho de monolito sequencial single-process atende usuário único; a operação por múltiplos auditores simultâneos exigirá adaptação — uso de mecanismo de bloqueio sobre o `audit_index.csv`, separação de namespaces de ciclos por operador, ou eventualmente migração para arquitetura com banco de dados leve. Essa adaptação é tratada no Eixo V deste bloco.

## **9.3 Eixo II — Atividades 3, 4 e 5 (Módulos da Sala de Sigilo)**

**Natureza da extensão.** O piloto exercita apenas as Atividades 1 (Validação de Módulo) e 2 (Revalidação de Módulo). As Atividades 3, 4 e 5 são exclusivas dos módulos selecionados para análise na Sala de Sigilo da RFB e correspondem aos três momentos descritos no Bloco 4 do documento conceitual e no Bloco 6 do documento da estratégia integrada do GT: produção do roteiro de perguntas para a reunião extraordinária de extração de dados (Atividade 3), produção do roteiro de testes para execução em campo e relatório de avaliação das respostas da RFB (Atividade 4), e validação dos dados coletados em campo (Atividade 5).

A extensão para essas atividades é incremental, não estrutural. A arquitetura do piloto — Motor de Start, Orquestrador, agentes em sequência, Stranger's Room com duas rodadas, Motor de Saída, chancela de Lestrade — é reutilizada integralmente. O que muda em cada nova atividade é o conjunto de inputs aceitos pelo Motor de Start, as instruções específicas que Mycroft delega aos agentes executores, e o tipo de output produzido ao final.

**Caminho de extensão.** A extensão para cada atividade segue o mesmo padrão.

Para a Atividade 3, o gatilho coincide com o encerramento da Atividade 1 nos módulos pré-selecionados para a Sala de Sigilo: ao chancelar o Relatório Preliminar, Lestrade confirma que o Roteiro de Perguntas para a Reunião Extraordinária também está pronto para saída. Tecnicamente, isso significa que Sherlock, na fase `sherlock_validacao` da Atividade 1 dos módulos da Sala de Sigilo, produz dois artefatos em vez de um — o output classificado ponto a ponto e o roteiro de perguntas. Mycroft consolida ambos. O Motor de Saída opera sobre os dois documentos. A chancela de Lestrade abrange ambos.

Para a Atividade 4, o gatilho é o recebimento, por Lestrade, da ata e da transcrição da reunião extraordinária realizada pelos auditores do GT junto à RFB. O Motor de Start verifica a presença desses documentos e gera novo manifesto de abertura referenciando o histórico completo do módulo. Watson analisa a ata e a transcrição, extrai pontos relevantes sobre como a extração foi realizada e gera insumos analíticos. Mycroft integra. Sherlock produz dois documentos: o roteiro de testes para execução em campo na Sala de Sigilo, em linguagem acessível aos auditores do GT, e o relatório de concordância ou discordância com as respostas dadas pela RFB na reunião extraordinária. A Stranger's Room opera com mesmo protocolo de duas rodadas. O Motor de Saída opera sobre os dois documentos.

Para a Atividade 5, o gatilho é o retorno dos auditores do GT da Sala de Sigilo com os dados coletados em campo. O Motor de Start verifica a presença dos dados e gera manifesto de abertura referenciando todo o histórico do módulo (Atividades 1, 3 e 4). Watson analisa os dados coletados em campo, confronta com os dados entregues pela RFB e produz análise comparativa com insights sobre o batimento entre os dois conjuntos. Sherlock valida os resultados dos testes, confronta os dados coletados com os dados entregues e produz conclusão sobre a consistência do módulo. O output da Atividade 5 retroalimenta a Atividade 2 como input adicional de evidência para o relatório final.

**Riscos arquiteturais antecipados.** A extensão não é arquiteturalmente arriscada — todos os componentes existentes são reutilizados. O risco principal é operacional: as Atividades 4 e 5 dependem de coordenação efetiva com os auditores do GT em campo, com protocolos formais de extração de dados pelo controle interno da RFB, com ambiente de processamento adequado para os dados extraídos. Essa coordenação é responsabilidade do GT Reforma Tributária e foge ao controle do Departamento, mas o sistema precisa estar preparado para receber os artefatos quando chegarem.

Há também risco terminológico: os documentos produzidos pelas Atividades 3 e 4 são consumidos por auditores do GT que não são especialistas em desenvolvimento, em validação metodológica formal ou em terminologia jurídica avançada. O roteiro de testes precisa ser legível pelos auditores em campo, e isso impõe ao Sherlock uma exigência de tradução que não estava presente nas Atividades 1 e 2. Os prompts e skills de Sherlock para essas atividades exigem calibração específica.

## **9.4 Eixo III — Suporte aos Demais 16 Módulos da CBS**

**Natureza da extensão.** O piloto exercita o sistema sobre o MOD_SINT_001 (módulo sintético) e o MOD_010 (Pessoa Física). Os demais dezesseis módulos da CBS — descritos no Bloco 6 do documento da estratégia integrada do GT — são objeto da operação plena do Departamento até 2032.

A extensão para os demais módulos é, em larga medida, exercício de operação contínua, não de desenvolvimento. O sistema, depois do piloto e da transição ao Foundry, está preparado para receber qualquer módulo conforme as etapas externas (1.1, 1.2, 1.3 do GT) o consolidem e o entreguem. Cada módulo segue o ciclo padrão: Atividade 1 sobre o material recebido da RFB, contraditório técnico mediado pelo GT, Atividade 2 sobre a resposta da RFB, e — para os cinco módulos pré-selecionados para a Sala de Sigilo — Atividades 3, 4 e 5.

**Particularidades por módulo.** Embora o ciclo seja padrão, alguns módulos apresentam particularidades que merecem atenção quando chegam ao Departamento.

O MOD_001 (Central) é o módulo de maior peso individual na formação da alíquota, conforme registrado no Bloco 6 do documento da estratégia integrada do GT. A complexidade volumétrica e a interdependência com outros módulos exigirão prompts e skills de Watson e Sherlock especificamente calibrados para o módulo. A primeira execução desse módulo no Departamento em produção é, na prática, exercício de calibração, não de operação rotineira.

O MOD_007 (Redutor de Compras Governamentais) tem impacto direto sobre o resultado do MOD_001 e exige tratamento articulado: o relatório consolidado final precisa demonstrar que o entendimento desse módulo é coerente com o entendimento do Central. A coordenação entre os ciclos dos dois módulos é trabalho do GT, mas o sistema precisa permitir que o Departamento, ao operar sobre o MOD_007, tenha acesso aos outputs já produzidos sobre o MOD_001 como referência cruzada.

O MOD_008 (Simples Nacional) tem universo de mais de dezoito milhões de empresas e teve piloto de validação já concluído pelo GT antes do Departamento ser instituído. Esse piloto produziu material que serve de baseline para a operação posterior do Departamento sobre o módulo, e o ciclo do Departamento sobre o MOD_008 tem natureza de ratificação técnica do trabalho prévio, não de validação inaugural.

Os MOD_009 (Operações Financeiras) e MOD_012 (Importação Geral) são os outros dois módulos da Sala de Sigilo, com complexidades técnicas próprias. Os módulos de prioridade padrão (MOD_002 a MOD_006, MOD_010, MOD_011, MOD_013 a MOD_017) seguem o ciclo padrão sem Atividades 3, 4 e 5.

**Necessidades de evolução do sistema.** A operação plena dos dezessete módulos pode revelar necessidades que o piloto e os primeiros ciclos pós-transição não anteciparam. Algumas são previsíveis: refinamento contínuo dos prompts e skills à luz do aprendizado acumulado, ajustes de configuração de modelos por módulo (alguns módulos podem se beneficiar de modelo distinto em Sherlock, por exemplo), evolução do Design System à medida que necessidades de visualização específica de cada módulo apareçam.

Outras necessidades são imprevisíveis e só emergirão na operação. A arquitetura do piloto, com configuração concentrada em três arquivos e separação clara entre componentes, facilita a absorção dessas necessidades sem refatoração estrutural. O log de planejamento previsto em 8.7, mantido ao longo da operação plena, é o instrumento natural para registrar essas necessidades à medida que aparecem.

**Relatório consolidado dos 17 módulos.** Ao término dos dezessete ciclos completos (Atividades 1 e 2 para todos, mais Atividades 3, 4 e 5 para os cinco da Sala de Sigilo), o Departamento produz o relatório consolidado que fundamentará o Acórdão do Tribunal. Esse relatório é produto distinto dos relatórios finais por módulo: integra a posição do Tribunal sobre a totalidade das propostas de cálculo recebidas e fundamenta o cálculo da alíquota de referência da CBS. A produção desse relatório é, conceitualmente, atividade pós-piloto adicional, ainda que não tenha sido enumerada como Atividade 6 nos documentos antecedentes.

A arquitetura do Departamento permite essa atividade naturalmente: Mycroft consolida sobre os outputs já encerrados de todos os ciclos. A particularidade é o volume — Mycroft, em uma única execução, opera sobre o conjunto integrado de todos os relatórios finais, e o pacote de input chega à fronteira da janela de contexto dos modelos. Estratégia de chunking, sumarização hierárquica em duas passagens (primeiro síntese por bloco temático, depois síntese geral), ou uso de modelo com janela de contexto especialmente longa para essa execução são opções a serem avaliadas no momento.

## **9.5 Eixo IV — Integração com o Motor Gerador de Documentos Institucionais**

**Natureza da integração.** O piloto produz outputs em Markdown estruturado, conforme R-13 do Bloco 5. A conversão final para docx no padrão Design System TCU-CBS v5 é responsabilidade do motor gerador de documentos já existente no projeto maior. A integração refinada entre o Departamento e esse motor é tarefa pós-piloto, e este eixo descreve seu escopo.

O motor gerador de documentos opera atualmente sobre Markdown ou documento docx existente como entrada, produzindo docx padronizado conforme os parâmetros documentados no Apêndice A do documento da estratégia integrada do GT: tipografia Aptos, sistema cromático TCU-CBS, espaçamento padronizado, sistema semântico de status com cores e ícones próprios. A integração com o Departamento estabelece a ponte entre o Markdown produzido por Mycroft e o docx final que o GT distribui para a RFB no contraditório técnico ou que o Tribunal anexa ao Acórdão.

**Trajetória da integração.** A integração ocorre em três passos.

Passo 1: padronização do Markdown produzido pelo Departamento. O motor gerador de documentos consome um subset definido de elementos Markdown (cabeçalhos por nível, listas, tabelas, citações, blocos de código, estados semânticos representados por marcações específicas). O piloto já produz Markdown estruturado, mas a aderência rigorosa ao subset esperado pelo motor não é critério de aceitação do piloto. O passo 1 da integração é levantar o subset, ajustar o template de output de Mycroft para aderir estritamente, e validar com pequena bateria de conversões manuais.

Passo 2: automação da conversão. O Departamento, ao chancelar um output, dispara o motor gerador de documentos sobre o Markdown e produz, na mesma operação, o docx correspondente. Tecnicamente, o Departamento invoca o motor como subprocesso ou via API, conforme a interface que o motor expõe. O docx é colocado no diretório de output do ciclo, ao lado do Markdown, e ambos são entregues ao GT. O `audit_index.csv` registra ambos os artefatos.

Passo 3: ajuste do Motor de Saída para operar sobre ambos os formatos. O Motor de Saída, no piloto, opera apenas sobre o Markdown — formato simples de varrer com regras heurísticas. A varredura do docx exige adaptação: ou o Motor opera sobre o Markdown antes da conversão (preferível, porque Markdown é mais simples) e a conversão preserva fielmente o conteúdo já filtrado, ou o Motor adquire capacidade de varrer docx (mais complexo, porque o docx tem texto distribuído em múltiplos elementos XML).

A escolha entre as duas estratégias é decisão técnica do momento da integração, baseada em quão fielmente a conversão preserva o conteúdo do Markdown. Se a conversão é literal (texto inalterado, apenas formatação adicionada), o Motor de Saída opera sobre o Markdown e a varredura sobre o docx é desnecessária. Se a conversão envolve transformações de texto (expansão de marcações semânticas, geração de sumários, inclusão de cabeçalhos institucionais), o Motor precisa varrer o docx ou a conversão precisa ser controlada para não introduzir marcas internas.

**Riscos antecipados.** O risco principal é de divergência entre as expectativas do motor gerador de documentos e a produção do Mycroft. O motor pode ter exigências formais específicas — formato exato de declaração de campos, ordem dos cabeçalhos, ausência de elementos não suportados — que o piloto não considerou. A primeira tentativa de integração revelará essas divergências, e a calibração é trabalho iterativo.

Outro risco é a manutenção dupla. Mudanças no motor gerador de documentos (nova versão do Design System, ajustes do TCU em tipografia ou sistema cromático) podem exigir adaptação simultânea no Departamento. A coordenação entre as evoluções dos dois sistemas é trabalho institucional contínuo, não trabalho de desenvolvimento isolado.

## **9.6 Eixo V — Evoluções Estruturais Menores**

Este eixo agrupa um conjunto de evoluções estruturais que não justificam eixo próprio mas precisam ser registradas como dívida técnica do piloto, a ser paga em momento posterior.

**Vetorização semântica de traces e relatórios.** O sistema de filesystem-first do piloto facilita inspeção humana direta, mas dificulta busca semântica sobre o histórico. Em produção, com dezenas de ciclos encerrados e centenas de arquivos da Stranger's Room acumulados, a capacidade de fazer perguntas como "em quais módulos Sherlock encontrou divergência sobre o tratamento de receitas financeiras?" exige indexação semântica. A vetorização não substitui o filesystem; complementa com camada de busca eficiente. Implementação prevista: uso de embedding via OpenAI ou modelo open-source local, indexação em base vetorial leve (Chroma, LanceDB), consultas via subcomando dedicado da CLI. A introdução não altera os artefatos institucionais — apenas adiciona camada de consulta.

**Dashboard analítico do Departamento.** A operação plena gera volume de dados estruturados no `audit_index.csv` que justificam visualização sintética: número de ciclos por módulo, distribuição de status finais, custo agregado por módulo, latência média por configuração de modelo, taxa de overrule de Mycroft sobre Watson e sobre Sherlock, distribuição de classificações semânticas (Atendido / Atendido Parcialmente / Divergência / etc.) por módulo. Essas visualizações servem ao GT Reforma Tributária para acompanhamento institucional e ao Departamento para diagnóstico operacional. Implementação prevista: dashboard simples em Streamlit ou equivalente, lendo o `audit_index.csv` e os metadados dos ciclos, sem alteração na arquitetura subjacente.

**Operação multiusuário.** Conforme antecipado em 9.2, a operação plena exige suporte a múltiplos auditores simultâneos. A adaptação técnica envolve: mecanismo de bloqueio sobre o `audit_index.csv` para escrita atômica concorrente; identificação do auditor em todos os registros (campo `lestrade_operator_id` adicional ao índice); separação de visibilidade quando múltiplos ciclos estão em andamento simultaneamente em módulos distintos; convenção de paths que permita identificar quem operou cada ciclo. Não exige migração para banco de dados — o filesystem com lock cooperativo é suficiente para o volume previsto, e mantém a virtude da inspeção humana direta.

**Integração com Active Directory e identidade institucional.** O piloto opera com auditor único representado pelo desenvolvedor, sem autenticação. A operação institucional exige autenticação via AD do TCU ou serviço equivalente, com cada chancela de Lestrade carregando a identidade verificada do auditor responsável. A integração é trabalho técnico padrão (via biblioteca de autenticação Microsoft, kerberos ou OIDC) e fica registrada como exigência da fase de produção em Foundry, não do piloto.

**Observabilidade externa.** O piloto opera com observabilidade integralmente local, conforme RNF-OBSE-05. Em produção, a integração com sistemas institucionais de monitoramento (Datadog, Grafana, ou ferramenta equivalente adotada pelo TI do TCU) é exigência operacional natural, especialmente para detecção precoce de falhas, alertas em latência anômala, e dashboards de saúde do sistema. A integração é incremental: o sistema continua produzindo seus logs locais, e um exportador opcional encaminha dados para o serviço externo. Os artefatos institucionais (manifesto, Stranger's Room, relatórios) permanecem no filesystem; apenas os logs técnicos e métricas operacionais são duplicados.

**Política de retenção de longo prazo.** O piloto preserva todo ciclo encerrado integralmente, conforme Artigo 16 da Constituição. Em produção, com horizonte até 2032 e dezenas de ciclos por ano, o volume cumulativo do `workspace/` cresce significativamente. A política de retenção de longo prazo precisa equilibrar a exigência constitucional de preservação com a viabilidade operacional do armazenamento. Soluções possíveis: arquivamento em armazenamento frio (Azure Blob Storage tier Archive) após período definido sem acesso, mantendo apenas índice ativo localmente; compressão de diretórios de ciclos antigos; eventualmente migração de ciclos com mais de cinco anos para armazenamento institucional permanente do TCU. A definição da política é trabalho institucional, não técnico, e fica fora do escopo do piloto.

**Refinamento contínuo de prompts e skills.** Os arquivos `soul.md`, `skills.md` e `agent.md` de cada agente, produzidos no piloto, são versão inicial sujeita a refinamento contínuo. Cada ciclo executado em produção produz aprendizado sobre como os agentes performam — onde Mycroft questiona insuficientemente, onde Watson alucina classificações, onde Sherlock fundamenta de forma genérica em vez de citar dispositivo específico. Esse aprendizado é capturado em log de revisão dedicado e dispara revisões pontuais dos prompts. A disciplina é manter cada revisão versionada e registrar, no manifesto do ciclo seguinte, qual versão dos prompts está em uso. Reprodutibilidade conforme RNF-REPR-04 depende dessa disciplina.

## **9.7 Quadro de Síntese da Evolução Pós-Piloto**

A síntese, em formato comprimido para visão de conjunto:

| Eixo | Natureza | Pré-condição mínima | Horizonte estimado |
|---|---|---|---|
| I — Transição ao Foundry | Troca de provider + aprovação institucional | Encerramento do piloto + aprovação TI/Segurança | Imediatamente após piloto |
| II — Atividades 3, 4 e 5 | Extensão incremental da arquitetura | Transição ao Foundry concluída + módulos da Sala de Sigilo prontos | Concomitante à operação plena dos módulos da Sala de Sigilo |
| III — Demais 16 módulos | Operação contínua | Transição ao Foundry concluída | Operação contínua até 2032 |
| IV — Integração motor docx | Padronização do output + automação da conversão | Operação plena estabilizada | Primeiro semestre da operação plena |
| V — Evoluções estruturais menores | Dívida técnica acumulada | Operação plena estabilizada | Distribuída ao longo do horizonte |

A ordem temporal natural é: encerrar o piloto → executar a transição ao Foundry → iniciar a operação plena com os módulos disponíveis → integrar progressivamente o motor gerador de documentos → estender para as Atividades 3, 4 e 5 conforme os módulos da Sala de Sigilo se tornem prontos → absorver as evoluções estruturais menores conforme as necessidades emerjam.

Esse roadmap pós-piloto não é compromisso operacional do desenvolvedor isolado: é mapa institucional do que o Tribunal precisará organizar para que o Departamento opere plenamente até 2032. A construção do PRD próprio da fase de produção, com requisitos detalhados e cronograma vinculante, é trabalho dessa fase, não do piloto. O Bloco 9 do PRD do piloto cumpre seu papel ao deixar registrado, com clareza, o conjunto de evoluções previstas.

---

# **Bloco 10 — Glossário e Referências**

## **10.1 Lógica deste Bloco**

O Bloco 10 cumpre função distinta dos blocos anteriores: não introduz nova matéria normativa, mas consolida o vocabulário e os pontos de apoio que permitem a leitura autônoma do PRD por terceiros não familiarizados com o projeto.

A consolidação aqui não é redundante. Os termos de uso recorrente foram explicados, em contexto, ao longo dos blocos anteriores; o Bloco 10 reúne essas explicações em um lugar único, em ordem alfabética, com definição compacta e referência ao bloco onde o termo foi tratado em profundidade. As referências documentais e normativas, de igual modo, ficam consolidadas em listagem única para que o leitor encontre, sem busca, a totalidade das fontes que o PRD invoca.

A organização é em quatro seções: glossário propriamente dito, com os termos definidos; referências documentais, agrupadas por natureza (documentos antecedentes do projeto, base normativa, recursos técnicos, recursos conceituais); identificação processual e institucional; e encerramento do PRD com a indicação da próxima etapa do trabalho de documentação.

## **10.2 Glossário**

**Acórdão 2833/2025-Plenário.** Acórdão do Tribunal de Contas da União, de 3 de dezembro de 2025, sob relatoria do Ministro Vital do Rêgo, que homologou a metodologia de cálculo da alíquota de referência da CBS elaborada pela Receita Federal do Brasil. Constitui, junto com a Constituição Federal de 1988, a Emenda Constitucional 132/2023 e a Lei Complementar 214/2025, a base normativa válida para todo o trabalho do Departamento.

**Agente.** Componente funcional do Departamento de Validação Assistida com função estritamente delimitada e hierarquia de atuação clara. Há quatro agentes: três automatizados com modelos de linguagem acoplados (Mycroft, Watson, Sherlock) e um humano (Lestrade). Tratado em profundidade no Bloco 3 do documento conceitual `dva_cbs_completo_v03.docx`.

**`agent.md`.** Arquivo de configuração runtime de um agente, contendo frontmatter YAML com modelo, provider, temperatura, tools, política de retry e demais parâmetros de invocação, mais o prompt de sistema do agente. Ausente em Lestrade. Detalhamento previsto no SDD.

**`agents_spec.yaml`.** Arquivo de configuração que mapeia, em ponto único, cada agente ao modelo e ao provider que utiliza, juntamente com parâmetros de runtime. Permite a troca de modelo sem alteração de código.

**Atividade.** Unidade de trabalho do Departamento, composta por gatilho de início, conjunto de inputs, execução interna sequencial sob orquestração de Mycroft, pontos de Human-in-the-Gate e output rastreável. Há cinco atividades catalogadas (1 a 5), com a possibilidade de atividades ad hoc por solicitação de Lestrade dentro dos limites constitucionais. Tratada no Bloco 4 do documento conceitual.

**`audit_index.csv`.** Arquivo CSV que constitui o índice único e cronológico de todos os ciclos do Departamento, com identificador, módulo, atividade, status, datas, agentes envolvidos e métricas agregadas. Tratado em RF-PE-03 e RF-PE-04.

**Auditor Chefe.** Cargo formal do agente Mycroft Holmes, responsável pela orquestração interna do Departamento.

**Auditor de Integridade Técnica.** Cargo formal do agente Dr. John Watson, responsável pelas verificações da Camada 0.

**Auditor de Validação Metodológica CBS.** Cargo formal do agente Sherlock Holmes, responsável pelas verificações das Camadas 1, 2 e 3.

**Auditor Responsável | Human-in-the-Gate.** Cargo formal do agente humano Lestrade, único componente do Departamento sem linha de código dedicada e sem modelo de linguagem acoplado, e única porta de entrada e saída do Departamento em relação ao mundo externo.

**Camada 0.** Camada de validação que verifica a integridade física e a consistência interna dos documentos entregues pela RFB, sem confronto com a metodologia homologada. Operada por Watson. Tratada no Bloco 3 do documento da estratégia integrada do GT.

**Camada 1.** Camada de validação que verifica a aderência metodológica dos procedimentos da RFB ao prescrito pelo Acórdão 2833/2025-Plenário. Operada por Sherlock.

**Camada 2.** Camada de validação que verifica a reprodutibilidade da extração dos dados pela RFB, em modalidade documental para todos os módulos e em modalidade completa (em campo na Sala de Sigilo) para os módulos pré-selecionados.

**Camada 3.** Camada de validação que verifica a consistência do resultado final apresentado pela RFB à luz das camadas anteriores.

**CBS.** Contribuição sobre Bens e Serviços, tributo criado pela Emenda Constitucional 132/2023 cujo cálculo da alíquota de referência é o objeto do trabalho do TCU sob o mandato da reforma tributária.

**Ciclo.** Unidade de execução do Departamento, correspondente a uma instância de uma atividade sobre um módulo. Cada ciclo tem identificador único (`cycle_id`), diretório de trabalho isolado, manifesto de abertura, traces da Stranger's Room, output consolidado e registro no `audit_index.csv`.

**Clube Diógenes.** Clube literário descrito no conto "O Intérprete Grego" de Arthur Conan Doyle, frequentado por Mycroft Holmes. A arquitetura do Departamento toma o Clube Diógenes como metáfora estrutural — silêncio interno, especialistas que não se sobrepõem, hierarquia de síntese e revisão, porta única de saída. Tratado no Bloco 2 do documento conceitual.

**Constituição do Departamento.** Conjunto de dezesseis artigos que estabelecem as regras fundamentais de operação do Departamento. Constitui restrição absoluta para o piloto e para a operação plena. Estabelecida no Bloco 5 do documento conceitual.

**`cycle_id`.** Identificador único de ciclo no formato `{MOD_ID}_A{ATIVIDADE}_{TIMESTAMP_UTC}`. Tratado em RF-MS-04.

**Departamento de Validação Assistida.** Unidade funcional, com autonomia e identidade própria, responsável pela análise técnica de integridade dos documentos entregues pela RFB e pela verificação de aderência à metodologia homologada. Inserido dentro do fluxo mais amplo conduzido pelo GT Reforma Tributária. Sigla: DVA-CBS.

**Etapa.** Unidade do fluxo operacional do GT Reforma Tributária, descrita no Bloco 4 do documento da estratégia integrada do GT. Há seis etapas (1 a 6), das quais o Departamento opera predominantemente nas Etapas 3 (análise pelo Departamento) e 6 (revalidação e relatório final), com participação na Etapa 4 (reunião extraordinária e trabalho em campo) por meio dos roteiros que produz nas Atividades 3 e 4. Etapa não se confunde com Camada nem com Atividade.

**Fase.** No PRD, a expressão "fase" é empregada em dois contextos distintos. No contexto interno do ciclo do Departamento, fase é a unidade da Stranger's Room, com duas fases por ciclo: `watson_integridade` e `sherlock_validacao`. No contexto do roadmap do piloto, fase é a unidade temporal de progresso (Fase 0, A, B, C, D), conforme Bloco 8.

**Foundry.** Abreviação de Azure AI Foundry, plataforma de modelos de linguagem da Microsoft que constitui o destino institucional do Departamento na transição pós-piloto, conforme Bloco 9.

**GT Reforma Tributária.** Grupo de Trabalho da SecexContas/TCU instituído para executar o mandato constitucional do TCU sobre o cálculo da alíquota de referência da CBS. Conduz as etapas externas ao Departamento e recebe os outputs deste após chancela de Lestrade.

**HitG (Human-in-the-Gate).** Princípio estruturante segundo o qual nenhuma transição entre etapas ou fases ocorre sem aceite formal do auditor humano responsável. Estabelecido no Bloco 4 do documento da estratégia integrada do GT e replicado dentro do Departamento por meio do agente Lestrade.

**Lestrade.** Agente humano do Departamento, exercendo o papel de Auditor Responsável e Human-in-the-Gate. Único ponto de contato oficial entre o Departamento e o mundo externo. Nome derivado do Inspetor Lestrade, personagem de Arthur Conan Doyle.

**`LLMClient`.** Camada de abstração no código que isola o conhecimento sobre providers específicos de modelo (OpenRouter, Foundry, Anthropic, OpenAI). Permite a troca de provider sem alteração do código de aplicação, conforme RNF-PORT-03.

**Manifesto de abertura.** Arquivo Markdown gerado pelo Motor de Start no início de cada ciclo, registrando módulo, atividade, arquivos de input com hashes, timestamp e demais metadados estruturais do ciclo. Tratado em RF-MS-05.

**Metodologia homologada.** Documento normativo elaborado pela RFB e homologado pelo Tribunal por meio do Acórdão 2833/2025-Plenário. Constitui, junto à legislação, a única base normativa válida para análise de mérito realizada no Departamento, conforme Artigo 2 da Constituição.

**MOD_010.** Identificador do módulo "Pessoa Física", utilizado na Fase D do roadmap do piloto como material real entregue pela RFB e tratado pelo GT no piloto de validação concluído anteriormente.

**MOD_SINT_001.** Identificador do módulo sintético construído na Fase 0 do roadmap do piloto, contendo inconsistências propositais documentadas em `inconsistencias_conhecidas.md`. Utilizado nas Fases A e B do piloto.

**Módulo.** Unidade temática da metodologia homologada. Há dezessete módulos (MOD_001 a MOD_017), correspondentes aos Apêndices I a XVII do Acórdão 2833/2025-Plenário. Tratados no Bloco 6 do documento da estratégia integrada do GT.

**Motor de Saída.** Componente do Departamento que executa a verificação peremptória exigida pelo Artigo 15 da Constituição antes da chancela final de Lestrade, varrendo o documento consolidado à procura de marcas internas, identificações de agente ou referências a estruturas próprias do Departamento. Tratado em RF-MV.

**Motor de Start.** Componente do Departamento que abre cada ciclo, verificando inputs, calculando hashes, gerando manifesto, isolando o ambiente de trabalho e aguardando confirmação de Lestrade. Tratado em RF-MS.

**Mycroft.** Agente do Departamento exercendo o papel de Auditor Chefe (orquestração interna). Nome derivado de Mycroft Holmes, personagem de Arthur Conan Doyle.

**OpenRouter.** Plataforma de roteamento de modelos de linguagem que serve, no piloto, como provider único para Watson, Sherlock e Mycroft. Tratada como restrição R-05 do Bloco 5.

**Orquestrador.** Componente de infraestrutura do Departamento que conduz a sequência interna do ciclo após a confirmação de Lestrade. Distinto de Mycroft: o Orquestrador é infraestrutura, Mycroft é o agente de modelo de linguagem que toma decisões dentro dessa infraestrutura. Tratado em RF-OR.

**Provider.** Provedor de serviços de modelos de linguagem. No piloto, OpenRouter; em produção, Azure AI Foundry.

**RFB.** Secretaria Especial da Receita Federal do Brasil, órgão da administração tributária federal que elaborou a metodologia homologada e que entrega ao TCU as propostas de cálculo da CBS módulo a módulo.

**Sala de Sigilo.** Ambiente controlado da RFB onde os auditores do TCU realizam, em modalidade completa da Camada 2, a reexecução das consultas de extração nas bases de dados da Receita, sem extração de dados brutos para fora da infraestrutura. Tratada no Bloco 6 do documento da estratégia integrada do GT.

**SDD.** Software Design Document. Documento de design técnico do sistema, próximo a ser produzido após o PRD. Detalha a arquitetura interna, a estrutura de módulos de código, as interfaces entre componentes, os formatos de troca de dados e as decisões técnicas de implementação.

**SecexContas.** Secretaria de Controle Externo de Contas do Tribunal de Contas da União, unidade na qual está alocado o GT Reforma Tributária e o processo TC 015.848/2025-6.

**Sherlock.** Agente do Departamento exercendo o papel de Auditor de Validação Metodológica CBS. Nome derivado de Sherlock Holmes, personagem de Arthur Conan Doyle.

**`skills.md`.** Arquivo de catálogo das habilidades operacionais nomeadas de um agente, com gatilho, inputs, passos e output esperado para cada habilidade. Ausente em Lestrade. Detalhamento previsto no SDD.

**`soul.md`.** Arquivo que descreve a identidade, perfil, valores e limites do agente em prosa. Ausente em Lestrade. Detalhamento previsto no SDD.

**Stranger's Room.** Componente de persistência e protocolo dos artefatos de revisão de Mycroft sobre os agentes executores. Tecnicamente, diretório com convenção de nomes numerada (01_apresentacao.md, 02_critica_mycroft_r1.md, 03_resposta_r1.md, 04_critica_mycroft_r2.md, 05_resposta_r2.md, 99_decisao_final.md) e protocolo de escrita estritamente sequencial. Tratada em RF-SR. Nome derivado da Sala dos Estrangeiros do Clube Diógenes em Conan Doyle.

**TCU.** Tribunal de Contas da União, órgão de controle externo da União, dotado pela Emenda Constitucional 132/2023 da competência inédita de calcular a alíquota de referência da CBS.

**Trace.** Registro técnico de uma chamada a modelo de linguagem ou de um evento estruturado do sistema. Os traces de chamadas a modelo ficam em `workspace/cycles/{cycle_id}/_runtime/llm_calls/`; os logs de eventos ficam em `workspace/cycles/{cycle_id}/_runtime/events.jsonl`. Tratados em RNF-RAST-06 e RNF-OBSE-02 a RNF-OBSE-03.

**Watson.** Agente do Departamento exercendo o papel de Auditor de Integridade Técnica. Nome derivado do Dr. John Watson, personagem de Arthur Conan Doyle.

**`workspace/`.** Diretório raiz do espaço de trabalho do Departamento, configurável via variável de ambiente `DIOGENES_WORKSPACE`. Contém os subdiretórios `input/` (entregas externas, intocáveis), `cycles/` (diretórios de trabalho dos ciclos) e o arquivo `audit_index.csv`. Tratado em RF-PE-01 e RF-PE-02.

## **10.3 Referências**

### **10.3.1 Documentos Antecedentes do Projeto**

- `dva_cbs_completo_v03.docx` — Documento de Arquitetura Conceitual do Departamento de Validação Assistida da CBS (DVA-CBS, Projeto Diógenes). Versão 0.3, uso interno restrito. Estrutura em cinco blocos: Missão e Contexto, A História que Levou ao Nome, Os Agentes, Workflows por Atividade, e Constituição do Departamento. Constitui base conceitual para todo o trabalho descrito neste PRD.

- `GT_CBS_Estrategia_Integrada_Validacao.docx` — Estratégia Integrada de Validação da CBS produzida pelo GT Reforma Tributária. Versão 1.0, datada de 30 de abril de 2026, uso interno restrito. Estrutura em sete blocos e um apêndice: Mandato/Contexto/Escopo, Estratégia Geral, Camadas de Validação, Workflow Operacional, O Departamento no Fluxo do GT, Módulos da Sala de Sigilo, Governança, e Apêndice de Padronização Documental. Estabelece o fluxo institucional dentro do qual o Departamento opera.

### **10.3.2 Base Normativa**

- Constituição da República Federativa do Brasil, de 5 de outubro de 1988.
- Emenda Constitucional nº 132, de 20 de dezembro de 2023 — Reforma Tributária.
- Lei Complementar nº 214, de 16 de janeiro de 2025 — Disciplina o Imposto sobre Bens e Serviços, a Contribuição sobre Bens e Serviços e o Imposto Seletivo. Especialmente os artigos 19 e 349 a 353.
- Lei Complementar nº 227 — alterações à LC 214/2025 incorporadas à base de referência.
- Acórdão TCU 2833/2025-Plenário, de 3 de dezembro de 2025, relatado pelo Ministro Vital do Rêgo. Homologa a metodologia de cálculo da alíquota de referência da CBS, organizada em dezessete módulos (Apêndices I a XVII).

### **10.3.3 Recursos Técnicos**

- Especificação OpenAPI do OpenRouter — disponível em `https://openrouter.ai/docs`. Define o protocolo de chamadas que a camada `LLMClient` implementa no piloto.
- Catálogo de modelos do OpenRouter — disponível em `https://openrouter.ai/models`. Contém a relação atualizada de modelos disponíveis, com precificação e características técnicas. Consultado para a definição final dos candidatos das Fases A e B do roadmap.
- Documentação do Azure AI Foundry — disponível em `https://learn.microsoft.com/azure/ai-foundry`. Referência para a implementação futura do `AzureFoundryClient` na fase pós-piloto.
- Documentação das bibliotecas Python da stack: Pydantic 2.x, httpx, Typer, Rich, python-frontmatter, PyYAML, python-docx, openpyxl, sqlparse, nbformat, pytest. Versões fixadas em `pyproject.toml` no momento de início da Fase 0.

### **10.3.4 Recursos Conceituais**

- Doyle, Arthur Conan. "The Greek Interpreter" (O Intérprete Grego), publicado em The Strand Magazine, setembro de 1893, posteriormente coletado em "The Memoirs of Sherlock Holmes" (As Memórias de Sherlock Holmes). Conto que estabelece o Clube Diógenes e a figura de Mycroft Holmes como inteligência sintética superior, inspiração estrutural para a arquitetura do Departamento.

- Material institucional do TCU sobre o sistema cromático, tipográfico e semântico do Design System TCU-CBS, em sua quinta versão. Referenciado no Apêndice A do documento da estratégia integrada do GT e mencionado em RNF-USAB-05 do PRD.

## **10.4 Identificação Processual e Institucional**

| Item | Identificação |
|---|---|
| Processo | TC 015.848/2025-6 |
| Unidade | SecexContas — Secretaria de Controle Externo de Contas |
| Órgão | Tribunal de Contas da União |
| Grupo de Trabalho | GT Reforma Tributária |
| Departamento | Departamento de Validação Assistida da CBS (DVA-CBS) |
| Codinome | Projeto Diógenes |
| Relator | Ministro Vital do Rêgo |
| Documento | PRD — Piloto Diógenes Local |
| Versão | 0.1 |
| Data | 7 de maio de 2026 |
| Uso | Interno Restrito |

## **10.5 Encerramento do PRD**

Este PRD encerra-se com a consolidação acima. Sua função é estabelecer, com profundidade adequada, o conjunto de requisitos, restrições, premissas, critérios de aceitação, métricas, roadmap e horizonte pós-piloto que orientam a construção do Piloto Diógenes em ambiente local, antes da transição ao Azure AI Foundry e da operação plena do Departamento.

A próxima etapa do trabalho de documentação é o **SDD — Software Design Document**, que detalhará: a estrutura interna do repositório de código; as interfaces entre os componentes (Motor de Start, Orquestrador, agentes, Stranger's Room, Motor de Saída, persistência, CLI); os formatos exatos dos arquivos institucionais e técnicos (manifesto, traces, decisões finais, relatórios); o protocolo de troca de dados entre o Orquestrador e os agentes; os esquemas de validação Pydantic dos artefatos persistidos; a política de retry da camada `LLMClient`; e o padrão de logs estruturados. O SDD é o documento que traduz o "o quê" deste PRD no "como" da implementação.

Após o SDD, serão produzidos os arquivos `soul.md`, `skills.md` e `agent.md` para cada um dos três agentes automatizados (Mycroft, Watson, Sherlock), nessa ordem: a identidade primeiro, as habilidades em seguida, a configuração runtime por último. Esses arquivos completam o conjunto inicial de documentação institucional necessário para o início da Fase 0 do roadmap.

A partir desse momento, o trabalho passa do plano da documentação para o plano da implementação. O PRD continua vivo — revisões pontuais serão necessárias à medida que aprendizados emergirem da implementação —, mas seu papel principal está cumprido quando a Fase 0 se inicia tendo o conjunto de requisitos aqui consolidado como contrato técnico explícito entre quem projeta, quem implementa e quem audita.

---

*DVA-CBS | Projeto Diógenes — TC 015.848/2025-6*
*Tribunal de Contas da União | Secretaria de Controle Externo de Contas*
*Documento de Trabalho Interno | Uso Restrito*
*Versão 0.1 — 7 de maio de 2026*
