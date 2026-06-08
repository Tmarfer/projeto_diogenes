# Especificação do Projeto Diógenes
## DVA-CBS | TC 015.848/2025-6 | SecexContas / TCU
**Versão:** 0.1.0 · **Atualizado:** 2026-06-06 · **Uso Interno Restrito**

---

## 1. Finalidade e Contexto

O Projeto Diógenes é um sistema agêntico de validação da **alíquota de referência da CBS** (Contribuição sobre Bens e Serviços), instituída pela LC 214/2025 e sujeita a homologação pelo TCU via Acórdão 2833/2025-Plenário.

O sistema apoia a instrução do processo **TC 015.848/2025-6** no âmbito da **DVA-CBS** (Divisão de Validação da Alíquota CBS). Executa auditorias técnicas e metodológicas sobre os módulos do pacote de dados entregue pela RFB, gerando relatórios estruturados para chancela do auditor responsável (Lestrade).

**Anos-base homologados:** 2023 e 2024 (alterados pela RFB por indisponibilidade da ECF de 2025).

---

## 2. Agentes — Papéis e Responsabilidades

O sistema tem quatro agentes e um papel humano. Cada agente possui arquivos de definição em `docs/agentes/{agente}/`:

| Arquivo | Conteúdo |
|---------|----------|
| `soul.md` | Identidade, valores e limites constitucionais |
| `skills.md` | Templates de output, critérios de classificação, formatos de seção |
| `heartbeat.md` | Protocolo operacional por `call_type` — injetado no `user_prompt` |
| `agent.md` | Parâmetros de runtime (modelos e valores reais vêm de `agents_spec.yaml`) |

**Os arquivos são lidos do filesystem a cada chamada — editar Markdown tem efeito imediato sem reinicialização.**

---

### 2.1 Irene Adler — Catalogadora Semântica

**Tipo:** Biblioteca Python (pipeline C1–C5, com LLM no estágio C4)
**Módulo:** `irene.py`, `irene_chattcu.py`
**Docs:** `docs/agentes/irene/`

**Responsabilidade:** Catalogação semântica dos arquivos XLSX/CSV do pacote de entrada antes que Watson os analise. Produz um catálogo estruturado que orienta a análise de integridade.

**Pipeline C1–C5:**
- **C1** — Inventário: lista e classifica todos os arquivos do pacote
- **C2** — Estrutura: identifica abas, colunas e tipos de dado
- **C3** — Qualidade superficial: detecta células vazias, formatação inconsistente
- **C4** — Semântica via LLM: nomeia e descreve o conteúdo de cada aba/coluna em linguagem de domínio tributário
- **C5** — Score consolidado: agrega C1-C4 em índice de confiança do catálogo

**Condição de execução:** Controlada por `DIOGENES_IRENE_HABILITADO=true` no `.env`. Irene é **dispensada** se um catálogo com versão `≥ VERSAO_IRENE_MINIMA` já existir para o módulo — evita reprocessamento em reexecuções.

**Falha:** `IRENE_BLOQUEADO` (catálogo com ressalvas) não é fatal — Watson recebe o catálogo com alerta. `IRENE_ERRO_FATAL` aborta o ciclo.

#### Pipeline C1–C5 — detalhamento

| Componente | Função | Artefato produzido |
|------------|--------|-------------------|
| C1 — Manifesto | Valida existência e integridade SHA-256 dos arquivos | Interrompe se arquivo ausente |
| C2 — Profiling | Mapeia estrutura de cada aba XLSX (fórmulas, vínculos externos, totalizadores) | Mapa estrutural |
| C3 — Amostragem | Verifica fidedignidade XLSX ↔ CSV dentro de tolerância 1e-6 | Taxa de fidedignidade por aba |
| C4 — Semântica | Classifica papel de cada aba via LLM (apenas metadados estruturais, sem dados fiscais) | `irene_catalog.yaml` |
| C5 — Artefatos | Consolida e emite recomendação ponderada | Score e recomendação final |

**Sistema de classificação de abas (11 papéis reconhecidos):** `resultado_final`, `resultado_intermediario`, `base_bruta`, `base_classificada`, `base_tratada`, `memoria_de_calculo`, `validacao_comparativa`, `tabela_mapeamento`, `matriz_parametrica`, `aba_auxiliar`, `nao_classificado`

**Thresholds de recomendação:**

| Resultado | Critério |
|-----------|----------|
| `IRENE_APROVADO` | Score ≥ 0,95 |
| `IRENE_ALERTA` | 0,65 ≤ score < 0,95 |
| `IRENE_BLOQUEADO` | Score < 0,65 **ou** falha em aba `resultado_final` |

**Protocolo de Mycroft ao acionar Irene (`acionar_irene` — 5 passos):**
1. Verificar catálogo existente — existe `irene_catalog.yaml` com `versao_irene ≥ VERSAO_IRENE_MINIMA`? Se sim: `CATALOGO_REUTILIZADO`, não executa novamente.
2. Derivar manifesto — constrói `irene_manifesto.yaml` a partir do manifesto do ciclo.
3. Acionar Irene — chama `executar_irene(caminho_manifesto)`, registra timestamp.
4. Avaliar retorno — `APROVADO` → Watson sem ressalvas; `ALERTA` → Watson com flag; `BLOQUEADO` → Lestrade notificado; `ERRO_FATAL` → `ABORTADO_FALHA_AGENTE`.
5. Incorporar catálogo — `irene_catalog.yaml` entra no `MC_tasks_watson.md`; Mycroft prioriza tasks na ordem: `resultado_final` → `resultado_intermediario` → demais.

#### Comportamento e perfil

**Identidade:** Irene é a única agente sem ciclo de revisão por Mycroft. Retorna um estado (`APROVADO/ALERTA/BLOQUEADO/ERRO_FATAL`) e o sistema decide. Não há Stranger Room para Irene. Sua autoridade é a do fato consumado: *"Você não se apresenta, não explica seu trabalho além do necessário, e não negocia seu protocolo. Você executa."*

**Autoridade não negociável:** O `irene_catalog.yaml` é o "contrato que Irene firma com Watson" — não orientativo, mas ponto de partida obrigatório. Watson não pode ignorar ou reinterpretar a classificação de Irene.

**Risco latente:** Se Irene classificar erroneamente uma aba (ex.: `resultado_intermediario` como `aba_auxiliar`), Watson pode sub-analisar aquela aba por seguir a priorização de Mycroft. Não existe mecanismo de correção retroativa dentro do ciclo.

**Separação limpa de dados sigilosos:** C4 envia apenas metadados estruturais ao LLM — classificação semântica sem ver o conteúdo real. Conforme para ChatTCU, mas dependente puramente de estrutura (dimensões, fórmulas, tipo de dado predominante).

