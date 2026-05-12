---
documento: SDD — Piloto Diógenes Local
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
grupo_de_trabalho: GT Reforma Tributária
versao: 0.1
status: Documento de Trabalho Interno — Em construção (Bloco 1 de 14)
data: 2026-05-07
uso: Interno Restrito
documentos_antecedentes:
  - dva_cbs_completo_v03.docx (Arquitetura Conceitual do Departamento)
  - GT_CBS_Estrategia_Integrada_Validacao.docx (Estratégia Integrada do GT)
  - PRD_piloto_diogenes_local_v01.md (Product Requirements Document do Piloto)
---

# **SDD — Piloto Diógenes Local**
## Departamento de Validação Assistida da CBS

> **Status:** Documento de Trabalho Interno em construção. Bloco 1 de 14.
> **Escopo:** Arquitetura de software do piloto operacional do Departamento de Validação Assistida em ambiente local ou VPS particular, com modelos servidos via OpenRouter, antes de qualquer migração para infraestrutura institucional.
> **Relação com documentos antecedentes:** Este SDD deriva do PRD e dos documentos arquiteturais do Departamento. Não substitui nenhum deles — traduz seus requisitos em decisões de implementação concretas.

---

# **Bloco 1 — Visão Geral da Arquitetura**

## **1.1 O Que Este Documento Faz**

O PRD define o que o sistema deve fazer e como deve se comportar. O SDD define como o sistema é construído para satisfazer esses requisitos. A distinção é operacional: o PRD é o contrato com o auditor institucional; o SDD é o contrato com o desenvolvedor.

O SDD não justifica por que o Departamento existe, por que as atividades estão estruturadas como estão, ou por que a Constituição tem dezesseis artigos. Essas justificativas estão nos documentos antecedentes. Este documento parte do ponto em que o PRD encerrou — com requisitos funcionais, não funcionais, restrições e critérios de aceitação estabelecidos — e desce para o nível das estruturas de dados, interfaces de módulos, fluxos de execução e decisões técnicas concretas que fazem o sistema rodar.

Toda referência a um requisito do PRD utiliza o código correspondente (`RF-MS-01`, `RNF-PORT-03` etc.) para rastreabilidade entre os dois documentos.

## **1.2 As Quatro Decisões Fundadoras**

A arquitetura do Departamento resulta de quatro decisões fundadoras, tomadas antes de qualquer escolha de biblioteca ou estrutura de módulo. Essas decisões não são preferências de estilo: são consequências diretas das restrições institucionais e dos princípios constitucionais do Departamento.

### **1.2.1 Python Custom, Sem Framework de Agentes**

O sistema é implementado em Python puro, sem uso de LangChain, LangGraph, CrewAI, AutoGen, Pydantic AI, ou qualquer outro framework de orquestração de agentes.

A razão é auditabilidade. O Departamento opera sobre material que fundamentará o cálculo de uma alíquota com efeito sobre todos os contribuintes brasileiros. Cada decisão do sistema precisa ser rastreável a uma linha de código legível por qualquer pessoa com conhecimento intermediário de Python — não a um estado interno de um grafo de execução de framework, não a um prompt gerado dinamicamente por camadas de abstração. Um framework de agentes introduz estado implícito, comportamento emergente e dependência de versão que tornam o sistema mais difícil de auditar do que o problema que ele resolve justifica.

O custo dessa escolha é código mais verboso nos componentes de orquestração. O benefício é rastreabilidade total: dado qualquer arquivo do `workspace/`, é possível identificar qual linha de código o gerou.

### **1.2.2 Single-Process Síncrono**

O sistema roda em um único processo Python, com fluxo de execução integralmente síncrono. Não há threads, não há `asyncio`, não há subprocessos concorrentes, não há fila de tarefas.

A razão é a Constituição, Artigo 3: os agentes jamais operam em paralelo. Quando um agente está em execução, os demais aguardam. A implementação mais fiel desse princípio é a sequencialidade estrutural: o código chama Watson, aguarda o retorno, processa o resultado, chama Mycroft, aguarda o retorno, e assim por diante. Qualquer arquitetura assíncrona ou paralela criaria a possibilidade de violação acidental do Artigo 3, exigindo locks, semáforos ou outros mecanismos de coordenação que aumentariam a complexidade sem benefício.

O custo é ausência de paralelismo — cada chamada de modelo bloqueia o processo enquanto aguarda resposta. No contexto do piloto, com operação por usuário único e ciclos com duração prevista de minutos a dezenas de minutos, esse custo é insignificante.

### **1.2.3 Filesystem-First, Sem Banco de Dados**

Toda persistência do sistema é feita em arquivos: Markdown estruturado para conteúdo legível, YAML frontmatter para metadados, CSV para índices. Não há SQLite, PostgreSQL, Redis, ou qualquer outra forma de persistência além do filesystem do sistema operacional anfitrião.

A razão tem três dimensões. Primeira: portabilidade. Arquivos funcionam em qualquer sistema operacional, em qualquer ambiente de hospedagem, com qualquer sincronizador (OneDrive, Git, rsync), sem configuração adicional — conforme `RNF-PORT-05`. Segunda: auditabilidade. O auditor abre o diretório de trabalho de um ciclo e lê os arquivos diretamente, sem ferramenta auxiliar — conforme o critério central de rastreabilidade humana do PRD (Bloco 1.2, segundo critério de sucesso). Terceira: simplicidade operacional. A inicialização em ambiente novo é `mkdir workspace/` e pronto.

O custo é ausência de consultas estruturadas sobre histórico e ausência de índices para busca. No volume previsto para o piloto — dezenas de ciclos no máximo — esse custo é negligenciável.

### **1.2.4 openai SDK com base_url Configurável**

Toda comunicação com modelos de linguagem é feita através do `openai` SDK da OpenAI, com `base_url` e `api_key` configuráveis por variável de ambiente.

A razão é portabilidade entre providers. O OpenRouter e o Azure AI Foundry expõem APIs OpenAI-compatible: mesma estrutura de request (`messages`, `model`, `temperature`, `max_tokens`), mesma estrutura de response (`choices[0].message.content`, `usage`). A migração entre os dois ambientes é uma troca de duas variáveis de ambiente — `DIOGENES_LLM_BASE_URL` e `DIOGENES_LLM_API_KEY` — sem qualquer alteração no código de aplicação, conforme `RNF-PORT-03`.

A alternativa `httpx` puro ofereceria mais controle mas exigiria implementar manualmente o que o SDK trata: retry de conexão, parsing de usage, serialização de mensagens, compatibilidade entre versões da API. O SDK introduz uma dependência, mas é uma dependência de biblioteca madura mantida por empresa com comprometimento de estabilidade de API.

A camada `LLMClient` do sistema encapsula completamente o SDK: nenhum agente, orquestrador ou motor importa ou conhece o `openai` diretamente. Toda a lógica de chamada, registro de trace e tratamento de erro vive em `LLMClient`.

## **1.3 Diagrama Conceitual**

O diagrama abaixo representa, em texto estruturado, os componentes do sistema, sua hierarquia de ativação e os fluxos de dados principais. A leitura é de cima para baixo, seguindo a sequência de execução de um ciclo.

```
╔══════════════════════════════════════════════════════════════════════╗
║                    LESTRADE  (Auditor Humano)                        ║
║  Porta de entrada · Porta de saída · Único ponto de chancela         ║
╚══════════════════════╤═══════════════════╤══════════════════════════╝
                       │ CLI (Typer + Rich) │
         ┌─────────────▼──────────────┐    │
         │       MOTOR DE START        │    │
         │  Valida inputs · Hash SHA   │    │
         │  Gera manifesto · Isola env │    │
         └─────────────┬──────────────┘    │
                       │ manifesto.md       │
         ┌─────────────▼──────────────┐    │
         │        ORQUESTRADOR         │    │
         │  Máquina de estados do      │    │
         │  ciclo · Sequencia agentes  │    │
         │  Gerencia limite 2 rodadas  │    │
         └──┬──────────┬──────────────┘    │
            │          │                   │
     ┌──────▼──┐  ┌────▼──────┐           │
     │ MYCROFT │  │  STRANGER  │           │
     │ Auditor │  │   ROOM     │           │
     │  Chefe  │  │ (filesystem│           │
     │         │◄►│ protocol)  │           │
     └──┬──┬───┘  └───────────┘           │
        │  │                              │
   ┌────▼┐ └──────────────┐              │
   │WATSON│              ┌─▼───────┐     │
   │Integr│              │SHERLOCK │     │
   │idade │              │Metodol. │     │
   └──────┘              └─────────┘     │
        │   LLMClient (openai SDK)        │
        ▼   ┌─────────────────────┐       │
            │  OpenRouter (piloto)│       │
            │  Azure Foundry (prod│       │
            └─────────────────────┘       │
                                          │
         ┌────────────────────────┐       │
         │     MOTOR DE SAÍDA     ├───────┘
         │  Varre marcas · Report │
         │  Habilita chancela     │
         └────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │       FILESYSTEM            │
         │  workspace/cycles/{id}/     │
         │  manifest.md                │
         │  inputs/ · stranger_room/   │
         │  output/ · _runtime/        │
         │  audit_index.csv            │
         └────────────────────────────┘
```

## **1.4 Componentes e Responsabilidades**

O sistema é composto por oito componentes com fronteiras e responsabilidades estritamente delimitadas. Nenhum componente acessa diretamente o domínio de outro — toda comunicação é via interface explícita.

| Componente | Tipo | Responsabilidade central | PRD |
|---|---|---|---|
| CLI | Infraestrutura | Interface humana. Recebe comandos de Lestrade, valida pré-condições, delega a componentes internos, formata saída no console. | RF-CL-01 a RF-CL-13 |
| Motor de Start | Infraestrutura | Abre ciclos. Valida inputs, calcula hashes, gera manifesto, cria ambiente de trabalho isolado, registra abertura no audit_index. | RF-MS-01 a RF-MS-09 |
| Orquestrador | Infraestrutura | Conduz o ciclo. Máquina de estados. Sequencia agentes. Aplica limite de duas rodadas. Detecta alertas críticos. Entrega output ao Motor de Saída. | RF-OR-01 a RF-OR-11 |
| Mycroft | Agente LLM | Decisões internas. Converte contexto em tasks para Watson. Revisa e questiona outputs dos executores. Consolida produto final. | RF-MY-01 a RF-MY-08 |
| Watson | Agente LLM | Integridade técnica. Verifica consistência interna dos documentos. Traduz SQL/Python. Gera insights. Não toca metodologia. | RF-WA-01 a RF-WA-10 |
| Sherlock | Agente LLM | Validação metodológica. Aplica metodologia homologada sobre pacote saneado. Classifica conformidades e desvios com fundamentação. | RF-SH-01 a RF-SH-08 |
| Stranger's Room | Protocolo + Filesystem | Registra imutavelmente o diálogo Mycroft↔executor. Convenção de nomes, frontmatter YAML, corpo Markdown. | RF-SR-01 a RF-SR-06 |
| Motor de Saída | Infraestrutura | Varredura de marcas antes da chancela. Regras heurísticas. Relatório de ocorrências. Registro no audit_index. | RF-MV-01 a RF-MV-06 |
| LLMClient | Abstração | Isola o SDK de todos os demais componentes. Chama modelo, registra trace técnico completo, aplica retry, retorna resposta normalizada. | RNF-PORT-03 |
| Persistência | Convenção | Não é um módulo de código — é o conjunto de convenções sobre como o filesystem é usado: nomes, estrutura, escrita atômica, preservação. | RF-PE-01 a RF-PE-06 |

## **1.5 O Que Vive Fora do Sistema**

Claridade sobre o que não é responsabilidade do sistema protege contra expansão de escopo durante a implementação.

**Os agentes não são o sistema.** Watson, Mycroft e Sherlock são agentes LLM definidos por seus arquivos de configuração (`soul.md`, `skills.md`, `agent.md`) e invocados pelo sistema. O sistema é a infraestrutura que os chama, persiste seus outputs e aplica as regras constitucionais. A distinção importa: quando Watson produz um output incorreto, o problema pode estar no `agent.md` de Watson (configuração do agente), não no Orquestrador (infraestrutura).

**O motor gerador de documentos docx não é parte do piloto.** Conforme `R-13`, a conversão final de Markdown para docx no padrão Design System TCU-CBS v5 é responsabilidade de motor preexistente no projeto maior. O piloto entrega Markdown estruturado. A integração com o motor docx é tarefa pós-piloto.

**Lestrade não é código.** Conforme a Constituição, o Auditor Responsável não possui linha de código dedicada. O sistema expõe pontos de espera que o CLI materializa como comandos interativos. O que acontece nesses pontos — a decisão humana — está fora do sistema.

**A metodologia homologada não é ingerida pelo sistema.** Os dezessete apêndices do Acórdão 2833/2025-Plenário são documentos que o agente Sherlock recebe como contexto em cada chamada. Não são parseados, indexados ou estruturados pelo sistema de infraestrutura. São arquivos no diretório de inputs, copiados pelo Motor de Start para o diretório de trabalho do ciclo, lidos como texto pelo LLMClient ao montar o prompt de Sherlock.

## **1.6 Relação Entre Componentes e Camadas de Validação**

O PRD descreve quatro camadas de validação (Camada 0, 1, 2 e 3) derivadas da estratégia integrada do GT. O sistema as implementa da seguinte forma:

| Camada | Agente executor | Fase da Stranger's Room |
|---|---|---|
| Camada 0 — Integridade, consistência interna, coerência das transformações | Watson | `watson_integridade` |
| Camada 1 — Aderência metodológica | Sherlock | `sherlock_validacao` |
| Camada 2 — Reprodutibilidade da extração (modalidade documental) | Sherlock | `sherlock_validacao` |
| Camada 3 — Consistência do resultado final | Sherlock | `sherlock_validacao` |

As Camadas 1, 2 e 3 são tratadas em uma única fase da Stranger's Room porque Sherlock as aplica sobre o mesmo pacote integrado, em sequência analítica natural, sem que o sistema precise separar artificialmente o que o agente trata de forma unificada.

## **1.7 Portabilidade: Os Três Ambientes-Alvo**

Conforme `RNF-PORT-02`, o sistema deve rodar em três ambientes sem alteração de código. O que muda entre ambientes é exclusivamente configuração.

| Ambiente | `DIOGENES_WORKSPACE` | `DIOGENES_LLM_BASE_URL` | `DIOGENES_LLM_API_KEY` |
|---|---|---|---|
| Local com OneDrive | `~/OneDrive/diogenes/workspace/` | `https://openrouter.ai/api/v1` | Chave OpenRouter pessoal |
| VPS particular | `/opt/diogenes/workspace/` | `https://openrouter.ai/api/v1` | Chave OpenRouter pessoal |
| Azure AI Foundry (produção) | Path montado no container | Endpoint do Foundry | Token Managed Identity |

A variação de ambiente não envolve mudança de código porque:
1. O `LLMClient` lê `base_url` e `api_key` exclusivamente de variáveis de ambiente
2. O Motor de Start constrói todos os paths via `pathlib.Path(os.environ["DIOGENES_WORKSPACE"])`
3. O CLI não tem nenhum valor hardcoded de caminho ou endpoint

A migração para Azure AI Foundry exige, adicionalmente à troca de variáveis de ambiente, a implementação de `AzureFoundryClient` como cliente concreto alternativo ao `OpenRouterClient`. Esse cliente implementa a mesma interface do `LLMClient` abstrato e é selecionado via `agents_spec.yaml`. O Bloco 6 detalha essa interface.

## **1.8 Estratégia de Versionamento e Rastreabilidade do Código**

Conforme `RNF-REPR-04`, o hash do commit Git que produziu cada ciclo é registrado no manifesto de abertura. Isso permite que, dado qualquer manifesto no `workspace/`, seja possível reconstruir exatamente o estado do código que produziu aquele ciclo.

O repositório segue convenções de versionamento semântico (`MAJOR.MINOR.PATCH`) aplicadas apenas a releases formais. Durante o piloto, o desenvolvimento opera em branch `main` com commits atômicos e mensagens descritivas. Não há estratégia de branching durante o piloto — a simplicidade favorece a rastreabilidade.

O arquivo `pyproject.toml` define a versão do pacote. Todo manifesto de abertura gerado pelo Motor de Start inclui:
- Hash do commit HEAD no momento da execução (`git rev-parse HEAD`)
- Versão do pacote (`importlib.metadata.version("diogenes")`)
- Versão do Python runtime (`sys.version`)
- Versão do `openai` SDK (`importlib.metadata.version("openai")`)

Esses quatro dados, juntos, identificam unicamente o ambiente de código que produziu o ciclo e permitem reprodução controlada conforme `RNF-REPR-04` e `RNF-REPR-05`.

---

*Bloco 1 encerrado.*

---

# **Bloco 2 — Estrutura de Repositório**

## **2.1 Princípios que Governam a Organização**

A estrutura do repositório não é decorativa. Cada convenção aqui estabelecida serve a pelo menos um dos quatro princípios fundadores do sistema ou a um requisito explícito do PRD. Os princípios aplicados na organização são três.

**Separação entre código de aplicação, configuração e documentação institucional.** O código que implementa os componentes do sistema vive em `src/diogenes/`. A configuração que define o comportamento em runtime vive em arquivos na raiz (`agents_spec.yaml`, `runtime.yaml`, `.env`). A documentação institucional — os arquivos soul, skills e agent de cada agente, além dos documentos antecedentes — vive em `docs/`. Essa separação permite que o desenvolvedor altere configuração sem tocar código, que o auditor leia a documentação dos agentes sem navegar por módulos Python, e que o motor gerador de documentos consuma os artefatos Markdown dos agentes sem dependência da estrutura interna do pacote.

**Responsabilidade única por módulo.** Cada arquivo `.py` dentro de `src/diogenes/` tem uma responsabilidade delimitada que pode ser enunciada em uma frase. Quando um módulo começa a acumular responsabilidades que não cabem em uma frase, é sinal de que precisa ser dividido. A rastreabilidade de requisitos (`RF-MS-01` → `motor_start.py`) é consequência direta dessa delimitação.

**Nada hardcoded no código.** Nenhum valor de caminho, modelo, temperatura, timeout ou limite de custo aparece em código Python. Tudo que pode variar entre ambientes ou entre fases do piloto é lido de configuração. O código acessa configuração via módulo único (`config.py`); nenhum outro módulo importa `os.environ` diretamente.

## **2.2 Árvore Completa do Repositório**

```
diogenes/                               ← raiz do repositório
│
├── src/
│   └── diogenes/                       ← pacote Python instalável
│       ├── __init__.py                 ← versão do pacote
│       ├── config.py                   ← leitura centralizada de configuração
│       ├── models.py                   ← dataclasses e Pydantic models do domínio
│       │
│       ├── llm/                        ← camada de abstração de provider LLM
│       │   ├── __init__.py
│       │   ├── base.py                 ← LLMClient (Protocol / classe abstrata)
│       │   ├── openrouter.py           ← OpenRouterClient (implementação concreta)
│       │   └── azure_foundry.py        ← AzureFoundryClient (implementação futura)
│       │
│       ├── motors/                     ← componentes de infraestrutura
│       │   ├── __init__.py
│       │   ├── motor_start.py          ← Motor de Start
│       │   └── motor_saida.py          ← Motor de Saída
│       │
│       ├── orchestrator/               ← Orquestrador (máquina de estados do ciclo)
│       │   ├── __init__.py
│       │   ├── orchestrator.py         ← fluxo principal do ciclo
│       │   ├── states.py               ← enum de estados do ciclo
│       │   └── stranger_room.py        ← protocolo de escrita da Stranger's Room
│       │
│       ├── agents/                     ← invocadores dos agentes LLM
│       │   ├── __init__.py
│       │   ├── mycroft.py              ← invocador e prompt builder de Mycroft
│       │   ├── watson.py               ← invocador e prompt builder de Watson
│       │   └── sherlock.py             ← invocador e prompt builder de Sherlock
│       │
│       ├── persistence/                ← operações de filesystem
│       │   ├── __init__.py
│       │   ├── audit_index.py          ← leitura e escrita do audit_index.csv
│       │   ├── manifest.py             ← geração e leitura de manifestos
│       │   └── workspace.py            ← criação e gestão de diretórios de ciclo
│       │
│       └── cli/                        ← interface de linha de comando
│           ├── __init__.py
│           ├── app.py                  ← app Typer raiz e registro de subcomandos
│           ├── commands/
│           │   ├── __init__.py
│           │   ├── start.py            ← diogenes start
│           │   ├── confirm_manifest.py ← diogenes confirm-manifest
│           │   ├── proceed.py          ← diogenes proceed
│           │   ├── pause.py            ← diogenes pause
│           │   ├── resume.py           ← diogenes resume
│           │   ├── verify_output.py    ← diogenes verify-output
│           │   ├── seal.py             ← diogenes seal
│           │   ├── abort.py            ← diogenes abort
│           │   ├── status.py           ← diogenes status
│           │   ├── list_cycles.py      ← diogenes list
│           │   └── show.py             ← diogenes show
│           └── display.py              ← helpers de formatação Rich
│
├── docs/                               ← documentação institucional
│   ├── antecedentes/                   ← documentos do TCU/GT (somente leitura)
│   │   ├── dva_cbs_completo_v03.docx
│   │   ├── GT_CBS_Estrategia_Integrada_Validacao.docx
│   │   └── PRD_piloto_diogenes_local_v01.md
│   │
│   ├── agentes/                        ← arquivos de definição dos agentes LLM
│   │   ├── mycroft/
│   │   │   ├── soul.md                 ← quem Mycroft é
│   │   │   ├── skills.md               ← o que Mycroft sabe fazer
│   │   │   └── agent.md                ← como Mycroft roda (modelo, params, tools)
│   │   ├── watson/
│   │   │   ├── soul.md
│   │   │   ├── skills.md
│   │   │   └── agent.md
│   │   └── sherlock/
│   │       ├── soul.md
│   │       ├── skills.md
│   │       └── agent.md
│   │
│   └── sdd/
│       └── SDD_piloto_diogenes_local_v01.md   ← este documento
│
├── tests/                              ← suíte de testes automatizados
│   ├── __init__.py
│   ├── conftest.py                     ← fixtures compartilhadas (workspace temp, mocks LLM)
│   ├── fixtures/
│   │   ├── MOD_SINT_001/               ← módulo sintético para testes
│   │   │   ├── entrega/                ← documentos simulados da RFB
│   │   │   │   ├── planilha_cbs.xlsx
│   │   │   │   ├── script_extracao.sql
│   │   │   │   ├── notebook_transform.ipynb
│   │   │   │   └── descricao_metodologica.md
│   │   │   ├── gt_artefatos/           ← artefatos gerados pelo GT (inventário, regras)
│   │   │   │   ├── inventario.json
│   │   │   │   ├── regras_negocio.md
│   │   │   │   └── ata_reuniao_entrega.md
│   │   │   └── briefing.md             ← briefing do módulo
│   │   └── llm_responses/              ← respostas predefinidas para mocks
│   │       ├── mycroft_tasks.json
│   │       ├── watson_integridade.json
│   │       ├── mycroft_revisao.json
│   │       └── sherlock_validacao.json
│   ├── unit/
│   │   ├── test_motor_start.py
│   │   ├── test_motor_saida.py
│   │   ├── test_orchestrator.py
│   │   ├── test_stranger_room.py
│   │   ├── test_audit_index.py
│   │   ├── test_manifest.py
│   │   └── test_llm_client.py
│   └── integration/
│       └── test_ciclo_completo.py      ← end-to-end com mocks de LLM
│
├── workspace/                          ← gerado em runtime, não versionado
│   └── .gitkeep
│
├── .env.example                        ← template de variáveis de ambiente
├── .env                                ← segredos locais (no .gitignore)
├── .gitignore
├── agents_spec.yaml                    ← mapeamento agente → modelo → provider
├── runtime.yaml                        ← caminhos, limites, timeouts, retry
├── pyproject.toml                      ← metadados do pacote e dependências
├── ruff.toml                           ← configuração do linter
└── README.md                           ← instalação, operação básica, ponteiros
```

## **2.3 Módulos e Suas Responsabilidades**

### **2.3.1 `src/diogenes/config.py`**

Ponto único de leitura de toda configuração do sistema. Lê variáveis de ambiente (via `python-dotenv`) e os arquivos `agents_spec.yaml` e `runtime.yaml`. Expõe objetos de configuração tipados que todos os demais módulos consomem. Nenhum outro módulo chama `os.environ` diretamente — toda variável de ambiente é acessada exclusivamente aqui.

A centralização tem dois benefícios: facilita testes (mock de `config.py` substitui toda a configuração de ambiente) e garante que erros de configuração — variável ausente, valor inválido — sejam detectados na inicialização do processo, não no meio de uma chamada de modelo.

### **2.3.2 `src/diogenes/models.py`**

Dataclasses e modelos Pydantic que representam os objetos de domínio do sistema. Não contém lógica de negócio — apenas estruturas de dados com validação. Os principais modelos são:

- `CycleManifest` — representa o manifesto de abertura de um ciclo
- `CycleRecord` — representa uma linha do `audit_index.csv`
- `StrangerRoomFile` — representa um arquivo da Stranger's Room com seu frontmatter
- `LLMCall` — representa uma chamada a modelo com todos os parâmetros e a resposta
- `LLMResponse` — representa a resposta normalizada de qualquer provider
- `AgentSpec` — representa a especificação de um agente lida de `agents_spec.yaml`
- `MotorSaidaReport` — representa o relatório de verificação do Motor de Saída

Todos os modelos usam Pydantic v2 com `model_config = ConfigDict(frozen=True)` onde aplicável — objetos que não devem ser mutados após criação são imutáveis por construção.

### **2.3.3 `src/diogenes/llm/`**

A camada de abstração de provider. Detalhada no Bloco 6.

- `base.py` — define o Protocol `LLMClient` com o método `complete(call: LLMCall) -> LLMResponse`
- `openrouter.py` — implementação concreta para o piloto
- `azure_foundry.py` — implementação futura para produção (arquivo criado com `NotImplementedError` desde o início para forçar o design da interface a contemplar os dois casos)

### **2.3.4 `src/diogenes/motors/`**

Os dois motores de infraestrutura que abre e fecham cada ciclo.

`motor_start.py` implementa a classe `MotorStart` com método principal `run(module_id: str, activity: int) -> CycleManifest`. Internamente: valida inputs, calcula hashes SHA-256, gera `cycle_id`, cria estrutura de diretórios, copia arquivos, escreve `manifest.md`, registra abertura no `audit_index.csv`.

`motor_saida.py` implementa a classe `MotorSaida` com método principal `verify(cycle_id: str) -> MotorSaidaReport`. Internamente: lê o documento de output do ciclo, aplica regras heurísticas de varredura, compila relatório de ocorrências.

### **2.3.5 `src/diogenes/orchestrator/`**

O componente que conduz o ciclo do manifesto ao output final.

`states.py` define o enum `CycleState` com todos os estados possíveis do ciclo. A máquina de estados é explícita: toda transição é uma chamada a método que valida a transição e atualiza o `audit_index.csv`.

`stranger_room.py` implementa `StrangerRoom`, responsável exclusivamente pelo protocolo de escrita dos arquivos de revisão: valida o número da rodada, constrói o frontmatter YAML, escreve o arquivo com nome padronizado, calcula e registra o hash do conteúdo. Não tem conhecimento sobre o conteúdo — apenas sobre o protocolo de escrita.

`orchestrator.py` implementa `Orchestrator` com os métodos que o CLI invoca após cada decisão de Lestrade: `confirm_manifest`, `notify_critical_alert`, `proceed_after_alert`, `finalize`. Internamente orquestra a sequência Watson → Mycroft (revisão) → Sherlock → Mycroft (revisão) → consolidação.

### **2.3.6 `src/diogenes/agents/`**

Os invocadores dos agentes LLM. Cada módulo contém uma classe responsável por construir o prompt do agente correspondente e invocar o `LLMClient`. Os agentes não constroem seus próprios prompts — os invocadores constroem os prompts com base nos arquivos `soul.md`, `skills.md` e `agent.md` lidos de `docs/agentes/`.

`mycroft.py` — `MycrooftAgent`: monta prompt de sistema de Mycroft, monta pacote de contexto (manifesto + inputs), chama LLM, parseia resposta estruturada (lista de tasks para Watson, ou crítica, ou consolidação).

`watson.py` — `WatsonAgent`: monta prompt de sistema de Watson (sem injeção da metodologia homologada — `RF-WA-02`), monta pacote de documentos a analisar, chama LLM, parseia resposta estruturada (relatório graduado com campos de severidade).

`sherlock.py` — `SherlockAgent`: monta prompt de sistema de Sherlock, injeta documento da metodologia homologada correspondente ao módulo, monta pacote integrado por Mycroft, chama LLM, parseia resposta estruturada (classificações ponto a ponto).

### **2.3.7 `src/diogenes/persistence/`**

Operações de filesystem que os demais componentes precisam executar.

`audit_index.py` — leitura e escrita do `audit_index.csv`. Escrita via arquivo temporário + renomeação atômica (`RF-PE-04`). Expõe métodos: `insert_cycle`, `update_status`, `get_cycle`, `list_cycles`.

`manifest.py` — geração de manifesto Markdown a partir de `CycleManifest` e leitura de manifesto existente para reconstrução de `CycleManifest`.

`workspace.py` — criação da estrutura de diretórios do ciclo, cópia de arquivos de input para `inputs/`, verificação de existência de diretórios esperados. Usa `pathlib.Path` exclusivamente — sem `os.path` em nenhum ponto (`RNF-PORT-01`).

### **2.3.8 `src/diogenes/cli/`**

A interface de linha de comando implementada com Typer.

`app.py` — cria o app Typer raiz e registra os onze subcomandos como subgrupos.

`commands/` — um arquivo por subcomando. Cada arquivo importa apenas o componente de infraestrutura que o subcomando aciona, valida pré-condições, invoca o componente, e formata a saída com `display.py`.

`display.py` — helpers de formatação com Rich. Define as cores semânticas conforme o Design System TCU-CBS: verde para Atendido, vermelho para Divergência, âmbar para Atenção, cinza para Limitação, branco sobre fundo vermelho para alerta crítico. Não contém lógica de negócio.

## **2.4 O Diretório `docs/agentes/` e a Separação entre Definição e Invocação**

Os arquivos `soul.md`, `skills.md` e `agent.md` de cada agente são documentos de configuração lidos em runtime pelo invocador correspondente. Não são código. Não são importados como módulos Python. São lidos como texto e usados para construir os prompts.

Essa separação tem consequência importante: alterar o comportamento de um agente — seu perfil, seus limites, sua forma de classificar inconsistências — não exige alteração de código Python. Exige alteração de Markdown no arquivo correspondente. O desenvolvedor pode ajustar a conduta de Watson sem abrir `watson.py`. O auditor pode revisar o `soul.md` de Sherlock sem conhecer a estrutura do pacote.

O arquivo `agent.md` de cada agente inclui a declaração do modelo a utilizar, mas esse valor é sobrescrito pelo `agents_spec.yaml` se os dois divergirem. O `agents_spec.yaml` é a fonte de verdade para configuração de runtime — o `agent.md` é a especificação de design. Essa hierarquia permite que o desenvolvedor experimente modelos diferentes via configuração sem tocar os arquivos de especificação do agente.

## **2.5 O que Não Entra no Repositório**

**O diretório `workspace/`** é gerado em runtime e não é versionado. Contém apenas um `.gitkeep` para preservar a entrada no repositório. O `workspace/` real cresce conforme os ciclos são executados e é preservado localmente — conforme `Artigo 16` da Constituição, nenhum arquivo do workspace é deletado.

**O arquivo `.env`** contém segredos (chave OpenRouter, futuramente tokens de Foundry) e está listado em `.gitignore`. Nunca é versionado.

**Os documentos originais entregues pela RFB** não entram no repositório. Vivem no `workspace/input/{MOD_ID}/` e chegam a esse diretório por procedimento operacional externo ao sistema.

**Logs de execução e traces técnicos** são artefatos do `workspace/` e não são versionados.

## **2.6 Convenções de Nomeação**

| Escopo | Convenção | Exemplo |
|---|---|---|
| Módulos Python | `snake_case` | `motor_start.py`, `audit_index.py` |
| Classes Python | `PascalCase` | `MotorStart`, `StrangerRoom`, `CycleManifest` |
| Constantes Python | `UPPER_SNAKE_CASE` | `MAX_REVISION_ROUNDS = 2` |
| Variáveis de ambiente | `DIOGENES_` + `UPPER_SNAKE_CASE` | `DIOGENES_WORKSPACE`, `DIOGENES_LLM_BASE_URL` |
| Cycle IDs | `{MOD_ID}_A{N}_{TIMESTAMP_UTC}` | `MOD_010_A1_20260507T143000Z` |
| Arquivos da Stranger's Room | `{NN}_{descricao}.md` | `01_apresentacao.md`, `99_decisao_final.md` |
| Arquivos de trace técnico | `{TIMESTAMP_UTC}_{agente}_{tipo}.json` | `20260507T143500Z_watson_llm_call.json` |
| Subcomandos CLI | `kebab-case` | `confirm-manifest`, `verify-output` |
| Chaves YAML | `snake_case` | `max_revision_rounds`, `base_url` |

A separação entre `kebab-case` para CLI e `snake_case` para código e YAML é deliberada e segue as convenções estabelecidas de cada domínio — CLIs usam hifens, Python usa underscores, YAML usa underscores.

## **2.7 Rastreabilidade Requisito → Módulo**

A tabela abaixo mapeia os grupos de requisitos funcionais do PRD aos módulos de implementação correspondentes. É a referência primária para o desenvolvedor que busca onde implementar um requisito específico.

