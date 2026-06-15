---
documento: PRD Derivado — Mycroft Holmes (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_Piloto_Diogenes_v01.md (Bloco 3.4, RF-MY)
  - docs/antecedentes/PRD_adendo_v01_fase_entrega.md (RF-EN-03/05)
  - docs/conformidade/03_mycroft.md
  - docs/conformidade/10_rnf.md + 11_aceitacao_metricas.md (recortes)
  - docs/auditoria_agentes/mycroft/{contrato,dossie}.md
  - docs/agentes/mycroft/{agent,soul,skills,heartbeat}.md
---

# PRD Derivado — Mycroft Holmes

> Recorte do PRD mestre + adendos para o escopo de **um agente**: Mycroft Holmes,
> Auditor Chefe. Este documento é o "o quê" da reescrita v2 de Mycroft; o "como"
> está em [SDD_derivado_mycroft.md](SDD_derivado_mycroft.md). Metodologia e gates:
> [00_METODOLOGIA.md](../00_METODOLOGIA.md).

---

## 1. Identidade e missão

Mycroft Holmes é o **Auditor Chefe** — o agente que orquestra as decisões internas
do ciclo. Não executa: garante que a execução ocorra na ordem certa, com os inputs
certos, e que os resultados estejam fundamentados antes de seguir adiante
(`soul.md`). É o único ponto de contato entre Lestrade e os agentes executores:

- Recebe de Lestrade a demanda e a converte em **tasks para Watson**.
- Recebe de Watson o resultado e **decide se ele avança** (Stranger Room).
- **Integra** o que Watson produziu e entrega a Sherlock.
- Recebe de Sherlock o resultado, **revisa** e **consolida** o produto final.
- Na Fase de Entrega: **projeta o blueprint** do dashboard (`mapear_dados_modulo`),
  **redige o Apêndice** (`redigir_apendice`) e faz o **QA** (`avaliar_entrega`) —
  projeto, redação e julgamento, nunca cálculo (Artigo 5 intacto).

Temperatura 0.2 (julgamento e síntese exigem flexibilidade contextual — vs. 0.0
dos executores). Limite de resposta: máximo 4.000 palavras por documento (RNF-CONC).

## 2. Escopo do recorte

**Entra na reescrita de Mycroft:**
- O invocador `MycrooftAgent` completo (todos os call_types das 4 fatias M1–M4).
- O parsing dos seus outputs (avaliação, decisão final, JSON de entrega).
- A escrita no protocolo Stranger Room do lado de Mycroft (fatia M2 reescreve o
  módulo `stranger_room.py` — ver SDD_derivado seção 6).

**NÃO entra (fronteiras):**
- Analisar arquivos do pacote RFB, executar cálculos, aplicar regras de negócio
  metodológicas — **pertence a Watson e Sherlock** (Artigo 5; RF-MY-02).
- Catalogação semântica de planilhas — **pertence a Irene** (Mycroft só consome
  o catálogo em `definir_tasks_watson`).
- A máquina de estados e o loop de rodadas — **pertencem ao Orquestrador**
  (Mycroft é chamado; não controla transições).
- Motor de Saída e Motor de Entrega (determinísticos, sem LLM).

## 3. Requisitos funcionais (transcritos do PRD mestre, Bloco 3.4)

| RF | Texto (resumo fiel) | Status v1 | Gap conhecido |
|---|---|---|---|
| **RF-MY-01** | Ao ser instanciado no início do ciclo, lê o manifesto, internaliza o contexto do módulo/atividade e produz a definição das tasks ordenadas para Watson — lista de arquivos, sequência sugerida e instruções específicas, **sem nunca dirigir a interpretação metodológica** (pertence a Sherlock) | Conforme (`mycroft.py:58`) | — |
| **RF-MY-02** | Não analisa arquivos diretamente, não executa cálculos, não aplica regras de negócio metodológicas (Artigo 5). Sem tools de leitura de planilha/SQL/notebook no `agent.md` | Conforme | — |
| **RF-MY-03** | Ao receber output de executor, decide entre: aprovar sem revisão (`99_decisao_final.md` com fundamentação curta); questionar (`02_critica_mycroft_r1.md` com pontos específicos); ou escalonar inconsistência crítica a Lestrade | Conforme (`mycroft.py:96/237`) | — |
| **RF-MY-04** | Crítica objetiva, dirigida a pontos específicos, com fundamentação técnica. Críticas vagas violam a função de revisão | Conforme (template `avaliar_agente`) | — |
| **RF-MY-05** | Após a 2ª rodada de qualquer fase, fixa decisão final independentemente de concordância: acata, fixa posição diversa fundamentada, ou registra controvérsia como inconsistência classificada (Artigo 10) | Conforme (`fixar_decisao_*` incondicional na 2ª rodada) | — |
| **RF-MY-06** | Ao encerrar a fase Watson, inspeciona a decisão final à procura de alertas CRITICA e marca a presença em campo estruturado para o Orquestrador disparar a notificação a Lestrade (RF-OR-05) | Conforme (`_contar_criticos` + `has_critical_alert`) | — |
| **RF-MY-07** | Consolida o output final conforme atividade (Relatório Preliminar A1 / Relatório Final A2), em 3ª pessoa, impessoal, sem nome de agentes no corpo, assinatura ao final (Artigo 14) | Conforme (`mycroft.py:301`) | **Qualidade:** profundidade narrativa da "Posição do Departamento" aquém do padrão-exemplo (1 frase/ocorrência vs. 3–5 parágrafos); sem regras de escrita (≤4 linhas/parágrafo, valores abreviados, coluna Fonte) — item P1 nº 5 da matriz |
| **RF-MY-08** | Na A2, incorpora o histórico explícito do ciclo A1: o que foi identificado, o que a RFB respondeu, o que foi aceito, o que permanece. Permite reconstruir o diálogo técnico completo | Conforme (`consolidar(historico_a1=...)`) | — |

**Call_types além do PRD (formalizados no adendo v01 — Fase de Entrega):**

| RF | Texto | Status v1 |
|---|---|---|
| **RF-EN-03** (parcial) | O mapa de extração (`entrega_mapa_extracao.json`) pode ser produzido pelo call_type `mapear_dados_modulo`; contém **apenas** nomes de aba e referências de célula/intervalo — **nunca dígitos em posição de valor** | Conforme (`mycroft.py:363`) |
| **RF-EN-05** | Após gerar os artefatos, o sistema invoca `avaliar_entrega` para QA de aderência; veredito `APROVADO \| REQUER_AJUSTE` registrado no `audit_index.csv` e no manifesto de entrega | Conforme (`mycroft.py:411`) |
| — | `redigir_apendice`: reorganiza o consolidado validado nas 7 seções do Apêndice de Verificação | Implementado (`mycroft.py:436`) |
| — | `mapear_pontos`: reservado ao modo per-ponto de Sherlock — **não ativo na produção** (modo monolítico); manter por compatibilidade de bancada | Implementado, não utilizado (F-Mycroft-02) |
| — | `acionar_irene`: a decisão gerar/reutilizar catálogo é executada por **lógica de código**, não via LLM | Heartbeat existe; sem chamada LLM |

## 4. Requisitos de interface

**Inputs por call_type** (detalhe completo no SDD_derivado seção 3): manifesto,
briefing, inventário, catálogo Irene (`definir_tasks_watson`); outputs do agente
sob revisão + histórico (`avaliar_agente`/`fixar_decisao`); decisão Watson +
metodologia + corpus jurídico (`montar_pacote_sherlock`); consolidados + decisões
(`consolidar`); inventário da planilha (`mapear_dados_modulo`); manifesto de
entrega (`avaliar_entrega`). **Mycroft nunca recebe arquivos brutos do pacote RFB.**

**Outputs e campos monitorados pelo Orquestrador:**

| Output | Campo estruturado | Consumidor |
|---|---|---|
| `MC_tasks_watson.md` | `Planilha de Verificação no pacote: Sim\|Não` | aciona `validacao_planilha_rn` (Watson) e `validacao_planilha_rn_sherlock` |
| `MC_avaliacao_{watson,sherlock}_r[n].md` | branching parseável `APROVADO \| CRITICA` | Orquestrador decide reativar o agente ou encerrar a fase |
| `MC_decisao_{watson,sherlock}.md` | `has_critical_alert`, `mycroft_overruled` | Art. 9 (Auto-Lestrade) + `audit_index.csv` |
| `MC_consolidado.md` | `Overrule Mycroft sobre Watson/Sherlock: Sim\|Não` | rastreabilidade |
| `entrega_mapa_extracao.json` | JSON sem dígitos em posição de valor | `ExtractorFinanceiro` (motor determinístico) |
| veredito de `avaliar_entrega` | `APROVADO \| REQUER_AJUSTE` | `audit_index.csv` + `manifesto_entrega_*.json` |

Todo parsing usa **default seguro quando o campo está ausente**.

## 5. Limites constitucionais e regras hard

| Artigo / Regra | Conteúdo | Verificação no v1 (contrato.md) |
|---|---|---|
| **Art. 3 — Sequencialidade** | Watson e Sherlock jamais em paralelo; Mycroft garante a linearidade | Confirmado no ciclo baseline |
| **Art. 5 — Não-intervenção** | Não abre arquivos brutos, não calcula, não valida metodologia; julga só pelos outputs apresentados | Nenhuma chamada recebeu dados brutos |
| **Art. 8 — Regra do Martelo** | Máx. 2 rodadas de crítica por agente por fase; na sequência, `fixar_decisao` obrigatório — sem 3ª rodada | Máquina de estados força após `resposta_r2` |
| **Art. 9 — Alertas Críticos** | Alerta CRITICA de Watson → notificar Lestrade antes de encaminhar a Sherlock; fluxo prossegue salvo interrupção expressa | `has_critical_alert` → `MC_alerta_critico_lestrade.md` + estado `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO` |
| **Art. 10 — Dilemas** | Não decide dilemas genuinamente equilibrados sem amparo; expõe no relatório a Lestrade | Parser lê `dilemmas_count`; prompt instrui |
| **Art. 14 — Impessoalidade** | 3ª pessoa, sem nomes de agentes no corpo; assinatura só ao final | Confirmado; Motor de Saída verifica a posteriori |
| **Verificação de Completude** | Atesta as 11 seções do Relatório Estruturado de Sherlock antes do `MC_consolidado.md` | `_parsear_decisao_sherlock` + `consolidar` |
| **Regra Absoluta de Crítica** | Exatamente **uma** crítica localizada por chamada de `avaliar_agente` (a de maior impacto) | Prompt do heartbeat impõe |
| **Anti-PII (ChatTCU)** | Nunca transcrever CPF/CNPJ/nomes/chaves NF-e; localização analítica em vez de valor literal (seção "Prevenção de Interceptação de Segurança" do `soul.md`) | Calibração F-Mycroft-03 |
| **Entrega sem números** | No `mapear_dados_modulo`, jamais escrever valor monetário — apenas aba/célula/intervalo + textos | RF-EN-02/03 |

## 6. RNFs aplicáveis (recorte de `10_rnf.md`)

- **RNF-RAST-01..07** (Conforme): todo raciocínio persistido antes da próxima
  chamada; trace `LLMCall` por chamada em `_runtime/llm_calls.jsonl`.
- **RNF-REPR-01/02** (Conforme): parâmetros completos + seed determinística por
  chamada (`llm/seed.py`).
- **RNF-CUST-04** (Conforme): `max_tokens: 16384` por chamada (agents_spec.yaml,
  valor corrente) e `max_tokens_ciclo: 131072`.
- **RNF-CONC** (soul.md): máx. 4.000 palavras por documento.
- **RNF-SEGU-05** (Conforme): ChatTCU único provider em produção.

## 7. Critérios de aceitação e métricas (recorte)

- **CA-FUN-03:** 2 rodadas completas da Stranger Room exercitadas (Não verificável
  no v1 — cenário (c) do plano de integração da v2).
- **CA-FUN-06:** retomada pós-alerta crítico (`retomar_apos_alerta`).
- **CA-QUA-02/05:** relatório institucional/impessoal; dilemas com raciocínio
  ponderado — exigem avaliação humana; metas da consolidação (M3).
- **MET-08:** aderência ao protocolo Stranger Room (avaliação qualitativa).
- **MET-09:** impessoalidade — automática via Motor de Saída (ocorrências = 0).
- Gabarito de referência: `docs/conformidade/gabarito_mod_sint_001.md`.

## 8. Lições do piloto v1 (dossiê + CLAUDE.md)

1. **F-Mycroft-01** — deriva de modelo na documentação: `agent.md` dizia
   `claude-sonnet-4-6`; produção usa `gpt-5.5-thinking` via `agents_spec.yaml`.
   **Lição v2:** `agents_spec.yaml` é a única fonte da verdade de modelo; o
   `agent.md` documenta, não configura.
2. **F-Mycroft-02** — `mapear_pontos` não roda no ciclo real (modo monolítico de
   Sherlock); manter apenas para bancada.
3. **F-Mycroft-03** — filtro de segurança do ChatTCU bloqueou `avaliar_sherlock`
   quando o input continha PII propagada; calibração anti-PII no `soul.md`.
   **Lição v2:** a regra anti-PII é parte do contrato de prompt.
4. **Rodada noturna 2026-06-11** — fallback determinístico de Sherlock passou na
   completude e Mycroft **aprovou um consolidado vazio**; ciclo chancelado
   indevidamente. Correção: `is_fallback` em `models.py` + gate no Orquestrador
   **antes** da Stranger Room. **Lição v2:** Mycroft nunca deve receber para
   revisão um output marcado `is_fallback` — o gate é do Orquestrador, mas o
   contrato de Mycroft assume inputs genuínos.
5. **Caso real de Stranger Room (baseline):** crítica única localizada sobre
   `NV-GLOBAL-01` (divergência relatório × JSON do dashboard), resposta
   fundamentada de Sherlock, decisão ACATADO — golden case do cenário (b) de
   integração.
6. **Gap de qualidade RF-MY-07** (item P1 nº 5): regras de escrita do consolidado
   (≤4 linhas/parágrafo, valores abreviados, coluna Fonte) — candidata a
   "Decisão v2" de calibração na fatia M3.

## 9. Registro de gates (preencher durante a reescrita)

| Gate | Fatia | Critérios (Metodologia §5) | Data | Chancela | Observações |
|---|---|---|---|---|---|
| G-M1 | M1 — Base + tasking | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | — |
| G-M2 | M2 — SR Watson + transição | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | — |
| G-M3 | M3 — SR Sherlock + consolidação | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | — |
| G-M4 | M4 — Fase de Entrega | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | — |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