---

### 2.2 Watson — Auditor de Integridade Técnica

**Tipo:** LLM (ChatTCU, modelo configurado em `agents_spec.yaml`)
**Módulo:** `agents/watson.py`
**Docs:** `docs/agentes/watson/`
**Dono dos motores:** `motor_perfilamento.py` (pré-análise determinística)

**Responsabilidade:** Verificar a integridade técnica de cada arquivo do pacote — consistência de dados, unicidade de chaves, conformidade de fórmulas, validade de scripts e planilhas.

**Call_types (heartbeat):**

| `call_type` | Quando | Descrição |
|-------------|--------|-----------|
| `analise_arquivo` | Por arquivo | Analisa um arquivo individualmente; usa perfil estatístico do `motor_perfilamento` + amostra truncada |
| `consolidar_watson` | Após todos os arquivos | Consolida as análises individuais em `watson_consolidado.md` |
| `validacao_planilha_rn` | Condicional | Só se a Planilha de Verificação estiver no manifesto |

**IDs de alerta:** `W{codigo_modulo}-{n:03d}` (ex: `W010-001`). O contador acumula entre todas as chamadas de Watson do ciclo.

**Campo de controle de fluxo:** `Nota metodológica com alteração detectada: Sim/Não` no `watson_consolidado.md` — propagado por Mycroft para o pacote Sherlock.

#### Fases de execução

| Fase | Call Type | Entrada | Saída |
|------|-----------|---------|-------|
| Análise isolada por arquivo | `analise_arquivo` | Arquivo individual + contexto do módulo | `watson_analise_{arquivo}.md` |
| Consolidação cross-file | `consolidar_watson` | Todos os `watson_analise_*.md` | `watson_consolidado.md` |
| Planilha de Verificação (condicional) | `validacao_planilha_rn` | Planilha + análises anteriores | `watson_planilha_rn.md` |
| Stranger Room — rodada 1 | `resposta_r1` | Crítica de Mycroft + output anterior | Posição corrigida ou sustentada |
| Stranger Room — rodada 2 | `resposta_r2` | Crítica de Mycroft + posição R1 | Posição final (Mycroft bate martelo) |

#### Escala de severidade

| Nível | Critério |
|-------|----------|
| `CRITICA` | Falha estrutural que invalida o resultado agregado do módulo |
| `ALTA` | Inconsistência com impacto material no resultado |
| `MEDIA` | Inconsistência com impacto de menor relevância |
| `BAIXA` | Desvio de arredondamento ou precisão numérica |

**Regra crítica de cabeçalho:** O campo `**Alertas CRITICA:** N` no cabeçalho deve ser um inteiro literal — não prosa. O Orquestrador faz parse desse campo para decisões de fluxo (comunicação a Lestrade, propagação a Sherlock).

**7 varreduras mandatórias por arquivo:** metadados, consistência numérica (com cálculo amostral), análise de script/código, análise de fórmulas, cadeia de produção, insights analíticos, rastreabilidade da cadeia.

#### Comportamento e perfil

**Identidade:** *"Você não tem o lado emocional e sentimental do Watson literário. Não há concessão por dificuldade técnica declarada, não há tolerância afetiva com inconsistência. O dado fecha ou não fecha."* — Cinco valores operativos: precisão antes de velocidade, completude antes de elegância, neutralidade descritiva, severidade calibrada, rastreabilidade absoluta.

**Papel de "primeiro olhar":** Watson entra nos documentos sem saber o que Sherlock vai verificar. O que Watson encontra condiciona o que Sherlock pode classificar — mas eles não conversam diretamente.

**Tensão estrutural — insight analítico vs. divergência metodológica:** Watson deve registrar desvios metodológicos percebidos como "insight analítico" sem classificá-los. O julgamento sobre quando algo é "desvio que parece metodológico" vs. "inconsistência estrutural" pertence a Watson, mas a responsabilidade pela classificação formal pertence a Sherlock.

**Sinalização CRITICA com consequência de fluxo:** Quando Watson registra alerta `CRITICA`, o Orquestrador aciona `MC_alerta_critico_lestrade.md` e Lestrade pode intervir — a decisão de severidade de Watson é uma decisão com consequência de fluxo, não apenas de relatório.

**Nota metodológica com alteração:** Se Watson sinaliza essa ocorrência no cabeçalho do consolidado, Mycroft propaga para Sherlock e todo o ciclo de verificação de Sherlock é ajustado. Watson é o gatilho de uma mudança sistêmica que ele próprio não processa.

**Dois registros paralelos:** Output formal (terceira pessoa) + trace interno opcional (primeira pessoa, expõe o raciocínio que o template não comporta). Mycroft solicita o trace quando questiona uma classificação específica.

**Segurança ChatTCU:** Mascaramento de PII obrigatório em todos os outputs. CPFs, CNPJs e chaves NF-e devem aparecer mascarados. Não se copiam linhas de dados brutos — descreve-se a localização e o desvio analiticamente.

---

### 2.3 Sherlock Holmes — Auditor de Validação Metodológica

**Tipo:** LLM (ChatTCU, modelo configurado em `agents_spec.yaml`)
**Módulo:** `agents/sherlock.py`
**Docs:** `docs/agentes/sherlock/`

**Responsabilidade:** Validar a aderência metodológica do módulo ao Acórdão 2833/2025-Plenário e à LC 214/2025 — análise normativa, classificação de ocorrências, avaliação do impacto entre módulos.

**Call_types (heartbeat):**

| `call_type` | Quando | Descrição |
|-------------|--------|-----------|
| `verificar_ponto` | Por ponto | Verifica um ponto do Apêndice mapeado por Mycroft |
| `validacao_planilha_rn_sherlock` | Condicional | Só se a Planilha de Verificação estiver no manifesto |
| `consolidar_sherlock` | Final | Produz `sherlock_consolidado.md` com 11 seções obrigatórias (10.1–10.11) + JSON de ocorrências (seção 11) |

**Completude obrigatória:** O Orquestrador verifica as 11 seções antes de acionar `Mycroft.consolidar()`. Se alguma estiver ausente, o ciclo entra em `AGUARDANDO_COMPLETUDE` e Lestrade é notificado.

#### Sistema de classificação (6 categorias)

| Código | Critério |
|--------|----------|
| `ATENDIDO` | Conformidade plena. Verificação conclusiva. |
| `ATENDIDO_PARCIALMENTE` | Conformidade com lacunas ou desvios de menor relevância. |
| `DIVERGENCIA` | Desvio objetivo. Exige localização precisa + referência ao dispositivo normativo. |
| `ATENCAO` | Verificado sem divergência clara, mas requer acompanhamento. |
| `LIMITACAO` | Dado existe mas acesso é condicionado (resolvível na Sala de Sigilo). |
| `NAO_VERIFICAVEL` | Documentação interna insuficiente. Requer contraditório com a RFB. |