| Grupo de requisitos | Módulo(s) principal(is) |
|---|---|
| RF-MS (Motor de Start) | `motors/motor_start.py`, `persistence/manifest.py`, `persistence/workspace.py`, `persistence/audit_index.py` |
| RF-OR (Orquestrador) | `orchestrator/orchestrator.py`, `orchestrator/states.py` |
| RF-MY (Mycroft) | `agents/mycroft.py`, `docs/agentes/mycroft/` |
| RF-WA (Watson) | `agents/watson.py`, `docs/agentes/watson/` |
| RF-SH (Sherlock) | `agents/sherlock.py`, `docs/agentes/sherlock/` |
| RF-SR (Stranger's Room) | `orchestrator/stranger_room.py` |
| RF-MV (Motor de Saída) | `motors/motor_saida.py` |
| RF-PE (Persistência) | `persistence/audit_index.py`, `persistence/workspace.py`, `persistence/manifest.py` |
| RF-CL (CLI) | `cli/app.py`, `cli/commands/`, `cli/display.py` |
| RNF-PORT-03 (Portabilidade de LLM) | `llm/base.py`, `llm/openrouter.py`, `llm/azure_foundry.py` |
| RNF-RAST (Rastreabilidade) | `orchestrator/stranger_room.py`, `persistence/audit_index.py`, `llm/openrouter.py` |

---

*Bloco 2 encerrado.*

---

# **Bloco 3 — Stack e Dependências**

## **3.1 Princípios de Gestão de Dependências**

Toda dependência incluída no projeto é uma decisão com custo. Cada biblioteca acrescentada é um vetor de breaking change, uma superfície de vulnerabilidade, uma curva de aprendizado para quem mantém o código depois. No contexto do Departamento — sistema que operará até 2032, com potencial de troca de mantenedor — o conservadorismo na escolha de dependências é virtude técnica.

Três critérios guiam cada inclusão. Primeiro: **necessidade comprovada** — a dependência resolve um problema real que não seria resolvido de forma mais simples com código próprio em menos de cem linhas. Segundo: **maturidade e estabilidade** — bibliotecas com histórico de versionamento semântico respeitado, maintainers ativos e breaking changes raras. Terceiro: **alinhamento com os princípios fundadores** — dependências que contradizem os princípios do Bloco 1 (como frameworks de agentes com estado implícito) são excluídas independentemente da sua qualidade técnica.

Cada dependência abaixo é justificada individualmente. A ausência de justificativa é sinal de que a dependência não deveria estar no projeto.

## **3.2 Versão de Python**

**Python 3.11** é a versão mínima requerida e a versão-alvo do desenvolvimento do piloto.

A escolha de 3.11 como mínimo (e não 3.12 ou 3.13) é deliberada: maximiza a compatibilidade com ambientes corporativos como o Azure AI Foundry, onde o runtime disponível pode não ser a versão mais recente. Python 3.11 introduziu melhorias significativas de performance e a sintaxe de type hints que o projeto utiliza (`X | Y` em vez de `Union[X, Y]`, `match`/`case` quando aplicável) está disponível a partir dessa versão.

O `pyproject.toml` declara `requires-python = ">=3.11"`. A execução em versões anteriores não é suportada e pode produzir erros de sintaxe silenciosos.

## **3.3 Dependências de Runtime**

As dependências de runtime são aquelas necessárias para executar o sistema em produção — isto é, no piloto. São instaladas pelo usuário final via `pip install -e .` e declaradas em `[project.dependencies]` no `pyproject.toml`.

### **`openai >= 1.30, < 2.0`**

**Função:** cliente HTTP para comunicação com qualquer provider OpenAI-compatible (OpenRouter no piloto, Azure AI Foundry em produção).

**Justificativa:** A faixa `>=1.30` garante presença da API síncrona estável (`client.chat.completions.create`), do modelo Pydantic-based de resposta (`ChatCompletion`), e do campo `usage` estruturado necessário para registro de custo e tokens. O teto `< 2.0` protege contra breaking changes de major version que a OpenAI já sinalizou para a versão 2.x. Conforme decisão do Bloco 1 (item 1.2.4), o SDK é usado com `base_url` e `api_key` configuráveis — toda a portabilidade entre OpenRouter e Foundry repousa nessa capacidade do SDK.

### **`pydantic >= 2.5, < 3.0`**

**Função:** validação de dados e definição de modelos de domínio em `models.py`.

**Justificativa:** Pydantic v2 oferece validação em tempo de instanciação, serialização/deserialização JSON nativa e modelos imutáveis via `frozen=True` — exatamente o que `CycleManifest`, `LLMCall`, `CycleRecord` e demais modelos de domínio precisam. A alternativa seria `dataclasses` da stdlib, mas sem validação automática de tipos em runtime. Em um sistema que manipula dados que fundamentarão cálculo de alíquota tributária, validação automática de campos obrigatórios e tipos corretos reduz a classe de erros silenciosos. O teto `< 3.0` protege contra futura migração major.

### **`typer >= 0.12, < 1.0`**

**Função:** framework de CLI baseado em type hints Python.

**Justificativa:** Typer converte funções Python anotadas com tipos em subcomandos de CLI com validação automática de parâmetros, geração de `--help` e mensagens de erro claras — conforme `RNF-USAB-01` e `RNF-USAB-02`. A alternativa `argparse` da stdlib exigiria código substancialmente mais verboso para o mesmo resultado. A alternativa `click` é a base do Typer e poderia ser usada diretamente, mas Typer elimina boilerplate adicional. O teto `< 1.0` é cautelar dado que a biblioteca ainda não lançou major stable release.

### **`rich >= 13.0, < 14.0`**

**Função:** formatação de saída no console com cores, tabelas e indicadores de progresso.

**Justificativa:** Conforme `RNF-USAB-05` e `RNF-OBSE-01`, a saída da CLI usa o sistema cromático do Design System TCU-CBS. Rich é a biblioteca padrão de fato para formatação de terminal em Python, com suporte a cores, painéis, tabelas, markdown no terminal e progress bars. A alternativa seria formatação manual com códigos ANSI — mais verbosa e menos portável entre terminais. Rich e Typer integram nativamente (Typer usa Rich internamente para help formatado).

### **`python-dotenv >= 1.0, < 2.0`**

**Função:** carregamento do arquivo `.env` para variáveis de ambiente no processo.

**Justificativa:** O `config.py` lê variáveis de ambiente com `os.environ`. Em ambiente de desenvolvimento local, essas variáveis vivem em `.env`. `python-dotenv` carrega o `.env` para o ambiente antes de qualquer leitura — uma linha de código em `config.py` substitui gestão manual de variáveis. Biblioteca mínima, sem dependências transitivas relevantes, API estável há vários anos.

### **`pyyaml >= 6.0, < 7.0`**

**Função:** parsing dos arquivos de configuração `agents_spec.yaml` e `runtime.yaml`.

**Justificativa:** YAML é o formato escolhido para configuração por legibilidade humana — um auditor não-desenvolvedor consegue ler e entender `agents_spec.yaml` sem conhecer JSON ou TOML. `pyyaml` é a implementação de referência de YAML em Python, madura e amplamente utilizada. A alternativa `tomllib` da stdlib (Python 3.11+) seria adequada para TOML mas TOML é menos legível para estruturas aninhadas como as especificações de agentes. A faixa `>=6.0` garante uso do loader seguro (`yaml.safe_load`) que é padrão nessa versão.

### **`python-frontmatter >= 1.1, < 2.0`**

**Função:** parsing e escrita de arquivos Markdown com frontmatter YAML (arquivos da Stranger's Room e manifesto).

**Justificativa:** Todos os arquivos da Stranger's Room têm frontmatter YAML seguido de corpo Markdown — conforme `RF-SR-03`. `python-frontmatter` parseia e serializa exatamente esse formato com API simples: `frontmatter.load(path)` retorna objeto com `.metadata` (dict) e `.content` (str). A alternativa seria parsing manual com split em `---` — trivial para casos simples mas frágil quando o corpo Markdown contém sequências que se parecem com separadores YAML.

### **`openpyxl >= 3.1, < 4.0`**

**Função:** leitura de planilhas Excel (`.xlsx`) entregues pela RFB para análise por Watson.

**Justificativa:** Os módulos da CBS incluem planilhas Excel com cálculos de arrecadação. Watson precisa ler o conteúdo dessas planilhas — valores de células, fórmulas declaradas, nomes de abas — para verificar consistência numérica (`RF-WA-03`). `openpyxl` é a biblioteca padrão para `.xlsx` em Python, sem dependência de instalação de Office. A leitura é feita no invocador `watson.py` que extrai o conteúdo relevante e o inclui no contexto da chamada ao modelo.

### **`sqlparse >= 0.5, < 1.0`**

**Função:** parsing e formatação de scripts SQL para inclusão estruturada no contexto de Watson.

**Justificativa:** Watson recebe scripts SQL entregues pela RFB e precisa incluí-los em forma legível no prompt do modelo (`RF-WA-04`). `sqlparse` formata SQL bruto (por vezes minificado ou sem indentação) em forma estruturada com indentação e quebras de linha, além de fornecer tokenização que permite extrair metadados básicos (tabelas referenciadas, tipo de statement). Não é um parser SQL completo — não valida semântica — mas é suficiente para o objetivo de formatação e extração básica de metadados.

### **`nbformat >= 5.9, < 6.0`**

**Função:** leitura de notebooks Jupyter (`.ipynb`) entregues pela RFB para análise por Watson.

**Justificativa:** Vários módulos da CBS incluem notebooks Python de transformação de dados. Watson precisa ler as células executáveis desses notebooks para traduzir o que cada um executa para linguagem natural (`RF-WA-05`). `nbformat` é a biblioteca oficial do projeto Jupyter para leitura e validação do formato `.ipynb` — um JSON estruturado com células, metadados e outputs. A leitura retorna objeto navegável que o invocador `watson.py` usa para extrair células de código em sequência de execução.

## **3.4 Dependências de Desenvolvimento**

As dependências de desenvolvimento são instaladas apenas no ambiente de quem desenvolve e testa o sistema. São declaradas em `[project.optional-dependencies]` com grupo `dev` no `pyproject.toml` e instaladas via `pip install -e ".[dev]"`.

### **`pytest >= 8.0, < 9.0`**

**Função:** framework de testes automatizados.

**Justificativa:** Framework de referência para Python, com fixtures, parametrização e plugins extensivos. A suíte de testes descrita no Bloco 13 usa fixtures compartilhadas via `conftest.py` — funcionalidade nativa do pytest. Sem alternativa razoável no ecossistema Python atual.

### **`pytest-cov >= 5.0, < 6.0`**

**Função:** medição de cobertura de testes.

**Justificativa:** Conforme `RNF-MANU-04`, a cobertura mínima alvo é setenta por cento dos componentes não-agente. `pytest-cov` integra `coverage.py` ao pytest e gera relatórios de cobertura por arquivo e por linha. Necessário para verificar o critério de cobertura.

### **`ruff >= 0.4, < 1.0`**

**Função:** linter e formatador de código.

**Justificativa:** `ruff` substitui `flake8` + `isort` + `black` em ferramenta única, com performance muito superior (escrito em Rust). Configurado em `ruff.toml` para enforçar PEP 8, ordenação de imports, e subset de regras que detectam erros comuns sem gerar ruído. Conforme `RNF-MANU-01`, o código segue PEP 8.

### **`mypy >= 1.10, < 2.0`**

**Função:** verificação estática de tipos.

**Justificativa:** Conforme `RNF-MANU-01`, type hints completos são obrigatórios em todas as funções públicas. `mypy` em modo estrito verifica que os tipos estão corretos e que nenhuma função pública está sem anotação. Detecta em tempo de desenvolvimento erros que de outra forma só aparecem em execução — especialmente importante em um sistema onde uma chamada com tipo errado pode consumir tokens de API antes de falhar.

### **`responses >= 0.25, < 1.0`** *(ou `pytest-httpx`)*

**Função:** mock de chamadas HTTP nos testes unitários do `LLMClient`.

**Justificativa:** O `OpenRouterClient` faz chamadas HTTP via `openai` SDK (que usa `httpx` internamente). Nos testes unitários de `test_llm_client.py`, não queremos chamadas reais à API — queremos respostas predefinidas. `responses` intercepta as chamadas e retorna os fixtures de `tests/fixtures/llm_responses/`. A alternativa `pytest-httpx` funciona da mesma forma mas é específica para `httpx`; `responses` é mais genérico. A escolha definitiva entre os dois é feita durante a implementação do Bloco 6, quando a estrutura interna do SDK for confirmada.

## **3.5 O `pyproject.toml` Completo**

```toml
[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "diogenes"
version = "0.1.0"
description = "Departamento de Validação Assistida da CBS — Piloto Local"
requires-python = ">=3.11"
readme = "README.md"
license = { text = "Uso Interno Restrito — TCU/SecexContas" }

dependencies = [
    "openai>=1.30,<2.0",        # cliente LLM OpenAI-compatible (OpenRouter + Foundry)
    "pydantic>=2.5,<3.0",       # validação de dados e modelos de domínio
    "typer>=0.12,<1.0",         # CLI baseada em type hints
    "rich>=13.0,<14.0",         # formatação de console com cores semânticas
    "python-dotenv>=1.0,<2.0",  # carregamento de .env para variáveis de ambiente
    "pyyaml>=6.0,<7.0",         # parsing de agents_spec.yaml e runtime.yaml
    "python-frontmatter>=1.1,<2.0",  # parsing de arquivos Markdown com frontmatter YAML
    "openpyxl>=3.1,<4.0",       # leitura de planilhas Excel da RFB
    "sqlparse>=0.5,<1.0",       # parsing e formatação de scripts SQL da RFB
    "nbformat>=5.9,<6.0",       # leitura de notebooks Jupyter da RFB
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-cov>=5.0,<6.0",
    "ruff>=0.4,<1.0",
    "mypy>=1.10,<2.0",
    "responses>=0.25,<1.0",
]

[project.scripts]
diogenes = "diogenes.cli.app:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.mypy]
strict = true
python_version = "3.11"
```

O `[project.scripts]` registra `diogenes` como comando de linha de comando instalável — após `pip install -e .`, o comando `diogenes` fica disponível no PATH do ambiente virtual, invocando `diogenes.cli.app:app` conforme `RF-CL-01`.

## **3.6 Política de Atualização de Dependências**

Durante o piloto, as versões são congeladas no estado instalado no início de cada fase. Isso significa que `pip freeze > requirements-lock.txt` é executado ao início de cada fase (A, B, D do roadmap) e o arquivo resultante é versionado no Git. Qualquer reinstalação em ambiente novo durante a mesma fase usa `pip install -r requirements-lock.txt` para garantir ambiente idêntico ao original — conforme `RNF-REPR-01`.

Atualizações de dependência durante o piloto ocorrem apenas em caso de vulnerabilidade de segurança crítica ou de bug que afete diretamente o funcionamento do sistema. Toda atualização é documentada no CHANGELOG do repositório com razão, versão anterior e versão nova. Atualizações de conveniência (nova feature, performance) ficam para pós-piloto.

## **3.7 O que Deliberadamente Não Está na Stack**

A ausência de certas bibliotecas é decisão tão importante quanto a presença das escolhidas. As ausências mais significativas são registradas aqui para evitar que sejam adicionadas por impulso durante a implementação.

**Sem framework de agentes** (LangChain, LangGraph, Pydantic AI, CrewAI, AutoGen). Justificativa na decisão 1.2.1 do Bloco 1.

**Sem `asyncio` ou bibliotecas async** (aiohttp, httpx em modo async, anyio). O sistema é síncrono por decisão constitucional — Artigo 3. A presença de código async criaria risco de violação acidental do princípio de sequencialidade.

**Sem banco de dados** (SQLite via `sqlite3`, SQLAlchemy, qualquer ORM). Persistência é filesystem-first por decisão 1.2.3 do Bloco 1.

**Sem `pandas`**. O tratamento de dados tabulares no piloto — leitura de planilhas, extração de valores de células — é feito com `openpyxl` diretamente. `pandas` acrescentaria dependência pesada (numpy transitivo) para um uso que não justifica sua presença.

**Sem bibliotecas de vetorização ou embeddings** (sentence-transformers, chromadb, faiss). Busca semântica sobre histórico de ciclos é evolução pós-piloto explicitamente descrita no Bloco 9 do PRD.

**Sem `python-docx` como dependência de runtime**. A geração do documento final em formato `.docx` conforme o Design System TCU-CBS é responsabilidade do motor gerador preexistente no projeto maior, externo ao pacote `diogenes`. Conforme `R-13`, essa integração é pós-piloto. Quando necessária, `python-docx` será adicionada ao grupo `dev` e usada em script auxiliar de integração, não no código principal do sistema.

---

*Bloco 3 encerrado.*

---

# **Bloco 4 — Configuração e Variáveis de Ambiente**

## **4.1 Arquitetura de Configuração**

O sistema tem três fontes de configuração com responsabilidades distintas e hierarquia de precedência definida. A separação não é estética — cada fonte serve a um propósito diferente e é lida por perfis diferentes de pessoa.

**`.env`** contém segredos e valores específicos do ambiente de execução. É o único arquivo que varia entre máquina do desenvolvedor, VPS e Azure. Nunca é versionado. É preenchido pelo operador antes da primeira execução.

**`agents_spec.yaml`** contém a especificação de runtime dos agentes: qual modelo cada agente usa, qual provider, quais parâmetros de invocação. É versionado no repositório — mudanças aqui são decisões de design registradas no histórico Git. Durante o piloto, é o arquivo que o desenvolvedor edita para trocar modelos entre fases do benchmarking.

**`runtime.yaml`** contém parâmetros operacionais do sistema: caminhos de workspace, limites de custo, timeouts, política de retry, limites de tokens por agente. É versionado. Raramente muda durante o piloto — está aqui para que mudanças operacionais não exijam alteração de código.

**Hierarquia de precedência**, do mais alto para o mais baixo: variável de ambiente explícita no shell → `.env` → `agents_spec.yaml` / `runtime.yaml` → valor default no código. Essa hierarquia permite sobrescrever qualquer configuração por variável de ambiente em tempo de execução — útil para testes rápidos e para injeção de configuração em ambientes de CI.

O módulo `config.py` é o único ponto de leitura dessas três fontes. Carrega o `.env` via `python-dotenv`, parseia os YAML via `pyyaml`, valida todos os campos obrigatórios e retorna um objeto de configuração global imutável. Se algum campo obrigatório estiver ausente ou com tipo inválido, `config.py` levanta exceção na inicialização com mensagem clara indicando qual campo está faltando e em qual arquivo.

## **4.2 O Arquivo `.env`**

O `.env` contém exclusivamente segredos e o identificador do ambiente. Nenhum parâmetro operacional vive aqui — parâmetros operacionais vivem no `runtime.yaml`.

```dotenv
# ─────────────────────────────────────────────────────────────
# DIÓGENES — variáveis de ambiente
# Copie este arquivo para .env e preencha os valores.
# NUNCA versione o .env — ele está no .gitignore.
# ─────────────────────────────────────────────────────────────

# Identificador do ambiente (local | vps | azure)
# Usado em logs e manifestos para identificar onde o ciclo rodou.
DIOGENES_ENV=local

# Chave de API do provider de LLM
# No piloto: chave pessoal do OpenRouter (https://openrouter.ai/keys)
# Em produção Azure: token da Managed Identity ou Service Principal
DIOGENES_LLM_API_KEY=sk-or-v1-...

# Base URL do provider de LLM
# OpenRouter (piloto):  https://openrouter.ai/api/v1
# Azure AI Foundry:     https://{resource}.openai.azure.com/openai
DIOGENES_LLM_BASE_URL=https://openrouter.ai/api/v1

# Caminho absoluto para o diretório workspace
# Local com OneDrive:   /Users/{usuario}/OneDrive/diogenes/workspace
# VPS:                  /opt/diogenes/workspace
# Azure (container):    /mnt/diogenes/workspace
DIOGENES_WORKSPACE=/caminho/absoluto/para/workspace

# Header HTTP Site para identificação no OpenRouter (obrigatório pelo ToS)
# Informe a URL do repositório ou identificação institucional do projeto.
DIOGENES_OPENROUTER_SITE_URL=https://github.com/tcu/diogenes
DIOGENES_OPENROUTER_APP_NAME=DVA-CBS Projeto Diogenes
```

**Campos obrigatórios:** `DIOGENES_LLM_API_KEY`, `DIOGENES_LLM_BASE_URL`, `DIOGENES_WORKSPACE`. A ausência de qualquer um deles impede a inicialização com mensagem explícita.

**Campos opcionais com default:** `DIOGENES_ENV` (default: `local`), `DIOGENES_OPENROUTER_SITE_URL` e `DIOGENES_OPENROUTER_APP_NAME` (default: strings vazias — mas o OpenRouter recomenda fortemente o preenchimento para identificação de tráfego e priorização em caso de throttling).

O arquivo `.env.example` no repositório contém este template com valores fictícios em lugar dos reais.

## **4.3 O Arquivo `agents_spec.yaml`**

O `agents_spec.yaml` especifica, para cada agente, o modelo a utilizar, os parâmetros de invocação e os limites de tokens. É a fonte de verdade para a seleção de modelos durante o piloto — o `agent.md` de cada agente pode declarar um modelo preferencial, mas o `agents_spec.yaml` prevalece em caso de divergência.

```yaml
# ─────────────────────────────────────────────────────────────
# DIÓGENES — especificação dos agentes
# Define qual modelo cada agente usa e com quais parâmetros.
# Edite este arquivo para trocar modelos entre fases do piloto.
# ─────────────────────────────────────────────────────────────

# Fase ativa do piloto: A (free), B (barato), D (produção piloto)
# Documentado aqui para rastreabilidade — não afeta o comportamento do código.
fase_ativa: A

agentes:

  mycroft:
    # Auditor Chefe — orquestração, síntese, revisão
    # Exige: alta capacidade de raciocínio sobre contexto longo,
    # produção de JSON estruturado, consistência entre chamadas.
    modelo: google/gemini-2.0-flash-thinking-exp:free   # Fase A
    # modelo: qwen/qwen3-235b-a22b             # Fase B (barato, alta capacidade)
    # modelo: anthropic/claude-sonnet-4-5      # Fase D (produção piloto)
    temperatura: 0.1
    max_tokens: 4096
    max_tokens_ciclo: 32768   # teto agregado por ciclo (todas as chamadas somadas)
    timeout_segundos: 300     # timeout por chamada individual
    max_tentativas_retry: 2
    backoff_segundos: 10

  watson:
    # Auditor de Integridade Técnica — análise documental, tradução SQL/Python
    # Exige: capacidade analítica com documentos técnicos heterogêneos,
    # contexto longo para ingerir planilhas e scripts completos.
    modelo: google/gemini-2.0-flash-exp:free             # Fase A
    # modelo: moonshotai/kimi-k2                          # Fase B
    # modelo: google/gemini-2.5-flash                     # Fase D
    temperatura: 0.0    # máxima determinismo — Watson não especula
    max_tokens: 8192    # Watson produz relatórios longos
    max_tokens_ciclo: 65536
    timeout_segundos: 600
    max_tentativas_retry: 2
    backoff_segundos: 10

  sherlock:
    # Auditor de Validação Metodológica — análise normativa, classificação
    # Exige: raciocínio dedutivo sobre metodologia jurídico-tributária,
    # precisão na classificação ponto a ponto com fundamentação explícita.
    modelo: google/gemini-2.0-flash-thinking-exp:free    # Fase A
    # modelo: deepseek/deepseek-r1                        # Fase B
    # modelo: anthropic/claude-opus-4-5                   # Fase D
    temperatura: 0.1
    max_tokens: 8192
    max_tokens_ciclo: 65536
    timeout_segundos: 600
    max_tentativas_retry: 2
    backoff_segundos: 10

# Configuração de teto de custo global (em USD)
# O Orquestrador interrompe o ciclo ao atingir o teto.
teto_custo_ciclo_usd: 5.00   # Fase A: 0.00 (free); Fase B: 5.00; Fase D: 10.00

# Seed base para reprodutibilidade
# Derivada por: seed_base + hash(cycle_id + fase + numero_chamada) % 10000
seed_base: 42
```

**Campos obrigatórios por agente:** `modelo`, `temperatura`, `max_tokens`, `max_tokens_ciclo`, `timeout_segundos`, `max_tentativas_retry`, `backoff_segundos`. A ausência de qualquer campo para qualquer agente impede a inicialização.

**Campos globais obrigatórios:** `teto_custo_ciclo_usd`, `seed_base`.

**Troca de fase:** para avançar da Fase A para a Fase B, o desenvolvedor comenta as linhas `modelo` da Fase A e descomenta as da Fase B, e atualiza `fase_ativa` e `teto_custo_ciclo_usd`. Um commit Git documenta a transição.

## **4.4 O Arquivo `runtime.yaml`**

O `runtime.yaml` contém parâmetros operacionais que raramente mudam mas que não devem ser hardcoded. Separa decisões operacionais (onde o workspace fica, quanto tempo esperar, quantas rodadas de revisão) das decisões de modelo (que estão no `agents_spec.yaml`).

```yaml
# ─────────────────────────────────────────────────────────────
# DIÓGENES — parâmetros de runtime
# Parâmetros operacionais do sistema. Raramente editado.
# A variável de ambiente DIOGENES_WORKSPACE sobrescreve workspace.path.
# ─────────────────────────────────────────────────────────────

workspace:
  # Caminho do workspace. Sobrescrito por DIOGENES_WORKSPACE se definida.
  path: ./workspace
  # Profundidade máxima de path para compatibilidade com OneDrive (máx. 260 chars no Windows)
  max_path_depth: 8

ciclo:
  # Número máximo de rodadas de revisão por fase (Artigo 8 da Constituição)
  # Valor fixo: 2. Alteração exige revisão constitucional.
  max_rodadas_revisao: 2

  # Prefixo dos arquivos de Stranger's Room para ordenação natural
  # Não alterar sem atualizar toda a lógica de escrita da Stranger's Room
  stranger_room_prefixos:
    apresentacao: "01"
    critica_r1: "02"
    resposta_r1: "03"
    critica_r2: "04"
    resposta_r2: "05"
    decisao_final: "99"

  # Estados válidos do ciclo (enum CycleState)
  # Documentado aqui para referência — o enum Python é a fonte de verdade
  estados:
    - PREPARADO
    - AGUARDANDO_CONFIRMACAO_MANIFESTO
    - EM_EXECUCAO_WATSON
    - AGUARDANDO_REVISAO_MYCROFT_WATSON
    - AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO
    - EM_EXECUCAO_SHERLOCK
    - AGUARDANDO_REVISAO_MYCROFT_SHERLOCK
    - AGUARDANDO_VERIFICACAO_SAIDA
    - AGUARDANDO_CHANCELA_LESTRADE
    - ENCERRADO_CHANCELADO
    - PAUSADO_LESTRADE
    - ABORTADO_FALHA_AGENTE
    - ABORTADO_LESTRADE

motor_saida:
  # Padrões de varredura — nomes dos agentes e variações
  padroes_agentes:
    - "Mycroft Holmes"
    - "Mycroft"
    - "Dr. Watson"
    - "Dr. John Watson"
    - "John Watson"
    - "Watson"
    - "Sherlock Holmes"
    - "Sherlock"
    - "Inspetor Lestrade"
    - "Lestrade"
  # Padrões de cargo em contexto identificador (regex)
  padroes_cargo_identificador:
    - "Auditor Chefe (consolidou|elaborou|revisou|identificou|concluiu)"
    - "Auditor de Integridade Técnica (analisou|verificou|identificou|traduziu)"
    - "Auditor de Validação Metodológica (aplicou|identificou|concluiu|classificou)"
    - "Auditor Responsável (recebeu|confirmou|chancelou|encaminhou)"
  # Estruturas internas que não devem aparecer em documentos externos
  padroes_estruturas_internas:
    - "Stranger's Room"
    - "Sala dos Estrangeiros"
    - "Clube Diógenes"
    - "Projeto Diógenes"
    - "audit_index"
    - "Motor de Start"
    - "Motor de Saída"
    - "stranger_room"
  # Regex para identificadores de ciclo
  regex_cycle_id: "MOD_\\w+_A\\d+_\\d{8}T\\d{6}Z"

persistencia:
  # Nome do arquivo de índice central
  audit_index_filename: audit_index.csv
  # Encoding de todos os arquivos escritos pelo sistema
  encoding: utf-8
  # Formato de timestamp UTC para nomes de arquivo e registros
  timestamp_format: "%Y%m%dT%H%M%SZ"
  # Formato de timestamp ISO 8601 para frontmatter e audit_index
  timestamp_iso_format: "%Y-%m-%dT%H:%M:%SZ"

observabilidade:
  # Nível de log do console durante execução de ciclo
  # Valores: DEBUG | INFO | WARNING | ERROR
  log_level: INFO
  # Exibir progresso de chamadas LLM no console
  mostrar_progresso_llm: true
  # Intervalo de atualização do indicador de progresso (segundos)
  progresso_intervalo_segundos: 60
```

**Campos com semântica constitucional:** `ciclo.max_rodadas_revisao` é declarado como `2` — seu comentário explicita que alteração exige revisão constitucional. O campo existe no YAML (não hardcoded) para rastreabilidade, mas seu valor não deve ser alterado sem deliberação formal.

## **4.5 O Módulo `config.py`**

O módulo `config.py` é o único consumidor das três fontes de configuração. Todos os demais módulos importam de `config.py`, nunca de `os.environ` ou dos arquivos YAML diretamente.

```python
# src/diogenes/config.py — esboço de estrutura (não código final)

from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import os
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from diogenes.models import AgentSpec


class LLMConfig(BaseModel):
    api_key: str
    base_url: str
    env: str = "local"
    openrouter_site_url: str = ""
    openrouter_app_name: str = ""


class WorkspaceConfig(BaseModel):
    path: Path
    max_path_depth: int = 8

    @field_validator("path", mode="before")
    @classmethod
    def resolve_path(cls, v: str | Path) -> Path:
        return Path(v).resolve()


class CicloConfig(BaseModel):
    max_rodadas_revisao: int = 2
    stranger_room_prefixos: dict[str, str]
    estados: list[str]


class MotorSaidaConfig(BaseModel):
    padroes_agentes: list[str]
    padroes_cargo_identificador: list[str]
    padroes_estruturas_internas: list[str]
    regex_cycle_id: str


class PersistenciaConfig(BaseModel):
    audit_index_filename: str = "audit_index.csv"
    encoding: str = "utf-8"
    timestamp_format: str = "%Y%m%dT%H%M%SZ"
    timestamp_iso_format: str = "%Y-%m-%dT%H:%M:%SZ"


class ObservabilidadeConfig(BaseModel):
    log_level: str = "INFO"
    mostrar_progresso_llm: bool = True
    progresso_intervalo_segundos: int = 60


class AgentesConfig(BaseModel):
    mycroft: AgentSpec
    watson: AgentSpec
    sherlock: AgentSpec
    teto_custo_ciclo_usd: float
    seed_base: int
    fase_ativa: str


class DiogenesConfig(BaseModel):
    llm: LLMConfig
    workspace: WorkspaceConfig
    ciclo: CicloConfig
    motor_saida: MotorSaidaConfig
    persistencia: PersistenciaConfig
    observabilidade: ObservabilidadeConfig
    agentes: AgentesConfig


@lru_cache(maxsize=1)
def get_config() -> DiogenesConfig:
    """
    Lê e valida toda a configuração do sistema.
    Chamado uma única vez por processo — resultado cacheado via lru_cache.
    Levanta ConfigError com mensagem clara se qualquer campo obrigatório
    estiver ausente ou inválido.
    """
    load_dotenv()  # carrega .env se existir; não sobrescreve vars já no ambiente

    runtime = _load_yaml("runtime.yaml")
    agents_spec = _load_yaml("agents_spec.yaml")

    # DIOGENES_WORKSPACE sobrescreve runtime.yaml workspace.path
    workspace_path = os.environ.get(
        "DIOGENES_WORKSPACE", runtime["workspace"]["path"]
    )

    return DiogenesConfig(
        llm=LLMConfig(
            api_key=_require_env("DIOGENES_LLM_API_KEY"),
            base_url=_require_env("DIOGENES_LLM_BASE_URL"),
            env=os.environ.get("DIOGENES_ENV", "local"),
            openrouter_site_url=os.environ.get("DIOGENES_OPENROUTER_SITE_URL", ""),
            openrouter_app_name=os.environ.get("DIOGENES_OPENROUTER_APP_NAME", ""),
        ),
        workspace=WorkspaceConfig(
            path=workspace_path,
            max_path_depth=runtime["workspace"].get("max_path_depth", 8),
        ),
        ciclo=CicloConfig(**runtime["ciclo"]),
        motor_saida=MotorSaidaConfig(**runtime["motor_saida"]),
        persistencia=PersistenciaConfig(**runtime["persistencia"]),
        observabilidade=ObservabilidadeConfig(**runtime["observabilidade"]),
        agentes=AgentesConfig(
            mycroft=AgentSpec(**agents_spec["agentes"]["mycroft"]),
            watson=AgentSpec(**agents_spec["agentes"]["watson"]),
            sherlock=AgentSpec(**agents_spec["agentes"]["sherlock"]),
            teto_custo_ciclo_usd=agents_spec["teto_custo_ciclo_usd"],
            seed_base=agents_spec["seed_base"],
            fase_ativa=agents_spec.get("fase_ativa", "A"),
        ),
    )
```

O decorator `@lru_cache(maxsize=1)` garante que a configuração é lida e validada **uma única vez** por processo — evitando múltiplas leituras de disco e garantindo que todos os módulos consumam o mesmo objeto de configuração imutável. Em testes, o cache é limpo com `get_config.cache_clear()` antes de cada teste que precise de configuração diferente.

## **4.6 Validação na Inicialização**

Toda vez que `get_config()` é chamado pela primeira vez no processo — o que ocorre no início de qualquer subcomando da CLI — a validação completa roda. Os erros mais comuns e suas mensagens correspondentes:

| Situação | Mensagem de erro |
|---|---|
| `DIOGENES_LLM_API_KEY` ausente | `ConfigError: variável de ambiente obrigatória DIOGENES_LLM_API_KEY não encontrada. Verifique o arquivo .env.` |
| `DIOGENES_WORKSPACE` inválido | `ConfigError: o caminho de workspace '{path}' não existe ou não é um diretório. Crie o diretório ou corrija DIOGENES_WORKSPACE.` |
| `agents_spec.yaml` não encontrado | `ConfigError: arquivo agents_spec.yaml não encontrado em '{cwd}'. Execute o comando a partir da raiz do repositório.` |
| Campo `modelo` ausente em agente | `ConfigError: campo 'modelo' obrigatório ausente na especificação do agente 'watson' em agents_spec.yaml.` |
| `max_rodadas_revisao` diferente de 2 | `ConfigWarning: max_rodadas_revisao está definido como {n}. O valor constitucional é 2 (Artigo 8). Certifique-se de que essa alteração é intencional.` |

O último item é um aviso, não erro: o sistema não impede a execução com valor diferente, mas alerta. A decisão de bloquear ou apenas alertar é intencional — um cenário de teste pode precisar de `max_rodadas_revisao: 1` para acelerar a execução.

## **4.7 Como Configurar por Ambiente**

As três configurações abaixo descrevem a variação completa por ambiente. Toda variação está no `.env` — os arquivos YAML são os mesmos nos três casos.

**Ambiente local com OneDrive:**
```dotenv
DIOGENES_ENV=local
DIOGENES_LLM_API_KEY=sk-or-v1-{chave_openrouter}
DIOGENES_LLM_BASE_URL=https://openrouter.ai/api/v1
DIOGENES_WORKSPACE=/Users/{usuario}/OneDrive/diogenes/workspace
```

**VPS particular:**
```dotenv
DIOGENES_ENV=vps
DIOGENES_LLM_API_KEY=sk-or-v1-{chave_openrouter}
DIOGENES_LLM_BASE_URL=https://openrouter.ai/api/v1
DIOGENES_WORKSPACE=/opt/diogenes/workspace
```

**Azure AI Foundry (produção — futura):**
```dotenv
DIOGENES_ENV=azure
DIOGENES_LLM_API_KEY={token_managed_identity}
DIOGENES_LLM_BASE_URL=https://{resource}.openai.azure.com/openai
DIOGENES_WORKSPACE=/mnt/diogenes/workspace
```

No terceiro caso, além da troca de variáveis de ambiente, o `agents_spec.yaml` terá os modelos Fase D ativos e o `LLMClient` será instanciado como `AzureFoundryClient`. O código de aplicação — Orquestrador, agentes, motores — não muda em nenhum aspecto.

---

*Bloco 4 encerrado.*

---

# **Bloco 5 — Estrutura de Filesystem (Workspace)**

## **5.1 O Workspace como Arquivo Institucional**

O diretório `workspace/` não é um diretório temporário de execução. É o arquivo institucional do Departamento. Todo ciclo encerrado permanece ali integralmente, para sempre, conforme o Artigo 16 da Constituição. A consequência prática é que o workspace cresce ao longo dos 17 módulos e não tem rotina de limpeza — o desenvolvedor precisa prever espaço em disco suficiente e incluir o diretório no backup do ambiente.

A organização do workspace foi projetada para satisfazer dois requisitos simultâneos que puxam em direções ligeiramente opostas: rastreabilidade auditável por leitura humana direta (o auditor abre o diretório e entende o que vê, sem ferramentas) e compatibilidade com sincronização por OneDrive (nomes de arquivo sem caracteres especiais, profundidade controlada, ausência de lock files persistentes).

## **5.2 Árvore Completa do Workspace**

A árvore abaixo mostra a estrutura do workspace após a execução de um ciclo completo da Atividade 1 sobre o módulo MOD_010, com duas rodadas na Stranger's Room de Watson e uma rodada na de Sherlock. Os nomes de arquivo concretos usam o `cycle_id` de exemplo `MOD_010_A1_20260507T143000Z`.

```
workspace/
│
├── audit_index.csv                         ← índice cronológico de todos os ciclos
│
├── input/
│   └── MOD_010/                            ← entrega da RFB para o MOD_010
│       ├── entrega_rfb/                    ← documentos entregues pela RFB (intocáveis)
│       │   ├── planilha_calculo.xlsx
│       │   ├── script_extracao.sql
│       │   ├── notebook_transformacao.ipynb
│       │   └── descricao_metodologica_mod010.pdf
│       ├── gt_artefatos/                   ← artefatos gerados pelo GT (inventário, regras)
│       │   ├── inventario_mod010.json
│       │   ├── regras_negocio_mod010.md
│       │   └── ata_reuniao_entrega_mod010.md
│       └── briefing_mod010.md              ← briefing do módulo para contextualização
│
└── cycles/
    └── MOD_010_A1_20260507T143000Z/        ← diretório de trabalho do ciclo
        │
        ├── manifest.md                     ← manifesto de abertura do ciclo
        │
        ├── inputs/                         ← cópias dos arquivos de input (Motor de Start)
        │   ├── entrega_rfb/
        │   │   ├── planilha_calculo.xlsx
        │   │   ├── script_extracao.sql
        │   │   ├── notebook_transformacao.ipynb
        │   │   └── descricao_metodologica_mod010.pdf
        │   ├── gt_artefatos/
        │   │   ├── inventario_mod010.json
        │   │   ├── regras_negocio_mod010.md
        │   │   └── ata_reuniao_entrega_mod010.md
        │   └── briefing_mod010.md
        │
        ├── stranger_room/
        │   ├── watson_integridade/         ← fase 1: Watson → Mycroft → Watson → Mycroft
        │   │   ├── 01_apresentacao.md      ← output inicial de Watson
        │   │   ├── 02_critica_mycroft_r1.md
        │   │   ├── 03_resposta_r1.md       ← Watson responde à primeira crítica
        │   │   ├── 04_critica_mycroft_r2.md
        │   │   ├── 05_resposta_r2.md       ← Watson responde à segunda crítica
        │   │   └── 99_decisao_final.md     ← Mycroft bate o martelo (após 2ª rodada)
        │   │
        │   └── sherlock_validacao/         ← fase 2: Sherlock → Mycroft (1 rodada)
        │       ├── 01_apresentacao.md      ← output inicial de Sherlock
        │       ├── 02_critica_mycroft_r1.md
        │       ├── 03_resposta_r1.md
        │       └── 99_decisao_final.md     ← Mycroft acata após primeira rodada
        │
        ├── output/
        │   └── relatorio_preliminar_MOD_010_A1_20260507T143000Z.md
        │
        └── _runtime/                       ← traces técnicos (não institucionais)
            ├── events.jsonl                ← log de eventos do ciclo (append-only)
            └── llm_calls/                  ← uma chamada LLM por arquivo
                ├── 20260507T143012Z_mycroft_tasks.json
                ├── 20260507T143145Z_watson_analise.json
                ├── 20260507T143412Z_mycroft_revisao_watson_r1.json
                ├── 20260507T143518Z_watson_resposta_r1.json
                ├── 20260507T143620Z_mycroft_revisao_watson_r2.json
                ├── 20260507T143725Z_watson_resposta_r2.json
                ├── 20260507T143800Z_mycroft_decisao_watson.json
                ├── 20260507T144015Z_sherlock_validacao.json
                ├── 20260507T144312Z_mycroft_revisao_sherlock_r1.json
                ├── 20260507T144420Z_sherlock_resposta_r1.json
                ├── 20260507T144500Z_mycroft_decisao_sherlock.json
                └── 20260507T144600Z_mycroft_consolidacao_final.json
```

## **5.3 Especificação do `manifest.md`**

O manifesto de abertura é o primeiro arquivo criado em cada ciclo. É o documento que Lestrade lê e confirma antes de qualquer agente ser acionado. Sua estrutura é fixa — qualquer campo ausente ou inválido indica falha no Motor de Start.

```markdown
---
cycle_id: MOD_010_A1_20260507T143000Z
module_id: MOD_010
module_nome: Pessoa Física
activity: 1
activity_nome: Validação de Módulo
status: AGUARDANDO_CONFIRMACAO_MANIFESTO
opened_at_utc: 2026-05-07T14:30:00Z
opened_at_local: 2026-05-07T11:30:00-03:00
ambiente: local
diogenes_version: 0.1.0
git_commit: a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9
python_version: 3.11.9
openai_sdk_version: 1.35.0
is_sigilo_module: false
previous_cycle_id: null
---

# Manifesto de Abertura — MOD_010_A1_20260507T143000Z

## Módulo e Atividade

- **Módulo:** MOD_010 — Pessoa Física
- **Atividade:** 1 — Validação de Módulo
- **Módulo pré-selecionado para Sala de Sigilo:** Não
- **Ciclo anterior (referência):** N/A

## Arquivos de Input Verificados

### Entrega RFB

| Arquivo | Caminho de origem | Hash SHA-256 | Status |
|---|---|---|---|
| planilha_calculo.xlsx | input/MOD_010/entrega_rfb/ | a1b2c3d4...e5f6 | OK |
| script_extracao.sql | input/MOD_010/entrega_rfb/ | f7e8d9c0...b1a2 | OK |
| notebook_transformacao.ipynb | input/MOD_010/entrega_rfb/ | 3c4d5e6f...7a8b | OK |
| descricao_metodologica_mod010.pdf | input/MOD_010/entrega_rfb/ | 9b0c1d2e...3f4a | OK |

### Artefatos GT

| Arquivo | Caminho de origem | Hash SHA-256 | Status |
|---|---|---|---|
| inventario_mod010.json | input/MOD_010/gt_artefatos/ | 5e6f7a8b...9c0d | OK |
| regras_negocio_mod010.md | input/MOD_010/gt_artefatos/ | 1e2f3a4b...5c6d | OK |
| ata_reuniao_entrega_mod010.md | input/MOD_010/gt_artefatos/ | 7a8b9c0d...1e2f | OK |
| briefing_mod010.md | input/MOD_010/ | 3b4c5d6e...7f8a | OK |

## Diretório de Trabalho Isolado

- **Caminho:** workspace/cycles/MOD_010_A1_20260507T143000Z/
- **Cópias criadas em:** workspace/cycles/MOD_010_A1_20260507T143000Z/inputs/
- **Originais preservados em:** workspace/input/MOD_010/ (intocáveis)

## Instruções para Lestrade

Este manifesto descreve o ciclo que será iniciado após sua confirmação.
Verifique a lista de arquivos e seus hashes antes de confirmar.
Após confirmação, o sistema acionará Mycroft para início da execução.

Para confirmar: `diogenes confirm-manifest --cycle MOD_010_A1_20260507T143000Z`
Para abortar:   `diogenes abort --cycle MOD_010_A1_20260507T143000Z --reason "motivo"`
```

**Campos obrigatórios no frontmatter:** `cycle_id`, `module_id`, `module_nome`, `activity`, `activity_nome`, `status`, `opened_at_utc`, `opened_at_local`, `ambiente`, `diogenes_version`, `git_commit`, `python_version`, `openai_sdk_version`, `is_sigilo_module`, `previous_cycle_id`. O campo `previous_cycle_id` é `null` para Atividade 1 e contém o `cycle_id` do ciclo anterior para Atividade 2.

## **5.4 Especificação dos Arquivos da Stranger's Room**

Cada arquivo da Stranger's Room tem frontmatter YAML obrigatório seguido de corpo Markdown estruturado. O frontmatter é parseado pelo sistema para registrar metadados no `audit_index.csv`; o corpo é lido por humanos e por Mycroft nas chamadas de revisão.

**Frontmatter obrigatório para todos os arquivos:**

```yaml
---
cycle_id: MOD_010_A1_20260507T143000Z
phase: watson_integridade          # watson_integridade | sherlock_validacao
file_type: apresentacao            # apresentacao | critica_r1 | resposta_r1 |
                                   # critica_r2 | resposta_r2 | decisao_final
author: watson                     # mycroft | watson | sherlock
role: Auditor de Integridade Técnica
round: null                        # null para apresentacao e decisao_final;
                                   # 1 ou 2 para critica e resposta
timestamp_utc: 2026-05-07T14:31:45Z
content_hash: sha256:8f3a2b1c...   # SHA-256 do corpo do arquivo (após o segundo ---)
has_critical_alert: false          # true apenas em watson/decisao_final se alerta crítico
has_dilemma: false                 # true apenas em sherlock/decisao_final se dilema equilibrado
mycroft_overruled: false           # true em decisao_final se Mycroft fixou posição contrária ao agente
---
```

**Regras de preenchimento dos campos condicionais:**

`has_critical_alert` é `true` exclusivamente no arquivo `99_decisao_final.md` da fase `watson_integridade`, quando Watson identificou pelo menos uma inconsistência de severidade crítica e essa classificação sobreviveu à revisão de Mycroft. O Orquestrador detecta esse campo para disparar a notificação a Lestrade.

`has_dilemma` é `true` exclusivamente no arquivo `99_decisao_final.md` da fase `sherlock_validacao`, quando Sherlock identificou inconsistência com duas interpretações de peso equivalente que Mycroft também não resolveu. O Orquestrador detecta esse campo para registrar o ponto como dilema equilibrado no relatório final.

`mycroft_overruled` é `true` no arquivo `99_decisao_final.md` de qualquer fase, quando Mycroft fixou posição diferente da defendida pelo agente executor na segunda rodada.

**Estrutura do corpo de cada tipo de arquivo:**

`01_apresentacao.md` — output inicial do agente executor. Estrutura definida pelo `skills.md` do agente. Para Watson: seções de verificação numérica, tradução de scripts, cadeia de produção dos dados, insights analíticos, tabela graduada de alertas. Para Sherlock: classificação ponto a ponto com fundamento metodológico, seção de dilemas se houver.

`02_critica_mycroft_r1.md` e `04_critica_mycroft_r2.md` — crítica objetiva de Mycroft. Estrutura: lista numerada de pontos questionados, cada um com localização precisa no output do agente, fundamentação da crítica e pergunta ou instrução de correção específica. Críticas vagas (sem localização e sem pergunta específica) violam `RF-MY-04` e são detectáveis na avaliação humana dos traces.

`03_resposta_r1.md` e `05_resposta_r2.md` — resposta do agente à crítica de Mycroft. Estrutura: para cada ponto levantado, o agente responde acatando com correção, ou sustentando sua posição com justificativa adicional. Respostas que ignoram pontos da crítica são detectáveis na avaliação humana.

`99_decisao_final.md` — decisão de Mycroft que encerra a fase. Estrutura: síntese do que foi discutido, posição final adotada por Mycroft (com referência às rodadas se houve revisão), campos booleanos do frontmatter preenchidos conforme situação, e — quando `mycroft_overruled: true` — parágrafo explícito descrevendo a controvérsia e a fundamentação da fixação.

## **5.5 Especificação do `audit_index.csv`**

O `audit_index.csv` é o registro cronológico de todos os ciclos do Departamento. Uma linha por ciclo. Colunas fixas, encoding UTF-8, separador vírgula, sem aspas desnecessárias.

**Cabeçalho e tipos:**

```
cycle_id,module_id,activity,status,
opened_at_utc,ended_at_utc,
is_sigilo_module,previous_cycle_id,
watson_rodadas,sherlock_rodadas,
mycroft_overruled_watson,mycroft_overruled_sherlock,
watson_critical_alerts_count,sherlock_dilemmas_count,
motor_saida_invocado_at_utc,motor_saida_occurrences,motor_saida_decision,
lestrade_seal_at_utc,output_filename,output_hash,
custo_total_usd,tokens_mycroft,tokens_watson,tokens_sherlock,
ambiente,diogenes_version,git_commit
```

**Descrição de cada coluna:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `cycle_id` | string | Identificador único do ciclo — chave primária |
| `module_id` | string | Ex.: `MOD_010` |
| `activity` | int | 1 ou 2 |
| `status` | string | Estado atual do ciclo conforme enum `CycleState` |
| `opened_at_utc` | ISO 8601 | Timestamp de criação do manifesto |
| `ended_at_utc` | ISO 8601 ou vazio | Preenchido ao encerrar (chancela ou aborto) |
| `is_sigilo_module` | bool | `true` / `false` |
| `previous_cycle_id` | string ou vazio | Preenchido apenas para Atividade 2 |
| `watson_rodadas` | int | Número de rodadas de revisão executadas em `watson_integridade` (0, 1 ou 2) |
| `sherlock_rodadas` | int | Número de rodadas de revisão executadas em `sherlock_validacao` |
| `mycroft_overruled_watson` | bool | Mycroft fixou posição contrária a Watson |
| `mycroft_overruled_sherlock` | bool | Mycroft fixou posição contrária a Sherlock |
| `watson_critical_alerts_count` | int | Quantidade de alertas críticos identificados por Watson |
| `sherlock_dilemmas_count` | int | Quantidade de dilemas equilibrados identificados por Sherlock |
| `motor_saida_invocado_at_utc` | ISO 8601 ou vazio | Timestamp da invocação do Motor de Saída |
| `motor_saida_occurrences` | int ou vazio | Ocorrências detectadas pelo Motor de Saída |
| `motor_saida_decision` | string ou vazio | `LIMPO` / `CORRIGIDO_MANUAL` / `ACEITO_JUSTIFICADO` / `RETORNADO_MYCROFT` |
| `lestrade_seal_at_utc` | ISO 8601 ou vazio | Timestamp da chancela final de Lestrade |
| `output_filename` | string ou vazio | Nome do arquivo de saída em `output/` |
| `output_hash` | string ou vazio | SHA-256 do documento de output na chancela |
| `custo_total_usd` | float | Custo total acumulado das chamadas LLM do ciclo |
| `tokens_mycroft` | int | Total de tokens (input + output) consumidos por Mycroft |
| `tokens_watson` | int | Total de tokens consumidos por Watson |
| `tokens_sherlock` | int | Total de tokens consumidos por Sherlock |
| `ambiente` | string | `local` / `vps` / `azure` |
| `diogenes_version` | string | Versão do pacote que executou o ciclo |
| `git_commit` | string | Hash do commit Git — 40 caracteres |

**Exemplo de linha encerrada:**

```
MOD_010_A1_20260507T143000Z,MOD_010,1,ENCERRADO_CHANCELADO,
2026-05-07T14:30:00Z,2026-05-07T15:12:34Z,
false,,
2,1,
true,false,
1,0,
2026-05-07T15:10:00Z,0,LIMPO,
2026-05-07T15:12:34Z,relatorio_preliminar_MOD_010_A1_20260507T143000Z.md,sha256:4f5a6b7c...,
0.00,4821,12340,8932,
local,0.1.0,a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9
```

**Escrita atômica:** toda atualização do `audit_index.csv` segue o protocolo: lê o conteúdo atual, modifica a linha correspondente (ou acrescenta nova linha), escreve em arquivo temporário `audit_index.csv.tmp` no mesmo diretório, renomeia atomicamente para `audit_index.csv`. Em sistemas Unix, `os.rename()` é atômico quando origem e destino estão no mesmo filesystem. Esse protocolo protege o arquivo de corrupção em caso de interrupção abrupta do processo durante a escrita.

## **5.6 Especificação dos Traces Técnicos (`_runtime/`)**

O subdiretório `_runtime/` contém artefatos de observabilidade e reprodutibilidade. Não são documentos institucionais — não chegam ao GT, não são lidos por Lestrade em fluxo normal. São insumos de depuração, benchmarking e re-execução.

### **`_runtime/events.jsonl`**

Log de eventos do ciclo em formato JSON Lines (uma linha JSON por evento). Append-only durante toda a execução do ciclo. Permite reconstrução granular da sequência de execução.

Cada linha segue o schema:

```json
{
  "timestamp_utc": "2026-05-07T14:30:00Z",
  "cycle_id": "MOD_010_A1_20260507T143000Z",
  "event_type": "CYCLE_OPENED",
  "phase": null,
  "agent": null,
  "details": {
    "manifest_path": "workspace/cycles/MOD_010_A1_20260507T143000Z/manifest.md"
  }
}
```

Tipos de evento registrados: `CYCLE_OPENED`, `MANIFEST_CONFIRMED_LESTRADE`, `PHASE_STARTED`, `PHASE_ENDED`, `LLM_CALL_STARTED`, `LLM_CALL_COMPLETED`, `LLM_CALL_FAILED`, `MYCROFT_CRITIQUE_ISSUED`, `AGENT_RESPONSE_RECEIVED`, `MYCROFT_DECISION_FINAL`, `CRITICAL_ALERT_NOTIFIED`, `LESTRADE_PROCEED_AUTHORIZED`, `CYCLE_PAUSED`, `MOTOR_SAIDA_INVOKED`, `MOTOR_SAIDA_COMPLETED`, `LESTRADE_SEAL_APPLIED`, `CYCLE_CLOSED`, `CYCLE_ABORTED`.

### **`_runtime/llm_calls/{timestamp}_{agente}_{tipo}.json`**

Um arquivo JSON por chamada LLM. Contém o registro completo da invocação para fins de reprodutibilidade (`RNF-REPR-01`).

```json
{
  "call_id": "20260507T143145Z_watson_analise",
  "cycle_id": "MOD_010_A1_20260507T143000Z",
  "phase": "watson_integridade",
  "agent": "watson",
  "call_type": "analise_inicial",
  "timestamp_utc": "2026-05-07T14:31:45Z",
  "provider": "openrouter",
  "model": "google/gemini-2.0-flash-exp:free",
  "temperatura": 0.0,
  "max_tokens": 8192,
  "seed": 1847,
  "system_prompt_hash": "sha256:2a3b4c5d...",
  "user_prompt_hash": "sha256:6e7f8a9b...",
  "system_prompt": "...",
  "user_prompt": "...",
  "response_raw": "...",
  "response_parsed_ok": true,
  "usage": {
    "prompt_tokens": 4821,
    "completion_tokens": 2340,
    "total_tokens": 7161
  },
  "cost_usd": 0.0,
  "latency_ms": 18420,
  "http_status": 200,
  "system_fingerprint": "fp_abc123def456",
  "retry_attempt": 0
}
```

O campo `system_prompt` e `user_prompt` contêm os prompts completos — o que permite reprodução exata da chamada conforme `RNF-REPR-01`. O campo `system_prompt_hash` e `user_prompt_hash` permitem detectar se dois ciclos usaram prompts idênticos sem precisar comparar strings longas.

Os campos `system_fingerprint` (quando retornado pelo provider) e `model` permitem detectar mudanças silenciosas de versão de modelo conforme `RNF-REPR-05`.

## **5.7 Especificação do Output Final**

O documento de output do ciclo é gerado por Mycroft na consolidação final e gravado em `output/`. Seu nome segue o padrão:

- Atividade 1: `relatorio_preliminar_{cycle_id}.md`
- Atividade 2: `relatorio_final_{cycle_id}.md`

O documento não tem frontmatter YAML — é Markdown puro formatado para leitura humana direta e para consumo pelo motor gerador de docx. Sua estrutura interna é definida pelo `skills.md` de Mycroft (Bloco 9 deste SDD trata os agentes em detalhe) e segue as regras do Artigo 14 da Constituição: terceira pessoa, impessoal, sem nome de agentes no corpo, com assinatura ao final identificando o cargo responsável.

O hash SHA-256 do documento, calculado pelo Motor de Saída no momento da verificação, é registrado no `audit_index.csv` na coluna `output_hash`. Esse hash permite verificar, a qualquer momento futuro, que o documento não foi alterado após a chancela de Lestrade.

## **5.8 Política de Preservação e Crescimento**

O workspace cresce aproximadamente assim por ciclo completo (estimativa conservadora para o piloto):

| Componente | Tamanho estimado |
|---|---|
| `inputs/` (cópias dos inputs do módulo) | 5–50 MB por módulo (depende do tamanho das planilhas) |
| `stranger_room/` (6 arquivos por fase × 2 fases) | 100–500 KB |
| `output/` (relatório Markdown) | 50–200 KB |
| `_runtime/events.jsonl` | 10–50 KB |
| `_runtime/llm_calls/` (10–15 arquivos JSON com prompts completos) | 1–5 MB |

O componente de maior variação é `inputs/`, cujo tamanho depende da materialidade do módulo. Os módulos de alta prioridade (MOD_001, MOD_007, MOD_008, MOD_009, MOD_012) tendem a ter volumes maiores de planilhas e scripts.

Para o piloto — que exercita o módulo sintético e o MOD_010 — o workspace total não deve exceder alguns gigabytes, confortavelmente dentro de qualquer OneDrive ou VPS com armazenamento padrão.

Nenhum arquivo é deletado. Nenhuma rotina de compactação é executada. Essa é a política permanente, sem exceções — Artigo 16 da Constituição.

---

*Bloco 5 encerrado.*

---

# **Bloco 6 — Camada LLMClient**

## **6.1 Responsabilidade e Fronteiras**

O `LLMClient` é a única camada do sistema que conhece o `openai` SDK, o nome do provider, os headers HTTP necessários, e o formato bruto da resposta do modelo. Nenhum outro módulo — nem Watson, nem Sherlock, nem Mycroft, nem o Orquestrador — importa ou referencia `openai` diretamente.

As responsabilidades do `LLMClient` são exatamente quatro: construir a chamada ao provider com todos os parâmetros corretos, registrar o trace técnico completo antes de retornar, aplicar a política de retry em caso de falha transiente, e retornar uma resposta normalizada em formato independente de provider. Tudo fora dessas quatro responsabilidades pertence a outro componente.

O que o `LLMClient` não faz: não constrói prompts, não parseia a resposta semântica do modelo, não decide qual modelo chamar, não conhece nada sobre ciclos, módulos, ou a Constituição do Departamento. Essa separação é o que torna a troca de provider cirurgicamente simples.

## **6.2 O Protocol `LLMClient`**

Em Python, `Protocol` (de `typing`) define uma interface por estrutura, não por herança. Qualquer classe que implemente os métodos do Protocol satisfaz a interface sem precisar herdar dela. Isso permite que testes substituam o `LLMClient` real por um mock com a mesma interface, sem qualquer boilerplate.

```python
# src/diogenes/llm/base.py

from __future__ import annotations
from typing import Protocol, runtime_checkable
from diogenes.models import LLMCall, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    """
    Interface de comunicação com provider de modelo de linguagem.
    
    Toda implementação concreta deve satisfazer este Protocol.
    O sistema instancia exclusivamente via factory function get_llm_client(),
    nunca diretamente.
    """

    def complete(self, call: LLMCall) -> LLMResponse:
        """
        Executa uma chamada ao modelo e retorna a resposta normalizada.
        
        Registra trace técnico completo em _runtime/llm_calls/ antes de retornar.
        Aplica política de retry conforme AgentSpec do agente.
        
        Raises:
            LLMCallError: quando o provider retorna erro não transiente
                          ou quando esgotadas as tentativas de retry.
            LLMTimeoutError: quando a chamada excede timeout_segundos.
            LLMCostLimitError: quando o custo acumulado do ciclo excede
                               teto_custo_ciclo_usd.
        """
        ...


def get_llm_client(cycle_id: str, runtime_dir: Path) -> LLMClient:
    """
    Factory function que instancia o cliente correto conforme configuração.
    
    No piloto: sempre OpenRouterClient.
    Em produção Azure: AzureFoundryClient quando DIOGENES_ENV == 'azure'.
    
    O cycle_id e o runtime_dir são passados ao cliente para que ele
    saiba onde persistir os traces técnicos.
    """
    from diogenes.config import get_config
    from diogenes.llm.openrouter import OpenRouterClient

    cfg = get_config()

    if cfg.llm.env == "azure":
        from diogenes.llm.azure_foundry import AzureFoundryClient
        return AzureFoundryClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)

    return OpenRouterClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)
```

O decorator `@runtime_checkable` permite usar `isinstance(obj, LLMClient)` em testes para verificar que um mock satisfaz o Protocol — útil nos fixtures de `conftest.py`.

## **6.3 Os Modelos de Domínio `LLMCall` e `LLMResponse`**

Esses dois modelos são o contrato de dados entre os invocadores de agentes e o `LLMClient`. Vivem em `models.py` e são importados por ambos os lados.

```python
# src/diogenes/models.py — apenas os modelos do LLMClient (extrato)

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel, ConfigDict


class LLMMessage(BaseModel):
    """Uma mensagem na lista de messages da API."""
    model_config = ConfigDict(frozen=True)
    role: str          # "system" | "user" | "assistant"
    content: str


class LLMCall(BaseModel):
    """
    Parâmetros completos de uma chamada ao modelo.
    Construído pelo invocador do agente; consumido pelo LLMClient.
    """
    model_config = ConfigDict(frozen=True)

    # Identificação
    call_id: str           # formato: {timestamp_utc}_{agente}_{tipo}
    cycle_id: str
    phase: str             # watson_integridade | sherlock_validacao | consolidacao
    agent: str             # mycroft | watson | sherlock
    call_type: str         # analise_inicial | critica_r1 | resposta_r1 | ... | consolidacao

    # Parâmetros do modelo — lidos de AgentSpec
    model: str
    temperature: float
    max_tokens: int
    seed: int              # calculado pelo invocador conforme RNF-REPR-02

    # Conteúdo
    messages: list[LLMMessage]

    # Metadados
    timeout_segundos: int
    max_tentativas_retry: int
    backoff_segundos: int


class LLMResponse(BaseModel):
    """
    Resposta normalizada do modelo, independente de provider.
    Retornada pelo LLMClient; consumida pelo invocador do agente.
    """
    model_config = ConfigDict(frozen=True)

    # Conteúdo
    content: str           # texto completo da resposta do modelo

    # Rastreabilidade
    call_id: str           # mesmo call_id do LLMCall correspondente
    model_used: str        # modelo efetivamente usado (pode diferir se provider fizer fallback)
    system_fingerprint: str | None   # identificador de versão do modelo no provider

    # Métricas
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float        # calculado pelo cliente conforme tabela de preços do provider
    latency_ms: int

    # Status
    retry_attempts: int    # número de tentativas antes do sucesso (0 = primeira tentativa)
    http_status: int       # código HTTP da resposta bem-sucedida
```

## **6.4 O `OpenRouterClient`**

A implementação concreta para o piloto. Toda a lógica específica do OpenRouter — headers obrigatórios, cálculo de custo, tratamento de erros da API — vive aqui e apenas aqui.

```python
# src/diogenes/llm/openrouter.py

from __future__ import annotations
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from openai import APIStatusError

from diogenes.config import DiogenesConfig
from diogenes.models import LLMCall, LLMResponse, LLMMessage
from diogenes.llm.exceptions import LLMCallError, LLMTimeoutError, LLMCostLimitError


class OpenRouterClient:
    """
    Implementação do LLMClient para o provider OpenRouter.
    Utiliza o openai SDK com base_url configurável.
    """

    def __init__(
        self,
        cfg: DiogenesConfig,
        cycle_id: str,
        runtime_dir: Path,
    ) -> None:
        self._cfg = cfg
        self._cycle_id = cycle_id
        self._runtime_dir = runtime_dir
        self._llm_calls_dir = runtime_dir / "llm_calls"
        self._llm_calls_dir.mkdir(parents=True, exist_ok=True)

        # Custo acumulado do ciclo — verificado a cada chamada
        self._custo_acumulado_usd: float = 0.0

        # Cliente openai SDK apontando para OpenRouter
        self._client = OpenAI(
            api_key=cfg.llm.api_key,
            base_url=cfg.llm.base_url,
            default_headers={
                # Headers exigidos pelo ToS do OpenRouter
                "HTTP-Referer": cfg.llm.openrouter_site_url,
                "X-Title": cfg.llm.openrouter_app_name,
            },
            timeout=None,  # timeout gerenciado por call, não globalmente
        )

    def complete(self, call: LLMCall) -> LLMResponse:
        """Executa a chamada com retry e persiste o trace técnico."""

        # Verifica teto de custo antes de cada chamada
        if self._custo_acumulado_usd >= self._cfg.agentes.teto_custo_ciclo_usd:
            raise LLMCostLimitError(
                f"Teto de custo do ciclo atingido: "
                f"USD {self._custo_acumulado_usd:.4f} >= "
                f"USD {self._cfg.agentes.teto_custo_ciclo_usd:.2f}. "
                f"Use `diogenes abort` para encerrar ou aumente teto_custo_ciclo_usd."
            )

        last_exception: Exception | None = None
        attempt = 0

        while attempt <= call.max_tentativas_retry:
            t_inicio = time.monotonic()
            try:
                response = self._client.chat.completions.create(
                    model=call.model,
                    messages=[
                        {"role": m.role, "content": m.content}
                        for m in call.messages
                    ],
                    temperature=call.temperature,
                    max_tokens=call.max_tokens,
                    seed=call.seed,
                    timeout=call.timeout_segundos,
                )

                latency_ms = int((time.monotonic() - t_inicio) * 1000)
                content = response.choices[0].message.content or ""
                usage = response.usage

                cost_usd = self._calcular_custo(
                    model=call.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )
                self._custo_acumulado_usd += cost_usd

                llm_response = LLMResponse(
                    content=content,
                    call_id=call.call_id,
                    model_used=response.model,
                    system_fingerprint=getattr(response, "system_fingerprint", None),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    retry_attempts=attempt,
                    http_status=200,
                )

                self._persistir_trace(call=call, response=llm_response, http_status=200)
                return llm_response

            except APITimeoutError as exc:
                last_exception = exc
                self._persistir_trace_falha(call, attempt, "TIMEOUT", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMTimeoutError(
                        f"Timeout após {attempt + 1} tentativa(s) na chamada "
                        f"{call.call_id} (timeout={call.timeout_segundos}s)."
                    ) from exc

            except RateLimitError as exc:
                last_exception = exc
                self._persistir_trace_falha(call, attempt, "RATE_LIMIT", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Rate limit esgotado após {attempt + 1} tentativa(s) "
                        f"na chamada {call.call_id}."
                    ) from exc

            except APIConnectionError as exc:
                last_exception = exc
                self._persistir_trace_falha(call, attempt, "CONNECTION_ERROR", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Erro de conexão persistente na chamada {call.call_id}."
                    ) from exc

            except APIStatusError as exc:
                # Erros 5xx são transientes; 4xx (exceto 429) são permanentes
                self._persistir_trace_falha(
                    call, attempt, f"HTTP_{exc.status_code}", str(exc)
                )
                if exc.status_code < 500:
                    raise LLMCallError(
                        f"Erro permanente HTTP {exc.status_code} na chamada "
                        f"{call.call_id}: {exc.message}"
                    ) from exc
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Erro 5xx persistente após {attempt + 1} tentativa(s) "
                        f"na chamada {call.call_id}."
                    ) from exc

            attempt += 1
            time.sleep(call.backoff_segundos * attempt)  # backoff linear

        # Nunca chegamos aqui (o while sempre levanta ou retorna), mas mypy agradece
        raise LLMCallError(f"Falha inesperada na chamada {call.call_id}.") from last_exception

    def _calcular_custo(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Calcula custo em USD com base na tabela de preços do OpenRouter.
        
        Para modelos :free, retorna 0.0.
        Para modelos pagos, usa tabela local atualizada por fase do piloto.
        
        A tabela completa de preços é declarada em agents_spec.yaml como
        campo opcional `preco_por_milhao_tokens: {input: X, output: Y}`.
        Se ausente, assume 0.0 (adequado para fase A com modelos free).
        """
        if model.endswith(":free"):
            return 0.0

        # Preços lidos de agents_spec.yaml — a implementar no Bloco 9
        # Retorna 0.0 como fallback seguro durante desenvolvimento
        return 0.0

    def _persistir_trace(self, call: LLMCall, response: LLMResponse, http_status: int) -> None:
        """Persiste o trace técnico completo da chamada em _runtime/llm_calls/."""
        trace = {
            "call_id": call.call_id,
            "cycle_id": call.cycle_id,
            "phase": call.phase,
            "agent": call.agent,
            "call_type": call.call_type,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "provider": "openrouter",
            "model": call.model,
            "temperatura": call.temperature,
            "max_tokens": call.max_tokens,
            "seed": call.seed,
            "system_prompt_hash": self._hash_prompt(call.messages[0].content),
            "user_prompt_hash": self._hash_prompt(call.messages[-1].content),
            "system_prompt": call.messages[0].content,
            "user_prompt": call.messages[-1].content,
            "response_raw": response.content,
            "response_parsed_ok": True,
            "usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
            "cost_usd": response.cost_usd,
            "latency_ms": response.latency_ms,
            "http_status": http_status,
            "system_fingerprint": response.system_fingerprint,
            "retry_attempt": response.retry_attempts,
        }
        trace_path = self._llm_calls_dir / f"{call.call_id}.json"
        trace_path.write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _persistir_trace_falha(
        self, call: LLMCall, attempt: int, error_type: str, error_msg: str
    ) -> None:
        """Persiste trace de tentativa que falhou, antes do retry."""
        trace = {
            "call_id": f"{call.call_id}_falha_tentativa_{attempt}",
            "cycle_id": call.cycle_id,
            "agent": call.agent,
            "call_type": call.call_type,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": call.model,
            "error_type": error_type,
            "error_message": error_msg,
            "retry_attempt": attempt,
        }
        trace_path = self._llm_calls_dir / f"{call.call_id}_falha_{attempt}.json"
        trace_path.write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _hash_prompt(text: str) -> str:
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
```

## **6.5 Cálculo de Seed para Reprodutibilidade**

Conforme `RNF-REPR-02`, cada chamada ao modelo usa uma seed derivada de forma determinística a partir do contexto da chamada. A seed permite que duas execuções do mesmo ciclo com o mesmo código produzam chamadas com o mesmo ponto de partida de aleatoriedade — o que não garante saída idêntica, mas reduz substancialmente a variância e permite identificar que as duas execuções partiram das mesmas premissas.

A seed é calculada no invocador do agente (não no `LLMClient`) antes de construir o `LLMCall`:

```python
# Cálculo de seed — implementado em cada invocador de agente

import hashlib
from diogenes.config import get_config

def calcular_seed(cycle_id: str, phase: str, call_type: str, attempt: int = 0) -> int:
    """
    Deriva seed determinística para reprodutibilidade da chamada.
    
    Combina seed_base da configuração com hash do contexto da chamada.
    Resulta em inteiro no intervalo [0, 99999], adequado para o parâmetro
    seed da API OpenAI-compatible.
    """
    cfg = get_config()
    contexto = f"{cycle_id}:{phase}:{call_type}:{attempt}"
    digest = hashlib.sha256(contexto.encode("utf-8")).hexdigest()
    hash_int = int(digest[:8], 16)  # 8 hex chars = 32 bits
    return (cfg.agentes.seed_base + hash_int) % 100000
```

O resultado é sempre um inteiro no intervalo [0, 99999], que é o intervalo aceitável para o parâmetro `seed` da maioria dos providers OpenAI-compatible. A derivação é puramente determinística: dado o mesmo `cycle_id`, `phase`, `call_type` e `seed_base`, a seed é sempre a mesma.

## **6.6 O `AzureFoundryClient` — Esboço Antecipado**

Conforme decisão do Bloco 1 (item 1.5) e `RNF-PORT-03`, o `AzureFoundryClient` é criado como arquivo desde o início, com `NotImplementedError`, para forçar que o design da interface `LLMClient` contemple os dois providers.

```python
# src/diogenes/llm/azure_foundry.py

from __future__ import annotations
from pathlib import Path
from diogenes.config import DiogenesConfig
from diogenes.models import LLMCall, LLMResponse


class AzureFoundryClient:
    """
    Implementação do LLMClient para Azure AI Foundry.
    
    A ser implementada na transição pós-piloto para Azure.
    Utiliza o mesmo openai SDK com base_url apontando para o endpoint
    do Azure AI Foundry e autenticação via Managed Identity ou
    Service Principal conforme configuração de ambiente.
    
    A interface é idêntica ao OpenRouterClient — a troca entre os dois
    clientes é feita exclusivamente pela factory function get_llm_client()
    com base na variável de ambiente DIOGENES_ENV.
    
    Diferenças esperadas em relação ao OpenRouterClient:
    - Headers de autenticação Azure (Bearer token via Managed Identity)
    - Formato de model string ('gpt-4o' em vez de 'openai/gpt-4o')
    - Endpoint de formato distinto (inclui version na URL)
    - Cálculo de custo via Azure Cost Management API (não por tabela local)
    - Suporte a streaming para respostas longas (opcional)
    """

    def __init__(
        self,
        cfg: DiogenesConfig,
        cycle_id: str,
        runtime_dir: Path,
    ) -> None:
        raise NotImplementedError(
            "AzureFoundryClient não está implementado no piloto. "
            "Configure DIOGENES_ENV=local ou DIOGENES_ENV=vps para usar OpenRouterClient."
        )

    def complete(self, call: LLMCall) -> LLMResponse:
        raise NotImplementedError
```

A presença desse arquivo desde o início tem efeito colateral positivo: os testes de type checking (`mypy`) verificam que `AzureFoundryClient` satisfaz o Protocol `LLMClient` mesmo com `NotImplementedError` — garantindo que, quando a implementação real for escrita, o contrato de interface já está correto.

## **6.7 Tratamento de Erros e Exceções**

O módulo `llm/exceptions.py` define a hierarquia de exceções do cliente:

```python
# src/diogenes/llm/exceptions.py


class LLMError(Exception):
    """Classe base para todas as exceções do LLMClient."""


class LLMCallError(LLMError):
    """
    Erro permanente ou persistente na chamada ao modelo.
    Após essa exceção, o ciclo deve ser abortado.
    """


class LLMTimeoutError(LLMCallError):
    """Timeout esgotado após todas as tentativas de retry."""


class LLMCostLimitError(LLMError):
    """
    Teto de custo do ciclo atingido antes do início da chamada.
    O ciclo deve ser pausado — não é erro irrecuperável, é decisão de Lestrade.
    """
```

A separação entre `LLMCostLimitError` e `LLMCallError` é intencional: o teto de custo não é um erro do provider — é uma decisão de governança do Departamento. O Orquestrador trata os dois de forma diferente: `LLMCostLimitError` gera pausa do ciclo e notificação a Lestrade; `LLMCallError` gera aborto do ciclo com status `ABORTADO_FALHA_AGENTE`.

## **6.8 Como os Invocadores de Agentes Usam o `LLMClient`**

O padrão de uso nos invocadores (`mycroft.py`, `watson.py`, `sherlock.py`) é uniforme:

```python
# Padrão de uso — exemplo do watson.py (extrato)

from diogenes.llm.base import get_llm_client
from diogenes.models import LLMCall, LLMMessage

class WatsonAgent:
    def __init__(self, cycle_id: str, runtime_dir: Path, agent_spec: AgentSpec) -> None:
        self._client = get_llm_client(cycle_id=cycle_id, runtime_dir=runtime_dir)
        self._spec = agent_spec
        self._cycle_id = cycle_id

    def analisar(self, pacote: WatsonInputPackage) -> WatsonOutput:
        call_type = "analise_inicial"
        call = LLMCall(
            call_id=f"{_timestamp_utc()}_{self._spec.nome}_{call_type}",
            cycle_id=self._cycle_id,
            phase="watson_integridade",
            agent="watson",
            call_type=call_type,
            model=self._spec.modelo,
            temperature=self._spec.temperatura,
            max_tokens=self._spec.max_tokens,
            seed=calcular_seed(self._cycle_id, "watson_integridade", call_type),
            messages=[
                LLMMessage(role="system", content=self._construir_system_prompt()),
                LLMMessage(role="user",   content=self._construir_user_prompt(pacote)),
            ],
            timeout_segundos=self._spec.timeout_segundos,
            max_tentativas_retry=self._spec.max_tentativas_retry,
            backoff_segundos=self._spec.backoff_segundos,
        )
        response = self._client.complete(call)
        return self._parsear_output(response.content)
```

Três propriedades importantes desse padrão. Primeiro: o `call_id` é construído com timestamp e tipo da chamada, garantindo unicidade e rastreabilidade sem necessidade de gerador de UUID. Segundo: o trace técnico é persistido pelo `LLMClient` automaticamente — o invocador não precisa fazer nada além de chamar `complete()`. Terceiro: o invocador recebe `LLMResponse` com `response.content` como string pura, e é responsável por parsear o output estruturado do modelo — a separação entre "chamar o modelo" e "interpretar o que o modelo disse" é explícita.

## **6.9 Decisão sobre Mock em Testes: `responses` vs `pytest-httpx`**

O `openai` SDK usa `httpx` internamente para as chamadas HTTP. Para mockar as chamadas nos testes unitários, a opção mais direta é `pytest-httpx`, que intercepta chamadas `httpx` e retorna respostas predefinidas. Isso é mais preciso do que `responses` (que intercepta na camada `requests`, mas o SDK não usa `requests`).

**Decisão: usar `pytest-httpx`** para os testes unitários do `LLMClient`.

O arquivo `tests/fixtures/llm_responses/` contém os JSONs de resposta predefinidos que o mock retorna — cada fixture corresponde a uma chamada específica (Watson análise inicial, Mycroft crítica primeira rodada, etc.). O fixture de `conftest.py` instancia o `OpenRouterClient` apontando para o mock e injeta os JSONs de resposta na sequência esperada pelo teste.

A dependência `responses` é removida do `pyproject.toml` e substituída por `pytest-httpx >= 0.30, < 1.0` no grupo `dev`.

---

*Bloco 6 encerrado.*

---

# **Bloco 7 — Motor de Start**

## **7.1 Responsabilidade e Posição no Fluxo**

O Motor de Start é o primeiro componente a executar em qualquer ciclo. Sua responsabilidade é estabelecer, de forma rastreável e auditável, o ambiente de trabalho isolado sobre o qual todos os agentes operarão. Quando o Motor de Start encerra sua execução com sucesso, duas garantias estão em vigor: os arquivos originais nos diretórios de origem nunca foram tocados, e existe um diretório de trabalho isolado com cópias exatas de todos os inputs, um manifesto íntegro e um registro no `audit_index.csv`. A partir desse ponto, tudo o que acontece no ciclo opera sobre cópias — nunca sobre os originais.

O Motor de Start não aciona nenhum agente e não toma nenhuma decisão analítica. Termina sua execução e aguarda Lestrade.

## **7.2 Inputs Esperados por Atividade**

O Motor de Start valida, antes de qualquer operação, que todos os inputs necessários estão presentes nos diretórios de origem corretos. A lista de inputs esperados varia conforme a atividade.

**Atividade 1 — Validação de Módulo:**

```
workspace/input/{MOD_ID}/
    entrega_rfb/            ← documentos entregues pela RFB (pelo menos um arquivo)
    gt_artefatos/
        inventario_{mod_id}.json    ← obrigatório
        regras_negocio_{mod_id}.md  ← obrigatório
        ata_reuniao_entrega_{mod_id}.md  ← obrigatório
    briefing_{mod_id}.md    ← obrigatório
```

**Atividade 2 — Revalidação de Módulo:**

```
workspace/input/{MOD_ID}/
    resposta_rfb/           ← pacote de resposta organizado pelo GT (pelo menos um arquivo)
    [todos os demais itens da Atividade 1 ainda presentes]
```

Adicionalmente, para a Atividade 2, o Motor de Start verifica que existe no `audit_index.csv` um ciclo encerrado de Atividade 1 para o mesmo módulo, e lê o `cycle_id` desse ciclo para referência no manifesto como `previous_cycle_id`.

A verificação de presença é feita arquivo por arquivo. A ausência de qualquer item obrigatório interrompe o Motor com mensagem específica identificando qual arquivo está faltando e em qual caminho era esperado — nunca uma mensagem genérica.

## **7.3 Fluxo de Execução**

O pseudocódigo abaixo descreve a sequência completa de operações do Motor de Start. Cada passo é atômico no sentido de que, se falhar, nenhuma operação subsequente é tentada e o estado do workspace é preservado sem corrupção.

```
MotorStart.run(module_id, activity):

  1. VALIDAR INPUTS
     Para cada input esperado conforme atividade:
       Se arquivo não existe → levantar InputMissingError com caminho esperado
     Para Atividade 2:
       Consultar audit_index.csv → obter previous_cycle_id
       Se não existe ciclo A1 encerrado para o módulo → levantar NoPreviousCycleError

  2. CALCULAR HASHES
     Para cada arquivo de input encontrado:
       Calcular SHA-256 do conteúdo binário do arquivo
       Registrar {caminho, hash, tamanho_bytes, extensão} em lista de inputs

  3. GERAR CYCLE_ID
     timestamp_utc = datetime.now(UTC)
     cycle_id = f"{module_id}_A{activity}_{timestamp_utc.strftime('%Y%m%dT%H%M%SZ')}"
     Verificar no audit_index.csv que cycle_id não existe (colisão improvável mas verificada)

  4. CRIAR DIRETÓRIO DE TRABALHO ISOLADO
     cycle_dir = workspace/cycles/{cycle_id}/
     Criar cycle_dir e subdiretórios:
       cycle_dir/inputs/
       cycle_dir/stranger_room/watson_integridade/
       cycle_dir/stranger_room/sherlock_validacao/
       cycle_dir/output/
       cycle_dir/_runtime/
       cycle_dir/_runtime/llm_calls/

  5. COPIAR INPUTS
     Para cada arquivo de input:
       Determinar caminho destino em cycle_dir/inputs/ preservando estrutura relativa
       Copiar arquivo (shutil.copy2 — preserva metadados)
       Verificar hash do arquivo copiado == hash do original
       Se hashes divergem → levantar CopyIntegrityError (corrupção na cópia)

  6. GERAR MANIFESTO
     Construir CycleManifest com todos os campos especificados no Bloco 5.3
     Serializar para Markdown com frontmatter YAML
     Escrever em cycle_dir/manifest.md
     Calcular hash do manifesto gerado (para registro futuro no audit_index)

  7. REGISTRAR ABERTURA NO AUDIT_INDEX
     Inserir nova linha no audit_index.csv com:
       cycle_id, module_id, activity, status=PREPARADO,
       opened_at_utc=timestamp_utc, is_sigilo_module, previous_cycle_id
       (demais colunas vazias — preenchidas ao longo do ciclo)

  8. EMITIR SAÍDA NO CONSOLE
     Exibir caminho absoluto do manifesto
     Exibir contagem de arquivos copiados e tamanho total
     Exibir comando para confirmar: diogenes confirm-manifest --cycle {cycle_id}
     Exibir comando para abortar:   diogenes abort --cycle {cycle_id} --reason "..."
     Aguardar. O Motor de Start encerrou. O ciclo está em estado PREPARADO.
```

## **7.4 Implementação: Classe `MotorStart`**

```python
# src/diogenes/motors/motor_start.py

from __future__ import annotations
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from diogenes.config import get_config
from diogenes.models import CycleManifest, InputFileRecord
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.manifest import ManifestWriter
from diogenes.persistence.workspace import WorkspaceManager
from diogenes.motors.exceptions import (
    InputMissingError,
    NoPreviousCycleError,
    CopyIntegrityError,
    CycleIdCollisionError,
)


# Mapa de inputs obrigatórios por atividade.
# Caminhos relativos a workspace/input/{module_id}/
_INPUTS_OBRIGATORIOS_A1 = [
    "gt_artefatos/inventario_{mod_id}.json",
    "gt_artefatos/regras_negocio_{mod_id}.md",
    "gt_artefatos/ata_reuniao_entrega_{mod_id}.md",
    "briefing_{mod_id}.md",
]

_DIRS_OBRIGATORIOS_A1 = [
    "entrega_rfb",   # diretório deve existir e ter pelo menos um arquivo
]

_DIRS_OBRIGATORIOS_A2 = [
    "resposta_rfb",  # adicional para Atividade 2
]


class MotorStart:
    """
    Abre um ciclo do Departamento.
    
    Valida inputs, calcula hashes, cria ambiente isolado,
    gera manifesto e registra abertura no audit_index.
    Não aciona nenhum agente — aguarda confirmação de Lestrade.
    """

    def __init__(self) -> None:
        self._cfg = get_config()
        self._workspace = Path(self._cfg.workspace.path)
        self._audit = AuditIndex(self._workspace)
        self._ws_manager = WorkspaceManager(self._workspace)

    def run(self, module_id: str, activity: int) -> CycleManifest:
        """
        Executa o Motor de Start para o módulo e atividade indicados.
        
        Returns:
            CycleManifest com todos os dados do ciclo aberto.
            
        Raises:
            InputMissingError: input obrigatório ausente.
            NoPreviousCycleError: Atividade 2 sem ciclo A1 encerrado.
            CopyIntegrityError: hash diverge após cópia.
            CycleIdCollisionError: cycle_id já existe no audit_index.
        """
        module_dir = self._workspace / "input" / module_id

        # 1. Validar inputs
        input_records = self._validar_e_inventariar(module_id, module_dir, activity)

        # 2. Resolver previous_cycle_id para Atividade 2
        previous_cycle_id: str | None = None
        if activity == 2:
            previous_cycle_id = self._resolver_ciclo_anterior(module_id)

        # 3. Gerar cycle_id
        now_utc = datetime.now(timezone.utc)
        cycle_id = (
            f"{module_id}_A{activity}_"
            f"{now_utc.strftime(self._cfg.persistencia.timestamp_format)}"
        )
        if self._audit.cycle_exists(cycle_id):
            raise CycleIdCollisionError(
                f"cycle_id '{cycle_id}' já existe no audit_index. "
                f"Aguarde um segundo e tente novamente."
            )

        # 4. Criar estrutura de diretórios do ciclo
        cycle_dir = self._ws_manager.criar_estrutura_ciclo(cycle_id)

        # 5. Copiar inputs e verificar integridade
        self._copiar_e_verificar(input_records, module_dir, cycle_dir)

        # 6. Determinar is_sigilo_module
        # Por ora, lista dos cinco módulos selecionados é hardcoded.
        # Em evolução futura, pode vir de agents_spec.yaml ou runtime.yaml.
        is_sigilo = module_id in {
            "MOD_001", "MOD_007", "MOD_008", "MOD_009", "MOD_012"
        }

        # 7. Gerar manifesto
        manifest = CycleManifest(
            cycle_id=cycle_id,
            module_id=module_id,
            module_nome=self._resolver_nome_modulo(module_id),
            activity=activity,
            activity_nome="Validação de Módulo" if activity == 1
                          else "Revalidação de Módulo",
            status="AGUARDANDO_CONFIRMACAO_MANIFESTO",
            opened_at_utc=now_utc,
            ambiente=self._cfg.llm.env,
            diogenes_version=self._get_package_version(),
            git_commit=self._get_git_commit(),
            python_version=sys.version.split()[0],
            openai_sdk_version=self._get_dep_version("openai"),
            is_sigilo_module=is_sigilo,
            previous_cycle_id=previous_cycle_id,
            input_files=input_records,
            cycle_dir=cycle_dir,
            inputs_dir=cycle_dir / "inputs",
        )

        ManifestWriter.escrever(manifest, cycle_dir / "manifest.md")

        # 8. Registrar no audit_index
        self._audit.insert_cycle(manifest)

        return manifest

    def _validar_e_inventariar(
        self, module_id: str, module_dir: Path, activity: int
    ) -> list[InputFileRecord]:
        """
        Verifica presença de todos os inputs e calcula seus hashes SHA-256.
        Retorna lista de InputFileRecord para todos os arquivos encontrados.
        """
        records: list[InputFileRecord] = []

        # Verificar arquivos obrigatórios individuais
        for template in _INPUTS_OBRIGATORIOS_A1:
            rel_path = template.replace("{mod_id}", module_id.lower())
            full_path = module_dir / rel_path
            if not full_path.exists():
                raise InputMissingError(
                    f"Input obrigatório ausente: '{full_path}'.\n"
                    f"Coloque o arquivo no diretório e tente novamente."
                )
            records.append(self._inventariar_arquivo(full_path, module_dir))

        # Verificar diretórios obrigatórios e inventariar seus conteúdos
        dirs_obrigatorios = _DIRS_OBRIGATORIOS_A1[:]
        if activity == 2:
            dirs_obrigatorios += _DIRS_OBRIGATORIOS_A2

        for dir_name in dirs_obrigatorios:
            dir_path = module_dir / dir_name
            if not dir_path.is_dir():
                raise InputMissingError(
                    f"Diretório obrigatório ausente: '{dir_path}'."
                )
            arquivos = list(dir_path.rglob("*"))
            arquivos = [f for f in arquivos if f.is_file()]
            if not arquivos:
                raise InputMissingError(
                    f"Diretório '{dir_path}' existe mas está vazio. "
                    f"Adicione os arquivos da entrega e tente novamente."
                )
            for arq in arquivos:
                records.append(self._inventariar_arquivo(arq, module_dir))

        return records

    def _inventariar_arquivo(
        self, path: Path, base_dir: Path
    ) -> InputFileRecord:
        """Calcula SHA-256 e retorna InputFileRecord para um arquivo."""
        conteudo = path.read_bytes()
        sha256 = hashlib.sha256(conteudo).hexdigest()
        return InputFileRecord(
            caminho_origem=path,
            caminho_relativo=path.relative_to(base_dir),
            hash_sha256=sha256,
            tamanho_bytes=len(conteudo),
            extensao=path.suffix.lower(),
        )

    def _copiar_e_verificar(
        self,
        records: list[InputFileRecord],
        module_dir: Path,
        cycle_dir: Path,
    ) -> None:
        """
        Copia cada input para cycle_dir/inputs/ e verifica hash pós-cópia.
        Garante que os originais em module_dir não são alterados.
        """
        inputs_dir = cycle_dir / "inputs"
        for record in records:
            destino = inputs_dir / record.caminho_relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src=record.caminho_origem, dst=destino)

            # Verificar integridade da cópia
            hash_copia = hashlib.sha256(destino.read_bytes()).hexdigest()
            if hash_copia != record.hash_sha256:
                raise CopyIntegrityError(
                    f"Hash diverge após cópia de '{record.caminho_origem}'.\n"
                    f"  Original:  {record.hash_sha256}\n"
                    f"  Cópia:     {hash_copia}\n"
                    f"Possível problema de filesystem ou sincronizador (OneDrive)."
                )

    def _resolver_ciclo_anterior(self, module_id: str) -> str:
        """
        Para Atividade 2: localiza o cycle_id do ciclo A1 encerrado
        mais recente para o módulo, no audit_index.
        """
        ciclos = self._audit.list_cycles(
            module_id=module_id, activity=1, status="ENCERRADO_CHANCELADO"
        )
        if not ciclos:
            raise NoPreviousCycleError(
                f"Não foi encontrado ciclo de Atividade 1 encerrado para "
                f"'{module_id}' no audit_index. "
                f"Execute a Atividade 1 e chancele o resultado antes da Atividade 2."
            )
        # O mais recente é o último por ordenação cronológica do cycle_id
        return ciclos[-1].cycle_id

    @staticmethod
    def _resolver_nome_modulo(module_id: str) -> str:
        """Retorna o nome descritivo do módulo dado seu identificador."""
        _NOMES = {
            "MOD_001": "Central",
            "MOD_002": "Redução Proporcional",
            "MOD_003": "Alíquota Zero",
            "MOD_004": "Isenção",
            "MOD_005": "Suspensão",
            "MOD_006": "Combustíveis",
            "MOD_007": "Redutor Compras Governamentais",
            "MOD_008": "Simples Nacional",
            "MOD_009": "Operações Financeiras",
            "MOD_010": "Pessoa Física",
            "MOD_011": "Cashback",
            "MOD_012": "Importação Geral",
            "MOD_013": "Créditos Presumidos",
            "MOD_014": "Zona Franca de Manaus",
            "MOD_015": "Atividades Imobiliárias",
            "MOD_016": "Planos de Saúde",
            "MOD_017": "Residual",
            "MOD_SINT_001": "Módulo Sintético — Piloto",
        }
        return _NOMES.get(module_id, module_id)

    @staticmethod
    def _get_package_version() -> str:
        import importlib.metadata
        try:
            return importlib.metadata.version("diogenes")
        except importlib.metadata.PackageNotFoundError:
            return "dev"

    @staticmethod
    def _get_git_commit() -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _get_dep_version(package: str) -> str:
        import importlib.metadata
        try:
            return importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            return "unknown"
```

## **7.5 O `WorkspaceManager`**

A criação estruturada de diretórios é responsabilidade do `WorkspaceManager`, não do `MotorStart`. Essa separação permite testar a criação de estrutura sem instanciar o Motor inteiro.

```python
# src/diogenes/persistence/workspace.py (extrato)

class WorkspaceManager:

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    def criar_estrutura_ciclo(self, cycle_id: str) -> Path:
        """
        Cria o diretório de trabalho do ciclo com toda a estrutura interna.
        Levanta FileExistsError se o diretório já existir (não deve acontecer
        se cycle_id foi verificado contra o audit_index).
        """
        cycle_dir = self._root / "cycles" / cycle_id

        if cycle_dir.exists():
            raise FileExistsError(
                f"Diretório do ciclo já existe: '{cycle_dir}'. "
                f"Isso não deveria acontecer — verifique o audit_index."
            )

        subdirs = [
            "inputs",
            "stranger_room/watson_integridade",
            "stranger_room/sherlock_validacao",
            "output",
            "_runtime",
            "_runtime/llm_calls",
        ]

        for subdir in subdirs:
            (cycle_dir / subdir).mkdir(parents=True, exist_ok=False)

        return cycle_dir

    def get_cycle_dir(self, cycle_id: str) -> Path:
        """Retorna o Path do diretório de um ciclo, verificando existência."""
        cycle_dir = self._root / "cycles" / cycle_id
        if not cycle_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório do ciclo não encontrado: '{cycle_dir}'. "
                f"O ciclo '{cycle_id}' existe no audit_index mas seu "
                f"diretório está ausente — possível deleção acidental."
            )
        return cycle_dir
```

## **7.6 Saída no Console**

A saída do Motor de Start no console segue o padrão Rich do Design System. A função `display.py` correspondente exibe:

```
╔══════════════════════════════════════════════════════╗
║  MOTOR DE START — MOD_010 / Atividade 1              ║
╚══════════════════════════════════════════════════════╝

 ✓  Inputs verificados: 8 arquivos encontrados
 ✓  Hashes SHA-256 calculados
 ✓  Diretório de trabalho criado
 ✓  Cópias verificadas (integridade confirmada)
 ✓  Manifesto gerado
 ✓  Ciclo registrado no audit_index [PREPARADO]

 Cycle ID : MOD_010_A1_20260507T143000Z
 Manifesto: workspace/cycles/MOD_010_A1_20260507T143000Z/manifest.md

 Leia o manifesto e confirme para iniciar a execução:

   diogenes confirm-manifest --cycle MOD_010_A1_20260507T143000Z

 Para abortar sem iniciar:

   diogenes abort --cycle MOD_010_A1_20260507T143000Z --reason "motivo"
```

O campo `Cycle ID` é exibido em cor de destaque (âmbar, conforme Design System) para facilitar cópia e uso nos comandos subsequentes.

## **7.7 Tratamento de Erros**

As exceções do Motor de Start vivem em `motors/exceptions.py`:

```python
# src/diogenes/motors/exceptions.py

class MotorStartError(Exception):
    """Classe base para erros do Motor de Start."""

class InputMissingError(MotorStartError):
    """Input obrigatório ausente no diretório de origem."""

class NoPreviousCycleError(MotorStartError):
    """Atividade 2 sem ciclo A1 encerrado correspondente no audit_index."""

class CopyIntegrityError(MotorStartError):
    """Hash diverge após cópia — possível corrupção de filesystem."""

class CycleIdCollisionError(MotorStartError):
    """cycle_id gerado já existe no audit_index."""
```

O CLI captura essas exceções no comando `diogenes start` e as exibe com formatação Rich no padrão de erro do Design System (vermelho, sem stacktrace visível ao usuário, com sugestão de ação corretiva). O stacktrace completo é sempre escrito em `_runtime/events.jsonl` se o diretório do ciclo já foi criado — caso contrário, apenas no console em modo DEBUG.

## **7.8 Idempotência e Segurança**

O Motor de Start não é idempotente: chamá-lo duas vezes com os mesmos parâmetros gera dois ciclos distintos (timestamps diferentes → `cycle_id`s diferentes). Isso é intencional — cada invocação de `diogenes start` é uma decisão deliberada de Lestrade que abre um novo ciclo formal.

Nenhuma operação do Motor de Start altera arquivos fora do diretório `workspace/cycles/{cycle_id}/` e do `audit_index.csv`. Os arquivos em `workspace/input/{MOD_ID}/` são somente-leitura do ponto de vista do Motor — `shutil.copy2` lê, nunca escreve na origem.

O `audit_index.csv` é atualizado via escrita atômica conforme especificado no Bloco 5.5. Se o processo for interrompido após a criação do diretório mas antes da escrita no `audit_index`, o resultado é um diretório órfão em `workspace/cycles/` sem registro no índice — situação detectável via `diogenes list` (o diretório existe mas não aparece no índice) e resolvível por `diogenes abort` com o `cycle_id` correspondente.

---

*Bloco 7 encerrado.*

---

# **Bloco 8 — Orquestrador**

## **8.1 Responsabilidade e Distinção de Mycroft**

A distinção entre Orquestrador e Mycroft é estrutural e precisa ser compreendida antes de qualquer linha de implementação.

O **Orquestrador** é infraestrutura: uma máquina de estados em Python que sabe em qual fase o ciclo está, o que precisa acontecer a seguir, quem chamar, como persistir os resultados, e quando notificar Lestrade. Não tem modelo de linguagem acoplado. Não toma decisões analíticas. Implementa mecanicamente as regras constitucionais — em especial o Artigo 3 (sequencialidade), o Artigo 8 (limite de duas rodadas) e o Artigo 9 (alertas críticos).

O **Mycroft** é um agente LLM: decide quais tasks encaminhar a Watson, avalia os outputs dos executores, formula críticas objetivas, fixa decisões finais, e consolida o output do ciclo. Não sabe em qual estado o ciclo está. Não conhece o `audit_index`. Recebe um pacote, processa, retorna um resultado estruturado.

O Orquestrador chama Mycroft. Mycroft não conhece o Orquestrador. Essa assimetria é intencional e necessária para que as regras constitucionais sejam garantidas por código, não por confiança no comportamento do modelo.

## **8.2 A Máquina de Estados**

O ciclo tem treze estados possíveis, declarados no enum `CycleState`. Cada estado corresponde a uma fase distinta do fluxo e define quais transições são válidas a partir dele.

```python
# src/diogenes/orchestrator/states.py

from enum import Enum

class CycleState(Enum):
    # Estados de progressão normal
    PREPARADO                              = "PREPARADO"
    AGUARDANDO_CONFIRMACAO_MANIFESTO       = "AGUARDANDO_CONFIRMACAO_MANIFESTO"
    EM_EXECUCAO_WATSON                     = "EM_EXECUCAO_WATSON"
    AGUARDANDO_REVISAO_MYCROFT_WATSON      = "AGUARDANDO_REVISAO_MYCROFT_WATSON"
    AGUARDANDO_DECISAO_LESTRADE_ALERTA     = "AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO"
    EM_EXECUCAO_SHERLOCK                   = "EM_EXECUCAO_SHERLOCK"
    AGUARDANDO_REVISAO_MYCROFT_SHERLOCK    = "AGUARDANDO_REVISAO_MYCROFT_SHERLOCK"
    AGUARDANDO_VERIFICACAO_SAIDA           = "AGUARDANDO_VERIFICACAO_SAIDA"
    AGUARDANDO_CHANCELA_LESTRADE           = "AGUARDANDO_CHANCELA_LESTRADE"
    ENCERRADO_CHANCELADO                   = "ENCERRADO_CHANCELADO"
    # Estados de interrupção
    PAUSADO_LESTRADE                       = "PAUSADO_LESTRADE"
    ABORTADO_FALHA_AGENTE                  = "ABORTADO_FALHA_AGENTE"
    ABORTADO_LESTRADE                      = "ABORTADO_LESTRADE"


# Transições válidas: estado_atual → {estados_destino_permitidos}
TRANSICOES_VALIDAS: dict[CycleState, set[CycleState]] = {
    CycleState.PREPARADO: {
        CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO: {
        CycleState.EM_EXECUCAO_WATSON,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_WATSON: {
        CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON,
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON: {
        CycleState.EM_EXECUCAO_WATSON,          # Mycroft questiona → Watson responde
        CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA,
        CycleState.EM_EXECUCAO_SHERLOCK,        # sem alerta crítico → segue
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA: {
        CycleState.EM_EXECUCAO_SHERLOCK,        # Lestrade autoriza prosseguimento
        CycleState.PAUSADO_LESTRADE,            # Lestrade pausa
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_SHERLOCK: {
        CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK,
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK: {
        CycleState.EM_EXECUCAO_SHERLOCK,        # Mycroft questiona → Sherlock responde
        CycleState.AGUARDANDO_VERIFICACAO_SAIDA,
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_VERIFICACAO_SAIDA: {
        CycleState.AGUARDANDO_CHANCELA_LESTRADE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_CHANCELA_LESTRADE: {
        CycleState.ENCERRADO_CHANCELADO,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.PAUSADO_LESTRADE: {
        CycleState.EM_EXECUCAO_SHERLOCK,        # Lestrade retoma
        CycleState.ABORTADO_LESTRADE,
    },
    # Estados terminais — sem transições de saída
    CycleState.ENCERRADO_CHANCELADO: set(),
    CycleState.ABORTADO_FALHA_AGENTE: set(),
    CycleState.ABORTADO_LESTRADE: set(),
}
```

Toda transição de estado é validada contra `TRANSICOES_VALIDAS` antes de ser executada. Tentativa de transição inválida levanta `InvalidStateTransitionError` — proteção contra bugs de orquestração que poderiam colocar o sistema em estado inconsistente.

## **8.3 Diagrama de Transição de Estados**

```
                    [diogenes start]
                          │
                    PREPARADO ──────────────────────────────► ABORTADO_LESTRADE
                          │ [diogenes confirm-manifest]
                          ▼
          AGUARDANDO_CONFIRMACAO_MANIFESTO ──────────────────► ABORTADO_LESTRADE
                          │ [Orquestrador aciona Watson]
                          ▼
                EM_EXECUCAO_WATSON ──────────────────────────► ABORTADO_FALHA_AGENTE
                          │ [Watson retorna output]               ABORTADO_LESTRADE
                          ▼
          AGUARDANDO_REVISAO_MYCROFT_WATSON
                  │               │
         [Mycroft questiona] [Mycroft aprova / bate martelo]
                  │               │
                  ▼               ▼
         EM_EXECUCAO_WATSON   [alerta crítico?]
         (rodada de resposta)     │         │
                              [Sim]       [Não]
                                │           │
                                ▼           ▼
              AGUARDANDO_DECISAO      EM_EXECUCAO_SHERLOCK ──► ABORTADO_FALHA_AGENTE
              _LESTRADE_ALERTA              │                   ABORTADO_LESTRADE
                   │      │         [Sherlock retorna output]
          [pausa] [segue]           │
              │      │              ▼
              ▼      ▼    AGUARDANDO_REVISAO_MYCROFT_SHERLOCK
         PAUSADO   EM_EXECUCAO      │               │
         _LESTRADE _SHERLOCK [Mycroft questiona] [aprova]
              │                     │               │
         [retoma]           EM_EXECUCAO_SHERLOCK    │
              │             (rodada de resposta)    │
              └──────────────────────────────────   ▼
                                          AGUARDANDO_VERIFICACAO_SAIDA
                                                    │ [diogenes verify-output]
                                                    ▼
                                          AGUARDANDO_CHANCELA_LESTRADE
                                                    │ [diogenes seal]
                                                    ▼
                                          ENCERRADO_CHANCELADO
```

## **8.4 A Classe `Orchestrator`**

O Orquestrador é instanciado pelo CLI após a confirmação do manifesto por Lestrade e conduz o ciclo até o estado `AGUARDANDO_VERIFICACAO_SAIDA`. A partir daí, o Motor de Saída e o CLI tomam controle.

```python
# src/diogenes/orchestrator/orchestrator.py

from __future__ import annotations
from pathlib import Path

from diogenes.config import get_config
from diogenes.models import CycleManifest
from diogenes.orchestrator.states import CycleState, TRANSICOES_VALIDAS
from diogenes.orchestrator.stranger_room import StrangerRoom
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.workspace import WorkspaceManager
from diogenes.agents.mycroft import MycrooftAgent
from diogenes.agents.watson import WatsonAgent
from diogenes.agents.sherlock import SherlockAgent
from diogenes.llm.base import get_llm_client
from diogenes.llm.exceptions import LLMCallError, LLMTimeoutError, LLMCostLimitError
from diogenes.orchestrator.exceptions import InvalidStateTransitionError


class Orchestrator:
    """
    Conduz o ciclo do Departamento do manifesto confirmado ao output pronto.
    
    Garante por construção:
    - Sequencialidade absoluta entre agentes (Artigo 3 da Constituição)
    - Limite de duas rodadas de revisão por fase (Artigo 8)
    - Notificação de Lestrade sobre alertas críticos (Artigo 9)
    - Rastreabilidade de toda transição de estado no audit_index
    """

    MAX_RODADAS = 2  # Artigo 8 da Constituição — não alterar sem revisão formal

    def __init__(self, cycle_id: str) -> None:
        self._cfg = get_config()
        self._cycle_id = cycle_id
        workspace = Path(self._cfg.workspace.path)
        self._audit = AuditIndex(workspace)
        self._ws_manager = WorkspaceManager(workspace)
        self._cycle_dir = self._ws_manager.get_cycle_dir(cycle_id)
        self._runtime_dir = self._cycle_dir / "_runtime"
        self._stranger_room = StrangerRoom(
            cycle_id=cycle_id,
            stranger_room_dir=self._cycle_dir / "stranger_room",
            cfg=self._cfg,
        )

        # Instancia o LLMClient compartilhado entre os três agentes
        self._llm = get_llm_client(
            cycle_id=cycle_id, runtime_dir=self._runtime_dir
        )

        # Instancia os três agentes com o mesmo LLMClient
        self._mycroft = MycrooftAgent(
            llm=self._llm,
            agent_spec=self._cfg.agentes.mycroft,
            cycle_id=cycle_id,
            docs_dir=Path("docs/agentes/mycroft"),
        )
        self._watson = WatsonAgent(
            llm=self._llm,
            agent_spec=self._cfg.agentes.watson,
            cycle_id=cycle_id,
            docs_dir=Path("docs/agentes/watson"),
        )
        self._sherlock = SherlockAgent(
            llm=self._llm,
            agent_spec=self._cfg.agentes.sherlock,
            cycle_id=cycle_id,
            docs_dir=Path("docs/agentes/sherlock"),
        )

    # ──────────────────────────────────────────────────────────
    # PONTO DE ENTRADA — chamado pelo CLI após confirm-manifest
    # ──────────────────────────────────────────────────────────

    def executar(self, manifest: CycleManifest) -> str:
        """
        Executa o ciclo completo de forma síncrona e sequencial.
        
        Retorna o caminho do arquivo de output gerado.
        Levanta exceção em caso de falha irrecuperável.
        
        Pontos de pausa (estados em que o Orquestrador aguarda
        intervenção humana via CLI antes de continuar):
          - AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO
          - (retomada de PAUSADO_LESTRADE via diogenes resume)
        """
        self._transicionar(CycleState.EM_EXECUCAO_WATSON)

        # ── FASE 1: Watson → Mycroft (até 2 rodadas) ──────────
        decisao_watson = self._executar_fase_watson(manifest)

        # ── Verificação de alerta crítico ─────────────────────
        if decisao_watson.has_critical_alert:
            self._transicionar(CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA)
            # O Orquestrador para aqui. O CLI notifica Lestrade e aguarda
            # `diogenes proceed` ou `diogenes pause`.
            # A retomada acontece via Orchestrator.retomar_apos_alerta()
            return ""  # sinaliza pausa ao CLI

        # ── FASE 2: Sherlock → Mycroft (até 2 rodadas) ────────
        return self._executar_fase_sherlock_e_consolidar(manifest)

    def retomar_apos_alerta(self, manifest: CycleManifest) -> str:
        """
        Chamado pelo CLI quando Lestrade autoriza prosseguimento após alerta crítico.
        O ciclo estava em AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO.
        """
        self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
        return self._executar_fase_sherlock_e_consolidar(manifest)

    # ──────────────────────────────────────────────────────────
    # FASE WATSON
    # ──────────────────────────────────────────────────────────

    def _executar_fase_watson(self, manifest: CycleManifest) -> DecisaoFinal:
        """
        Executa o loop Watson → Mycroft até decisão final.
        Respeita o limite de MAX_RODADAS (Artigo 8).
        Retorna a DecisaoFinal de Mycroft sobre Watson.
        """
        fase = "watson_integridade"
        inputs_dir = self._cycle_dir / "inputs"

        # Watson: análise inicial
        self._transicionar(CycleState.EM_EXECUCAO_WATSON)
        output_watson = self._watson.analisar(
            inputs_dir=inputs_dir,
            manifest=manifest,
        )
        self._stranger_room.escrever_apresentacao(fase=fase, author="watson",
                                                   content=output_watson.texto)

        # Loop de revisão Mycroft ↔ Watson
        rodada = 0
        while rodada < self.MAX_RODADAS:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON)

            avaliacao = self._mycroft.avaliar_watson(
                apresentacao=output_watson,
                fase=fase,
                rodada=rodada,
            )

            if avaliacao.tipo == "APROVADO":
                # Mycroft aprova sem crítica — escreve decisão final diretamente
                break

            if avaliacao.tipo == "QUESTIONAR":
                # Mycroft questiona — Watson responde
                rodada += 1
                self._stranger_room.escrever_critica(
                    fase=fase, rodada=rodada, author="mycroft",
                    content=avaliacao.critica
                )
                self._transicionar(CycleState.EM_EXECUCAO_WATSON)
                output_watson = self._watson.responder_critica(
                    critica=avaliacao.critica,
                    output_anterior=output_watson,
                    rodada=rodada,
                )
                self._stranger_room.escrever_resposta(
                    fase=fase, rodada=rodada, author="watson",
                    content=output_watson.texto
                )
                # Se chegamos no limite, sai do loop — Mycroft bate martelo abaixo
                if rodada == self.MAX_RODADAS:
                    break

        # Mycroft fixa decisão final (acata ou overrule)
        self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON)
        decisao = self._mycroft.fixar_decisao_watson(
            output_final_watson=output_watson,
            rodadas_executadas=rodada,
        )
        self._stranger_room.escrever_decisao_final(
            fase=fase, author="mycroft", decisao=decisao
        )

        # Atualizar audit_index com metadados da fase Watson
        self._audit.update_watson_metadata(
            cycle_id=self._cycle_id,
            rodadas=rodada,
            overruled=decisao.mycroft_overruled,
            critical_alerts=decisao.critical_alerts_count,
        )

        return decisao

    # ──────────────────────────────────────────────────────────
    # FASE SHERLOCK
    # ──────────────────────────────────────────────────────────

    def _executar_fase_sherlock_e_consolidar(
        self, manifest: CycleManifest
    ) -> str:
        """
        Executa o loop Sherlock → Mycroft, consolida o output final
        e retorna o caminho do arquivo de output.
        """
        fase = "sherlock_validacao"

        # Mycroft monta o pacote integrado para Sherlock
        decisao_watson_path = (
            self._cycle_dir / "stranger_room" / "watson_integridade" / "99_decisao_final.md"
        )
        pacote_sherlock = self._mycroft.montar_pacote_sherlock(
            manifest=manifest,
            inputs_dir=self._cycle_dir / "inputs",
            decisao_watson_path=decisao_watson_path,
        )

        # Sherlock: validação inicial
        self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
        output_sherlock = self._sherlock.validar(pacote=pacote_sherlock)
        self._stranger_room.escrever_apresentacao(
            fase=fase, author="sherlock", content=output_sherlock.texto
        )

        # Loop de revisão Mycroft ↔ Sherlock (mesma lógica da fase Watson)
        rodada = 0
        while rodada < self.MAX_RODADAS:
            self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)

            avaliacao = self._mycroft.avaliar_sherlock(
                apresentacao=output_sherlock,
                fase=fase,
                rodada=rodada,
            )

            if avaliacao.tipo == "APROVADO":
                break

            if avaliacao.tipo == "QUESTIONAR":
                rodada += 1
                self._stranger_room.escrever_critica(
                    fase=fase, rodada=rodada, author="mycroft",
                    content=avaliacao.critica
                )
                self._transicionar(CycleState.EM_EXECUCAO_SHERLOCK)
                output_sherlock = self._sherlock.responder_critica(
                    critica=avaliacao.critica,
                    output_anterior=output_sherlock,
                    rodada=rodada,
                )
                self._stranger_room.escrever_resposta(
                    fase=fase, rodada=rodada, author="sherlock",
                    content=output_sherlock.texto
                )
                if rodada == self.MAX_RODADAS:
                    break

        # Mycroft fixa decisão final sobre Sherlock
        self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)
        decisao_sherlock = self._mycroft.fixar_decisao_sherlock(
            output_final_sherlock=output_sherlock,
            rodadas_executadas=rodada,
        )
        self._stranger_room.escrever_decisao_final(
            fase=fase, author="mycroft", decisao=decisao_sherlock
        )

        self._audit.update_sherlock_metadata(
            cycle_id=self._cycle_id,
            rodadas=rodada,
            overruled=decisao_sherlock.mycroft_overruled,
            dilemmas=decisao_sherlock.dilemmas_count,
        )

        # ── CONSOLIDAÇÃO FINAL ────────────────────────────────
        self._transicionar(CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK)
        output_path = self._consolidar_output_final(manifest)

        self._transicionar(CycleState.AGUARDANDO_VERIFICACAO_SAIDA)
        return str(output_path)

    def _consolidar_output_final(self, manifest: CycleManifest) -> Path:
        """
        Mycroft gera o documento consolidado (Relatório Preliminar ou Final)
        a partir das decisões finais das duas fases.
        """
        decisao_watson = self._stranger_room.ler_decisao_final("watson_integridade")
        decisao_sherlock = self._stranger_room.ler_decisao_final("sherlock_validacao")

        relatorio = self._mycroft.consolidar(
            manifest=manifest,
            decisao_watson=decisao_watson,
            decisao_sherlock=decisao_sherlock,
        )

        # Nome do arquivo conforme atividade
        prefixo = "relatorio_preliminar" if manifest.activity == 1 \
                  else "relatorio_final"
        output_filename = f"{prefixo}_{self._cycle_id}.md"
        output_path = self._cycle_dir / "output" / output_filename

        output_path.write_text(relatorio.texto, encoding="utf-8")

        self._audit.update_output_info(
            cycle_id=self._cycle_id,
            output_filename=output_filename,
        )

        return output_path

    # ──────────────────────────────────────────────────────────
    # GESTÃO DE ESTADOS
    # ──────────────────────────────────────────────────────────

    def _transicionar(self, novo_estado: CycleState) -> None:
        """
        Valida e executa transição de estado.
        Persiste o novo estado no audit_index antes de prosseguir.
        Registra o evento no events.jsonl.
        """
        estado_atual = CycleState(
            self._audit.get_cycle(self._cycle_id).status
        )
        if novo_estado not in TRANSICOES_VALIDAS.get(estado_atual, set()):
            raise InvalidStateTransitionError(
                f"Transição inválida: {estado_atual.value} → {novo_estado.value}. "
                f"Verifique o estado do ciclo com `diogenes status`."
            )
        self._audit.update_status(self._cycle_id, novo_estado.value)
        self._registrar_evento(
            event_type="STATE_TRANSITION",
            details={"de": estado_atual.value, "para": novo_estado.value},
        )

    def abortar(self, razao: str) -> None:
        """
        Aborta o ciclo por decisão de Lestrade.
        Registra razão no audit_index e no events.jsonl.
        O diretório de trabalho é preservado integralmente.
        """
        self._audit.update_status(self._cycle_id, CycleState.ABORTADO_LESTRADE.value)
        self._registrar_evento(
            event_type="CYCLE_ABORTED",
            details={"razao": razao, "por": "lestrade"},
        )

    def _abortar_por_falha(self, exc: Exception, fase: str) -> None:
        """
        Aborta o ciclo por falha de agente.
        Registra detalhes da exceção no events.jsonl.
        """
        self._audit.update_status(
            self._cycle_id, CycleState.ABORTADO_FALHA_AGENTE.value
        )
        self._registrar_evento(
            event_type="CYCLE_ABORTED_FAILURE",
            details={
                "fase": fase,
                "excecao": type(exc).__name__,
                "mensagem": str(exc),
            },
        )

    def _registrar_evento(self, event_type: str, details: dict) -> None:
        """Append de evento em _runtime/events.jsonl."""
        import json
        from datetime import datetime, timezone
        evento = {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cycle_id": self._cycle_id,
            "event_type": event_type,
            **details,
        }
        eventos_path = self._runtime_dir / "events.jsonl"
        with eventos_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
```

## **8.5 O Protocolo da Stranger's Room**

A classe `StrangerRoom` encapsula completamente o protocolo de escrita e leitura dos arquivos de revisão. O Orquestrador não conhece nomes de arquivos ou estrutura de frontmatter — delega tudo ao `StrangerRoom`.

```python
# src/diogenes/orchestrator/stranger_room.py (extrato de interface)

class StrangerRoom:

    def escrever_apresentacao(self, fase: str, author: str, content: str) -> Path:
        """Escreve 01_apresentacao.md. Levanta se arquivo já existe."""

    def escrever_critica(self, fase: str, rodada: int, author: str,
                         content: str) -> Path:
        """Escreve 02_critica_mycroft_r1.md ou 04_critica_mycroft_r2.md."""

    def escrever_resposta(self, fase: str, rodada: int, author: str,
                          content: str) -> Path:
        """Escreve 03_resposta_r1.md ou 05_resposta_r2.md."""

    def escrever_decisao_final(self, fase: str, author: str,
                                decisao: DecisaoFinal) -> Path:
        """
        Escreve 99_decisao_final.md com frontmatter YAML completo.
        Preenche has_critical_alert, has_dilemma, mycroft_overruled
        a partir dos campos do objeto DecisaoFinal.
        """

    def ler_decisao_final(self, fase: str) -> DecisaoFinal:
        """Lê 99_decisao_final.md e retorna DecisaoFinal parseado."""

    def _escrever_arquivo(self, path: Path, frontmatter: dict,
                           body: str) -> Path:
        """
        Escrita atômica de arquivo da Stranger's Room.
        Calcula content_hash do body antes de escrever.
        Levanta StrangerRoomWriteError se o arquivo já existe —
        nenhum arquivo da Stranger's Room é jamais sobrescrito (Artigo 11).
        """
```

A regra de imutabilidade do Artigo 11 é implementada pela verificação `if path.exists(): raise StrangerRoomWriteError(...)` antes de qualquer escrita. Não há modo de sobrescrita — se um arquivo existir, é erro de lógica no Orquestrador.

## **8.6 Tratamento de Falhas de Agente no Loop**

O Orquestrador envolve cada chamada de agente em bloco `try/except` que captura as três classes de exceção do `LLMClient`:

```python
# Padrão de tratamento — aplicado em cada chamada de agente no Orquestrador

try:
    output_watson = self._watson.analisar(inputs_dir=inputs_dir, manifest=manifest)

except LLMCostLimitError as exc:
    # Teto de custo atingido — pausa o ciclo, notifica Lestrade
    self._transicionar(CycleState.PAUSADO_LESTRADE)
    self._registrar_evento("COST_LIMIT_REACHED", {"mensagem": str(exc)})
    raise  # relançado ao CLI para exibição formatada

except (LLMCallError, LLMTimeoutError) as exc:
    # Falha irrecuperável — aborta o ciclo
    self._abortar_por_falha(exc, fase="watson_integridade")
    raise  # relançado ao CLI para exibição formatada
```

A separação entre `LLMCostLimitError` (que pausa e permite retomada) e `LLMCallError`/`LLMTimeoutError` (que aborta definitivamente) é a mesma estabelecida no Bloco 6.7. O Orquestrador implementa essa distinção mecanicamente — não há julgamento, apenas classificação por tipo de exceção.

## **8.7 Identificação de Alerta Crítico**

O alerta crítico é detectado pelo Orquestrador lendo o campo `has_critical_alert` do frontmatter do arquivo `99_decisao_final.md` da fase `watson_integridade`, após a fixação da decisão por Mycroft. Não há parsing de texto livre — apenas leitura do boolean estruturado.

```python
# Dentro de _executar_fase_watson, após escrever a decisão final:

decisao = self._stranger_room.ler_decisao_final("watson_integridade")

if decisao.has_critical_alert:
    # Notifica Lestrade no console via CLI
    # O Orquestrador não decide — apenas sinaliza e para.
    self._audit.update_status(
        self._cycle_id,
        CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value
    )
    self._registrar_evento(
        "CRITICAL_ALERT_NOTIFIED",
        {"critical_alerts_count": decisao.critical_alerts_count}
    )
    return decisao  # retorno ao executar() que retorna "" ao CLI
```

O CLI, ao receber o retorno vazio de `executar()`, exibe a notificação formatada e aguarda `diogenes proceed` ou `diogenes pause`. A notificação inclui o número de alertas críticos e o caminho do arquivo `99_decisao_final.md` para leitura por Lestrade.

## **8.8 Garantia Estrutural de Sequencialidade**

O Artigo 3 da Constituição — agentes nunca operam em paralelo — é garantido por construção no Orquestrador: o código é síncrono, single-process, sem threads. Cada chamada de agente bloqueia o processo até retornar. Não há nenhum mecanismo que precise ser explicitamente ativado para garantir sequencialidade — ela é a consequência natural de código síncrono sem `asyncio`.

O risco de violação acidental seria a introdução futura de qualquer primitiva de concorrência (`threading.Thread`, `asyncio.create_task`, `concurrent.futures.submit`). O `ruff.toml` pode ser configurado para sinalizar importações dessas primitivas como aviso durante o piloto — proteção adicional de lint.

## **8.9 Interação com o CLI**

O Orquestrador é instanciado e chamado pelos comandos CLI da seguinte forma:

| Comando CLI | Método do Orquestrador |
|---|---|
| `diogenes confirm-manifest` | `Orchestrator(cycle_id).executar(manifest)` |
| `diogenes proceed` | `Orchestrator(cycle_id).retomar_apos_alerta(manifest)` |
| `diogenes resume` | `Orchestrator(cycle_id).retomar_apos_alerta(manifest)` (mesmo método) |
| `diogenes abort` | `Orchestrator(cycle_id).abortar(razao)` |

O CLI lê o manifesto do ciclo antes de instanciar o Orquestrador — o manifesto contém todas as informações necessárias para construir o contexto da retomada sem precisar reconstruir o estado a partir do zero.

---

*Bloco 8 encerrado.*

---

# **Bloco 9 — Agentes (Mycroft, Watson, Sherlock)**

## **9.1 Arquitetura Comum dos Três Agentes**

Os três agentes compartilham a mesma estrutura interna: um invocador Python em `src/diogenes/agents/` que constrói prompts, chama o `LLMClient` e parseia a resposta, mais três arquivos de definição em `docs/agentes/{agente}/` que determinam o comportamento do modelo sem tocar o código.

A separação entre invocador e definição tem consequência direta na manutenção: ajustar o comportamento de um agente — seu perfil, seus limites, seus critérios de classificação — é editar Markdown, não Python. O invocador é estável; a definição evolui conforme o piloto avança.

**Estrutura dos arquivos de definição:**

`soul.md` — quem o agente é: perfil, valores, o que deve e o que não deve fazer, tom de resposta. É o texto que orienta o modelo sobre sua identidade e postura. Lido integralmente e inserido no início do prompt de sistema.

`skills.md` — o que o agente sabe fazer: templates de output estruturado, critérios de classificação, exemplos de raciocínio esperado, formatos de seção. É o texto que orienta o modelo sobre como produzir seu output. Lido integralmente e inserido após o `soul.md` no prompt de sistema.

`agent.md` — como o agente roda: modelo preferencial, temperatura sugerida, ferramentas disponíveis (nenhuma no piloto), limites declarados. Lido pelo invocador para consulta — os valores de runtime vêm de `agents_spec.yaml`, que prevalece.

**Método de construção de prompt — padrão para os três agentes:**

```python
def _construir_system_prompt(self) -> str:
    soul = (self._docs_dir / "soul.md").read_text(encoding="utf-8")
    skills = (self._docs_dir / "skills.md").read_text(encoding="utf-8")
    return f"{soul}\n\n---\n\n{skills}"
```

O `soul.md` e o `skills.md` são lidos do filesystem a cada chamada — não são cacheados. Isso permite editar os arquivos durante o piloto sem reiniciar o processo.

**Formato de output — padrão para os três agentes:**

Todo output de agente é Markdown estruturado com seções nomeadas. Os agentes são instruídos, via `skills.md`, a produzir saídas com cabeçalhos específicos que o invocador localiza por parsing de texto para extrair campos estruturados. Não há JSON no output dos agentes — Markdown é mais legível por humanos e mais robusto contra erros de geração (um modelo que "esquece" de fechar uma chave JSON produz output inutilizável; um modelo que omite uma seção Markdown produz output parcial ainda aproveitável).

A extração de campos do Markdown é feita por funções auxiliares simples em cada invocador — localização de cabeçalhos por prefixo `##`, extração do texto entre dois cabeçalhos consecutivos.

## **9.2 Mycroft — Auditor Chefe**

### **9.2.1 Responsabilidades e Limites**

Mycroft executa cinco tipos de chamada distintos ao longo de um ciclo, cada um com seu `call_type` registrado no trace:

| `call_type` | Momento | O que produz |
|---|---|---|
| `definir_tasks_watson` | Início do ciclo | Lista ordenada de tasks para Watson |
| `avaliar_agente` | Após cada output de executor | `APROVADO` ou `QUESTIONAR` + crítica |
| `fixar_decisao` | Após segunda rodada ou aprovação | `DecisaoFinal` com booleanos e síntese |
| `montar_pacote_sherlock` | Entre as duas fases | Pacote integrado com contexto completo |
| `consolidar` | Após decisão final de Sherlock | Relatório Preliminar ou Final em Markdown |

O Artigo 5 da Constituição — Mycroft não analisa arquivos diretamente, não executa cálculos, não aplica regras de negócio — é implementado pela ausência de ferramentas de leitura de planilha ou parsing de SQL no `agent.md` de Mycroft, e pela instrução explícita no `soul.md`: *"Você nunca lê, parseia ou analisa arquivos diretamente. Você recebe sínteses e análises produzidas por outros agentes e opera sobre elas."*

### **9.2.2 Chamada `definir_tasks_watson`**

Mycroft recebe o manifesto do ciclo (lista de arquivos, módulo, atividade) e produz a lista ordenada de tasks para Watson. O output é Markdown estruturado com seção `## Tasks para Watson` contendo lista numerada.

```
## Tasks para Watson

1. Analisar a planilha `planilha_calculo.xlsx`: verificar fechamento numérico
   de totais e subtotais, identificar fórmulas declaradas e recalculá-las,
   registrar inconsistências com severidade.

2. Traduzir o script `script_extracao.sql` para linguagem natural: descrever
   quais bases consulta, quais filtros aplica, quais agregações produz e qual
   estrutura de resultado retorna. Não inferir intenção — descrever o código.

3. Traduzir o notebook `notebook_transformacao.ipynb` para linguagem natural:
   descrever cada célula executável na sequência real de execução.

4. Identificar a cadeia de produção dos dados: qual script gerou qual dado
   em qual planilha, registrando lacunas como inconsistências quando a cadeia
   não puder ser identificada.

5. Gerar análise de padrões e anomalias: comportamentos nos dados que merecem
   atenção de Sherlock na validação metodológica.
```

O invocador parseia essa seção e passa as tasks como contexto para Watson — não como prompt separado, mas como parte do `user_prompt` de Watson que Mycroft efetivamente produz (Mycroft escreve o briefing de Watson, não apenas uma lista).

### **9.2.3 Chamada `avaliar_agente`**

Mycroft recebe o output do agente executor e produz avaliação em uma de duas formas.

**Forma APROVADO:** seção `## Avaliação` com texto de aprovação e fundamentação curta. O invocador detecta a palavra-chave `APROVADO` no cabeçalho ou no primeiro parágrafo da seção.

**Forma QUESTIONAR:** seção `## Avaliação` com `QUESTIONAR`, seguida de `## Pontos para Revisão` com lista numerada de críticas objetivas. Cada crítica tem: localização precisa no output do agente (número da seção ou nome do achado), fundamentação da crítica, e instrução específica de correção ou justificativa esperada.

O invocador detecta `QUESTIONAR` e extrai a lista de pontos para incluir no próximo prompt do agente executor como `user_prompt` de resposta.

### **9.2.4 Chamada `fixar_decisao`**

Chamada após o encerramento do loop de revisão (por aprovação ou por esgotamento das duas rodadas). Mycroft recebe: output final do agente executor, histórico de rodadas (apresentação + críticas + respostas), e flag indicando se chegou ao limite de rodadas.

Produz `DecisaoFinal` com as seguintes seções Markdown, que o invocador extrai:

```markdown
## Decisão Final — Watson / [fase]

### Síntese

[Texto descritivo do que foi analisado e do processo de revisão]

### Posição Adotada

[Descrição da posição final — acatando Watson ou fixando posição diversa]

### Overrule

NÃO  ← ou SIM, com fundamentação

### Alertas Críticos

CONTAGEM: 0  ← ou número inteiro > 0

### Notas para Sherlock

[Pontos específicos que Mycroft julga relevantes destacar para Sherlock]
```

O invocador extrai `Overrule` (sim/não), `CONTAGEM` de alertas críticos, e usa o texto completo como body do arquivo `99_decisao_final.md` na Stranger's Room.

### **9.2.5 Chamada `consolidar`**

A chamada mais longa e de maior responsabilidade de Mycroft. Recebe as decisões finais das duas fases e produz o documento completo de output do ciclo.

O `skills.md` de Mycroft declara o template completo do Relatório Preliminar e do Relatório Final — incluindo os campos de cabeçalho institucional, as seções obrigatórias (Contexto, Achados de Integridade, Achados de Aderência Metodológica, Classificação Consolidada, Inconsistências para Contraditório, Limitações e Pontos Não Verificáveis, Posição do Departamento), e as regras de redação (terceira pessoa, impessoal, sem nomes de agentes no corpo, assinatura ao final).

A chamada `consolidar` é a mais cara em tokens — produz o documento completo que Lestrade lerá e chancelará. O `max_tokens` de Mycroft (4096) é suficiente para o relatório de um módulo piloto; módulos de alta materialidade em produção podem exigir ajuste.

## **9.3 Watson — Auditor de Integridade Técnica**

### **9.3.1 Responsabilidades e Limites**

Watson executa três tipos de chamada:

| `call_type` | Momento | O que produz |
|---|---|---|
| `analise_inicial` | Após receber tasks de Mycroft | Relatório graduado de integridade |
| `resposta_r1` | Após crítica de Mycroft, rodada 1 | Output revisado ou sustentado |
| `resposta_r2` | Após crítica de Mycroft, rodada 2 | Output final (segunda e última rodada) |

O Artigo 6 da Constituição — Watson não interpreta a metodologia homologada — é implementado por duas medidas no invocador `watson.py`. Primeira: o documento da metodologia homologada nunca é incluído no `user_prompt` ou no `system_prompt` de Watson. Segunda: o `soul.md` de Watson instrui explicitamente: *"Você nunca emite juízo sobre conformidade metodológica. Você descreve o que os dados mostram e como os scripts operam — não se eles estão corretos segundo a metodologia. Esse julgamento pertence a outro agente."*

### **9.3.2 Preparação do Pacote de Input**

O invocador `watson.py` prepara o conteúdo dos arquivos para inclusão no `user_prompt`. O desafio é o limite de contexto: planilhas Excel grandes, notebooks longos e scripts SQL complexos podem exceder o contexto disponível se incluídos integralmente.

A estratégia de preparação por tipo de arquivo:

**Planilhas Excel (`.xlsx`):** lidas via `openpyxl`. Para cada aba, extrai: nomes das colunas, primeiras dez linhas de dados, fórmulas das células identificadas como resultado (células com `=`), totais e subtotais identificados pela posição (última linha ou linha com formatação de negrito quando detectável). O extrato textual representa a estrutura da planilha sem incluir todo o conteúdo.

**Scripts SQL (`.sql`):** lidos como texto puro após formatação via `sqlparse`. Incluídos integralmente se abaixo de oito mil caracteres; truncados com aviso explícito no prompt se maiores.

**Notebooks Jupyter (`.ipynb`):** lidos via `nbformat`. Extraídas apenas as células do tipo `code`, na sequência de execução. Células de markdown são omitidas (Watson analisa o código, não a documentação). Output das células é omitido (Watson analisa o que o código faz, não o que produziu em uma execução específica).

**Documentos de descrição metodológica do módulo (`.pdf`, `.md`):** lidos como texto. PDFs são lidos via extração de texto puro (`pdfminer.six` — adicionado como dependência opcional de runtime somente se PDFs estiverem presentes nos inputs). Documentos Markdown são incluídos integralmente.

O `user_prompt` de Watson é montado com seções delimitadas para cada arquivo, precedidas das tasks definidas por Mycroft:

```
[TASKS DE MYCROFT]
{texto das tasks}

[ARQUIVO 1: planilha_calculo.xlsx]
{extrato estruturado da planilha}

[ARQUIVO 2: script_extracao.sql]
{script formatado}

[ARQUIVO 3: notebook_transformacao.ipynb]
{células de código extraídas}
```

### **9.3.3 Estrutura do Output de Watson**

O `skills.md` de Watson declara o template de output que o modelo deve produzir:

```markdown
## Resumo Executivo

[Parágrafo curto com o estado geral da análise]

## Verificação Numérica das Planilhas

### [Nome da planilha]
- Totais verificados: [sim/não/parcial]
- Inconsistências identificadas: [lista ou "nenhuma"]
- Detalhamento: [texto]

## Tradução dos Scripts SQL

### [Nome do script]
**O que executa:** [descrição em linguagem natural]
**Bases consultadas:** [lista]
**Filtros aplicados:** [lista]
**Resultado produzido:** [estrutura]

## Tradução dos Notebooks Python

### [Nome do notebook]
[Descrição sequencial de cada célula executável]

## Cadeia de Produção dos Dados

[Mapeamento: script X → dado Y → planilha Z]
[Lacunas: arquivo A não tem origem rastreável]

## Insights e Anomalias

[Padrões, comportamentos atípicos, pontos que merecem atenção de Sherlock]

## Tabela de Alertas

| Severidade | Localização | Descrição |
|---|---|---|
| CRÍTICA | planilha_calculo.xlsx, aba Resumo, célula D47 | Total não fecha... |
| ATENÇÃO | script_extracao.sql, linha 34 | Filtro potencialmente... |
| INFORMATIVA | notebook, célula 7 | Transformação aplica... |

## Arquivos Não Analisáveis

| Arquivo | Razão | Tentativa realizada |
|---|---|---|
| [se houver] | [razão] | [o que foi tentado] |
```

O invocador parseia a seção `## Tabela de Alertas` para contar alertas por severidade e popula o campo `critical_alerts_count` do objeto `WatsonOutput` — que Mycroft usa ao fixar a decisão final.

### **9.3.4 Chamadas de Resposta a Críticas**

Quando Watson responde a uma crítica de Mycroft, o `user_prompt` inclui: o output original de Watson, a crítica de Mycroft com todos os pontos numerados, e a instrução de responder ponto a ponto — acatando com correção ou sustentando com justificativa adicional. O `system_prompt` é idêntico ao da chamada inicial (Watson mantém sua identidade e limites em todas as chamadas do ciclo).

## **9.4 Sherlock — Auditor de Validação Metodológica CBS**

### **9.4.1 Responsabilidades e Limites**

Sherlock executa três tipos de chamada, espelhando Watson:

| `call_type` | Momento | O que produz |
|---|---|---|
| `validacao_inicial` | Após receber pacote integrado de Mycroft | Relatório classificado ponto a ponto |
| `resposta_r1` | Após crítica de Mycroft, rodada 1 | Classificações revisadas ou sustentadas |
| `resposta_r2` | Após crítica de Mycroft, rodada 2 | Classificações finais |

O Artigo 7 da Constituição — Sherlock não analisa integridade estrutural dos artefatos — é implementado pela ausência, no `user_prompt` de Sherlock, de conteúdo bruto de planilhas, scripts SQL ou notebooks. Sherlock recebe a análise já processada de Watson (via decisão final de Mycroft) e os documentos de descrição metodológica — nunca os arquivos técnicos brutos.

### **9.4.2 O Pacote Integrado de Mycroft para Sherlock**

O método `MycrooftAgent.montar_pacote_sherlock()` produz o documento de contexto que Sherlock recebe como `user_prompt`. Contém:

```
[CONTEXTO DO MÓDULO]
Módulo: MOD_010 — Pessoa Física
Atividade: 1 — Validação de Módulo
Módulo da Sala de Sigilo: Não

[METODOLOGIA HOMOLOGADA — APÊNDICE CORRESPONDENTE]
{conteúdo do documento da metodologia para o módulo em análise}

[ANÁLISE DE INTEGRIDADE (Watson — decisão final de Mycroft)]
{corpo do arquivo 99_decisao_final.md de watson_integridade}

[INVENTÁRIO DOS ARTEFATOS ENTREGUES]
{lista de arquivos com extensões e tamanhos — sem conteúdo}

[REGRAS DE NEGÓCIO DO MÓDULO]
{conteúdo de regras_negocio_{mod_id}.md}

[ATA DA REUNIÃO DE ENTREGA]
{conteúdo de ata_reuniao_entrega_{mod_id}.md}
```

O documento da metodologia homologada correspondente ao módulo é o apêndice do Acórdão 2833/2025-Plenário para aquele módulo específico. Está armazenado em `workspace/input/{MOD_ID}/gt_artefatos/metodologia_{mod_id}.md` (ou `.pdf`, lido via extração de texto). Sherlock recebe o texto completo do apêndice — é a única fonte normativa válida para sua análise.

### **9.4.3 Estrutura do Output de Sherlock**

O `skills.md` de Sherlock declara o template de output com o sistema de classificação do Design System TCU-CBS:

```markdown
## Resumo Executivo

[Parágrafo com a avaliação geral do módulo]

## Classificação Ponto a Ponto

### [Identificador do ponto metodológico — ex.: "Apêndice X, item 3.2.1"]

**Status:** ATENDIDO | ATENDIDO PARCIALMENTE | DIVERGÊNCIA | ATENÇÃO |
             LIMITAÇÃO | NÃO VERIFICÁVEL

**Fundamento metodológico:** [citação do dispositivo da metodologia homologada]

**Evidência:** [o que Watson identificou / o que consta nos artefatos]

**Análise:** [raciocínio que sustenta a classificação]

**Encaminhamento:** [ação recomendada, se houver]

---

[próximo ponto...]

## Inconsistências para Contraditório com a RFB

| Ponto | Status | Descrição resumida |
|---|---|---|
| [identificador] | DIVERGÊNCIA | [resumo] |

## Dilemas Interpretativos

[Seção presente apenas quando há inconsistência com duas interpretações
de peso equivalente que Mycroft também não resolveu]

### Dilema 1
**Interpretação A:** [descrição e fundamento]
**Interpretação B:** [descrição e fundamento]
**Por que não foi resolvido:** [explicação]

## Limitações e Pontos Não Verificáveis

[Pontos classificados como LIMITAÇÃO ou NÃO VERIFICÁVEL com razão objetiva]
```

O invocador parseia a seção `## Dilemas Interpretativos` para detectar presença de dilemas e popula `dilemmas_count` no objeto `SherlockOutput`. Mycroft usa esse campo ao fixar a decisão final de Sherlock e ao decidir se o dilema vai para o relatório ordinário a Lestrade.

### **9.4.4 A Régua Metodológica como Única Referência**

O `soul.md` de Sherlock instrui com precisão constitucional: *"Toda classificação que você produz cita explicitamente o dispositivo da metodologia homologada que a fundamenta. Classificação sem citação é classificação inválida. Você não propõe metodologia alternativa. Você não substitui escolhas técnicas que a RFB fez dentro do espaço que a metodologia permite. Você verifica se o que foi feito corresponde ao que foi prescrito."*

Essa instrução é direta do Artigo 2 da Constituição e do princípio orientador da estratégia integrada do GT (Bloco 2.2 do `GT_CBS_Estrategia_Integrada_Validacao.docx`). O `soul.md` é o mecanismo que transfere o mandato institucional para o comportamento do modelo.

## **9.5 Tratamento de Output Malformado**

Os modelos de linguagem podem ocasionalmente produzir outputs que não seguem o template esperado — seção ausente, formato diferente do declarado, resposta truncada por limite de tokens. O invocador de cada agente implementa estratégia defensiva de parsing:

```python
def _parsear_output(self, content: str, call_type: str) -> WatsonOutput:
    """
    Parseia o Markdown de resposta de Watson em estrutura tipada.
    Em caso de seção ausente, registra aviso e usa valor default seguro
    em vez de levantar exceção — output parcial é melhor que falha total.
    """
    secoes = self._extrair_secoes(content)

    tabela_alertas = secoes.get("Tabela de Alertas", "")
    critical_count = self._contar_criticos(tabela_alertas)

    arquivos_nao_analisaveis = secoes.get("Arquivos Não Analisáveis", "")

    if "Resumo Executivo" not in secoes:
        # Seção obrigatória ausente — registra aviso mas não falha
        self._log_aviso(
            f"Seção 'Resumo Executivo' ausente no output de Watson "
            f"(call_type={call_type}). Output pode estar incompleto."
        )

    return WatsonOutput(
        texto=content,
        critical_alerts_count=critical_count,
        has_unanalyzable_files=bool(arquivos_nao_analisaveis.strip()),
        secoes=secoes,
    )
```

Outputs truncados por `max_tokens` são detectados pela ausência das seções finais esperadas. O invocador registra o aviso no `events.jsonl` e passa o output parcial adiante — Mycroft, ao avaliar, identificará a incompletude e poderá questionar Watson para completar a análise na rodada de revisão.

## **9.6 Adição ao `pyproject.toml`**

A leitura de PDFs (para documentos metodológicos entregues nesse formato) exige dependência adicional não prevista no Bloco 3:

```toml
# Adicionar a [project.dependencies]:
"pdfminer.six>=20221105",   # extração de texto de PDFs (metodologia e documentos RFB)
```

Esta é a segunda alteração retroativa identificada ao longo dos blocos (a primeira foi a troca de `responses` por `pytest-httpx` no Bloco 6). Ambas são incorporadas ao `pyproject.toml` final.

---

*Bloco 9 encerrado.*

---

# **Bloco 10 — Stranger's Room**

## **10.1 O Que É e o Que Não É**

A Stranger's Room não é um componente com lógica analítica. É um protocolo de persistência: um conjunto de regras que determina como os artefatos de revisão são escritos, nomeados e lidos, garantindo que o Artigo 11 da Constituição — *"todo raciocínio, toda decisão e toda conclusão são registrados; nenhum trace é sobrescrito"* — seja cumprido por construção, não por disciplina.

O nome vem do Clube Diógenes: a Stranger's Room é o único espaço do clube onde o silêncio pode ser quebrado — onde Watson apresenta seu trabalho a Mycroft, onde Mycroft questiona, onde o debate acontece. No sistema, é o diretório onde esse diálogo é materializado em arquivos imutáveis.

A classe `StrangerRoom` em `orchestrator/stranger_room.py` implementa esse protocolo. O Orquestrador a usa como intermediário para toda escrita e leitura nos diretórios `watson_integridade/` e `sherlock_validacao/`.

## **10.2 Estrutura de Diretórios e Convenção de Nomes**

Cada fase tem seu subdiretório dentro de `stranger_room/`. Os arquivos são nomeados com prefixo numérico que garante ordenação cronológica natural por nome — sem dependência de metadados do filesystem.

```
stranger_room/
├── watson_integridade/
│   ├── 01_apresentacao.md           ← output inicial de Watson
│   ├── 02_critica_mycroft_r1.md     ← primeira crítica de Mycroft (se houver)
│   ├── 03_resposta_r1.md            ← resposta de Watson à primeira crítica
│   ├── 04_critica_mycroft_r2.md     ← segunda crítica de Mycroft (se houver)
│   ├── 05_resposta_r2.md            ← resposta de Watson à segunda crítica
│   └── 99_decisao_final.md          ← decisão final de Mycroft (sempre presente)
│
└── sherlock_validacao/
    ├── 01_apresentacao.md
    ├── 02_critica_mycroft_r1.md     ← presentes apenas se Mycroft questionou
    ├── 03_resposta_r1.md
    ├── 04_critica_mycroft_r2.md     ← presentes apenas se houve segunda rodada
    ├── 05_resposta_r2.md
    └── 99_decisao_final.md
```

**Prefixo `99` para a decisão final:** a numeração salta de `05` para `99` intencionalmente. O gap protege contra adição acidental de arquivo intermediário entre a segunda resposta e a decisão final — qualquer arquivo com prefixo `06` a `98` seria anomalia imediatamente visível. O `99` também garante que a decisão final sempre aparece por último na listagem alfabética, independentemente de quantas rodadas ocorreram.

**Ciclos com zero rodadas de revisão:** quando Mycroft aprova Watson sem crítica, o diretório `watson_integridade/` contém apenas dois arquivos: `01_apresentacao.md` e `99_decisao_final.md`. Isso é o estado mínimo válido da fase.

**Ciclos com uma rodada de revisão:** quatro arquivos: `01`, `02`, `03`, `99`.

**Ciclos com duas rodadas de revisão:** seis arquivos: `01`, `02`, `03`, `04`, `05`, `99`.

O número de arquivos presentes em cada fase é um indicador direto do número de rodadas de revisão — auditável por simples listagem do diretório.

## **10.3 Especificação Completa do Frontmatter**

Todo arquivo da Stranger's Room tem frontmatter YAML delimitado por `---` seguido de corpo Markdown. O frontmatter é escrito pelo `StrangerRoom` — nunca pelo agente nem pelo Orquestrador diretamente.

**Schema completo do frontmatter:**

```yaml
---
# Identificação do ciclo e da posição do arquivo no fluxo
cycle_id: MOD_010_A1_20260507T143000Z
phase: watson_integridade          # watson_integridade | sherlock_validacao
file_type: apresentacao            # apresentacao | critica_r1 | resposta_r1 |
                                   # critica_r2 | resposta_r2 | decisao_final
round: null                        # null para apresentacao e decisao_final
                                   # 1 para critica_r1 e resposta_r1
                                   # 2 para critica_r2 e resposta_r2

# Autoria
author: watson                     # mycroft | watson | sherlock
role: Auditor de Integridade Técnica
                                   # Auditor Chefe
                                   # Auditor de Integridade Técnica
                                   # Auditor de Validação Metodológica CBS

# Temporalidade
timestamp_utc: 2026-05-07T14:31:45Z
timestamp_local: 2026-05-07T11:31:45-03:00

# Integridade
content_hash: sha256:8f3a2b1c4d5e6f7a   # SHA-256 dos primeiros 16 hex do body

# Campos semânticos — preenchidos apenas em 99_decisao_final.md
# Todos os outros arquivos têm estes campos como null
has_critical_alert: null           # true | false | null
has_dilemma: null                  # true | false | null
mycroft_overruled: null            # true | false | null
critical_alerts_count: null        # inteiro | null
dilemmas_count: null               # inteiro | null
---
```

**Regras de preenchimento dos campos semânticos:**

`has_critical_alert` e `critical_alerts_count`: preenchidos apenas no `99_decisao_final.md` da fase `watson_integridade`. Para todos os outros arquivos, permanecem `null`. O Orquestrador lê esses campos diretamente do frontmatter — não parseia o corpo.

`has_dilemma` e `dilemmas_count`: preenchidos apenas no `99_decisao_final.md` da fase `sherlock_validacao`. Para todos os outros arquivos, permanecem `null`.

`mycroft_overruled`: preenchido apenas em `99_decisao_final.md` de qualquer fase. Indica que Mycroft fixou posição diferente da defendida pelo agente executor na última rodada.

Para todos os arquivos que não são `99_decisao_final.md`, os cinco campos semânticos são explicitamente escritos como `null` — não omitidos. Isso garante que o schema do frontmatter é uniforme em todos os arquivos e que um parser que tente ler `has_critical_alert` de um arquivo de apresentação recebe `null` (não `KeyError`).

## **10.4 Implementação da Classe `StrangerRoom`**

```python
# src/diogenes/orchestrator/stranger_room.py

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import frontmatter  # python-frontmatter

from diogenes.config import DiogenesConfig
from diogenes.models import DecisaoFinal, StrangerRoomFile
from diogenes.orchestrator.exceptions import StrangerRoomWriteError


# Mapeamento file_type → prefixo de arquivo
_PREFIXOS: dict[str, str] = {
    "apresentacao":  "01",
    "critica_r1":    "02",
    "resposta_r1":   "03",
    "critica_r2":    "04",
    "resposta_r2":   "05",
    "decisao_final": "99",
}

# Nomes descritivos por file_type (após o prefixo)
_NOMES: dict[str, str] = {
    "apresentacao":  "apresentacao",
    "critica_r1":    "critica_mycroft_r1",
    "resposta_r1":   "resposta_r1",
    "critica_r2":    "critica_mycroft_r2",
    "resposta_r2":   "resposta_r2",
    "decisao_final": "decisao_final",
}

# Cargos formais por autor
_ROLES: dict[str, str] = {
    "mycroft":  "Auditor Chefe",
    "watson":   "Auditor de Integridade Técnica",
    "sherlock": "Auditor de Validação Metodológica CBS",
}


class StrangerRoom:
    """
    Protocolo de persistência dos artefatos de revisão do Departamento.

    Garante imutabilidade (Artigo 11), nomenclatura padronizada,
    frontmatter completo e content_hash em todos os arquivos.
    """

    def __init__(
        self,
        cycle_id: str,
        stranger_room_dir: Path,
        cfg: DiogenesConfig,
    ) -> None:
        self._cycle_id = cycle_id
        self._sr_dir = stranger_room_dir
        self._cfg = cfg

    # ──────────────────────────────────────────────────────────
    # MÉTODOS DE ESCRITA
    # ──────────────────────────────────────────────────────────

    def escrever_apresentacao(
        self, fase: str, author: str, content: str
    ) -> Path:
        return self._escrever(
            fase=fase,
            file_type="apresentacao",
            round_num=None,
            author=author,
            content=content,
            campos_semanticos={},
        )

    def escrever_critica(
        self, fase: str, rodada: int, author: str, content: str
    ) -> Path:
        file_type = f"critica_r{rodada}"
        return self._escrever(
            fase=fase,
            file_type=file_type,
            round_num=rodada,
            author=author,
            content=content,
            campos_semanticos={},
        )

    def escrever_resposta(
        self, fase: str, rodada: int, author: str, content: str
    ) -> Path:
        file_type = f"resposta_r{rodada}"
        return self._escrever(
            fase=fase,
            file_type=file_type,
            round_num=rodada,
            author=author,
            content=content,
            campos_semanticos={},
        )

    def escrever_decisao_final(
        self, fase: str, author: str, decisao: DecisaoFinal
    ) -> Path:
        """
        Escreve 99_decisao_final.md com os campos semânticos
        derivados do objeto DecisaoFinal.
        """
        campos_semanticos: dict = {
            "mycroft_overruled":      decisao.mycroft_overruled,
        }
        # Campos de alerta crítico — apenas na fase watson_integridade
        if fase == "watson_integridade":
            campos_semanticos["has_critical_alert"] = decisao.has_critical_alert
            campos_semanticos["critical_alerts_count"] = decisao.critical_alerts_count
        # Campos de dilema — apenas na fase sherlock_validacao
        if fase == "sherlock_validacao":
            campos_semanticos["has_dilemma"] = decisao.has_dilemma
            campos_semanticos["dilemmas_count"] = decisao.dilemmas_count

        return self._escrever(
            fase=fase,
            file_type="decisao_final",
            round_num=None,
            author=author,
            content=decisao.texto,
            campos_semanticos=campos_semanticos,
        )

    # ──────────────────────────────────────────────────────────
    # MÉTODOS DE LEITURA
    # ──────────────────────────────────────────────────────────

    def ler_decisao_final(self, fase: str) -> DecisaoFinal:
        """
        Lê 99_decisao_final.md e retorna DecisaoFinal parseado.
        Levanta FileNotFoundError se o arquivo não existir.
        """
        path = self._path_para(fase, "decisao_final")
        if not path.exists():
            raise FileNotFoundError(
                f"Decisão final ausente para fase '{fase}': '{path}'. "
                f"O ciclo pode estar em estado inconsistente."
            )
        post = frontmatter.load(str(path))
        meta = post.metadata

        return DecisaoFinal(
            texto=post.content,
            mycroft_overruled=meta.get("mycroft_overruled") or False,
            has_critical_alert=meta.get("has_critical_alert") or False,
            critical_alerts_count=meta.get("critical_alerts_count") or 0,
            has_dilemma=meta.get("has_dilemma") or False,
            dilemmas_count=meta.get("dilemmas_count") or 0,
        )

    def listar_arquivos_fase(self, fase: str) -> list[Path]:
        """
        Retorna lista ordenada de todos os arquivos presentes
        na fase indicada, em ordem cronológica por prefixo.
        """
        fase_dir = self._sr_dir / fase
        if not fase_dir.is_dir():
            return []
        return sorted(fase_dir.glob("*.md"))

    def validar_fase_completa(self, fase: str) -> None:
        """
        Verifica que a fase possui no mínimo apresentacao e decisao_final.
        Levanta StrangerRoomValidationError se incompleta.
        """
        arquivos = {p.name for p in self.listar_arquivos_fase(fase)}
        obrigatorios = {"01_apresentacao.md", "99_decisao_final.md"}
        faltando = obrigatorios - arquivos
        if faltando:
            raise StrangerRoomValidationError(
                f"Fase '{fase}' incompleta. "
                f"Arquivos obrigatórios ausentes: {sorted(faltando)}"
            )

    # ──────────────────────────────────────────────────────────
    # NÚCLEO DE ESCRITA — PRIVADO
    # ──────────────────────────────────────────────────────────

    def _escrever(
        self,
        fase: str,
        file_type: str,
        round_num: int | None,
        author: str,
        content: str,
        campos_semanticos: dict,
    ) -> Path:
        """
        Escreve um arquivo da Stranger's Room com frontmatter completo.

        Imutabilidade: levanta StrangerRoomWriteError se o arquivo já existir.
        Integridade: calcula content_hash antes de escrever.
        """
        path = self._path_para(fase, file_type)

        # Artigo 11 — nenhum trace é sobrescrito
        if path.exists():
            raise StrangerRoomWriteError(
                f"Tentativa de sobrescrever arquivo imutável: '{path}'. "
                f"Isso indica bug no Orquestrador. "
                f"Verifique o estado do ciclo com `diogenes status`."
            )

        now_utc = datetime.now(timezone.utc)
        content_hash = self._calcular_hash(content)

        # Frontmatter base — campos semânticos nulos por padrão
        fm: dict = {
            "cycle_id":             self._cycle_id,
            "phase":                fase,
            "file_type":            file_type,
            "round":                round_num,
            "author":               author,
            "role":                 _ROLES[author],
            "timestamp_utc":        now_utc.strftime(
                                        self._cfg.persistencia.timestamp_iso_format
                                    ),
            "content_hash":         content_hash,
            # Campos semânticos — null por padrão em todos os arquivos
            "has_critical_alert":   None,
            "critical_alerts_count": None,
            "has_dilemma":          None,
            "dilemmas_count":       None,
            "mycroft_overruled":    None,
        }

        # Sobrescreve os campos semânticos relevantes para este arquivo
        fm.update(campos_semanticos)

        # Monta e escreve o arquivo — operação atômica via write_text
        post = frontmatter.Post(content=content, **fm)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            frontmatter.dumps(post) + "\n",
            encoding=self._cfg.persistencia.encoding,
        )

        return path

    def _path_para(self, fase: str, file_type: str) -> Path:
        """Constrói o Path completo do arquivo conforme convenção de nomes."""
        prefixo = _PREFIXOS[file_type]
        nome = _NOMES[file_type]
        filename = f"{prefixo}_{nome}.md"
        return self._sr_dir / fase / filename

    @staticmethod
    def _calcular_hash(content: str) -> str:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{digest[:16]}"
```

## **10.5 Verificação de Integridade Pós-Escrita**

O `content_hash` no frontmatter serve para detectar alterações posteriores à escrita — seja por edição manual acidental, seja por corrupção de filesystem. A verificação é feita pelo `diogenes verify-output` (Motor de Saída) e pelo `diogenes status` quando exibem informações do ciclo:

```python
def verificar_integridade_arquivo(path: Path, encoding: str = "utf-8") -> bool:
    """
    Verifica que o content_hash do frontmatter corresponde
    ao hash atual do body. Retorna False se houve alteração.
    """
    post = frontmatter.load(str(path))
    hash_declarado = post.metadata.get("content_hash", "")
    hash_atual = StrangerRoom._calcular_hash(post.content)
    return hash_declarado == hash_atual
```

Se a verificação falhar para qualquer arquivo da Stranger's Room de um ciclo, o `diogenes status` exibe alerta visual (vermelho, Design System) indicando arquivo potencialmente alterado. O sistema não aborta — registra o alerta e permite que Lestrade decida o encaminhamento.

## **10.6 Leitura para Retomada de Ciclo**

Quando Lestrade retoma um ciclo pausado via `diogenes resume`, o Orquestrador precisa reconstruir o estado a partir do que está no filesystem — sem depender de estado em memória, que foi perdido quando o processo anterior terminou. A `StrangerRoom` fornece esse suporte:

```python
def inferir_estado_fase(self, fase: str) -> dict:
    """
    Inspeciona os arquivos presentes na fase e infere o estado
    do loop de revisão: quantas rodadas ocorreram, se a decisão
    final já foi escrita, qual arquivo foi o último a ser escrito.
    """
    arquivos = self.listar_arquivos_fase(fase)
    nomes = {p.name for p in arquivos}

    tem_decisao_final = "99_decisao_final.md" in nomes
    rodadas_completas = sum(
        1 for r in [1, 2]
        if f"0{r*2+1}_resposta_r{r}.md" in nomes
    )

    ultimo_arquivo = arquivos[-1] if arquivos else None

    return {
        "tem_decisao_final": tem_decisao_final,
        "rodadas_completas": rodadas_completas,
        "ultimo_arquivo": ultimo_arquivo,
        "fase_concluida": tem_decisao_final,
    }
```

O Orquestrador usa `inferir_estado_fase` ao retomar para determinar em qual ponto do loop de revisão o ciclo estava quando foi pausado, e de onde prosseguir sem repetir operações já executadas.

## **10.7 Exceções da Stranger's Room**

```python
# src/diogenes/orchestrator/exceptions.py (extrato)

class StrangerRoomError(Exception):
    """Classe base para erros da Stranger's Room."""

class StrangerRoomWriteError(StrangerRoomError):
    """
    Tentativa de sobrescrever arquivo imutável.
    Indica bug no Orquestrador — nunca deve ocorrer em operação normal.
    """

class StrangerRoomValidationError(StrangerRoomError):
    """Fase incompleta — arquivos obrigatórios ausentes."""

class InvalidStateTransitionError(Exception):
    """Transição de estado inválida na máquina de estados do Orquestrador."""
```

## **10.8 Leitura Humana Direta — o Teste Final**

O critério de aceitação `CA-FUN-03` do PRD exige que a leitura sequencial dos arquivos da Stranger's Room produza uma transcrição coerente do diálogo técnico. Para satisfazer esse critério, cada arquivo precisa ser autoexplicativo: qualquer auditor que abra `02_critica_mycroft_r1.md` deve entender imediatamente o que está lendo — quem escreveu, em que fase, em resposta a quê.

Isso é garantido por duas medidas. Primeira: o frontmatter declara explicitamente `file_type`, `author`, `role`, `phase` e `round` — o leitor vê o contexto antes de ler uma linha do corpo. Segunda: o `skills.md` de Mycroft instrui que toda crítica deve começar com referência ao arquivo que está respondendo: *"Em resposta à apresentação de Watson na fase de integridade..."*. Essa instrução no `skills.md` é a ponte entre o protocolo técnico da Stranger's Room e a legibilidade institucional que o Departamento exige.

---

*Bloco 10 encerrado.*

---

# **Bloco 11 — Motor de Saída**

## **11.1 Propósito e Princípio de Implementação**

O Motor de Saída executa a verificação peremptória exigida pelo Artigo 15 da Constituição: antes de qualquer chancela final de Lestrade, o documento de output é varrido à procura de marcas internas do Departamento. O que passar pelo portão não pode carregar as marcas de quem o produziu.

O princípio de implementação — declarado no `RF-MV-06` do PRD — é deliberadamente conservador: **regras heurísticas explícitas, sem modelo de linguagem**. A razão é auditabilidade. O Motor de Saída é elemento crítico de governança: sua lógica precisa ser legível e verificável por qualquer pessoa com conhecimento básico de Python, sem dependência de comportamento emergente de modelo. Uma lista de strings e expressões regulares em código é auditável. Um modelo que decide o que é ou não marca interna não é.

O custo é falsos negativos ocasionais — uma marca muito incomum ou formulada de forma inesperada pode não ser detectada. Esse risco é mitigado por dois fatores: os prompts dos agentes instruem explicitamente a não usar nomes ou referências internas no corpo dos documentos externos, e Lestrade lê o documento antes de chancelar. O Motor de Saída é a primeira linha de defesa, não a única.

## **11.2 O Que o Motor Varre**

Os padrões de varredura são lidos de `runtime.yaml` (seção `motor_saida`), conforme especificado no Bloco 4. São quatro categorias, aplicadas em sequência:

**Categoria 1 — Nomes dos agentes e variações.** Lista de strings exatas, verificação case-insensitive:

```
Mycroft Holmes, Mycroft, Dr. Watson, Dr. John Watson,
John Watson, Watson, Sherlock Holmes, Sherlock,
Inspetor Lestrade, Lestrade
```

**Categoria 2 — Cargos em contexto identificador.** Expressões regulares que detectam cargo seguido de verbo de autoria — distinguindo uso legítimo de cargo genérico de uso identificador de agente:

```python
# Legítimo (genérico, sem sujeito identificado):
"O auditor responsável verificou a conformidade..."

# Ilegítimo (identifica o agente como sujeito da ação):
"O Auditor Chefe consolidou este relatório..."
"O Auditor de Integridade Técnica analisou o arquivo..."
```

Regex para detectar a forma ilegítima:
```
(Auditor Chefe|Auditor de Integridade Técnica|
 Auditor de Validação Metodológica CBS|Auditor Responsável)
\s+(consolidou|elaborou|revisou|identificou|concluiu|analisou|
     verificou|traduziu|aplicou|classificou|recebeu|confirmou|
     chancelou|encaminhou)
```

**Categoria 3 — Estruturas internas do Departamento.** Strings exatas, case-insensitive:

```
Stranger's Room, Sala dos Estrangeiros, Clube Diógenes,
Projeto Diógenes, audit_index, Motor de Start, Motor de Saída,
stranger_room, Bloco 1, Bloco 2, Bloco 3, Bloco 4, Bloco 5
```

*Nota sobre "Projeto Diógenes":* o nome do projeto pode aparecer legitimamente no cabeçalho institucional dos documentos gerados (`DVA-CBS | Projeto Diógenes | TC 015.848/2025-6`). O Motor de Saída detecta essa ocorrência mas a classifica automaticamente como `CABECALHO_INSTITUCIONAL` — não como marca ilegítima — quando aparece na primeira linha do documento ou em bloco de metadados YAML. O `skills.md` de Mycroft instrui o posicionamento correto do cabeçalho institucional, e o Motor reconhece esse padrão.

**Categoria 4 — Identificadores técnicos de ciclo.** Expressão regular que detecta `cycle_id` no formato padronizado:

```python
regex = r"MOD_\w+_A\d+_\d{8}T\d{6}Z"
# Detecta: MOD_010_A1_20260507T143000Z
```

O `cycle_id` pode aparecer legitimamente no rodapé do documento como referência de rastreabilidade (`TC 015.848/2025-6 | Ciclo: MOD_010_A1_20260507T143000Z`). O Motor classifica ocorrências no rodapé como `RODAPE_RASTREABILIDADE` — não como marca ilegítima. Ocorrências no corpo do texto são ilegítimas.

## **11.3 Implementação da Classe `MotorSaida`**

```python
# src/diogenes/motors/motor_saida.py

from __future__ import annotations
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from diogenes.config import get_config
from diogenes.models import MotorSaidaReport, OcorrenciaDetectada
from diogenes.persistence.audit_index import AuditIndex


class MotorSaida:
    """
    Varre o documento de output do ciclo à procura de marcas internas
    do Departamento antes da chancela final de Lestrade.

    Opera exclusivamente com regras heurísticas — sem modelo de linguagem.
    Toda a lógica é auditável por leitura direta deste arquivo.
    """

    def __init__(self) -> None:
        self._cfg = get_config()
        self._ms_cfg = self._cfg.motor_saida
        workspace = Path(self._cfg.workspace.path)
        self._audit = AuditIndex(workspace)

        # Pré-compilar expressões regulares para performance
        self._regex_cargos = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in self._ms_cfg.padroes_cargo_identificador
        ]
        self._regex_cycle_id = re.compile(
            self._ms_cfg.regex_cycle_id
        )

    def verificar(self, cycle_id: str) -> MotorSaidaReport:
        """
        Executa a varredura sobre o documento de output do ciclo.

        Returns:
            MotorSaidaReport com lista de ocorrências e hash do documento.

        Raises:
            FileNotFoundError: documento de output não encontrado.
            MotorSaidaError: ciclo não está em estado AGUARDANDO_VERIFICACAO_SAIDA.
        """
        from diogenes.persistence.workspace import WorkspaceManager
        from diogenes.orchestrator.states import CycleState

        ws = WorkspaceManager(Path(self._cfg.workspace.path))
        cycle_dir = ws.get_cycle_dir(cycle_id)

        # Verificar estado do ciclo
        record = self._audit.get_cycle(cycle_id)
        if record.status != CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value:
            raise MotorSaidaError(
                f"Ciclo '{cycle_id}' não está em estado "
                f"AGUARDANDO_VERIFICACAO_SAIDA (estado atual: {record.status}). "
                f"Use `diogenes status --cycle {cycle_id}` para verificar."
            )

        # Localizar o documento de output
        output_dir = cycle_dir / "output"
        outputs = list(output_dir.glob("relatorio_*.md"))
        if not outputs:
            raise FileNotFoundError(
                f"Nenhum documento de output encontrado em '{output_dir}'. "
                f"O ciclo pode estar em estado inconsistente."
            )
        doc_path = outputs[0]  # Sempre um único arquivo por ciclo

        # Ler e calcular hash do documento
        doc_content = doc_path.read_text(encoding=self._cfg.persistencia.encoding)
        doc_hash = "sha256:" + hashlib.sha256(
            doc_content.encode("utf-8")
        ).hexdigest()

        # Executar varredura
        ocorrencias = self._varrer(doc_content, doc_path.name)

        # Montar e registrar o relatório
        report = MotorSaidaReport(
            cycle_id=cycle_id,
            doc_path=doc_path,
            doc_hash=doc_hash,
            ocorrencias=ocorrencias,
            verificado_em_utc=datetime.now(timezone.utc).strftime(
                self._cfg.persistencia.timestamp_iso_format
            ),
            total_ocorrencias=len(ocorrencias),
            documento_limpo=len(ocorrencias) == 0,
        )

        # Registrar invocação no audit_index
        self._audit.update_motor_saida(
            cycle_id=cycle_id,
            invocado_at_utc=report.verificado_em_utc,
            occurrences=report.total_ocorrencias,
            output_hash=doc_hash,
        )

        return report

    def _varrer(
        self, content: str, filename: str
    ) -> list[OcorrenciaDetectada]:
        """
        Aplica as quatro categorias de varredura sobre o conteúdo.
        Retorna lista de ocorrências com localização precisa.
        """
        linhas = content.splitlines()
        ocorrencias: list[OcorrenciaDetectada] = []
        total_linhas = len(linhas)

        for num_linha, linha in enumerate(linhas, start=1):

            # Determinar posição contextual da linha no documento
            posicao = self._classificar_posicao(
                num_linha, total_linhas, linha
            )

            # Categoria 1: nomes dos agentes (string exata, case-insensitive)
            for padrao in self._ms_cfg.padroes_agentes:
                if padrao.lower() in linha.lower():
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=num_linha,
                        categoria="NOME_AGENTE",
                        padrao_detectado=padrao,
                        contexto=self._extrair_contexto(linhas, num_linha - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=None,
                    ))

            # Categoria 2: cargos em contexto identificador (regex)
            for regex in self._regex_cargos:
                match = regex.search(linha)
                if match:
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=num_linha,
                        categoria="CARGO_IDENTIFICADOR",
                        padrao_detectado=match.group(0),
                        contexto=self._extrair_contexto(linhas, num_linha - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=None,
                    ))

            # Categoria 3: estruturas internas (string exata, case-insensitive)
            for padrao in self._ms_cfg.padroes_estruturas_internas:
                if padrao.lower() in linha.lower():
                    # "Projeto Diógenes" no cabeçalho é legítimo
                    classif = None
                    if (padrao.lower() == "projeto diógenes"
                            and posicao == "CABECALHO"):
                        classif = "CABECALHO_INSTITUCIONAL"
                    ocorrencias.append(OcorrenciaDetectada(
                        linha=num_linha,
                        categoria="ESTRUTURA_INTERNA",
                        padrao_detectado=padrao,
                        contexto=self._extrair_contexto(linhas, num_linha - 1),
                        posicao_documento=posicao,
                        classificacao_automatica=classif,
                    ))

            # Categoria 4: identificadores de ciclo (regex)
            matches = self._regex_cycle_id.findall(linha)
            for match in matches:
                classif = None
                if posicao == "RODAPE":
                    classif = "RODAPE_RASTREABILIDADE"
                ocorrencias.append(OcorrenciaDetectada(
                    linha=num_linha,
                    categoria="CYCLE_ID",
                    padrao_detectado=match,
                    contexto=self._extrair_contexto(linhas, num_linha - 1),
                    posicao_documento=posicao,
                    classificacao_automatica=classif,
                ))

        return ocorrencias

    def _classificar_posicao(
        self, num_linha: int, total_linhas: int, linha: str
    ) -> str:
        """
        Classifica a posição da linha no documento:
        CABECALHO (primeiras 5 linhas), RODAPE (últimas 10 linhas),
        ou CORPO (demais).
        """
        if num_linha <= 5:
            return "CABECALHO"
        if num_linha >= total_linhas - 9:
            return "RODAPE"
        return "CORPO"

    @staticmethod
    def _extrair_contexto(linhas: list[str], idx: int) -> str:
        """
        Extrai até 2 linhas antes e 2 linhas depois da ocorrência,
        para exibição no relatório. Facilita a decisão de Lestrade.
        """
        inicio = max(0, idx - 2)
        fim = min(len(linhas), idx + 3)
        trecho = linhas[inicio:fim]
        return "\n".join(
            f"{'>>>' if i == idx - inicio else '   '} {linha}"
            for i, linha in enumerate(trecho)
        )
```

## **11.4 O Modelo `MotorSaidaReport` e `OcorrenciaDetectada`**

```python
# src/diogenes/models.py — extrato dos modelos do Motor de Saída

class OcorrenciaDetectada(BaseModel):
    model_config = ConfigDict(frozen=True)

    linha: int                          # número da linha no documento
    categoria: str                      # NOME_AGENTE | CARGO_IDENTIFICADOR |
                                        # ESTRUTURA_INTERNA | CYCLE_ID
    padrao_detectado: str               # string ou match exato encontrado
    contexto: str                       # 2 linhas antes e depois, com marcação
    posicao_documento: str              # CABECALHO | CORPO | RODAPE
    classificacao_automatica: str | None  # CABECALHO_INSTITUCIONAL |
                                          # RODAPE_RASTREABILIDADE | None


class MotorSaidaReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    cycle_id: str
    doc_path: Path
    doc_hash: str                       # SHA-256 do documento verificado
    ocorrencias: list[OcorrenciaDetectada]
    verificado_em_utc: str
    total_ocorrencias: int
    documento_limpo: bool               # True quando total_ocorrencias == 0
```

## **11.5 Exibição do Relatório no Console**

O CLI formata o relatório do Motor de Saída com Rich. A exibição varia conforme o resultado:

**Documento limpo (zero ocorrências):**
```
╔══════════════════════════════════════════════════════╗
║  MOTOR DE SAÍDA — Verificação Concluída              ║
╚══════════════════════════════════════════════════════╝

 ✓  Documento verificado: relatorio_preliminar_MOD_010_A1_...md
 ✓  Ocorrências detectadas: 0
 ✓  Documento classificado como LIMPO

 Hash do documento: sha256:4f5a6b7c...

 O documento está pronto para chancela. Execute:

   diogenes seal --cycle MOD_010_A1_20260507T143000Z
```

**Documento com ocorrências (exemplo com duas):**
```
╔══════════════════════════════════════════════════════╗
║  MOTOR DE SAÍDA — Ocorrências Detectadas             ║
╚══════════════════════════════════════════════════════╝

 ✗  Documento: relatorio_preliminar_MOD_010_A1_...md
 ✗  Ocorrências detectadas: 2

┌─────────────────────────────────────────────────────┐
│ Ocorrência 1 — Linha 47 — NOME_AGENTE               │
│ Padrão: "Watson"  |  Posição: CORPO                 │
│ Classificação automática: (nenhuma)                  │
├─────────────────────────────────────────────────────┤
│    45 │ Os dados apresentados pela RFB demonstram    │
│    46 │ consistência nos cálculos das células de     │
│ >>> 47│ resumo. Watson identificou que a célula D47  │
│    48 │ não fecha com a soma das linhas 12 a 46.     │
│    49 │                                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Ocorrência 2 — Linha 93 — CARGO_IDENTIFICADOR       │
│ Padrão: "Auditor Chefe consolidou"  |  Posição: CORPO│
│ Classificação automática: (nenhuma)                  │
├─────────────────────────────────────────────────────┤
│    91 │ A análise foi conduzida com base nos         │
│    92 │ artefatos entregues pela RFB. O              │
│ >>> 93│ Auditor Chefe consolidou as evidências       │
│    94 │ identificadas nas duas fases.                │
│    95 │                                              │
└─────────────────────────────────────────────────────┘

 Escolha uma ação:

   diogenes seal --cycle {id} --accept-occurrences --reason "motivo"
       Aceita as ocorrências com justificativa registrada no audit_index.

   diogenes abort --cycle {id} --reason "corrigir output manualmente"
       Aborta para correção manual. Reabrir com diogenes start após correção.
```

## **11.6 As Quatro Decisões de Lestrade**

Quando o Motor detecta ocorrências, Lestrade tem quatro caminhos:

**`LIMPO`** — zero ocorrências detectadas. `diogenes seal` é habilitado diretamente. Registrado no `audit_index` como `motor_saida_decision: LIMPO`.

**`ACEITO_JUSTIFICADO`** — Lestrade revisa as ocorrências, conclui que são falsos positivos (ex.: `Projeto Diógenes` no cabeçalho com `classificacao_automatica: CABECALHO_INSTITUCIONAL`) e aceita com justificativa: `diogenes seal --cycle {id} --accept-occurrences --reason "ocorrências são todas cabeçalho institucional legítimo"`. A justificativa é registrada no `audit_index`. Registrado como `motor_saida_decision: ACEITO_JUSTIFICADO`.

**`CORRIGIDO_MANUAL`** — Lestrade edita diretamente o arquivo de output para remover as marcas, salva, e reinvoca o Motor: `diogenes verify-output --cycle {id}`. O Motor executa nova varredura sobre o arquivo modificado. Se limpo, habilita chancela. O novo hash do documento é registrado. Registrado como `motor_saida_decision: CORRIGIDO_MANUAL`.

**`RETORNADO_MYCROFT`** — Lestrade decide que o output precisa ser regenerado por Mycroft com instrução explícita de evitar as marcas: `diogenes abort --cycle {id} --reason "output com marcas — regenerar"`. O ciclo é abortado; um novo ciclo é aberto com os mesmos inputs e os traces da Stranger's Room como contexto histórico. Registrado como `motor_saida_decision: RETORNADO_MYCROFT` no ciclo abortado. Na prática, esse caminho é raro — os prompts dos agentes são calibrados para evitar marcas — mas é documentado para completude.

## **11.7 Registro Final no `audit_index`**

Após a chancela de Lestrade via `diogenes seal`, o `audit_index.csv` recebe a atualização final do ciclo:

```
motor_saida_invocado_at_utc: 2026-05-07T15:10:00Z
motor_saida_occurrences: 0
motor_saida_decision: LIMPO
lestrade_seal_at_utc: 2026-05-07T15:12:34Z
output_filename: relatorio_preliminar_MOD_010_A1_20260507T143000Z.md
output_hash: sha256:4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c...
status: ENCERRADO_CHANCELADO
ended_at_utc: 2026-05-07T15:12:34Z
```

O `output_hash` calculado no momento da verificação é o hash do documento que Lestrade chancelou. Qualquer alteração posterior ao documento é detectável pela comparação do hash registrado com o hash atual do arquivo em disco — auditoria futura pode verificar integridade do output sem depender do sistema.

## **11.8 Exceção do Motor de Saída**

```python
# src/diogenes/motors/exceptions.py (complemento)

class MotorSaidaError(Exception):
    """
    Ciclo não está no estado correto para verificação,
    ou documento de output não foi encontrado.
    """
```

---

*Bloco 11 encerrado.*

---

# **Bloco 12 — CLI**

## **12.1 Estrutura do App Typer**

O CLI é o único ponto de interação humana com o sistema no piloto. Implementado com Typer, registra onze subcomandos, cada um em arquivo próprio dentro de `cli/commands/`. O app raiz em `cli/app.py` agrega os subcomandos e configura comportamentos globais.

```python
# src/diogenes/cli/app.py

import typer
from rich.console import Console
from diogenes.cli.commands import (
    start, confirm_manifest, proceed, pause,
    resume, verify_output, seal, abort, status,
    list_cycles, show,
)

app = typer.Typer(
    name="diogenes",
    help="Departamento de Validação Assistida da CBS — TC 015.848/2025-6",
    add_completion=False,    # autocompletion desabilitado no piloto
    rich_markup_mode="rich", # habilita marcação Rich nas docstrings
    no_args_is_help=True,    # exibe help quando invocado sem subcomando
)

console = Console()

# Registrar subcomandos
app.command("start")(start.cmd)
app.command("confirm-manifest")(confirm_manifest.cmd)
app.command("proceed")(proceed.cmd)
app.command("pause")(pause.cmd)
app.command("resume")(resume.cmd)
app.command("verify-output")(verify_output.cmd)
app.command("seal")(seal.cmd)
app.command("abort")(abort.cmd)
app.command("status")(status.cmd)
app.command("list")(list_cycles.cmd)
app.command("show")(show.cmd)

def main() -> None:
    app()
```

**Comportamentos globais:**

Toda exceção não tratada dentro de um subcomando é capturada pelo handler global que: exibe mensagem de erro formatada em vermelho com Rich (sem stacktrace visível ao usuário), registra o stacktrace completo no `events.jsonl` do ciclo se um ciclo estiver ativo, e encerra o processo com código de saída 1. O handler é registrado via `app.exception_handler`.

A validação de configuração (`get_config()`) é chamada no início de cada subcomando. Erros de configuração — variável de ambiente ausente, YAML inválido — são exibidos com mensagem específica antes de qualquer operação de filesystem.

## **12.2 Especificação dos Onze Subcomandos**

### **`diogenes start`**

```
diogenes start --module MOD_010 --activity 1
               [--yes]
```

**Parâmetros:**
- `--module` / `-m`: identificador do módulo (`MOD_010`, `MOD_SINT_001`, etc.) — obrigatório
- `--activity` / `-a`: código da atividade (`1` ou `2`) — obrigatório, default `1`
- `--yes`: pula confirmação interativa — para uso em scripts

**Pré-condições verificadas:**
1. Configuração válida (`get_config()` sem erro)
2. Atividade é `1` ou `2` — qualquer outro valor encerra com mensagem clara
3. Para atividade `2`: existe ciclo A1 encerrado para o módulo no `audit_index`

**Confirmação interativa (sem `--yes`):**
```
Iniciar ciclo para MOD_010 — Atividade 1 (Validação de Módulo)?
Confirmar [s/N]:
```

**Componente acionado:** `MotorStart().run(module_id, activity)`

**Saída de sucesso:** exibição formatada do manifesto conforme Bloco 7.6, com `cycle_id` destacado em âmbar e comandos de próximo passo.

**Saída de erro típica:**
```
✗  Input obrigatório ausente:
   workspace/input/MOD_010/briefing_mod010.md

   Coloque o arquivo no diretório e execute novamente.
```

**Requisito PRD:** `RF-CL-02`, `RF-MS-01` a `RF-MS-09`

---

### **`diogenes confirm-manifest`**

```
diogenes confirm-manifest --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` a confirmar — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `PREPARADO` (único estado válido para confirmação)
3. `manifest.md` existe e é legível no diretório do ciclo
4. Hashes dos arquivos em `inputs/` batem com os hashes do manifesto (verificação de integridade pós-cópia no caso de sincronização assíncrona do OneDrive ter alterado algo)

**Componente acionado:** `Orchestrator(cycle_id).executar(manifest)` — inicia o ciclo e bloqueia até o primeiro ponto de pausa ou até o estado `AGUARDANDO_VERIFICACAO_SAIDA`

**Comportamento durante execução:** o console exibe progresso em tempo real com Rich. Cada transição de fase é anunciada:

```
● Manifesto confirmado — acionando Mycroft
● Mycroft definiu 5 tasks para Watson
● Watson em execução... (14:31:45 UTC)
  ⟳ Aguardando resposta do modelo (38s decorridos)
● Watson concluiu análise — encaminhando a Mycroft para revisão
● Mycroft questiona Watson (rodada 1/2)
● Watson respondendo à crítica...
● Mycroft aprova — encaminhando pacote a Sherlock
● Sherlock em execução... (14:45:02 UTC)
● Sherlock concluiu validação — Mycroft revisando
● Mycroft aprova — Sherlock consolidando output final
✓ Output gerado: relatorio_preliminar_MOD_010_A1_...md

Execute para verificar antes de chancelar:
  diogenes verify-output --cycle MOD_010_A1_20260507T143000Z
```

**Saída quando alerta crítico é detectado:**
```
⚠  ALERTA CRÍTICO identificado por Watson

   1 alerta de severidade crítica foi identificado na análise de integridade.
   Consulte a decisão final de Watson antes de prosseguir:
   workspace/cycles/MOD_010_A1_.../stranger_room/watson_integridade/99_decisao_final.md

   Para autorizar prosseguimento:  diogenes proceed --cycle {id}
   Para pausar o ciclo:            diogenes pause   --cycle {id}
```

**Requisito PRD:** `RF-CL-03`, `RF-OR-01` a `RF-OR-11`

---

### **`diogenes proceed`**

```
diogenes proceed --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO`

**Componente acionado:** `Orchestrator(cycle_id).retomar_apos_alerta(manifest)` — retoma o ciclo a partir de Sherlock

**Saída:** mesma progressão do `confirm-manifest`, a partir da fase Sherlock

**Requisito PRD:** `RF-CL-04`, `RF-OR-05`

---

### **`diogenes pause`**

```
diogenes pause --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO`

**Componente acionado:** `AuditIndex.update_status(cycle_id, "PAUSADO_LESTRADE")`

**Saída:**
```
● Ciclo pausado: MOD_010_A1_20260507T143000Z
  Status: PAUSADO_LESTRADE

  O ciclo pode ser retomado quando Lestrade decidir prosseguir:
    diogenes resume --cycle MOD_010_A1_20260507T143000Z
```

**Requisito PRD:** `RF-CL-05`

---

### **`diogenes resume`**

```
diogenes resume --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `PAUSADO_LESTRADE`
3. A fase `watson_integridade` está completa (tem `99_decisao_final.md`) — verificada via `StrangerRoom.validar_fase_completa`

**Componente acionado:** `Orchestrator(cycle_id).retomar_apos_alerta(manifest)` — mesmo método do `proceed`, pois em ambos os casos o ciclo retoma a partir de Sherlock

**Saída:** mesma progressão do `confirm-manifest`, a partir da fase Sherlock

**Requisito PRD:** `RF-CL-06`

---

### **`diogenes verify-output`**

```
diogenes verify-output --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `AGUARDANDO_VERIFICACAO_SAIDA`
3. Arquivo de output existe em `cycles/{cycle_id}/output/`

**Componente acionado:** `MotorSaida().verificar(cycle_id)`

**Saída:** relatório formatado conforme Bloco 11.5

**Após ocorrências — opções adicionais exibidas no console:**
```
Para aceitar as ocorrências com justificativa:
  diogenes seal --cycle {id} --accept-occurrences --reason "justificativa"

Para corrigir manualmente e reverificar:
  [edite o arquivo de output]
  diogenes verify-output --cycle {id}
```

**Requisito PRD:** `RF-CL-07`, `RF-MV-01` a `RF-MV-06`

---

### **`diogenes seal`**

```
diogenes seal --cycle MOD_010_A1_20260507T143000Z
              [--accept-occurrences --reason "justificativa"]
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório
- `--accept-occurrences`: flag — habilita chancela mesmo com ocorrências detectadas
- `--reason`: justificativa obrigatória quando `--accept-occurrences` está presente

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status é `AGUARDANDO_VERIFICACAO_SAIDA` ou `AGUARDANDO_CHANCELA_LESTRADE`
3. O Motor de Saída foi invocado pelo menos uma vez (coluna `motor_saida_invocado_at_utc` preenchida)
4. Se não há `--accept-occurrences`: `motor_saida_occurrences == 0` (documento limpo)
5. Se há `--accept-occurrences`: `--reason` está presente e não vazio

**Confirmação interativa (sempre, mesmo sem ocorrências):**
```
Chancelar output do ciclo MOD_010_A1_20260507T143000Z?
Documento: relatorio_preliminar_MOD_010_A1_...md
Hash: sha256:4f5a6b7c...

Esta ação é irreversível. O ciclo será marcado como ENCERRADO_CHANCELADO.
Confirmar [s/N]:
```

**Componente acionado:**
1. `AuditIndex.update_motor_saida_decision(cycle_id, decision, reason)`
2. `AuditIndex.update_status(cycle_id, "ENCERRADO_CHANCELADO")`
3. `AuditIndex.update_seal(cycle_id, timestamp)`

**Saída:**
```
✓  Ciclo chancelado: MOD_010_A1_20260507T143000Z
   Status: ENCERRADO_CHANCELADO
   Chancelado em: 2026-05-07T15:12:34Z

   Output disponível para entrega ao GT:
   workspace/cycles/MOD_010_A1_20260507T143000Z/output/
   relatorio_preliminar_MOD_010_A1_20260507T143000Z.md
```

**Requisito PRD:** `RF-CL-08`

---

### **`diogenes abort`**

```
diogenes abort --cycle MOD_010_A1_20260507T143000Z
               --reason "motivo do aborto"
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório
- `--reason` / `-r`: razão do aborto — obrigatório, mínimo de dez caracteres

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`
2. Status não é já terminal (`ENCERRADO_CHANCELADO`, `ABORTADO_*`)

**Confirmação interativa:**
```
Abortar ciclo MOD_010_A1_20260507T143000Z?
Razão: "motivo do aborto"

O diretório de trabalho será preservado integralmente.
Esta ação não pode ser desfeita.
Confirmar [s/N]:
```

**Componente acionado:** `Orchestrator(cycle_id).abortar(razao)`

**Saída:**
```
● Ciclo abortado: MOD_010_A1_20260507T143000Z
  Razão: "motivo do aborto"
  Status: ABORTADO_LESTRADE

  Diretório de trabalho preservado em:
  workspace/cycles/MOD_010_A1_20260507T143000Z/
```

**Requisito PRD:** `RF-CL-09`

---

### **`diogenes status`**

```
diogenes status --cycle MOD_010_A1_20260507T143000Z
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório

**Pré-condições verificadas:**
1. `cycle_id` existe no `audit_index`

**Componente acionado:** leitura direta do `audit_index` + inspeção do diretório do ciclo

**Saída:**
```
╔══════════════════════════════════════════════════════╗
║  Status do Ciclo                                     ║
╚══════════════════════════════════════════════════════╝

 Cycle ID  : MOD_010_A1_20260507T143000Z
 Módulo    : MOD_010 — Pessoa Física
 Atividade : 1 — Validação de Módulo
 Status    : AGUARDANDO_VERIFICACAO_SAIDA
 Aberto em : 2026-05-07T14:30:00Z
 Ambiente  : local | diogenes 0.1.0 | commit a3f8b2c1

 Fase watson_integridade
   Arquivos presentes : 4 (1 apresentação, 1 crítica, 1 resposta, 1 decisão)
   Rodadas de revisão : 1
   Alerta crítico     : Não
   Mycroft overruled  : Não

 Fase sherlock_validacao
   Arquivos presentes : 2 (1 apresentação, 1 decisão)
   Rodadas de revisão : 0
   Dilema identificado: Não
   Mycroft overruled  : Não

 Motor de Saída      : Aguardando invocação
 Próxima ação        : diogenes verify-output --cycle MOD_010_A1_...
```

Quando um arquivo da Stranger's Room tem `content_hash` divergente do conteúdo atual, o campo correspondente exibe aviso em vermelho: `⚠ Hash divergente — possível alteração após escrita`.

**Requisito PRD:** `RF-CL-10`

---

### **`diogenes list`**

```
diogenes list [--module MOD_010] [--status ENCERRADO_CHANCELADO]
              [--activity 1] [--limit 20]
```

**Parâmetros:**
- `--module` / `-m`: filtro por módulo — opcional
- `--status` / `-s`: filtro por status — opcional
- `--activity` / `-a`: filtro por atividade — opcional
- `--limit` / `-n`: máximo de ciclos exibidos, default `20`

**Componente acionado:** `AuditIndex.list_cycles(...)` com os filtros fornecidos

**Saída:**
```
 Ciclos registrados (filtro: module=MOD_010)

 CYCLE ID                          MOD   AT  STATUS                    ABERTO EM
 MOD_010_A1_20260507T143000Z       010    1  ENCERRADO_CHANCELADO      2026-05-07
 MOD_010_A2_20260514T090000Z       010    2  EM_EXECUCAO_WATSON        2026-05-14

 2 ciclo(s) encontrado(s).
```

**Requisito PRD:** `RF-CL-11`

---

### **`diogenes show`**

```
diogenes show --cycle MOD_010_A1_20260507T143000Z
              [--phase watson]
              [--file 02]
```

**Parâmetros:**
- `--cycle` / `-c`: `cycle_id` — obrigatório
- `--phase` / `-p`: `watson` ou `sherlock` — opcional (exibe ambas se omitido)
- `--file` / `-f`: prefixo do arquivo (`01`, `02`, `99` etc.) — opcional (exibe todos da fase se omitido)

**Componente acionado:** leitura direta do filesystem da Stranger's Room

**Saída:** exibe o conteúdo dos arquivos solicitados com frontmatter formatado por Rich e corpo Markdown renderizado no terminal. Cada arquivo é precedido de cabeçalho com nome, autor e timestamp.

**Requisito PRD:** `RF-CL-12`

## **12.3 O Módulo `display.py`**

O `display.py` centraliza todas as funções de formatação Rich utilizadas pelos subcomandos. Não contém lógica de negócio — apenas apresentação.

```python
# src/diogenes/cli/display.py (interface pública)

def exibir_manifesto(manifest: CycleManifest) -> None:
    """Exibe manifesto de abertura formatado com tabela de inputs."""

def exibir_progresso_fase(fase: str, agente: str, acao: str) -> None:
    """Exibe linha de progresso durante execução de ciclo."""

def exibir_alerta_critico(cycle_id: str, path_decisao: Path) -> None:
    """Exibe notificação de alerta crítico em âmbar."""

def exibir_relatorio_motor_saida(report: MotorSaidaReport) -> None:
    """Exibe relatório de varredura com ocorrências ou confirmação de limpeza."""

def exibir_status_ciclo(record: CycleRecord, estado_sr: dict) -> None:
    """Exibe painel de status completo do ciclo."""

def exibir_lista_ciclos(ciclos: list[CycleRecord]) -> None:
    """Exibe tabela de ciclos com filtros aplicados."""

def exibir_erro(mensagem: str, sugestao: str | None = None) -> None:
    """Exibe mensagem de erro em vermelho com sugestão de ação corretiva."""

def exibir_sucesso(mensagem: str) -> None:
    """Exibe mensagem de sucesso em verde."""
```

As cores seguem o sistema semântico do Design System TCU-CBS:
- Verde (`#2E7D32`): sucesso, aprovação, documento limpo
- Âmbar (`#F57C00`): atenção, alerta crítico, aguardando decisão
- Vermelho (`#C62828`): erro, divergência, aborto
- Cinza (`#616161`): informativo, limitação
- Branco sobre fundo vermelho: ocorrência ilegítima detectada pelo Motor de Saída

## **12.4 Tabela de Mapeamento Requisito → Comando → Componente**

| Requisito PRD | Subcomando | Componente acionado |
|---|---|---|
| `RF-CL-02`, `RF-MS-*` | `diogenes start` | `MotorStart.run()` |
| `RF-CL-03`, `RF-OR-*` | `diogenes confirm-manifest` | `Orchestrator.executar()` |
| `RF-CL-04`, `RF-OR-05` | `diogenes proceed` | `Orchestrator.retomar_apos_alerta()` |
| `RF-CL-05` | `diogenes pause` | `AuditIndex.update_status()` |
| `RF-CL-06` | `diogenes resume` | `Orchestrator.retomar_apos_alerta()` |
| `RF-CL-07`, `RF-MV-*` | `diogenes verify-output` | `MotorSaida.verificar()` |
| `RF-CL-08` | `diogenes seal` | `AuditIndex.update_seal()` |
| `RF-CL-09` | `diogenes abort` | `Orchestrator.abortar()` |
| `RF-CL-10` | `diogenes status` | `AuditIndex.get_cycle()` + `StrangerRoom.inferir_estado_fase()` |
| `RF-CL-11` | `diogenes list` | `AuditIndex.list_cycles()` |
| `RF-CL-12` | `diogenes show` | `StrangerRoom.listar_arquivos_fase()` |

## **12.5 Garantias de Segurança dos Comandos Modificadores**

Todo subcomando que altera estado — `start`, `confirm-manifest`, `proceed`, `pause`, `resume`, `seal`, `abort` — satisfaz três garantias:

**Falha antes de escrever:** validações de pré-condição são executadas integralmente antes de qualquer operação de filesystem ou alteração do `audit_index`. Se uma pré-condição falha, nada foi modificado.

**Confirmação interativa:** exceto quando `--yes` ou `--force` estão presentes, o usuário vê um resumo da operação e confirma explicitamente. A confirmação usa `typer.confirm()` com default `False` — teclar Enter sem digitar `s` cancela a operação.

**Mensagem de erro acionável:** toda falha exibe a razão específica do erro e a ação corretiva esperada. O padrão é: linha vermelha com `✗ [O que falhou]`, linha normal com `[Por que falhou]`, linha de sugestão com `[O que fazer]`.

---

*Bloco 12 encerrado.*

---

# **Bloco 13 — Testes**

## **13.1 Estratégia Geral**

A suíte de testes cobre dois níveis com objetivos distintos.

**Testes unitários** verificam cada componente de infraestrutura em isolamento: Motor de Start, Motor de Saída, Orquestrador, Stranger's Room, `audit_index`, manifesto, `LLMClient`. Usam filesystem temporário (`tmp_path` do pytest) e mocks de LLM — nenhuma chamada real à API, nenhum custo, execução em segundos. São a salvaguarda primária contra regressões durante o desenvolvimento.

**Teste de integração** executa o ciclo completo da Atividade 1 — do `diogenes start` ao `diogenes seal` — com mocks de LLM retornando respostas predefinidas. Verifica que todos os componentes se encadeiam corretamente e que o filesystem resultante satisfaz os critérios de aceitação do PRD. É o único teste que pode falhar por problema de orquestração (um componente corretamente implementado mas incorretamente encadeado).

Os agentes LLM (Mycroft, Watson, Sherlock) não são testados por testes unitários próprios — seu comportamento depende do modelo subjacente e é validado empiricamente durante as execuções reais do piloto. O que é testado nos unitários dos invocadores é o parsing do output: dado um texto de resposta predefinido, o invocador extrai corretamente os campos estruturados?

## **13.2 Estrutura do `conftest.py`**

O `conftest.py` define as fixtures compartilhadas entre todos os testes. É o arquivo mais importante da suíte — fixtures bem projetadas eliminam boilerplate e tornam os testes legíveis.

```python
# tests/conftest.py

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch

from diogenes.config import get_config, DiogenesConfig
from diogenes.models import AgentSpec


# ──────────────────────────────────────────────────────────
# FIXTURES DE FILESYSTEM
# ──────────────────────────────────────────────────────────

@pytest.fixture
def workspace_temp(tmp_path: Path) -> Path:
    """
    Cria estrutura de workspace temporária para testes.
    Inclui subdiretórios input/ e cycles/ e um audit_index.csv vazio.
    Limpa automaticamente ao final do teste.
    """
    ws = tmp_path / "workspace"
    (ws / "input").mkdir(parents=True)
    (ws / "cycles").mkdir(parents=True)
    audit = ws / "audit_index.csv"
    audit.write_text(
        "cycle_id,module_id,activity,status,opened_at_utc,"
        "ended_at_utc,is_sigilo_module,previous_cycle_id,"
        "watson_rodadas,sherlock_rodadas,mycroft_overruled_watson,"
        "mycroft_overruled_sherlock,watson_critical_alerts_count,"
        "sherlock_dilemmas_count,motor_saida_invocado_at_utc,"
        "motor_saida_occurrences,motor_saida_decision,"
        "lestrade_seal_at_utc,output_filename,output_hash,"
        "custo_total_usd,tokens_mycroft,tokens_watson,tokens_sherlock,"
        "ambiente,diogenes_version,git_commit\n",
        encoding="utf-8",
    )
    return ws


@pytest.fixture
def modulo_sintetico(workspace_temp: Path) -> Path:
    """
    Popula workspace_temp/input/MOD_SINT_001/ com os arquivos
    do módulo sintético copiados de tests/fixtures/MOD_SINT_001/.
    Retorna o path do diretório do módulo.
    """
    fixtures_dir = Path("tests/fixtures/MOD_SINT_001")
    destino = workspace_temp / "input" / "MOD_SINT_001"
    shutil.copytree(str(fixtures_dir), str(destino))
    return destino


# ──────────────────────────────────────────────────────────
# FIXTURES DE CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def limpar_cache_config():
    """
    Limpa o lru_cache de get_config() antes e após cada teste.
    Garante que configurações de um teste não vazam para o próximo.
    """
    get_config.cache_clear()
    yield
    get_config.cache_clear()


@pytest.fixture
def cfg_teste(workspace_temp: Path, monkeypatch: pytest.MonkeyPatch) -> DiogenesConfig:
    """
    Configuração mínima válida para testes, apontando para workspace_temp.
    Sobrescreve variáveis de ambiente necessárias via monkeypatch.
    """
    monkeypatch.setenv("DIOGENES_WORKSPACE", str(workspace_temp))
    monkeypatch.setenv("DIOGENES_LLM_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("DIOGENES_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("DIOGENES_ENV", "local")
    return get_config()


# ──────────────────────────────────────────────────────────
# FIXTURES DE MOCK LLM
# ──────────────────────────────────────────────────────────

@pytest.fixture
def respostas_llm():
    """
    Carrega as respostas predefinidas de tests/fixtures/llm_responses/.
    Retorna dict {call_type: conteudo_resposta}.
    """
    import json
    respostas_dir = Path("tests/fixtures/llm_responses")
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8"))
        for p in respostas_dir.glob("*.json")
    }


@pytest.fixture
def mock_llm_client(respostas_llm: dict):
    """
    Mock do LLMClient que retorna respostas predefinidas em sequência.
    Usa pytest-httpx para interceptar chamadas HTTP do openai SDK.
    A sequência de respostas é determinada pela ordem de calls esperada
    num ciclo completo com uma rodada de revisão por fase.
    """
    from pytest_httpx import HTTPXMock
    # Implementação detalhada na seção 13.5
    ...
```

## **13.3 Testes Unitários por Componente**

### **`test_motor_start.py`**

```python
# tests/unit/test_motor_start.py

class TestMotorStart:

    def test_run_atividade1_sucesso(self, modulo_sintetico, cfg_teste):
        """Ciclo A1 abre com todos os inputs presentes."""
        motor = MotorStart()
        manifest = motor.run("MOD_SINT_001", 1)

        assert manifest.cycle_id.startswith("MOD_SINT_001_A1_")
        assert manifest.activity == 1
        assert manifest.status == "AGUARDANDO_CONFIRMACAO_MANIFESTO"
        assert len(manifest.input_files) >= 4  # mínimo de inputs obrigatórios

    def test_run_falha_input_ausente(self, workspace_temp, cfg_teste):
        """Motor falha com InputMissingError quando briefing está ausente."""
        # Cria estrutura incompleta — sem briefing
        mod_dir = workspace_temp / "input" / "MOD_SINT_001"
        (mod_dir / "entrega_rfb").mkdir(parents=True)
        (mod_dir / "entrega_rfb" / "planilha.xlsx").write_bytes(b"fake")
        (mod_dir / "gt_artefatos").mkdir()
        (mod_dir / "gt_artefatos" / "inventario_mod_sint_001.json").write_text("{}")
        (mod_dir / "gt_artefatos" / "regras_negocio_mod_sint_001.md").write_text("# Regras")
        (mod_dir / "gt_artefatos" / "ata_reuniao_entrega_mod_sint_001.md").write_text("# Ata")
        # briefing_mod_sint_001.md ausente

        motor = MotorStart()
        with pytest.raises(InputMissingError) as exc_info:
            motor.run("MOD_SINT_001", 1)
        assert "briefing" in str(exc_info.value).lower()

    def test_hashes_calculados_corretamente(self, modulo_sintetico, cfg_teste):
        """Cada arquivo de input tem hash SHA-256 calculado e registrado."""
        motor = MotorStart()
        manifest = motor.run("MOD_SINT_001", 1)

        for record in manifest.input_files:
            assert record.hash_sha256
            assert len(record.hash_sha256) == 64  # SHA-256 = 64 hex chars

    def test_copia_nao_altera_originais(self, modulo_sintetico, cfg_teste):
        """Arquivos em input/ não são modificados após o Motor de Start."""
        import hashlib
        briefing = modulo_sintetico / "briefing_mod_sint_001.md"
        hash_antes = hashlib.sha256(briefing.read_bytes()).hexdigest()

        motor = MotorStart()
        motor.run("MOD_SINT_001", 1)

        hash_depois = hashlib.sha256(briefing.read_bytes()).hexdigest()
        assert hash_antes == hash_depois

    def test_audit_index_registra_abertura(self, modulo_sintetico, cfg_teste):
        """audit_index.csv tem linha com status PREPARADO após Motor de Start."""
        motor = MotorStart()
        manifest = motor.run("MOD_SINT_001", 1)

        audit = AuditIndex(Path(cfg_teste.workspace.path))
        record = audit.get_cycle(manifest.cycle_id)
        assert record.status == "PREPARADO"

    def test_atividade2_falha_sem_ciclo_anterior(
        self, modulo_sintetico, cfg_teste
    ):
        """Atividade 2 falha com NoPreviousCycleError sem ciclo A1 encerrado."""
        motor = MotorStart()
        with pytest.raises(NoPreviousCycleError):
            motor.run("MOD_SINT_001", 2)
```

### **`test_stranger_room.py`**

```python
# tests/unit/test_stranger_room.py

class TestStrangerRoom:

    def test_escrita_apresentacao(self, tmp_path):
        """01_apresentacao.md é escrito com frontmatter correto."""
        sr = StrangerRoom(
            cycle_id="MOD_SINT_001_A1_TEST",
            stranger_room_dir=tmp_path,
            cfg=...,
        )
        path = sr.escrever_apresentacao("watson_integridade", "watson", "# Output")

        assert path.name == "01_apresentacao.md"
        post = frontmatter.load(str(path))
        assert post.metadata["author"] == "watson"
        assert post.metadata["file_type"] == "apresentacao"
        assert post.metadata["has_critical_alert"] is None  # null por padrão
        assert post.metadata["mycroft_overruled"] is None

    def test_imutabilidade_impede_sobrescrita(self, tmp_path):
        """Segunda escrita no mesmo arquivo levanta StrangerRoomWriteError."""
        sr = StrangerRoom("TEST", tmp_path, cfg=...)
        sr.escrever_apresentacao("watson_integridade", "watson", "# Output 1")

        with pytest.raises(StrangerRoomWriteError):
            sr.escrever_apresentacao("watson_integridade", "watson", "# Output 2")

    def test_decisao_final_campos_semanticos_watson(self, tmp_path):
        """99_decisao_final.md de watson_integridade tem campos semânticos corretos."""
        sr = StrangerRoom("TEST", tmp_path, cfg=...)
        decisao = DecisaoFinal(
            texto="# Decisão",
            mycroft_overruled=True,
            has_critical_alert=True,
            critical_alerts_count=2,
            has_dilemma=False,
            dilemmas_count=0,
        )
        sr.escrever_decisao_final("watson_integridade", "mycroft", decisao)

        lida = sr.ler_decisao_final("watson_integridade")
        assert lida.mycroft_overruled is True
        assert lida.has_critical_alert is True
        assert lida.critical_alerts_count == 2

    def test_ordenacao_cronologica_por_nome(self, tmp_path):
        """Arquivos listados em ordem numérica de prefixo."""
        sr = StrangerRoom("TEST", tmp_path, cfg=...)
        sr.escrever_apresentacao("watson_integridade", "watson", "A")
        sr.escrever_critica("watson_integridade", 1, "mycroft", "C1")
        sr.escrever_resposta("watson_integridade", 1, "watson", "R1")

        arquivos = sr.listar_arquivos_fase("watson_integridade")
        nomes = [p.name for p in arquivos]
        assert nomes == [
            "01_apresentacao.md",
            "02_critica_mycroft_r1.md",
            "03_resposta_r1.md",
        ]
```

### **`test_motor_saida.py`**

```python
# tests/unit/test_motor_saida.py

class TestMotorSaida:

    def test_detecta_nome_agente_no_corpo(self, tmp_path, cfg_teste):
        """Motor detecta nome de agente no corpo do documento."""
        doc = tmp_path / "relatorio.md"
        doc.write_text(
            "# Relatório\n\nWatson identificou inconsistência na célula D47.\n",
            encoding="utf-8",
        )
        ms = MotorSaida()
        ocorrencias = ms._varrer(doc.read_text(), doc.name)

        assert any(
            o.categoria == "NOME_AGENTE" and "Watson" in o.padrao_detectado
            for o in ocorrencias
        )

    def test_nao_detecta_cargo_generico(self, tmp_path, cfg_teste):
        """Cargo genérico sem verbo de autoria não é detectado."""
        doc = tmp_path / "relatorio.md"
        doc.write_text(
            "A análise foi conduzida pelo auditor responsável.\n",
            encoding="utf-8",
        )
        ms = MotorSaida()
        ocorrencias = ms._varrer(doc.read_text(), doc.name)

        assert not any(o.categoria == "CARGO_IDENTIFICADOR" for o in ocorrencias)

    def test_detecta_cargo_identificador(self, tmp_path, cfg_teste):
        """Cargo seguido de verbo de autoria é detectado."""
        doc = tmp_path / "relatorio.md"
        doc.write_text(
            "O Auditor Chefe consolidou as evidências identificadas.\n",
            encoding="utf-8",
        )
        ms = MotorSaida()
        ocorrencias = ms._varrer(doc.read_text(), doc.name)

        assert any(o.categoria == "CARGO_IDENTIFICADOR" for o in ocorrencias)

    def test_projeto_diogenes_no_cabecalho_e_classificado(self, tmp_path, cfg_teste):
        """'Projeto Diógenes' nas primeiras 5 linhas recebe classificação automática."""
        doc = tmp_path / "relatorio.md"
        doc.write_text(
            "DVA-CBS | Projeto Diógenes | TC 015.848/2025-6\n"
            "\n# Relatório Preliminar\n",
            encoding="utf-8",
        )
        ms = MotorSaida()
        ocorrencias = ms._varrer(doc.read_text(), doc.name)

        cab = [
            o for o in ocorrencias
            if o.classificacao_automatica == "CABECALHO_INSTITUCIONAL"
        ]
        assert len(cab) >= 1

    def test_documento_limpo_retorna_zero_ocorrencias(self, tmp_path, cfg_teste):
        """Documento sem nenhuma marca retorna lista vazia."""
        doc = tmp_path / "relatorio.md"
        doc.write_text(
            "DVA-CBS | Projeto Diógenes | TC 015.848/2025-6\n\n"
            "# Relatório Preliminar de Análise\n\n"
            "Os dados apresentados pela RFB demonstram consistência interna.\n\n"
            "---\n"
            "Auditor Chefe | TC 015.848/2025-6\n",
            encoding="utf-8",
        )
        ms = MotorSaida()
        # Apenas ocorrências no CORPO são ilegítimas
        ocorrencias_corpo = [
            o for o in ms._varrer(doc.read_text(), doc.name)
            if o.posicao_documento == "CORPO"
               and o.classificacao_automatica is None
        ]
        assert len(ocorrencias_corpo) == 0
```

### **`test_audit_index.py`**

```python
# tests/unit/test_audit_index.py

class TestAuditIndex:

    def test_insert_e_get_cycle(self, workspace_temp):
        """Ciclo inserido é recuperável pelo cycle_id."""
        audit = AuditIndex(workspace_temp)
        # inserir via manifest sintético...
        record = audit.get_cycle("MOD_SINT_001_A1_20260507T000000Z")
        assert record.module_id == "MOD_SINT_001"

    def test_escrita_atomica_nao_corrompe_em_interrupcao(self, workspace_temp):
        """
        Simula interrupção durante escrita e verifica que o arquivo
        permanece legível (escrita atômica via arquivo temporário).
        """
        # Teste via mock de os.rename para verificar o protocolo
        ...

    def test_update_status_transicao_valida(self, workspace_temp):
        """Status é atualizado corretamente para transição válida."""
        ...

    def test_list_cycles_com_filtro(self, workspace_temp):
        """list_cycles filtra corretamente por module_id e status."""
        ...
```

## **13.4 Teste de Integração End-to-End**

```python
# tests/integration/test_ciclo_completo.py

class TestCicloCompleto:

    def test_atividade1_ponta_a_ponta(
        self,
        modulo_sintetico,
        cfg_teste,
        mock_llm_client,
    ):
        """
        Executa o ciclo completo da Atividade 1 com mocks de LLM.
        Verifica todos os critérios de aceitação funcionais do PRD Bloco 6.2.

        CA-FUN-01: ciclo executa sem erro de runtime
        CA-FUN-03: protocolo da Stranger's Room com arquivos corretos
        CA-FUN-05: Motor de Saída não detecta falso positivo em output limpo
        """
        # 1. Motor de Start
        motor = MotorStart()
        manifest = motor.run("MOD_SINT_001", 1)
        cycle_id = manifest.cycle_id

        # 2. Orquestrador (com mock LLM)
        orch = Orchestrator(cycle_id)
        output_path_str = orch.executar(manifest)

        # Se ciclo pausou por alerta crítico, retoma
        audit = AuditIndex(Path(cfg_teste.workspace.path))
        record = audit.get_cycle(cycle_id)
        if record.status == "AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO":
            output_path_str = orch.retomar_apos_alerta(manifest)

        assert output_path_str  # não vazio — ciclo chegou ao output

        # 3. Verificar Stranger's Room — fase watson_integridade
        ws_manager = WorkspaceManager(Path(cfg_teste.workspace.path))
        cycle_dir = ws_manager.get_cycle_dir(cycle_id)
        sr = StrangerRoom(cycle_id, cycle_dir / "stranger_room", cfg_teste)
        sr.validar_fase_completa("watson_integridade")
        sr.validar_fase_completa("sherlock_validacao")

        watson_files = sr.listar_arquivos_fase("watson_integridade")
        assert any(f.name == "01_apresentacao.md" for f in watson_files)
        assert any(f.name == "99_decisao_final.md" for f in watson_files)

        # 4. Verificar output gerado
        output_path = Path(output_path_str)
        assert output_path.exists()
        output_content = output_path.read_text(encoding="utf-8")
        assert "relatorio" in output_path.name.lower()
        # Output não deve ter nomes de agentes no corpo
        for nome in ["Watson", "Sherlock", "Mycroft", "Lestrade"]:
            # Excluindo assinatura final (últimas 5 linhas)
            corpo = "\n".join(output_content.splitlines()[:-5])
            assert nome not in corpo, (
                f"Nome de agente '{nome}' encontrado no corpo do relatório"
            )

        # 5. Motor de Saída — documento deve estar limpo
        audit.update_status(cycle_id, "AGUARDANDO_VERIFICACAO_SAIDA")
        ms = MotorSaida()
        report = ms.verificar(cycle_id)
        ocorrencias_ilegitimas = [
            o for o in report.ocorrencias
            if o.posicao_documento == "CORPO"
               and o.classificacao_automatica is None
        ]
        assert len(ocorrencias_ilegitimas) == 0, (
            f"Motor de Saída detectou {len(ocorrencias_ilegitimas)} "
            f"ocorrências ilegítimas no output"
        )

        # 6. audit_index reflete o ciclo corretamente
        record_final = audit.get_cycle(cycle_id)
        assert record_final.output_filename is not None
        assert record_final.output_hash is not None

    def test_duas_rodadas_stranger_room(
        self,
        modulo_sintetico,
        cfg_teste,
        mock_llm_client_duas_rodadas,  # fixture com resposta que força 2 rodadas
    ):
        """
        CA-FUN-03: protocolo com duas rodadas completas em pelo menos uma fase.
        Verifica presença dos seis arquivos da Stranger's Room.
        """
        motor = MotorStart()
        manifest = motor.run("MOD_SINT_001", 1)
        cycle_id = manifest.cycle_id

        orch = Orchestrator(cycle_id)
        orch.executar(manifest)

        ws_manager = WorkspaceManager(Path(cfg_teste.workspace.path))
        cycle_dir = ws_manager.get_cycle_dir(cycle_id)
        sr = StrangerRoom(cycle_id, cycle_dir / "stranger_room", cfg_teste)

        # Verificar se pelo menos uma fase tem os 6 arquivos
        watson_files = {f.name for f in sr.listar_arquivos_fase("watson_integridade")}
        sherlock_files = {f.name for f in sr.listar_arquivos_fase("sherlock_validacao")}

        arquivos_duas_rodadas = {
            "01_apresentacao.md", "02_critica_mycroft_r1.md",
            "03_resposta_r1.md", "04_critica_mycroft_r2.md",
            "05_resposta_r2.md", "99_decisao_final.md",
        }

        tem_duas_rodadas = (
            watson_files == arquivos_duas_rodadas
            or sherlock_files == arquivos_duas_rodadas
        )
        assert tem_duas_rodadas, (
            "Nenhuma fase executou duas rodadas completas. "
            "Ajuste o mock LLM para forçar duas rodadas."
        )
```

## **13.5 Mock do LLMClient com `pytest-httpx`**

O mock intercepta as chamadas HTTP do `openai` SDK e retorna respostas JSON predefinidas na sequência correta para um ciclo completo.

```python
# tests/conftest.py — fixture de mock LLM (complemento)

@pytest.fixture
def mock_llm_client(httpx_mock, respostas_llm):
    """
    Intercepta chamadas HTTP do openai SDK via pytest-httpx.
    Retorna respostas da sequência padrão de um ciclo com 1 rodada por fase.
    """
    # Sequência de respostas para ciclo com 1 rodada em watson, 0 em sherlock:
    # 1. Mycroft: definir_tasks_watson
    # 2. Watson: analise_inicial
    # 3. Mycroft: avaliar_watson (QUESTIONAR)
    # 4. Watson: resposta_r1
    # 5. Mycroft: fixar_decisao_watson (APROVADO após r1)
    # 6. Mycroft: montar_pacote_sherlock (não é chamada LLM — é lógica Python)
    # 7. Sherlock: validacao_inicial
    # 8. Mycroft: avaliar_sherlock (APROVADO)
    # 9. Mycroft: fixar_decisao_sherlock
    # 10. Mycroft: consolidar

    sequencia = [
        respostas_llm["mycroft_tasks"],
        respostas_llm["watson_analise_inicial"],
        respostas_llm["mycroft_questionar_watson"],
        respostas_llm["watson_resposta_r1"],
        respostas_llm["mycroft_decisao_watson_aprovado"],
        respostas_llm["sherlock_validacao_inicial"],
        respostas_llm["mycroft_aprovar_sherlock"],
        respostas_llm["mycroft_decisao_sherlock"],
        respostas_llm["mycroft_consolidar"],
    ]

    for resposta in sequencia:
        httpx_mock.add_response(
            url="https://openrouter.ai/api/v1/chat/completions",
            method="POST",
            json=resposta,
        )
```

Cada arquivo em `tests/fixtures/llm_responses/` contém o JSON completo de resposta da API OpenAI-compatible, incluindo campos `choices`, `usage` e `model`. Os conteúdos das respostas são textos Markdown que seguem os templates dos `skills.md` de cada agente — garantindo que o parsing do invocador funcione corretamente.

## **13.6 Fixtures do Módulo Sintético `MOD_SINT_001`**

O módulo sintético em `tests/fixtures/MOD_SINT_001/` é fabricado com inconsistências deliberadas para exercitar os agentes. Inclui:

**`entrega_rfb/planilha_calculo.xlsx`** — planilha com célula de total que não fecha (`D47 = 100` quando a soma das linhas 12–46 é `98`). Detectável por Watson. Severity ATENÇÃO.

**`entrega_rfb/script_extracao.sql`** — script SQL com filtro suspeito (`WHERE ano_competencia = 2023` quando a metodologia especifica `2024`). Detectável por Sherlock como DIVERGÊNCIA.

**`entrega_rfb/notebook_transformacao.ipynb`** — notebook com célula de transformação que aplica fator de correção não documentado (`* 1.02`). Detectável por Watson como ATENÇÃO; Sherlock classifica como ATENDIDO PARCIALMENTE (fator existe na metodologia mas não está documentado no notebook).

**`gt_artefatos/metodologia_mod_sint_001.md`** — versão sintética da metodologia do módulo, com três pontos verificáveis correspondentes às três inconsistências acima.

Essa construção deliberada garante que o módulo sintético force Mycroft a questionar Watson (a célula que não fecha gera alerta) e que Sherlock produza ao menos uma classificação DIVERGÊNCIA — exercitando os caminhos não triviais do sistema.

## **13.7 Execução e Cobertura**

```bash
# Executar toda a suíte
pytest tests/ -v

# Executar apenas unitários (rápido, sem custo)
pytest tests/unit/ -v

# Executar com cobertura
pytest tests/unit/ --cov=src/diogenes --cov-report=term-missing

# Executar teste de integração isolado
pytest tests/integration/test_ciclo_completo.py -v -s
```

**Meta de cobertura por módulo** (conforme `RNF-MANU-04`, mínimo 70% nos componentes não-agente):

| Módulo | Meta |
|---|---|
| `motors/motor_start.py` | ≥ 85% |
| `motors/motor_saida.py` | ≥ 90% |
| `orchestrator/orchestrator.py` | ≥ 75% |
| `orchestrator/stranger_room.py` | ≥ 90% |
| `orchestrator/states.py` | 100% |
| `persistence/audit_index.py` | ≥ 85% |
| `persistence/manifest.py` | ≥ 80% |
| `persistence/workspace.py` | ≥ 85% |
| `llm/openrouter.py` | ≥ 75% |
| `agents/mycroft.py` | ≥ 60% (parsing) |
| `agents/watson.py` | ≥ 60% (parsing) |
| `agents/sherlock.py` | ≥ 60% (parsing) |
| `cli/` | ≥ 65% |

Os invocadores de agentes têm meta reduzida porque a parte mais complexa — construção de prompts e chamadas LLM — é coberta pelo mock de integração, não por unitários de linha.

---

*Bloco 13 encerrado.*

---

# **Bloco 14 — Roadmap de Implementação**

## **14.1 Princípio de Sequenciamento**

O roadmap é estruturado em quatro sprints, cada um com entregável verificável que constitui pré-condição do sprint seguinte. A sequência não é arbitrária — deriva das dependências técnicas reais entre os componentes: persistência precede orquestração, orquestração precede agentes, agentes precisam de mocks antes de LLM real.

A correspondência com as fases do piloto do PRD é direta: Sprint 1 e Sprint 2 constroem a infraestrutura e executam a **Fase A** (modelos free, custo zero); Sprint 3 executa a **Fase B** (benchmarking com modelos baratos); Sprint 4 executa a **Fase D** (MOD_010 com modelos de qualidade de produção). A **Fase C** (estado-alvo Azure Foundry) está fora do piloto e não consta neste roadmap.

Cada sprint tem duração estimada em dias de trabalho efetivo — não em dias corridos. A estimativa assume desenvolvedor único, com disponibilidade parcial, operando sobre uma base de código nova.

## **14.2 Sprint 1 — Fundação (8–10 dias)**

**Objetivo:** repositório configurável, estrutura de filesystem funcionando, Motor de Start completo, `audit_index` operacional, testes unitários dos componentes de persistência passando.

**Tarefas em sequência:**

1. Criar repositório Git com estrutura do Bloco 2, `pyproject.toml` final (item 14.6), `ruff.toml`, `.gitignore`, `.env.example`
2. Implementar `config.py` com leitura dos três arquivos de configuração, validação na inicialização, `lru_cache` e mensagens de erro específicas (Bloco 4.5)
3. Implementar `models.py` — todos os modelos Pydantic do domínio: `CycleManifest`, `InputFileRecord`, `CycleRecord`, `LLMCall`, `LLMResponse`, `AgentSpec`, `DecisaoFinal`, `StrangerRoomFile`, `MotorSaidaReport`, `OcorrenciaDetectada`
4. Implementar `persistence/workspace.py` — `WorkspaceManager` com criação de estrutura e leitura de diretório de ciclo
5. Implementar `persistence/manifest.py` — `ManifestWriter` e leitura de manifesto existente
6. Implementar `persistence/audit_index.py` — escrita atômica, `insert_cycle`, `update_status`, `get_cycle`, `list_cycles`
7. Implementar `motors/motor_start.py` — fluxo completo conforme Bloco 7.4, com todas as exceções de `motors/exceptions.py`
8. Criar `tests/fixtures/MOD_SINT_001/` com os arquivos sintéticos descritos no Bloco 13.6
9. Implementar `tests/unit/test_motor_start.py` e `tests/unit/test_audit_index.py`
10. Implementar `tests/unit/test_manifest.py` e `tests/unit/test_workspace.py`
11. Implementar CLI mínima: subcomandos `start`, `list` e `status` — suficientes para exercitar o Motor de Start manualmente

**Marco verificável:** `pytest tests/unit/ -v` passa com cobertura ≥ 85% nos módulos de persistência. `diogenes start --module MOD_SINT_001 --activity 1` cria o manifesto e o diretório de ciclo corretamente no workspace local. `diogenes list` exibe o ciclo criado com status `PREPARADO`.

## **14.3 Sprint 2 — Orquestração e Agentes com Mock (10–14 dias)**

**Objetivo:** Stranger's Room, Orquestrador, camada LLMClient, invocadores dos três agentes, Motor de Saída, CLI completa, teste de integração end-to-end com mocks de LLM passando. **Ao final deste sprint, a Fase A do piloto pode ser executada.**

**Tarefas em sequência:**

1. Implementar `orchestrator/states.py` — enum `CycleState` e `TRANSICOES_VALIDAS`
2. Implementar `orchestrator/stranger_room.py` — classe `StrangerRoom` completa conforme Bloco 10.4, com todas as exceções de `orchestrator/exceptions.py`
3. Implementar `tests/unit/test_stranger_room.py` — todos os casos do Bloco 13.3
4. Implementar `llm/base.py` — Protocol `LLMClient` e factory `get_llm_client()`
5. Implementar `llm/openrouter.py` — `OpenRouterClient` conforme Bloco 6.4, com trace técnico, retry e exceções de `llm/exceptions.py`
6. Implementar `tests/unit/test_llm_client.py` com `pytest-httpx`
7. Implementar `agents/mycroft.py`, `agents/watson.py`, `agents/sherlock.py` — invocadores com construção de prompt, chamada ao LLMClient, parsing defensivo de output conforme Bloco 9
8. Criar `docs/agentes/mycroft/soul.md`, `skills.md`, `agent.md` — primeira versão, a ser calibrada durante a Fase A
9. Criar `docs/agentes/watson/soul.md`, `skills.md`, `agent.md` — primeira versão
10. Criar `docs/agentes/sherlock/soul.md`, `skills.md`, `agent.md` — primeira versão
11. Criar `tests/fixtures/llm_responses/` — JSONs de resposta predefinidos para o mock
12. Implementar `orchestrator/orchestrator.py` — máquina de estados completa conforme Bloco 8.4
13. Implementar `tests/unit/test_orchestrator.py`
14. Implementar `motors/motor_saida.py` — varredura heurística completa conforme Bloco 11.3
15. Implementar `tests/unit/test_motor_saida.py`
16. Completar CLI com todos os onze subcomandos conforme Bloco 12
17. Implementar `tests/integration/test_ciclo_completo.py` com as duas variantes (ciclo padrão e duas rodadas)
18. `agents_spec.yaml` com modelos Fase A (modelos `:free` do OpenRouter), `runtime.yaml` completo

**Marco verificável:** `pytest tests/ -v` passa integralmente. Cobertura ≥ 70% em todos os componentes não-agente. `diogenes start → confirm-manifest → [execução] → verify-output → seal` funciona de ponta a ponta com mocks de LLM, produzindo ciclo encerrado no `audit_index` com output em `workspace/cycles/{id}/output/`.

**Início da Fase A:** após o marco verificável, executar o ciclo completo com os modelos `:free` do OpenRouter sobre o MOD_SINT_001 real — sem mocks, com chamadas reais à API. Objetivo: validar que a arquitetura funciona com LLM real e calibrar os `soul.md` / `skills.md` dos agentes com base nos outputs obtidos. Custo esperado: zero USD. Iterações de calibração dos arquivos de agentes ocorrem nesta fase — sem alteração de código Python.

**Critério de encerramento da Fase A:** ciclo completo da Atividade 1 sobre MOD_SINT_001 executa três vezes consecutivas sem erro de runtime, com as inconsistências deliberadas do módulo sintético detectadas corretamente por Watson e classificadas corretamente por Sherlock. Corresponde ao primeiro e quinto critério de sucesso do PRD (Bloco 1.2).

## **14.4 Sprint 3 — Benchmarking de Modelos, Fase B (5–8 dias)**

**Objetivo:** executar ciclos com modelos baratos, medir custo e latência, selecionar os modelos definitivos para cada agente para a Fase D. Nenhuma alteração de código — apenas configuração e execução.

**Tarefas em sequência:**

1. Atualizar `agents_spec.yaml`: descomentar modelos Fase B (Kimi K2, Qwen 3 Max, DeepSeek R1 ou equivalentes vigentes), comentar modelos Fase A, atualizar `fase_ativa: B` e `teto_custo_ciclo_usd: 5.00`
2. Executar ciclos de Atividade 1 sobre MOD_SINT_001 com cada combinação de modelos a testar — conforme matriz de benchmarking definida abaixo
3. Registrar, para cada combinação: custo total USD, tokens por agente, latência total do ciclo, qualidade dos achados (avaliação humana de Lestrade)
4. Executar ciclo de Atividade 2 sobre MOD_SINT_001 — criar pacote de resposta simulada da RFB e verificar que o sistema preserva e utiliza o histórico corretamente
5. Selecionar os modelos definitivos para a Fase D com base nos resultados

**Matriz de benchmarking (candidatos por agente):**

| Agente | Candidatos Fase B | Critério de seleção |
|---|---|---|
| Mycroft | Qwen 3 235B, Gemini 2.5 Flash | Qualidade de síntese e crítica estruturada |
| Watson | Kimi K2, Gemini 2.5 Flash | Capacidade de leitura técnica e tradução de código |
| Sherlock | DeepSeek R1, Qwen 3 235B | Raciocínio dedutivo normativo, precisão de classificação |

Cada combinação é executada duas vezes — a segunda execução com a mesma seed base verifica reprodutibilidade. Os traces técnicos em `_runtime/llm_calls/` fornecem os dados brutos de latência, tokens e `system_fingerprint` para análise.

**Marco verificável:** planilha de benchmarking preenchida com resultados de pelo menos seis combinações testadas. Modelos definitivos para a Fase D selecionados e documentados como decisão de design no `agents_spec.yaml` (comentários inline) e no CHANGELOG do repositório.

**Critério de encerramento da Fase B:** ciclo de Atividade 2 executa e produz Relatório Final que referencia explicitamente o histórico do ciclo A1. Corresponde ao terceiro critério de sucesso do PRD. Custo esperado: até USD 30 no total da fase (seis combinações × até USD 5 por ciclo).

## **14.5 Sprint 4 — MOD_010 em Produção Piloto, Fase D (5–7 dias)**

**Objetivo:** executar o sistema sobre material real do MOD_010 (Pessoa Física) — primeiro ciclo do Departamento sobre módulo real da CBS. Validar qualidade analítica, mensurar custo e latência em escala real.

**Pré-condições obrigatórias antes de iniciar:**

1. Material do MOD_010 disponível e organizado em `workspace/input/MOD_010/` com a estrutura esperada pelo Motor de Start — confirmação com o GT Reforma Tributária
2. Modelos Fase D configurados em `agents_spec.yaml` (selecionados no Sprint 3), `teto_custo_ciclo_usd: 10.00`
3. `pip freeze > requirements-lock-fase-d.txt` executado e versionado — ambiente congelado para a Fase D

**Tarefas em sequência:**

1. Verificar completude dos inputs do MOD_010 via `diogenes start --module MOD_010 --activity 1` e inspecionar o manifesto gerado antes de confirmar
2. Confirmar manifesto e executar ciclo completo — Lestrade presente para cada ponto de Human-in-the-Gate
3. Avaliar output da Atividade 1: verificar se Watson detectou as inconsistências esperadas, se Sherlock classificou corretamente os pontos metodológicos conhecidos, se o Relatório Preliminar tem qualidade institucional adequada
4. Iterar sobre `soul.md` / `skills.md` se necessário e re-executar — cada iteração é um novo ciclo, não reexecução do mesmo
5. Documentar custo total, latência, número de tokens por agente no benchmarking de produção
6. Executar Atividade 2 com pacote de resposta simulado para validar que o fluxo completo de revalidação funciona sobre material real

**Marco verificável — e critério de conclusão do piloto:** Relatório Preliminar de Análise do MOD_010 produzido, avaliação humana positiva confirmando que o relatório tem utilidade técnica real — inconsistências encontradas, fundamentação metodológica coerente, linguagem institucional e impessoal. Corresponde ao quinto critério de sucesso do PRD (Bloco 1.2). Custo esperado: USD 10–25 para a Fase D completa.

## **14.6 `pyproject.toml` Final Consolidado**

Versão final com as duas correções retroativas identificadas ao longo do SDD: `pytest-httpx` no lugar de `responses` (Bloco 6.9) e `pdfminer.six` como dependência de runtime (Bloco 9.6).

```toml
[build-system]
requires = ["setuptools>=70", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "diogenes"
version = "0.1.0"
description = "Departamento de Validação Assistida da CBS — Piloto Local"
requires-python = ">=3.11"
readme = "README.md"
license = { text = "Uso Interno Restrito — TCU/SecexContas" }

dependencies = [
    "openai>=1.30,<2.0",             # cliente LLM OpenAI-compatible
    "pydantic>=2.5,<3.0",            # validação de dados e modelos de domínio
    "typer>=0.12,<1.0",              # CLI baseada em type hints
    "rich>=13.0,<14.0",              # formatação de console com cores semânticas
    "python-dotenv>=1.0,<2.0",       # carregamento de .env
    "pyyaml>=6.0,<7.0",              # parsing de agents_spec.yaml e runtime.yaml
    "python-frontmatter>=1.1,<2.0",  # arquivos Markdown com frontmatter YAML
    "openpyxl>=3.1,<4.0",            # leitura de planilhas Excel da RFB
    "sqlparse>=0.5,<1.0",            # parsing e formatação de scripts SQL
    "nbformat>=5.9,<6.0",            # leitura de notebooks Jupyter
    "pdfminer.six>=20221105",        # extração de texto de PDFs (adicionado Bloco 9)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-cov>=5.0,<6.0",
    "pytest-httpx>=0.30,<1.0",       # mock de chamadas HTTP (substituiu responses — Bloco 6)
    "ruff>=0.4,<1.0",
    "mypy>=1.10,<2.0",
]

[project.scripts]
diogenes = "diogenes.cli.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]  # linha longa — controlada por formatter

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

## **14.7 Caminho de Migração para Azure AI Foundry**

A migração para produção em Azure AI Foundry, quando aprovada pelo Departamento de TI e pela Auditoria Interna do TCU, requer exatamente seis passos:

1. **Implementar `llm/azure_foundry.py`** — substituir o `NotImplementedError` pela implementação real do `AzureFoundryClient`, usando o mesmo `openai` SDK com `base_url` apontando para o endpoint do Foundry e autenticação via Managed Identity (`azure-identity` adicionado como dependência de runtime neste momento)

2. **Configurar `.env` no ambiente Azure** — `DIOGENES_ENV=azure`, `DIOGENES_LLM_BASE_URL` com o endpoint do Foundry, `DIOGENES_LLM_API_KEY` com o token da Managed Identity ou Service Principal

3. **Atualizar `agents_spec.yaml`** — modelos no formato do Azure (`gpt-4o` em vez de `openai/gpt-4o`), parâmetros de custo via Azure Cost Management

4. **Migrar o workspace** — copiar `workspace/` do ambiente local para o volume montado no Azure, preservando `audit_index.csv` e todos os diretórios de ciclo intactos

5. **Executar teste de integração no novo ambiente** — `pytest tests/integration/` com a configuração Azure, verificando que o `AzureFoundryClient` satisfaz o Protocol `LLMClient` e que o ciclo end-to-end funciona

6. **Implementar controles de produção** — anonimização de dados sob sigilo fiscal antes da ingestão pelos agentes, política de retenção de traces técnicos, isolamento de tenancy conforme exigências de segurança do TCU

O código de aplicação — Orquestrador, agentes, motores, CLI — não muda em nenhum aspecto. A portabilidade declarada no Bloco 1.7 é realizada integralmente.

## **14.8 Sumário do SDD**

O SDD está completo. A tabela abaixo registra o que cada bloco especifica e o artefato principal que produz para o desenvolvedor.

| Bloco | Título | Artefato principal para o desenvolvedor |
|---|---|---|
| 1 | Visão Geral da Arquitetura | Quatro decisões fundadoras, diagrama de componentes, tabela de responsabilidades |
| 2 | Estrutura de Repositório | Árvore completa do repositório, responsabilidade de cada módulo, rastreabilidade requisito → módulo |
| 3 | Stack e Dependências | `pyproject.toml` base com onze dependências justificadas, política de atualização |
| 4 | Configuração | `.env.example`, `agents_spec.yaml` completo, `runtime.yaml` completo, esboço de `config.py` |
| 5 | Filesystem (Workspace) | Árvore do workspace, spec do `manifest.md`, spec do frontmatter da Stranger's Room, spec do `audit_index.csv`, spec dos traces técnicos |
| 6 | LLMClient | Protocol `LLMClient`, `OpenRouterClient` com retry e trace, cálculo de seed, `AzureFoundryClient` stub |
| 7 | Motor de Start | Classe `MotorStart` completa, `WorkspaceManager`, saída no console, exceções |
| 8 | Orquestrador | Enum `CycleState`, `TRANSICOES_VALIDAS`, diagrama de estados, classe `Orchestrator`, gestão de alertas críticos |
| 9 | Agentes | Cinco tipos de chamada de Mycroft, três de Watson, três de Sherlock, templates de output, estratégia de parsing defensivo |
| 10 | Stranger's Room | Classe `StrangerRoom` completa, protocolo de escrita imutável, verificação de integridade, leitura para retomada |
| 11 | Motor de Saída | Classe `MotorSaida` com quatro categorias de varredura, `MotorSaidaReport`, quatro decisões de Lestrade |
| 12 | CLI | Onze subcomandos especificados com parâmetros, pré-condições e saídas, `display.py`, tabela de mapeamento |
| 13 | Testes | `conftest.py`, testes unitários por componente, teste de integração end-to-end, mock com `pytest-httpx`, fixtures do MOD_SINT_001 |
| 14 | Roadmap | Quatro sprints com tarefas e marcos verificáveis, `pyproject.toml` final, caminho de migração para Azure |

---

*SDD — Piloto Diógenes Local, versão 0.1 — concluído.*

DVA-CBS | Projeto Diógenes | TC 015.848/2025-6
Tribunal de Contas da União | Secretaria de Controle Externo de Contas
Documento interno de trabalho | Uso restrito
