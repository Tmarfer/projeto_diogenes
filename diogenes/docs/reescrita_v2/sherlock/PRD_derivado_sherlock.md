---
documento: PRD Derivado — Sherlock Holmes (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_Piloto_Diogenes_v01.md (Bloco 3.6, RF-SH)
  - docs/antecedentes/PRD_adendo_v02_homologacao_formatos.md (RF-HF)
  - docs/conformidade/05_sherlock.md
  - docs/auditoria_agentes/sherlock/{contrato,dossie}.md
  - docs/agentes/sherlock/{agent,soul,skills,heartbeat}.md
---

# PRD Derivado — Sherlock Holmes

> Recorte para o escopo de Sherlock, Auditor de Validação Metodológica CBS
> (Camadas 1, 2 e 3 da estratégia de validação). O "como" está em
> [SDD_derivado_sherlock.md](SDD_derivado_sherlock.md).

---

## 1. Identidade e missão

Sherlock recebe o pacote já saneado por Watson e integrado por Mycroft, aplica a
**metodologia homologada pelo Acórdão 2833/2025-Plenário** e diz — com precisão
cirúrgica e fundamentação irrefutável — o que está conforme, o que diverge e o
que não é possível verificar. "Cada divergência que você deixar passar é uma
divergência que o Tribunal chancelará" (`soul.md`). Raciocínio dedutivo a partir
da evidência; toda classificação tem citação explícita do dispositivo; toda
divergência é reproduzível por terceiro. Sem ironia, sem melancolia: relatório
seco, preciso e defensável — será lido pela RFB no contraditório. Temperatura
0.1 (a mesma evidência produz a mesma classificação).

**Modo operacional padrão: MONOLÍTICO** — `validacao_inicial` processa todos os
pontos numa única chamada (Passos do heartbeat); o modo per-ponto
(`verificar_ponto`, restrição UM_PONTO_POR_CHAMADA) é **reservado à bancada**.

## 2. Escopo do recorte

**Entra na reescrita de Sherlock:**
- O invocador `SherlockAgent`: `validar` (monolítico com degradação escalonada),
  `validacao_planilha_rn_sherlock` (condicional), `consolidar` (11 seções +
  JSON), `responder_critica`.
- `agents/contexto_metodologico.py` (seleção de metodologia e corpus jurídico —
  é o contrato de contexto de Sherlock).
- Parsing de `SherlockOutput` e o fallback marcado.

**NÃO entra (fronteiras):**
- Integridade estrutural, parsing de planilha, tradução de SQL — **Watson**
  (Art. 7: Sherlock parte das análises de Watson, nunca dos arquivos brutos).
- Montagem do pacote integrado — **Mycroft** (`montar_pacote_sherlock`).
- Loop de rodadas, verificação de completude das 11 seções, gate de fallback —
  **Orquestrador**.

## 3. Requisitos funcionais (transcritos do PRD mestre, Bloco 3.6)

| RF | Texto (resumo fiel) | Status v1 | Gap conhecido |
|---|---|---|---|
| **RF-SH-01** | Recebe o pacote integrado por Mycroft (inventário, documentos, decisão final de Watson, análise consolidada, briefing). Não inicia sem pacote completo nem pede arquivos por iniciativa própria | Conforme (`sherlock.py:88`) | — |
| **RF-SH-02** | Não analisa integridade estrutural; opera sobre pacote saneado (Art. 7). Sem tools de Camada 0 | Conforme | — |
| **RF-SH-03** | Aplica a metodologia homologada (Acórdão 2833/2025) do módulo, acessível como contexto | Conforme (`contexto_metodologico.py:39` teto 80k; corpus cat. D `:68` teto 30k) | **P1 nº 2:** corpus depende de `DIOGENES_CORPUS_JURIDICO_DIR` externo; sem default versionado no repo; ausência não bloqueia |
| **RF-SH-04** | Classifica cada ponto pelo sistema semântico TCU-CBS: Atendido, Atendido Parcialmente, Divergência, Atenção, Limitação, Não Verificável — fundamentado com referência ao dispositivo | Conforme (vocabulário exato no `skills.md`) | — |
| **RF-SH-05** | Dilema com duas interpretações de peso equivalente: registra com ambas fundamentadas e apresenta a Mycroft; não resolve arbitrariamente nem omite (Art. 10) | Conforme (`dilemmas_count`) | — |
| **RF-SH-06** | Cálculos próprios reproduzíveis: cada cálculo refazível por terceiro a partir da fundamentação registrada | **Parcial** | **P1 nº 3:** citação normativa por ponto não obrigatória; `fundamento_violado` do JSON opcional mesmo em CRITICO |
| **RF-SH-07** | Relatório classificado ponto a ponto, fundamentação explícita, identificação dos pontos para contraditório com a RFB | Conforme (11 seções verificadas antes de Mycroft.consolidar) | Fundamentação cita metodologia mas raramente dispositivo legal (LC 214/2025, art. X) — zero citações nos outputs reais auditados |
| **RF-SH-08** | Output estruturado equivalente ao de Watson, consumo unívoco por Mycroft | Conforme (`SherlockOutput` espelha `WatsonOutput`; JSON de ocorrências para dashboard) | — |

**Extensões além do PRD (implementadas no v1):**
- `validacao_planilha_rn_sherlock` (`sherlock.py:135`) — condicional à Planilha
  de Verificação.
- `responder_critica` (`sherlock.py:191`) — protocolo Stranger Room.
- Seção 10.10 renomeada "Deliberações Internas do Ciclo" (higiene de marca
  interna — era "Stranger Room").
- Degradação escalonada do `validar` (2026-06-11) e fallback marcado.

## 4. Requisitos de interface

**Input:** o pacote integrado (`MC_pacote_sherlock.md` + metodologia cat. C +
corpus jurídico cat. D + `watson_consolidado.md` + decisão de Watson) — **nunca**
arquivos originais do pacote RFB.

**Outputs e campos monitorados:**

| Output | Estrutura monitorada | Consumidor |
|---|---|---|
| apresentação da validação (monolítica) | múltiplos pontos `sherlock_ponto_*` com classificação + citação | Mycroft (`avaliar_sherlock`) |
| `sherlock_consolidado.md` | **11 seções obrigatórias (10.1–10.11)** + **JSON de ocorrências (seção 11)** — verificadas pelo Orquestrador ANTES de `Mycroft.consolidar()`; ausência → `AGUARDANDO_COMPLETUDE` | Orquestrador + Mycroft + dashboard da entrega |
| `sherlock_registro_decisao.md` | decisões de julgamento | Mycroft |
| `sherlock_planilha_rn.md` | perspectiva metodológica da Planilha de Verificação | consolidado |
| `sherlock_resposta_r[n].md` | resposta na Stranger Room | Mycroft |

Campos parseados: `dilemmas_count`, `has_divergencias`,
`nota_metodologica_com_alteracao`, `notas_metodologicas_count` (seção 7),
`pendencias_simulador_count` (seção 9), `is_fallback`. Defaults seguros.

**As 11 seções do Relatório Estruturado (10.x):** Identificação do Ciclo;
Síntese da Metodologia; Resultado Camada 0; Resultado Camadas 1–2; Consistência
Camada 3; Ocorrências Identificadas; Verificações Criadas pelos Agentes; Análise
de Impacto Sistêmico; Pendências para o Simulador Completo; Deliberações
Internas do Ciclo; Histórico de Revalidações.

## 5. Limites constitucionais e regras hard

| Artigo / Regra | Conteúdo | Verificação v1 |
|---|---|---|
| **Art. 7** | Camadas 1–3 apenas; parte das análises de Watson, não dos brutos | Confirmado |
| **Art. 4** | Age sob delegação (pacote integrado de Mycroft) | Confirmado |
| **Art. 10** | Dilema equilibrado → registrado e encaminhado, nunca resolvido arbitrariamente | Confirmado |
| **Art. 14** | 3ª pessoa, impessoal; "Sherlock" só na assinatura. **Exceção documentada:** trace interno em 1ª pessoa (Fix 3-B) | Confirmado (1 vazamento no baseline, higienizado) |
| **Limite de rodadas** | Máx. 2 respostas na Stranger Room | Confirmado |
| **Citação obrigatória** | Toda classificação com citação no formato canônico do `skills.md` (ex.: `[Acórdão 2833/2025 \| Apêndice X \| Módulo 10 \| Seção 3.1 \| RN-10.01]`) | Confirmado no formato; gap no dispositivo **legal** (RF-SH-07) |
| **Anti-PII (ChatTCU)** | Mascaramento e referência estrutural (Fix 3-C) | Calibrado |
| **Modo monolítico** | `validacao_inicial` processa todos os pontos; UM_PONTO_POR_CHAMADA só em `verificar_ponto` (bancada) | Calibrado (Fix 3-A) |

## 6. RNFs aplicáveis (recorte)

- **RNF-CUST-04:** max_tokens 8000; max_tokens_ciclo 131072.
- **Timeout/retry:** 1500s; retry 4× (demais call_types); `validacao_inicial`
  usa **2 tentativas por estágio** da degradação escalonada (override).
- **RNF-RAST/REPR:** trace por chamada; seed determinística.
- **RNF-OBSE:** réguas de truncamento registradas com ressalva obrigatória no
  output quando a degradação é acionada.

## 7. Critérios de aceitação e métricas (recorte)

- **MET-04 ≥ 70% / MET-05 < 15% / MET-07 ≥ 1,5** (adendo v02, RF-HF-04) — a
  fundamentação metodológica (MET-07) é a métrica-alvo de Sherlock.
- **MET-04 aprovado no SQL pós-calibração:** Sherlock 2,5/3 no MOD_SINT_SQL com
  âncora metodológica no pacote (lição RF-HF-03: sem metodologia no pacote, a
  medição é inválida).
- **Critério da rodada real (adendo v02):** ocorrências individualizadas, com
  fundamento canônico e número de Watson.
- **CA-QUA-03/05:** Stranger Room como deliberação real; dilemas ponderados.

## 8. Lições do piloto v1 (dossiê + CLAUDE.md)

1. **Causa raiz NV-GLOBAL-01 (zero pontos válidos):** o heartbeat mapeava
   `validacao_inicial → verificar_ponto` (UM_PONTO_POR_CHAMADA) enquanto o
   Orquestrador chama `validar()` uma única vez com o pacote inteiro — o modelo
   recusava por violação do próprio contrato. Fix 3-A: seção monolítica
   dedicada no heartbeat + mapeamento corrigido em `heartbeat.py`.
   **Lição v2:** o mapeamento call_type → seção de heartbeat é parte do contrato;
   teste específico para ele.
2. **Timeout estrutural do `validacao_inicial`:** estourou 600s 4× (2026-06-10)
   e 1500s 4× (MOD_010, 2026-06-11) — timeout maior não resolve. Solução:
   **degradação escalonada** (2 tentativas pacote completo → 2 com réguas
   truncadas 40k metodologia/15k corpus + ressalva obrigatória → fallback
   marcado + pausa do ciclo). **Lição v2:** a degradação é comportamento
   canônico, não contorno.
3. **Fallback silencioso chancelado:** o fallback determinístico fabricava as 11
   seções, passava na completude e o ciclo era selado vazio. Correção:
   `is_fallback` + gate antes da Stranger Room. **Lição v2:** o fallback existe
   para diagnóstico, nunca para prosseguir.
4. **Metodologia chegava truncada:** `_MAX_CHARS_METODOLOGIA` 20k→80k
   (2026-06-04) — RN de 28.5k chegava com ~6.3k. **Lição v2:** os tetos de
   contexto são parâmetros documentados do `contexto_metodologico.py`.
5. **Caso golden Stranger Room:** crítica única de Mycroft sobre `NV-GLOBAL-01`
   (relatório × JSON), resposta sustentando o mapeamento
   `NAO_VERIFICAVEL → ALERTA` do Template 2, ACATADO.
6. **Gaps P1 nº 2 e 3** (corpus versionado; citação canônica + `fundamento_violado`
   obrigatórios em CRITICO) — candidatas a "Decisões v2".

## 9. Registro de gate

| Gate | Critérios (Metodologia §5) | Data | Chancela | Observações |
|---|---|---|---|---|
| G-SH | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | Degradação escalonada testada com timeouts simulados |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