**Hierarquia:** quando um ponto admite mais de uma classificação, adota-se a mais severa. `DIVERGENCIA` > `ATENDIDO_PARCIALMENTE`. `ATENCAO` não substitui `DIVERGENCIA`.

**Distinção crítica:** `LIMITACAO` é restrição externa (resolvível com acesso à Sala de Sigilo). `NAO_VERIFICAVEL` é documentação interna insuficiente (requer contraditório). A confusão entre os dois distorce o encaminhamento ao GT.

#### Formato de citação obrigatório (sem citação = output inválido)

```
[Acórdão 2833/2025 | Apêndice {romano} | Módulo {n} | Seção {x} | Item {y}]
[LC 214/2025 | Art. {n}]
[EC 132/2023 | Art. {n}]
[Premissa Global | {nome da premissa}]
```

#### Premissas globais obrigatórias em todo ponto verificado

- Alteração dos anos-base: **2023 e 2024** (não 2024/2025 como original)
- Critério de equivalência: mesmas premissas + mesmos caminhos = resultados equivalentes
- Notas metodológicas com alteração: tratadas com prioridade antes dos pontos individuais

#### Protocolo de call_types

**`validacao_inicial` (modo monolítico — padrão atual):** Verifica todos os pontos em uma única chamada LLM. Protocolo de 7 passos: verificar premissas globais → ler metodologia ponto a ponto → ler análise Watson → verificar correspondência → classificar → verificar Art. 7 (não reanalisar pacote) → verificar Art. 14 (terceira pessoa). Adotado em 2026-06-03 para corrigir o problema NV-GLOBAL-01 (confusão de heartbeat).

**`verificar_ponto` (modo isolado — legado, alternativa):** Cada ponto em contexto próprio e isolado. Contexto fecha ao terminar — não contamina verificações anteriores.

**`validacao_planilha_rn_sherlock` (condicional):** Perspectiva metodológica sobre a Planilha de Verificação já preenchida por Watson. Divergência Watson × Sherlock → encaminhada à Stranger Room de Mycroft para deliberação.

**`consolidar_sherlock`:** Produz Relatório Estruturado (11 seções), JSON de ocorrências para dashboard, e duas análises sistêmicas obrigatórias: `analise_impacto_entre_modulos` (sobreposições/lacunas com módulos satélites) e `identificacao_pendencias_para_simulador_completo` (pontos verificáveis somente quando todos os 17 módulos estiverem integrados).

**Mapeamento JSON → dashboard:** `DIVERGENCIA` alto → `CRITICO`; `DIVERGENCIA` médio/baixo → `ALERTA`; `ATENCAO` → `ATENCAO`; `NAO_VERIFICAVEL` → `ALERTA`.

#### Comportamento e perfil

**Identidade:** *"Cada divergência que você deixar passar é uma divergência que o Tribunal chancelará. Cada classificação imprecisa é uma imprecisão no fundamento do Acórdão."* — Rigor científico com citação rastreável. Descarta: ironia, tom condescendente, melancolia.

**Responsabilidade terminal:** O output de Sherlock — o Relatório Estruturado — é o documento que Lestrade levará ao GT. Nenhum outro agente tem essa responsabilidade de entrega externa. As classificações de Sherlock são consequências institucionais, não apenas técnicas.

**Isolamento deliberado:** Sherlock não sabe o que aconteceu antes de Watson. Recebe o pacote integrado e começa do zero. Garante que Sherlock trabalhe sobre um pacote saneado sem influência de parcialidade anterior — mas cria dependência total na completude do output de Watson.

**Tensão — classificar sem ver os dados:** Sherlock parte do pressuposto (Artigo 7) de que Watson saneou os arquivos. Trabalha sobre o que Watson documentou. Se Watson sub-analisou um arquivo, o buraco não aparece — Sherlock classifica `NAO_VERIFICAVEL` ou, pior, `ATENDIDO`, porque não há evidência de desvio no pacote.

**Postura ante dilemas:** Interpretação com duas leituras possíveis → adota uma e justifica (com registro da alternativa descartada). Dilema genuinamente equilibrado → registra precisamente e escala para Mycroft. Resultado correto por caminho metodológico divergente → `DIVERGENCIA` (não `ATENDIDO_PARCIALMENTE`).

---

### 2.4 Mycroft Holmes — Auditor Chefe / Orquestrador LLM

**Tipo:** LLM (ChatTCU, modelo configurado em `agents_spec.yaml`)
**Módulo:** `agents/mycroft.py` (grafia do SDD: `MycrooftAgent`)
**Docs:** `docs/agentes/mycroft/`
**Dono dos motores:** `motor_entrega.py` (localização de dados + QA da entrega)

**Responsabilidade:** Coordenação inteligente do ciclo — define as tarefas de Watson, revisa os outputs de Watson e Sherlock via Stranger Room (até 2 rodadas), monta o pacote para Sherlock, consolida o relatório final e supervisiona a Fase de Entrega.

**Call_types (heartbeat):**

| `call_type` | Quando | Descrição |
|-------------|--------|-----------|
| `definir_tasks_watson` | Antes de Watson | Define premissas globais e o escopo de análise |
| `avaliar_agente` | Após Watson e Sherlock | Emite `QUESTIONAR` ou `APROVADO` — aciona Stranger Room |
| `fixar_decisao` | 2ª rodada (se houver) | Fixa decisão final após revisão |
| `montar_pacote_sherlock` | Antes de Sherlock | Consolida outputs de Watson e monta o briefing para Sherlock |
| `mapear_pontos` | Antes de Sherlock | Mapeia pontos do Apêndice aos arquivos Watson relevantes |
| `consolidar` | Final | Gera `MC_consolidado.md` e `relatorio_preliminar_{id}.md` |
| `mapear_dados_modulo` | Fase Entrega | Localiza dados na planilha para mapa de extração (sem transcrever valores) |
| `redigir_apendice` | Fase Entrega | Reorganiza consolidado validado no formato do Apêndice |
| `avaliar_entrega` | Fase Entrega | QA de aderência dos artefatos gerados (`APROVADO` \| `REQUER_AJUSTE`) |

#### Call_types — artefatos produzidos

