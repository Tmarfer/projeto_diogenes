---
documento: PRD Derivado — Dr. John Watson (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_Piloto_Diogenes_v01.md (Bloco 3.5, RF-WA)
  - docs/conformidade/04_watson.md
  - docs/auditoria_agentes/watson/{contrato,dossie}.md
  - docs/agentes/watson/{agent,soul,skills,heartbeat}.md
---

# PRD Derivado — Dr. John Watson

> Recorte para o escopo de Watson, Auditor de Integridade Técnica (Camada 0 da
> estratégia de validação). O "como" está em
> [SDD_derivado_watson.md](SDD_derivado_watson.md).

---

## 1. Identidade e missão

Watson é a **primeira linha de exame**: verifica se os números fecham, se os
scripts fazem o que declaram, se a cadeia de produção dos dados é rastreável de
ponta a ponta. Pragmatismo militar, disciplina de método, registro fiel — "o dado
fecha ou não fecha", sem juízo de intenção e **sem interpretação metodológica**
(pertence a Sherlock). Temperatura 0.0 (máximo determinismo — Watson não
especula); exige contexto longo (>128k) para o pacote RFB (~95k tokens).
Valores (`soul.md`): precisão antes de velocidade (localização exata: arquivo,
aba, célula, linha); completude antes de elegância (todos os arquivos, sem pular
sem registro); neutralidade descritiva (não sugere correções); severidade
calibrada; rastreabilidade absoluta.

## 2. Escopo do recorte

**Entra na reescrita de Watson:**
- O invocador `WatsonAgent` completo: `analisar_arquivo`, `consolidar` (com
  map-reduce), `validacao_planilha_rn` (condicional), `responder_critica`.
- Parsing do output (`WatsonOutput`) e helpers de extração de cabeçalho.
- `agents/file_prep.py` (conversão xlsx/sql/ipynb/pdf/md → texto;
  `ARQUIVOS_SEMPRE_ANALISE`) — é parte do contrato de input de Watson.

**NÃO entra (fronteiras):**
- Interpretar metodologia, emitir juízo de conformidade, usar taxonomia de
  Sherlock ("Atendido", "Divergência") — Artigo 6.
- Definir as tasks ou a ordem de análise — vem de Mycroft (`MC_tasks_watson.md`).
- O loop de rodadas da Stranger Room e o tracker de ID de alerta — Orquestrador.
- Catalogação semântica — Irene (Watson **consome** o catálogo).

## 3. Requisitos funcionais (transcritos do PRD mestre, Bloco 3.5)

| RF | Texto (resumo fiel) | Status v1 | Gap conhecido |
|---|---|---|---|
| **RF-WA-01** | Recebe do Orquestrador o pacote de tasks ordenadas definido por Mycroft, com lista explícita de arquivos e instruções. Não inicia análise por iniciativa própria nem inclui arquivos não previstos | Conforme (`watson.py:69`) | — |
| **RF-WA-02** | Não interpreta a metodologia homologada (Acórdão 2833/2025), não emite juízo metodológico, não confronta com regras de negócio da CBS (Art. 6). Sem injeção de metodologia no prompt; regra explícita no system prompt | Conforme | — |
| **RF-WA-03** | Para cada planilha: totais/subtotais fecham aritmeticamente; células declaradas como fórmula correspondem ao recálculo; inconsistências internas de apresentação | Conforme (texto canonicalizado de `file_prep.py` + catálogo Irene) | — |
| **RF-WA-04** | Para cada script SQL: tradução fiel para linguagem natural (bases, filtros, agregações, estrutura de resultado) sem inferência de intenção | Conforme (sqlparse) | — |
| **RF-WA-05** | Para cada notebook Python: tradução das células executáveis na ordem real de execução | Conforme (nbformat) | — |
| **RF-WA-06** | Identifica a cadeia de produção dos dados entre documentos; lacuna sem rastro registrada como inconsistência | Conforme (seção dedicada; "pontos de ruptura" propagados) | — |
| **RF-WA-07** | Análises extrapolativas (padrões, anomalias, comportamentos) segregadas das verificações literais, em seção própria | Conforme | — |
| **RF-WA-08** | Arquivo não analisável: registra ocorrência em campo dedicado (arquivo, razão, tentativa) e prossegue — não aborta os demais | Conforme (`has_unanalyzable_files`) | — |
| **RF-WA-09** | Relatório graduado com ≥3 níveis de severidade (crítica/atenção/informativa) por critérios objetivos do `skills.md` | Conforme (4 níveis: CRITICA/ALTA/MEDIA/BAIXA; IDs `W{MOD}-NNN`) | — |
| **RF-WA-10** | Output estruturado, com seções nomeadas e campos previsíveis; alertas críticos detectáveis mecanicamente | Conforme (`**Alertas CRITICA:** N`) | **Qualidade:** descrições de alerta com 1–2 linhas, sem bloco contexto/impacto/fundamentação/recomendação; fonte de dado (aba/célula) nem sempre citada — item P1 nº 4 da matriz |

**Extensões além do PRD (implementadas no v1):**
- `validacao_planilha_rn` — condicional: só quando a Planilha de Verificação está
  no manifesto (flag de `MC_tasks_watson.md`).
- Checkpoints por arquivo (`_runtime/watson_checkpoints/`) — retomada sem
  reprocessar; base do `--reuse-watson-from`.
- Confronto A2: instrução de comparação com histórico A1.
- `consolidar` map-reduce (2026-06-11): acima de 600k chars, consolidação por
  lotes + redução final.

## 4. Requisitos de interface

**Inputs:** `MC_tasks_watson.md` + exatamente **um arquivo por chamada** de
`analisar_arquivo` (texto canonicalizado por `file_prep.py`) + meta do invocador
(`proximo_id_alerta`); no `consolidar`, todas as `watson_analise_*.md` (NUNCA os
originais do pacote); no `responder_critica`, o output anterior + crítica de
Mycroft + trace do arquivo questionado (se existir).

**Outputs e campos monitorados:**

| Output | Campo estruturado | Consumidor |
|---|---|---|
| `watson_analise_{nome}.md` | `Último ID de alerta usado` | tracker do Orquestrador (`W{MOD}-NNN`) |
| `watson_trace_{nome}.md` (opcional) | 1ª pessoa — uso interno (`_runtime/`) | Mycroft (se questionar arquivo específico) |
| `watson_consolidado.md` | `**Alertas CRITICA:** N` (**inteiro estrito**); `Nota metodológica com alteração detectada: Sim\|Não` | `_contar_criticos`; propagação à transição Sherlock |
| `watson_registro_decisao.md` | decisões de julgamento e bifurcações | Mycroft (`avaliar_watson` — sempre injetado) |
| `watson_planilha_rn.md` | verificações ponto a ponto | pacote Sherlock |
| `watson_resposta_r[n].md` | resposta na Stranger Room | Mycroft |

Parsing sempre com default seguro; `_contar_criticos` lê o campo de cabeçalho
(sobrevive à truncagem de tabela) com fallback para nomes de seção.

## 5. Limites constitucionais e regras hard

| Artigo / Regra | Conteúdo | Verificação v1 |
|---|---|---|
| **Art. 4** | Nunca inicia por conta própria; executa as tasks delegadas | Confirmado |
| **Art. 6** | Integridade apenas; sem taxonomia metodológica (proibido "Atendido"/"Divergência"/"Conforme metodologia"); escala exclusiva CRITICA/ALTA/MEDIA/BAIXA | Confirmado no baseline |
| **Art. 13** | Opera só sobre cópias no diretório isolado do ciclo | Confirmado |
| **Art. 14** | 3ª pessoa, impessoal; assinatura só ao final | Confirmado |
| **Exceção do Trace** | `watson_trace_*.md` em 1ª pessoa; uso interno, nunca vai ao GT | Confirmado (`_runtime/`) |
| **Limite de rodadas** | Máx. 2 respostas na Stranger Room (`resposta_r1`/`r2`) | Orquestrador impede a 3ª |
| **Formato numérico estrito** | Contadores de cabeçalho (`Alertas CRITICA`, `Total`) são **inteiros**, sem prosa (calibração F1) | Calibrado 2026-06-03 |
| **Anti-PII (ChatTCU)** | Mascarar CPF/CNPJ/nomes/chaves (`***.***.***-**`); não transcrever blocos de dados brutos; localização analítica (calibração F2) | Calibrado 2026-06-03 |

## 6. RNFs aplicáveis (recorte)

- **RNF-RAST-01/06:** análise persistida antes da próxima chamada; trace
  `LLMCall` por chamada.
- **RNF-CUST-04:** `max_tokens: 8000`, `max_tokens_ciclo: 131072`;
  timeout 1500s, retry 4×/backoff 30s (agents_spec).
- **RNF-REPR-02:** seed determinística por chamada.
- **RNF-LATE:** análise por arquivo do MOD_010 real ≈ 5h no total (69+ arquivos) —
  motivo do checkpoint/`--reuse-watson-from`.

## 7. Critérios de aceitação e métricas (recorte)

- **MET-04 ≥ 70% / MET-05 < 15%:** detecção e falsos positivos contra
  `gabarito_mod_sint_001.md` (4 INC primárias + 2 latentes + 6 verdadeiros
  negativos) — Watson responde pela detecção de integridade (INC de Camada 0).
- **Adendo v02 (RF-HF-04):** homologação por formato — Watson 3/3 no
  MOD_SINT_SQL v1 (referência de qualidade por formato).
- **CA-QUA-01:** detecção das inconsistências propositais (avaliação humana).
- **Critério da rodada real (adendo v02, Bloco 4):** 100% dos arquivos
  analisáveis com análise individual — zero perdas silenciosas; alertas CRITICA
  dominados por achados materiais, não por metadados ausentes.

## 8. Lições do piloto v1 (dossiê + CLAUDE.md)

1. **F1 — contagem em prosa no cabeçalho:** Watson respondeu `Alertas CRITICA`
   com prosa, quebrando o extrator regex. Calibração: formato numérico estrito
   no `skills.md`/`heartbeat.md`. **Lição v2:** o contrato de cabeçalho é
   inteiro estrito; o parser mantém fallback tolerante.
2. **F2 — recusas do filtro de segurança ChatTCU:** 4 arquivos do baseline
   recusados ("I'm sorry..."), por PII/dados fiscais literais no prompt/resposta.
   Calibração anti-PII no `soul.md`. **Lição v2:** recusa do filtro = falha de
   chamada (retry/registro), nunca análise válida.
3. **Consolidação monolítica estourou (2026-06-11):** 2,43M chars/615k tokens
   numa chamada; agora map-reduce por lotes (>600k chars) com marcadores
   `[CONSOLIDAÇÃO PARCIAL — LOTE i/N]`. **Lição v2:** o consolidar em lotes é
   comportamento canônico, documentado no heartbeat.
4. **`nota_metodologica_com_alteracao` descartada no consolidado** (fix
   2026-06-11): a propagação à transição Sherlock nunca disparava. **Lição v2:**
   teste específico de propagação do flag.
5. **`is_fallback`:** todo fallback determinístico é marcado e nunca segue para
   revisão (gate do Orquestrador).
6. **Gap de qualidade RF-WA-10** (item P1 nº 4): template de ocorrência em 4
   blocos (contexto/impacto/fundamentação/recomendação) + fonte de dado —
   candidata a "Decisão v2".

## 9. Registro de gate

| Gate | Critérios (Metodologia §5) | Data | Chancela | Observações |
|---|---|---|---|---|
| G-WA | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | `responder_critica` testado com crítica-fixture do baseline (M2 ainda não existe) |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
