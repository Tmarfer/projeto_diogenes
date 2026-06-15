---
documento: Metodologia — Reescrita Guiada v2 (agente por agente)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_Piloto_Diogenes_v01.md (+ adendos v01 e v02)
  - docs/sdd/SDD_Piloto_Diogenes_v01.md
  - docs/conformidade/00_INDICE.md (matriz de conformidade)
  - docs/auditoria_agentes/{mycroft,irene,watson,sherlock}/{contrato,dossie}.md
  - docs/agentes/{mycroft,irene,watson,sherlock}/{agent,soul,skills,heartbeat}.md
---

# Metodologia — Reescrita Guiada v2

> **O que é este documento:** o plano mestre do novo ciclo de desenvolvimento do
> Diógenes — uma **reescrita guiada (v2)**, agente por agente, executada
> **manualmente pelo desenvolvedor** com apoio dos agentes do GitHub Copilot
> (`/agents devsquad`). O código v1 (maduro: 74/77 RFs Conforme, 216+ testes,
> ciclo real MOD_010 concluído) serve de **referência canônica**, não de rascunho.
> Todos os demais documentos de `docs/reescrita_v2/` derivam deste.

---

## Sumário

- [1. Princípios da metodologia](#1-princípios-da-metodologia)
- [2. Estrutura documental](#2-estrutura-documental)
- [3. Fatias de Mycroft](#3-fatias-de-mycroft)
- [4. Sequenciamento estanque e gates](#4-sequenciamento-estanque-e-gates)
- [5. Critérios de gate (padrão único)](#5-critérios-de-gate-padrão-único)
- [6. Fase de integração — Stranger Room](#6-fase-de-integração--stranger-room)
- [7. Decisões fixadas](#7-decisões-fixadas)
- [8. Protocolo de trabalho com o devsquad](#8-protocolo-de-trabalho-com-o-devsquad)
- [9. Templates dos documentos derivados](#9-templates-dos-documentos-derivados)

---

## 1. Princípios da metodologia

1. **Um agente por vez, de forma estanque.** O desenvolvimento só avança para o
   próximo agente quando o anterior passa pelo seu gate. Exceção única: Mycroft,
   que é desenvolvido em **4 fatias intercaladas** seguindo a ordem do ciclo real
   (Seção 3) — quando o fluxo do ciclo "chama" o próximo agente, Mycroft pausa,
   o agente chamado é desenvolvido por completo, e Mycroft retoma na fatia seguinte.

2. **PRD_derivado e SDD_derivado por agente.** Cada agente ganha dois documentos
   que destilam, para o seu recorte: os RFs do PRD mestre + adendos, os blocos
   relevantes do SDD, o status da matriz de conformidade, o contrato e o dossiê
   de auditoria, e os 4 arquivos de definição (`agent.md`, `soul.md`, `skills.md`,
   `heartbeat.md`). O desenvolvedor e o devsquad trabalham **só com os derivados** —
   os documentos mestres viram fonte de consulta, não de trabalho.

3. **Os 4 `.md` do agente continuam vivos em runtime.** O sistema lê
   `docs/agentes/{agente}/*.md` do filesystem a cada chamada LLM. Os derivados
   **consolidam** esses arquivos como insumo de desenvolvimento (heartbeat
   transcrito verbatim por ser contrato de prompt; soul/skills sintetizados) —
   **não os substituem**.

4. **Handoff pronto para o devsquad.** Cada derivado termina com seções de
   **Pacote de Trabalho** (`PT-<SIGLA>-<n>`): contexto mínimo, escopo, arquivos
   de referência v1, arquivos a produzir, critérios de aceite e prompt sugerido
   para colar no Copilot. O desenvolvedor é o integrador e o revisor final
   (papel de Lestrade da reescrita).

5. **O comportamento canônico é o do v1.** Prompt byte-idêntico, parsing
   compatível com os campos de cabeçalho monitorados pelo Orquestrador, e testes
   v1 como régua. Toda divergência deliberada é registrada na seção
   "Decisões v2" do SDD_derivado correspondente — nunca implícita.

---

## 2. Estrutura documental

```
docs/reescrita_v2/
  00_METODOLOGIA.md                     ← este documento (plano mestre)
  mycroft/
    PRD_derivado_mycroft.md             ← o "o quê" do agente
    SDD_derivado_mycroft.md             ← o "como" + PT-MY-1..4 (um Pacote por fatia)
  irene/
    PRD_derivado_irene.md
    SDD_derivado_irene.md               ← PT-IR-1
  watson/
    PRD_derivado_watson.md
    SDD_derivado_watson.md              ← PT-WA-1
  sherlock/
    PRD_derivado_sherlock.md
    SDD_derivado_sherlock.md            ← PT-SH-1
  integracao/
    PLANO_INTEGRACAO_stranger_room.md   ← cenários de integração + PT-INT-1
```

**Por que 2 documentos por agente, e não 1 por fatia:** as fatias de Mycroft
compartilham soul, skills e o invocador (`MycrooftAgent`). Fatiar o conteúdo
documental criaria duplicação e risco de divergência; o fatiamento acontece nos
**Pacotes de Trabalho** ao final do SDD_derivado de Mycroft.

---

## 3. Fatias de Mycroft

Mycroft é o agente mais entrelaçado com o ciclo: seus call_types abrem, costuram
e fecham todas as fases. As fatias seguem a **ordem do fluxo real** do ciclo
(`Orchestrator.executar()` + Fase de Entrega):

| Fatia | Escopo (call_types) | O que entrega |
|---|---|---|
| **M1 — Base do invocador + tasking** | leitura dos 4 `.md`, construção de prompt (`system = soul + skills`, `user = heartbeat[call_type] + inputs`), parsing base, `definir_tasks_watson` | Mycroft capaz de abrir o ciclo: internalizar manifesto, detectar Planilha de Verificação, incorporar o catálogo Irene (via **fixture real** de ciclo baseline — é o que permite desenvolver M1 antes de Irene) e emitir `MC_tasks_watson.md` |
| **M2 — Stranger Room Watson + transição** | `avaliar_agente` (avaliar_watson), `fixar_decisao` (Regra do Martelo, Art. 8), protocolo Stranger Room (persistência imutável, `StrangerRoomWriteError`), inspeção de alerta crítico (Art. 9 → Auto-Lestrade), `montar_pacote_sherlock` | Revisão completa da fase `watson_integridade` + pacote integrado para Sherlock (com propagação de "Nota metodológica com alteração") |
| **M3 — Stranger Room Sherlock + consolidação** | `avaliar_sherlock`, `fixar_decisao_sherlock` (reuso do protocolo de M2), `consolidar` (verificação das 11 seções, impessoalidade, histórico A1→A2, overrules) | Fechamento do ciclo: `MC_decisao_sherlock.md` + `MC_consolidado.md` + `relatorio_preliminar_{id}.md` |
| **M4 — Fase de Entrega** | `mapear_dados_modulo` (blueprint sem valores numéricos), `avaliar_entrega` (QA APROVADO\|REQUER_AJUSTE), `redigir_apendice` | Os call_types LLM do `diogenes deliver` (RF-EN-03/05 do adendo v01) |

> **Nota de fluxo:** `mapear_dados_modulo` e `avaliar_entrega` pertencem ambos à
> Fase de Entrega (rodam no `deliver`, **depois** de `consolidar`) — por isso
> formam a fatia M4, e não se distribuem entre M1 e M3.

---

## 4. Sequenciamento estanque e gates

```
1. M1  (Mycroft, fatia 1)            → gate G-M1
2. Irene  (completa, C1–C5)          → gate G-IR
3. Watson (completo)                 → gate G-WA
4. M2  (Mycroft, fatia 2)            → gate G-M2
5. Sherlock (completo)               → gate G-SH
6. M3  (Mycroft, fatia 3)            → gate G-M3
7. M4  (Mycroft, fatia 4 — Entrega)  → gate G-M4
8. Integração — Stranger Room        → gate G-INT   (fim da v2)
```

A ordem espelha o ciclo real: Irene cataloga → Mycroft define tasks → Watson
analisa → Mycroft revisa e monta pacote → Sherlock valida → Mycroft revisa,
consolida e entrega. Duas dependências cruzadas resolvidas por fixture:

- **M1 antes de Irene:** o catálogo (`irene_catalog.yaml`) entra em M1 como
  fixture real de ciclo baseline — o contrato do catálogo é estável.
- **Watson antes de M2:** `watson.responder_critica` recebe a crítica de Mycroft
  como input; uma crítica real do baseline (`02_critica_mycroft_r1.md`) serve de
  fixture até M2 existir.

**Regra de avanço:** nenhum trabalho do passo N+1 começa antes do gate do passo N
estar chancelado (checklist da Seção 5 preenchido no documento derivado do agente).

---

## 5. Critérios de gate (padrão único)

Um agente (ou fatia de Mycroft) é considerado **acabado** quando, cumulativamente:

| # | Critério | Como verificar |
|---|---|---|
| 1 | Todos os call_types/estágios do escopo implementados, com testes unitários equivalentes aos v1 passando | `pytest tests/` na branch v2 |
| 2 | **Prompt byte-idêntico ao v1** — ou divergência deliberada documentada em "Decisões v2" do SDD_derivado | `diogenes bench preview {agente} --call-type {ct}` na v1 e na v2; diff |
| 3 | Outputs parseiam contra os **campos de cabeçalho monitorados pelo Orquestrador** (`Alertas CRITICA: N`, `Nota metodológica com alteração detectada`, `Planilha de Verificação no pacote`, 11 seções de Sherlock), com defaults seguros quando ausentes | testes de parsing + inspeção |
| 4 | Checklist de RFs do PRD_derivado atestado item a item com evidência `arquivo:linha` | tabela preenchida no PRD_derivado |
| 5 | Comparação golden contra artefatos do ciclo baseline e/ou gabarito `MOD_SINT_001` quando aplicável | `docs/conformidade/gabarito_mod_sint_001.md` |
| 6 | **Chancela explícita do desenvolvedor** registrada no documento derivado (data + observações) | seção de gate do derivado |

---

## 6. Fase de integração — Stranger Room

A Stranger Room é o ponto de integração mais crítico (e o que mais impacta
Mycroft): protocolo imutável de revisão Mycroft ↔ Watson/Sherlock, máximo de
2 rodadas por fase (Art. 8), fixação de decisão obrigatória após a 2ª rodada.
No v1 está 6/6 Conforme (`docs/conformidade/06_strangers_room.md`) e protegida
por invariante — **na v2, qualquer mudança de formato dos arquivos da sala exige
versionamento novo do protocolo**, registrado em "Decisões v2".

Os cenários mínimos de integração (detalhados em
`integracao/PLANO_INTEGRACAO_stranger_room.md`):

(a) aprovação direta sem rodada; (b) 1 rodada crítica→resposta→aprovação;
(c) 2 rodadas → `fixar_decisao` forçado; (d) imutabilidade dos arquivos;
(e) gate de `is_fallback` ANTES da escrita na sala (fase re-executável);
(f) Art. 9 — alerta crítico → Auto-Lestrade; (g) ciclo completo MOD_SINT_001
pontuado contra o gabarito; (h) regra da crítica única.

---

## 7. Decisões fixadas

| Decisão | Valor | Racional |
|---|---|---|
| Natureza do ciclo | **Reescrita guiada (v2)** | Código v1 como referência canônica; derivados como especificação da nova versão |
| Onde vive o código v2 | **Branch dedicada `feat/reescrita-v2`, mesmo path `src/diogenes/`** | Testes e CLI atuais continuam servindo de régua; `main` intacta durante toda a reescrita; merge ao final (pós G-INT) |
| Fatias de Mycroft | **4 fatias** (M4 = Fase de Entrega) | `mapear_dados_modulo` e `avaliar_entrega` são ambos do `deliver` |
| Ferramenta de desenvolvimento | **GitHub Copilot `/agents devsquad`**, dirigido manualmente pelo desenvolvedor | Pacotes de Trabalho são o formato de handoff |
| Ordem dos agentes | **Mycroft (fatiado) → Irene → Watson → Sherlock → Integração** | Espelha o fluxo do ciclo real |

---

## 8. Protocolo de trabalho com o devsquad

1. **Abrir o Pacote de Trabalho** do passo corrente (no SDD_derivado do agente).
2. **Colar o prompt sugerido** no Copilot devsquad, anexando os arquivos de
   "Contexto mínimo" listados no Pacote.
3. **Restrições inegociáveis em todo prompt** (SDD Bloco 1.2 — repetidas em cada
   Pacote): código síncrono sem threads/asyncio; `config.py` único ponto de
   leitura de configuração; `models.py` sem imports internos; Stranger Room
   imutável (`StrangerRoomWriteError`); Motor de Saída sem LLM; ChatTCU único
   provider em produção; originais do pacote RFB nunca alterados.
4. **Revisar a entrega** contra os critérios de aceite do Pacote; rodar os
   testes; comparar prompts via `bench preview`.
5. **Preencher o gate** (Seção 5) no documento derivado e só então avançar.
6. Achados que mudem o contrato de um agente futuro → registrar desde já na
   seção "Decisões v2" do derivado daquele agente.

---

## 9. Templates dos documentos derivados

### 9.1 PRD_derivado_<agente>.md — o "o quê" (contrato com o auditor)

| # | Seção | Fonte primária |
|---|---|---|
| 1 | Identidade e missão | `soul.md` + bloco do agente no PRD mestre |
| 2 | Escopo do recorte (o que entra / o que NÃO entra; fronteiras com os outros agentes) | `soul.md` + `contrato.md` |
| 3 | Requisitos funcionais transcritos (RF-XX-*) com status v1 e gap conhecido | PRD mestre + adendos + `docs/conformidade/0N_<agente>.md` |
| 4 | Requisitos de interface (inputs/outputs; campos de cabeçalho monitorados) | SDD + CLAUDE.md + `contrato.md` |
| 5 | Limites constitucionais e regras hard | `soul.md`/`skills.md` + `contrato.md` |
| 6 | RNFs aplicáveis (recorte) | `docs/conformidade/10_rnf.md` |
| 7 | Critérios de aceitação e métricas (recorte CA-*/MET-*) | `docs/conformidade/11_aceitacao_metricas.md` + gabaritos |
| 8 | Lições do piloto v1 (achados, calibrações, episódios de resiliência) | `dossie.md` + CLAUDE.md |
| 9 | Registro de gate (checklist da Seção 5 + chancela) | este documento |

### 9.2 SDD_derivado_<agente>.md — o "como" (contrato com o devsquad)

| # | Seção | Fonte primária |
|---|---|---|
| 1 | Relação com o SDD mestre (blocos de origem) | SDD |
| 2 | Posição na arquitetura (quem chama / é chamado; estados) | SDD Bloco 1 + `orchestrator/states.py` |
| 3 | Invocador: classe, assinaturas, tabela call_types × parâmetros | código v1 + `contrato.md` + `agents_spec.yaml` |
| 4 | Consolidação dos 4 `.md` (heartbeat **verbatim**; soul/skills sintetizados) | `docs/agentes/<agente>/*.md` |
| 5 | Dataclasses e parsing (defaults seguros) | `models.py` + código v1 |
| 6 | Artefatos no filesystem (lê/escreve) | `contrato.md` + ciclo baseline |
| 7 | Fluxo de execução por call_type (condicionais, transições) | CLAUDE.md + `orchestrator.py` |
| 8 | Erro e resiliência (`is_fallback`, degradação, map-reduce, gates) | CLAUDE.md (correções 2026-06-11) + código v1 |
| 9 | **Decisões v2** (preservar / aberto à reescrita / divergências Evoluído) | matriz de conformidade + decisões do desenvolvedor |
| 10 | Testes de referência v1 | `tests/` |
| 11 | Pacote(s) de Trabalho | template 9.3 |

**Irene** usa os mesmos esqueletos com vocabulário adaptado: "estágios C1–C5" no
lugar de "call_types"; heartbeat verbatim apenas do estágio C4 (único com LLM).

### 9.3 Template do Pacote de Trabalho

```markdown
## Pacote de Trabalho PT-<SIGLA>-<n> — <título>
**Fatia/Fase:** ... | **Pré-requisitos:** <gates anteriores> | **Status:** A INICIAR

### Objetivo
1–3 frases.

### Contexto mínimo (leitura obrigatória do devsquad)
Este derivado (seções X–Y) + arquivos pontuais (heartbeat.md, agents_spec.yaml, ...).

### Escopo — entregáveis
Módulos, call_types/estágios, testes. **Fora de escopo:** o que NÃO tocar.

### Arquivos de referência v1 (somente leitura)
Caminhos do código atual.

### Arquivos a produzir (v2)
Na branch `feat/reescrita-v2`, mesmo path `src/diogenes/`.

### Critérios de aceite
Checklist verificável — espelha o gate (Seção 5 da Metodologia); lista os RFs cobertos.

### Prompt sugerido (colar no Copilot devsquad)
> Papel + contexto resumido + restrições inegociáveis (Seção 8.3 da Metodologia)
> + entregáveis + critérios de aceite.
```

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