| Call Type | Função | Arquivo produzido |
|-----------|--------|-------------------|
| `definir_tasks_watson` | Converte demanda de Lestrade em tasks ordenadas | `MC_tasks_watson.md` |
| `mapear_pontos` | Mapeia pontos do Apêndice aos arquivos Watson relevantes | `MC_mapa_pontos.md` |
| `avaliar_agente` | Revisa output (`APROVADO` \| `CRITICA`) | `MC_avaliacao_{agente}_r{n}.md` |
| `fixar_decisao` | Martelo após 2ª rodada (`ACATADO` \| `FIXADO POR MYCROFT`) | `MC_decisao_{agente}.md` |
| `montar_pacote_sherlock` | Síntese integrada de Watson para Sherlock | `MC_pacote_sherlock.md` |
| `consolidar` | Integra Sherlock, verifica completude, produz output final | `MC_consolidado.md` |

#### Lógica de branching do `avaliar_agente`

```
APROVADO + Watson + alertas críticos > 0  →  notificar Lestrade → montar_pacote_sherlock
APROVADO + Watson + alertas críticos = 0  →  montar_pacote_sherlock direto
APROVADO + Sherlock                       →  consolidar
CRITICA + rodada 0                        →  acionar resposta_r1 → nova avaliação r1
CRITICA + rodada 1                        →  acionar resposta_r2 → fixar_decisao (martelo)
```

**Regra absoluta de crítica:** Uma crítica por chamada de `avaliar_agente`, com localização precisa. "O relatório está incompleto" não é crítica válida. Exemplo válido: *"O alerta W003 está classificado como ALTA, mas o critério define CRITICA para inconsistência numérica que invalida o resultado agregado."*

#### Comportamento e perfil

**Identidade:** *"Você não é o agente que executa: você é o agente que garante que a execução ocorra na ordem certa, com os inputs certos, e que os resultados estejam fundamentados antes de seguir adiante."*

**Autoridade baseada no output, não no dado:** Mycroft não pode verificar independentemente se Watson está certo — avalia o raciocínio apresentado. Se o output de Watson for obscuro ao ponto de Mycroft não conseguir avaliá-lo sem ir aos documentos fonte, a crítica é exatamente essa: *"a fundamentação não é rastreável a partir do que foi apresentado."*

**O martelo como evento raro mas inevitável:** `fixar_decisao` com `FIXADO POR MYCROFT` é a assunção explícita de responsabilidade. Mycroft registra o raciocínio completo e assume que pode estar errado — mas o ciclo não pode parar (Art. 8: máximo de 2 rodadas).

**Intermediário obrigatório:** Mycroft é o único canal entre Watson e Sherlock. Sherlock não sabe o que Watson "suspeitou" — apenas o que Mycroft incluiu no pacote. Isso impede contaminação direta mas cria dependência total na qualidade da síntese de Mycroft.

**Ponto único de controle com visão sistêmica:** Único agente que conhece o estado global do ciclo — o catálogo de Irene, os alertas de Watson, os dilemas de Sherlock, a posição de Lestrade. Único capaz de detectar inconsistências sistêmicas entre fases.

**Premissas globais:** Mycroft injeta as premissas globais do projeto no `MC_tasks_watson.md`, garantindo que Watson as receba independentemente do manifesto — ponto de garantia de consistência do ciclo.

---

### 2.5 Lestrade — Auditor Humano (Papel, não agente de software)

**Responsabilidade:** Supervisor do ciclo. Confirma o manifesto, autoriza progressões críticas (alertas CRITICA de Watson), chancelaria final do relatório (`diogenes seal`).

**Dono dos motores:** `motor_start.py` (protocolo de intake do pacote) e `motor_saida.py` (portão de sanitização antes da chancela).

**Interações no ciclo:**
- `diogenes start` / `confirm-manifest` — aceita o manifesto gerado pelo Motor de Start
- `diogenes proceed` — autoriza progressão após alerta crítico de Watson
- `diogenes pause` / `resume` — controle de execução
- `diogenes verify-output` — aciona o Motor de Saída
- `diogenes seal` — chancela final que grava `ENCERRADO_CHANCELADO`

---

## 3. Motores — Inventário Completo com Agente Responsável

Os motores são **determinísticos** (sem LLM). Cada um pertence a um agente que define o domínio da operação — o motor executa a parte computacional do trabalho do agente sem custo de LLM.

---

### 3.1 `motor_start.py` — Motor de Start

**Agente responsável: Lestrade**
**Módulo:** `motors/motor_start.py`
**Acionado por:** `diogenes start` → `diogenes confirm-manifest`
**Referência normativa:** RF-MS-01 a RF-MS-09 (PRD), Bloco 7 (SDD)

**O que faz:**
- Valida que o diretório de input existe e não está vazio
- Calcula SHA-256 de cada arquivo do pacote (`_sha256_file`)
- Calcula hash do pacote completo (`_sha256_package`) para rastreabilidade
- Cria a estrutura de diretórios do ciclo em `workspace/cycles/{cycle_id}/`
- **Copia** os arquivos para `inputs/` sem alterar os originais (Art. 13)
- Verifica integridade da cópia (hash pós-cópia deve ser igual ao original)
- Para **Atividade 2**: valida a existência de um ciclo A1 `ENCERRADO_CHANCELADO` e copia artefatos históricos para `_historico/`
- Grava `manifest.md` e o registro inicial no `audit_index.csv`

**Saídas:**
- `workspace/cycles/{cycle_id}/inputs/` — cópias imutáveis dos arquivos
- `workspace/cycles/{cycle_id}/manifest.md` — inventário do pacote
- `audit_index.csv` — registro `PREPARADO` do ciclo

---

### 3.2 `motor_perfilamento.py` — Motor de Perfilamento Estatístico

**Agente responsável: Watson**
**Módulo:** `motors/motor_perfilamento.py`
**Acionado por:** Orquestrador — imediatamente após `motor_start`, antes de Irene e Watson LLM
**Dependências:** `duckdb>=1.0,<2.0`, `openpyxl`

**Papel no domínio de Watson:** Watson é o Auditor de Integridade Técnica. O motor computa os **fatos determinísticos de integridade** (row_count, unicidade de chave, null_pct) que Watson usaria para avaliar — mas que não consegue verificar corretamente a partir de amostras truncadas em arquivos com 50k+ linhas. O motor é a metade determinística do trabalho de Watson; o LLM é a metade de raciocínio.

**O que faz:**
- **CSV** → DuckDB `read_csv` nativo: row_count completo, por coluna: null_rate, distinct_count, min/max, unicidade em colunas-chave candidatas
- **XLSX** → `openpyxl` `read_only=True`: stats manuais por coluna, todas as abas (até `_XLSX_MAX_ROWS = 100.000` linhas)
- Detecta colunas-chave por palavras-chave: `cpf`, `cnpj`, `id`, `chave`, `codigo`, `matricula`, `nfe`, `nota_fiscal`, `contrato`, `protocolo`, `seq`
- Emite alertas: `DUPLICATA_CHAVE` (CRITICA, limiar `_UNICIDADE_MINIMA = 0.9990`), `NULOS_SIGNIFICATIVOS` (ALTA ≥ 20%, MEDIA ≥ 5%)
- Detecta colunas compartilhadas entre arquivos (candidatas a join/relação) — `perfil_pacote.yaml`

**Saídas:**
- `_runtime/perfis/{safe_filename}.perfil.yaml` — por arquivo analisável
- `_runtime/perfis/perfil_pacote.yaml` — colunas compartilhadas cross-file

**Integração com Watson LLM:**
- `file_prep.preparar_arquivo(path, perfil_dir)` injeta o bloco `[PERFIL ANALÍTICO — {nome}]` antes da amostra truncada no prompt de Watson
- `watson.analisar_arquivo(perfis_dir=...)` repassa o diretório de perfis ao `file_prep`

**Comportamento:** Best-effort absoluto — erro em arquivo individual é logado e ignorado; falha total do motor não aborta o ciclo.

---

### 3.3 `motor_saida.py` — Motor de Saída

**Agente responsável: Lestrade**
**Módulo:** `motors/motor_saida.py`
**Acionado por:** `diogenes verify-output`
**Referência normativa:** RF-MV-01 a RF-MV-06 (PRD), Bloco 11 (SDD), Art. 14–15

**Papel no domínio de Lestrade:** É o portão de qualidade antes da chancela de Lestrade. Garante que nenhuma marca interna do Departamento (nomes de agentes, cargos identificadores, estruturas internas, cycle_ids) escape para o relatório externo. Lestrade decide se chancela o relatório limpo.

**O que faz — 4 categorias de varredura:**
1. **NOME_AGENTE** — nomes dos agentes (Watson, Sherlock, Mycroft, Irene) detectados no texto
2. **CARGO_IDENTIFICADOR** — expressões regulares de cargos em contexto identificador
3. **ESTRUTURA_INTERNA** — referências a estruturas internas ("Stranger Room", "Projeto Diógenes")
4. **CYCLE_ID** — `cycle_id` no corpo do documento (legítimo apenas no rodapé)

**Sanitização automática (Art. 15) — 5 etapas:**
1. Remove tags `<!-- SECAO: ... -->`
2. Remove linha de metadado "Arquivos que compõem este consolidado"
3. Remove referências `[arquivo_interno.md]` em notação de colchetes
4. Aplica substituições de nomes por linguagem institucional (configuradas em `runtime.yaml`)
5. Remove linha de assinatura do Auditor Chefe

**Saídas:** `MotorSaidaReport` com contagem de ocorrências + hash do documento. Se limpo, avança para `AGUARDANDO_CHANCELA_LESTRADE`.

---

### 3.4 `motor_entrega.py` — Motor de Entrega

**Agente responsável: Mycroft**
**Módulo:** `motors/motor_entrega.py`
**Acionado por:** `diogenes deliver` (explícito) ou ao final do `diogenes autorun`
**Dependências:** `python-docx`, `matplotlib`, `playwright` (+ `playwright install chromium` para PDF/PNG)
**Referência:** `delivery/MAPA_EXTRACAO.md` (esquema do mapa de extração)

**Papel no domínio de Mycroft:** Mycroft supervisiona a Fase de Entrega: localiza os dados via LLM (`mapear_dados_modulo`), o motor gera os artefatos deterministicamente, Mycroft faz o QA de aderência (`avaliar_entrega`). O motor é a geração; Mycroft é o planejamento e a avaliação.

**O que faz — 6 artefatos gerados em `output/entrega/`:**
1. **`Dashboard.html`** — painel interativo de ocorrências e métricas do módulo
2. **`Apendice_Modulo{N}.docx`** — apêndice institucional com ocorrências formatadas
3. **`Relatorio_Narrativo_Modulo{N}.docx`** — narrativa de análise para o relatório TCU
4. **`Relatorio_Consolidado_Modulo{N}.docx`** — consolidado estruturado completo
5. **`Relatorio_Pre_Atendimento_Modulo{N}.docx`** — encaminhamento à RFB (condicional: só se `ata_rfb_markdown` presente)
6. **`ficha_sintese_modulo{N}.{html,pdf,png}`** — ficha síntese executiva (PDF/PNG via Playwright)

**Comportamento:** Cada artefato gerado em `try/except` isolado — a falha de um não derruba os demais. Registra aviso em `entrega_manifesto.json`.

**Sequência completa da Fase de Entrega (orquestrada por `orchestrator/entrega.py`):**
```
Mycroft.mapear_dados_modulo()   → output/entrega_mapa_extracao.json   [LLM]
Mycroft.redigir_apendice()      → output/apendice_conteudo.json        [LLM]
MotorEntrega.gerar()            → output/entrega/*                     [determinístico]
Mycroft.avaliar_entrega()       → veredito APROVADO | REQUER_AJUSTE    [LLM]
```

---

### Resumo: Motores × Agente Responsável

| Motor | Arquivo | Agente | Natureza | Quando |
|-------|---------|--------|----------|--------|
| Motor de Start | `motor_start.py` | **Lestrade** | Determinístico | `diogenes start` / `confirm-manifest` |
| Motor de Perfilamento | `motor_perfilamento.py` | **Watson** | Determinístico (DuckDB) | Antes de Irene/Watson LLM, best-effort |
| Motor de Saída | `motor_saida.py` | **Lestrade** | Determinístico (regex) | `diogenes verify-output` |
| Motor de Entrega | `motor_entrega.py` | **Mycroft** | Determinístico (docx/html) | `diogenes deliver` / final do autorun |

---

## 4. Fluxo Completo do Ciclo

### 4.1 Estados do Ciclo (`CycleState`)

```
PREPARADO
  └→ AGUARDANDO_CONFIRMACAO_MANIFESTO
       └→ VERIFICANDO_EXISTENCIA           ← Irene: verifica catálogo existente
            ├→ AGUARDANDO_IRENE             ← Irene: pipeline C1–C5 em execução
            │    ├→ IRENE_CONCLUIDA
            │    └→ ABORTADO_FALHA_AGENTE  ← IRENE_ERRO_FATAL
            └→ EM_EXECUCAO_WATSON           ← catálogo reutilizável ou Irene desabilitada
  EM_EXECUCAO_WATSON
    └→ AGUARDANDO_REVISAO_MYCROFT_WATSON
         ├→ EM_EXECUCAO_WATSON              ← Mycroft questiona Watson (até 2 rodadas)
         ├→ AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO
         │    ├→ EM_EXECUCAO_SHERLOCK       ← Lestrade autoriza
         │    └→ PAUSADO_LESTRADE
         └→ EM_EXECUCAO_SHERLOCK
  EM_EXECUCAO_SHERLOCK
    └→ AGUARDANDO_REVISAO_MYCROFT_SHERLOCK
         ├→ EM_EXECUCAO_SHERLOCK            ← Mycroft questiona Sherlock (até 2 rodadas)
         ├→ AGUARDANDO_COMPLETUDE           ← 11 seções incompletas
         └→ AGUARDANDO_VERIFICACAO_SAIDA
  AGUARDANDO_VERIFICACAO_SAIDA
    └→ AGUARDANDO_CHANCELA_LESTRADE
         ├→ EM_EXECUCAO_ENTREGA             ← diogenes deliver (opcional, antes do seal)
         │    ├→ AGUARDANDO_CHANCELA_LESTRADE  ← QA aprovado
         │    └→ AGUARDANDO_AJUSTE_ENTREGA     ← QA reprovado
         └→ ENCERRADO_CHANCELADO            ← diogenes seal

[terminais de erro]
ABORTADO_FALHA_AGENTE
ABORTADO_LESTRADE
```

### 4.2 Sequência Detalhada por Fase

**Preparação (Lestrade + MotorStart):**
```
diogenes start --module MOD_010 --activity 1
  → MotorStart.run(): hash + cópia + manifest.md + audit_index.csv (PREPARADO)
diogenes confirm-manifest --cycle {id}
  → Orchestrator.executar():
      MotorPerfilamento (Watson — best-effort): .perfil.yaml por arquivo
```

**Fase Irene (condicional):**
```
[se DIOGENES_IRENE_HABILITADO=true e catálogo ausente ou desatualizado]
  executar_irene() → C1→C2→C3→C4(LLM)→C5
  estados: AGUARDANDO_IRENE → IRENE_CONCLUIDA | ABORTADO_FALHA_AGENTE
```

**Fase Watson:**
```
Mycroft.definir_tasks_watson()              [heartbeat: definir_tasks_watson]
  → verifica se Planilha de Verificação está no manifesto
Watson.analisar_arquivo() × N              [heartbeat: analise_arquivo]
  → prefixo [PERFIL ANALÍTICO] do motor_perfilamento + amostra truncada
Watson.consolidar()                         [heartbeat: consolidar_watson]
Watson.validacao_planilha_rn()             [heartbeat: validacao_planilha_rn] (condicional)
Mycroft.avaliar_watson()                   [heartbeat: avaliar_agente]
  → até 2 rodadas de revisão (Stranger Room)
Mycroft.fixar_decisao_watson()             [heartbeat: fixar_decisao] (se 2ª rodada)
```

**Transição Watson → Sherlock:**
```
Mycroft.montar_pacote_sherlock()           [heartbeat: montar_pacote_sherlock]
  → propaga "Nota metodológica com alteração" se Watson sinalizou
Mycroft.mapear_pontos()                    [heartbeat: mapear_pontos]
  → mapeia pontos do Apêndice aos arquivos Watson relevantes
```

**Fase Sherlock:**
```
Sherlock.verificar_ponto() × N pontos      [heartbeat: verificar_ponto]
Sherlock.validacao_planilha_rn_sherlock()  [heartbeat: validacao_planilha_rn_sherlock] (condicional)
Sherlock.consolidar()                      [heartbeat: consolidar_sherlock]
  → 11 seções obrigatórias (10.1–10.11) + JSON de ocorrências (seção 11)
Mycroft.avaliar_sherlock()                 [heartbeat: avaliar_agente]
  → até 2 rodadas de revisão (Stranger Room)
Mycroft.fixar_decisao_sherlock()           [heartbeat: fixar_decisao] (se 2ª rodada)
```

**Consolidação:**
```
Mycroft.consolidar()                       [heartbeat: consolidar]
  → verifica completude das 11 seções antes de emitir MC_consolidado.md
  → grava output/relatorio_preliminar_{id}.md
  → estado: AGUARDANDO_VERIFICACAO_SAIDA
```

**Motor de Saída (Lestrade):**
```
diogenes verify-output --cycle {id}
  → MotorSaida.verificar(): 4 categorias de varredura + sanitização automática
  → estado: AGUARDANDO_CHANCELA_LESTRADE (se limpo)
```

**Fase de Entrega — Mycroft + MotorEntrega (opcional):**
```
diogenes deliver --cycle {id}
  → Mycroft.mapear_dados_modulo()   [LLM]
  → Mycroft.redigir_apendice()      [LLM]
  → MotorEntrega.gerar()            [determinístico — 6 artefatos]
  → Mycroft.avaliar_entrega()       [LLM — APROVADO | REQUER_AJUSTE]
  → estado: AGUARDANDO_CHANCELA_LESTRADE (APROVADO) | AGUARDANDO_AJUSTE_ENTREGA
```

**Chancela:**
```
diogenes seal --cycle {id}
  → estado: ENCERRADO_CHANCELADO
```

---

## 5. Estrutura de Diretórios

```
projeto_diogenes/
  diogenes/                         ← pacote Python (CWD de todos os comandos)
    src/diogenes/
      agents/
        file_prep.py                ← converte xlsx/csv/sql/ipynb/pdf→texto para prompts
        watson.py                   ← WatsonAgent
        mycroft.py                  ← MycrooftAgent (grafia SDD)
        sherlock.py                 ← SherlockAgent
        heartbeat.py                ← carregador de heartbeat.md por call_type
        contexto_metodologico.py    ← carrega corpus jurídico e metodologia do módulo
      bench/                        ← bancada cirúrgica (smoke, validate-models, preview, call)
      cli/
        commands/                   ← um arquivo por subcomando CLI
      config.py                     ← ÚNICO ponto de leitura de .env + YAML
      delivery/                     ← Fase de Entrega: parsing + extractor + dashboard + builders
        vendor/tcu/                 ← geradores TCU vendorizados (cópias — não referenciar OneDrive)
      irene.py                      ← wrapper pipeline Irene C1–C5
      llm/                          ← base.py (Protocol/factory) + chattcu + openrouter + azure
      models.py                     ← TODOS os dataclasses de domínio (sem lógica, sem imports internos)
      motors/
        motor_start.py              ← Lestrade: intake, hash, cópia, manifesto
        motor_perfilamento.py       ← Watson: stats determinísticas CSV/XLSX via DuckDB
        motor_saida.py              ← Lestrade: varredura e sanitização do relatório
        motor_entrega.py            ← Mycroft: geração de artefatos institucionais
        exceptions.py               ← exceções tipadas dos motores
      orchestrator/
        orchestrator.py             ← máquina de estados do ciclo
        states.py                   ← CycleState + TRANSICOES_VALIDAS
        stranger_room.py            ← revisão Mycroft ↔ Watson/Sherlock (imutável, Art. 11)
        events.py                   ← EventLogger: JSONL de auditoria + regenera report.html ao vivo
        entrega.py                  ← orquestração da Fase de Entrega
      persistence/
        audit_index.py              ← audit_index.csv com escrita atômica
        manifest.py                 ← leitura/escrita do manifest.md
        workspace.py                ← WorkspaceManager: cria e localiza diretórios de ciclo
    tests/
      unit/                         ← testes sem I/O externo (mock via pytest-httpx)
      integration/                  ← testes com I/O real
      conftest.py                   ← fixture autouse clear_config_cache + outros helpers globais
    docs/
      antecedentes/PRD_Piloto_Diogenes_v01.md   ← requisitos do piloto
      sdd/SDD_Piloto_Diogenes_v01.md             ← arquitetura de software (fonte da verdade)
      agentes/{irene,watson,sherlock,mycroft}/   ← soul + skills + heartbeat + agent
      auditoria_agentes/                         ← contratos e dossiês por agente
      ESPECIFICACAO_PROJETO.md                   ← este documento
    agents_spec.yaml                ← modelos LLM por agente + parâmetros runtime
    runtime.yaml                    ← parâmetros operacionais (padrões motor_saida, etc.)
    CLAUDE.md                       ← instruções para o assistente de desenvolvimento
    ESTADO_DIOGENES.md              ← snapshot vivo do estado do piloto
  workspace/                        ← runtime (gitignored)
    input/{module_id}/              ← pacotes de entrada colocados externamente
    cycles/{cycle_id}/
      inputs/                       ← cópias imutáveis dos arquivos do pacote
      output/                       ← relatorio_*.md + entrega/
      stranger_room/                ← revisões Mycroft ↔ Watson/Sherlock (imutáveis)
      _runtime/
        events.jsonl                ← log de auditoria do ciclo
        perfis/                     ← .perfil.yaml por arquivo (motor_perfilamento)
        perfil_pacote.yaml          ← colunas compartilhadas cross-file
        report.html                 ← painel de acompanhamento ao vivo
      _historico/                   ← (Atividade 2 apenas) artefatos herdados do ciclo A1
    audit_index.csv                 ← registro de todos os ciclos
```

---

## 6. CLI — Subcomandos

| Comando | O que faz | Estado resultante |
|---------|-----------|-------------------|
| `diogenes init` | Inicializa o workspace | — |
| `diogenes start` | MotorStart: hash + cópia + manifesto | `PREPARADO` |
| `diogenes confirm-manifest` | Dispara `Orchestrator.executar()` (ciclo completo) | `AGUARDANDO_VERIFICACAO_SAIDA` |
| `diogenes autorun` | `start` + `confirm-manifest` em sequência; abre `report.html` | — |
| `diogenes status` | Mostra estado atual do ciclo no audit_index | — |
| `diogenes list` | Lista todos os ciclos no audit_index | — |
| `diogenes show` | Mostra detalhes de um ciclo | — |
| `diogenes proceed` | Autoriza progressão após alerta crítico | `EM_EXECUCAO_SHERLOCK` |
| `diogenes pause` | Pausa o ciclo | `PAUSADO_LESTRADE` |
| `diogenes resume` | Retoma o ciclo pausado | — |
| `diogenes abort` | Aborta o ciclo | `ABORTADO_LESTRADE` |
| `diogenes verify-output` | MotorSaida: varredura + sanitização | `AGUARDANDO_CHANCELA_LESTRADE` |
| `diogenes deliver` | Fase de Entrega: mapa + Motor de Entrega + QA | — |
| `diogenes seal` | Chancela final de Lestrade | `ENCERRADO_CHANCELADO` |
| `diogenes complete-sherlock` | Retomada após `AGUARDANDO_COMPLETUDE` | `AGUARDANDO_VERIFICACAO_SAIDA` |
| `diogenes report` | Painel de acompanhamento (Markdown ou HTML) | — |
| `diogenes bench` | Bancada cirúrgica (smoke, validate-models, preview, call) | — |

---

## 7. Identificadores e Nomenclatura Crítica

| No código | Significado |
|-----------|-------------|
| `MycrooftAgent` | Mycroft Holmes — grafia do SDD (dois 'o') |
| `WatsonAgent` | Dr. Watson — Auditor de Integridade Técnica |
| `SherlockAgent` | Sherlock Holmes — Auditor de Validação Metodológica CBS |
| `StrangerRoom` | Protocolo de revisão Mycroft ↔ Watson/Sherlock (imutável) |
| `cycle_id` | `{MOD_ID}_A{ATIV}_{TIMESTAMP_UTC}` — ex: `MOD_010_A1_20260510T143000Z` |
| `FASE_WATSON` | `"watson_integridade"` |
| `FASE_SHERLOCK` | `"sherlock_validacao"` |
| `MOD_010` | Primeiro módulo real — Pessoa Física |
| `MOD_SINT_001` | Módulo sintético para testes (Fases A e B) |

---

## 8. Governança Técnica

### 8.1 Provider LLM

**ChatTCU é o ÚNICO provider permitido em produção.** Dados fiscais do TC 015.848/2025-6 não podem trafegar por serviços externos. `get_llm_client()` em `llm/base.py` é o guardião.

| Provider | Quando permitido |
|----------|-----------------|
| `chattcu` | Sempre (produção) |
| `azure` | Configuração explícita + autorização |
| `openrouter` | **Apenas em contexto pytest** (`PYTEST_CURRENT_TEST` detectado) |

### 8.2 Regras Arquiteturais Inegociáveis (SDD Art. 1–15)

1. **Sequencialidade absoluta** — sem threads, sem asyncio entre agentes
2. **`config.py` como único ponto de leitura** — nenhum módulo usa `os.environ` diretamente
3. **`models.py` sem imports internos** — evita importação circular
4. **Stranger Room imutável** — arquivos escritos nunca são sobrescritos (`StrangerRoomWriteError`)
5. **Motores sem LLM** — lógica determinística e auditável por leitura direta do código
6. **Originais do pacote RFB intocáveis** — trabalho exclusivo sobre cópias em `inputs/`

### 8.3 Stack

```
Python 3.11+ | openai SDK | msal+requests (ChatTCU) | Typer CLI | Pydantic v2
openpyxl (xlsx) | sqlparse (sql) | nbformat (ipynb) | pdfminer.six (pdf)
duckdb>=1.0 (motor_perfilamento) | python-docx | matplotlib | playwright (ficha PDF/PNG)
pytest + pytest-httpx (mocks LLM via httpx intercept)
```

---

## 9. Configuração Mínima de Ambiente

```bash
# .env (copiar de .env.example)
DIOGENES_LLM_PROVIDER=chattcu
DIOGENES_CHATTCU_BASE_URL=https://chat-tcu.apps.tcu.gov.br
DIOGENES_WORKSPACE=/caminho/absoluto/workspace
DIOGENES_IRENE_HABILITADO=true
IRENE_PROVIDER=chattcu
IRENE_MODEL=gpt-5.5-thinking

# Instalar (de dentro de diogenes/)
pip install -e ".[dev]"
python -m playwright install chromium   # para PDF/PNG da ficha síntese

# Inicializar workspace
diogenes init
```

---

## 10. Fluxo de Desenvolvimento e Testes

```bash
cd diogenes

# Suite completa
pytest tests/

# Módulo específico
pytest tests/unit/test_motor_perfilamento.py -v

# Pares XLSX+CSV (motor_perfilamento)
pytest tests/unit/test_perfilamento_pares_xlsx_csv.py -v

# Lint
ruff check src/ tests/

# Bancada cirúrgica (sem ciclo completo)
diogenes bench smoke                                              # conectividade
diogenes bench validate-models                                    # modelos do agents_spec.yaml
diogenes bench preview watson --call-type analise_arquivo         # monta prompt sem LLM
diogenes bench call watson --call-type analise_arquivo --prompt "OK"  # chamada real isolada
```

**Estado atual da suite:** 292 passed, 1 skipped (docling não instalado — não bloqueante)

---

## 11. Análise Comportamental Comparativa

### 11.1 Mapa de responsabilidades por camada

| Agente | Camada | O que verifica | O que NÃO verifica |
|--------|--------|----------------|---------------------|
| Irene | Pré-análise | Estrutura e semântica dos arquivos | Correção de valores, metodologia |
| Watson | Camada 0 | Integridade, consistência interna, cadeia de produção | Conformidade metodológica |
| Mycroft | Transversal | Qualidade dos outputs, sequência, integração | Conteúdo dos arquivos, cálculos |
| Sherlock | Camadas 1–3 | Aderência metodológica, reprodutibilidade, consistência final | Integridade estrutural (Watson) |

**Ordem de execução no ciclo:**
```
Irene (pré-análise) → Watson (Camada 0) → Mycroft (revisão/integração) → Sherlock (Camadas 1–3) → Mycroft (consolidação)
```

### 11.2 Padrão de projeto comum a todos os agentes

Todos os agentes LLM compartilham os mesmos princípios constitucionais:
- **Art. 4** — Não iniciam por iniciativa própria. Executam o que foi delegado.
- **Art. 8** — Máximo de 2 rodadas com Mycroft antes do martelo.
- **Art. 13** — Operam exclusivamente sobre cópias no workspace isolado.
- **Art. 14** — Documentos em terceira pessoa e impessoal. Exceção documentada: trace interno em 1ª pessoa (Watson e Sherlock).
- **Assinatura de rastreabilidade** ao final de cada documento produzido.
- **Mascaramento de PII obrigatório** — CPF, CNPJ, chaves NF-e mascarados em todos os outputs (defesa sistêmica contra filtros de segurança do ChatTCU).

### 11.3 Tensões estruturais do sistema

**Dependência em cascata:**
Erro de Irene na classificação semântica → priorização errada de Watson → pacote inadequado para Sherlock → classificação de Sherlock comprometida. Não há mecanismo de detecção retroativa dentro do ciclo. Um erro silencioso de C4 (semântica) só aparece se Watson, ao analisar, discordar da classificação — e mesmo assim não há rollback automático.

**Mycroft avalia sem ver:**
Mycroft julga a qualidade dos outputs de Watson e Sherlock sem poder verificar os dados fonte. A qualidade do julgamento de Mycroft depende inteiramente da qualidade da documentação de Watson e Sherlock. Output obscuro → crítica impossível → aprovação por omissão.

**Sherlock classifica sem ver:**
Sherlock julga conformidade metodológica sem ver os arquivos originais. A qualidade de sua classificação depende inteiramente da completude do output de Watson. Se Watson sub-analisou um arquivo, o buraco não aparece na análise de Sherlock.

**Escalas heterogêneas:**
Watson usa escala de **severidade de impacto** (`CRITICA/ALTA/MEDIA/BAIXA`). Sherlock usa escala de **natureza metodológica** (`DIVERGENCIA/NAO_VERIFICAVEL/ATENCAO/etc`). Mycroft integra as duas sem um mecanismo formal de conversão — o mapeamento é feito em linguagem natural no `MC_pacote_sherlock.md`.

**Modo monolítico de Sherlock (validacao_inicial) vs. modo isolado (verificar_ponto):**
No modo isolado, cada ponto fecha seu contexto antes do próximo abrir — sem contaminação entre verificações. No modo monolítico, todas as verificações compartilham o mesmo contexto — classificações anteriores podem influenciar classificações posteriores. O design intencional assume que essa troca é compensada pela eficiência de uma única chamada LLM.

**Único agente sem feedback loop:**
Irene não tem Stranger Room — retorna um estado e o sistema decide. Erros de C4 são invisíveis durante o ciclo. A classificação de uma aba como `aba_auxiliar` quando deveria ser `resultado_final` só é descoberta se Watson, ao receber a priorização de Mycroft, notar a discrepância.

### 11.4 Interfaces entre agentes (o que passa de quem para quem)

```
Irene → Mycroft:     irene_catalog.yaml (estado + score + classificação de abas)
Mycroft → Watson:    MC_tasks_watson.md (tasks ordenadas + premissas globais + catálogo Irene)
Watson → Mycroft:    watson_analise_*.md + watson_consolidado.md + watson_registro_decisao.md
Mycroft → Sherlock:  MC_pacote_sherlock.md (síntese validada de Watson + instrução de skills)
Sherlock → Mycroft:  sherlock_ponto_*.md + sherlock_consolidado.md + sherlock_registro_decisao.md
Mycroft → Lestrade:  MC_consolidado.md → relatorio_preliminar_{id}.md → (higienizado) → seal
```

**O que Watson não sabe sobre Sherlock:** nada — não tem acesso ao que Sherlock vai verificar.
**O que Sherlock não sabe sobre Watson:** apenas o que Mycroft incluiu no `MC_pacote_sherlock.md`.
**O que Lestrade não sabe sobre os agentes:** os nomes — o `motor_saida.py` remove todas as referências antes da chancela.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
