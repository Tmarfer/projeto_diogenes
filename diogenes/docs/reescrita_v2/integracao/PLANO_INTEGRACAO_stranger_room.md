---
documento: Plano de Integração — Stranger Room (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_Piloto_Diogenes_v01.md (Bloco 3.7, RF-SR; Caso de Uso 3)
  - docs/conformidade/06_strangers_room.md (6/6 Conforme no v1)
  - docs/conformidade/gabarito_mod_sint_001.md
  - src/diogenes/orchestrator/{stranger_room,orchestrator,states}.py
  - docs/reescrita_v2/{mycroft,watson,sherlock}/SDD_derivado_*.md
---

# Plano de Integração — Stranger Room

> Fase final da Reescrita Guiada v2 (passo 8 da [Metodologia](../00_METODOLOGIA.md)).
> Com os quatro agentes reescritos e chancelados (G-M1..G-M4, G-IR, G-WA, G-SH),
> esta fase integra tudo e testa o ponto mais crítico do sistema: o protocolo
> da Stranger Room — revisão Mycroft ↔ Watson/Sherlock, máximo de 2 rodadas,
> imutabilidade absoluta. Pacote de Trabalho: PT-INT-1 (Seção 4).

---

## 1. O que está sendo integrado

| Peça | Origem | Papel na integração |
|---|---|---|
| `MycrooftAgent` (M1–M4) | PT-MY-1..4 | avalia, critica, fixa decisão, consolida |
| `stranger_room.py` v2 | PT-MY-2 | persistência imutável dos artefatos de revisão |
| `WatsonAgent` + `file_prep` | PT-WA-1 | apresenta e responde críticas (fase `watson_integridade`) |
| `SherlockAgent` + contexto | PT-SH-1 | apresenta e responde críticas (fase `sherlock_validacao`) |
| Irene v2 | PT-IR-1 | catálogo real (substitui a fixture usada em M1) |
| Orquestrador (v1, não reescrito) | `orchestrator.py` | máquina de estados, loop de rodadas (MAX_RODADAS=2), gates |

**Invariante de protocolo:** os arquivos da sala
(`01_apresentacao.md`, `02_critica_mycroft_r1.md`, `03_resposta_r1.md`,
`04_critica_mycroft_r2.md`, `05_resposta_r2.md`, `99_decisao_final.md`) com
frontmatter YAML (`cycle_id`, `phase`, `author`, `role`, `round`, `timestamp`,
`content_hash`) — **qualquer mudança de formato exige versionamento novo do
protocolo** (Metodologia §6).

## 2. Cenários de integração (obrigatórios)

Todos referenciam RF-SR-01..06 e `06_strangers_room.md`. Executar primeiro com
mocks (pytest-httpx), depois com ChatTCU real sobre MOD_SINT_001.

| # | Cenário | O que comprova | RF / fonte |
|---|---|---|---|
| (a) | **Aprovação direta sem rodada** — agente apresenta, Mycroft emite `APROVADO`, sala contém `01` + `99` apenas | branching parseável; decisão com fundamentação curta | RF-MY-03, RF-SR-02 |
| (b) | **1 rodada: crítica → resposta → aprovação** — usar como golden o caso real do baseline: crítica única sobre `NV-GLOBAL-01` (relatório × JSON), resposta de Sherlock sustentando o mapeamento do Template 2, decisão ACATADO | crítica localizada (regra da crítica única); leitura sequencial reconstrói a deliberação | RF-MY-04, RF-SR-05; dossiê Mycroft §3 |
| (c) | **2 rodadas → martelo forçado** — Mycroft refuta 2×; após `05_resposta_r2.md`, o Orquestrador impede 3ª chamada e força `fixar_decisao` | Art. 8 absoluto; `99_decisao_final.md` cita as duas rodadas | RF-OR-04, RF-MY-05; CA-FUN-03 (não verificado no v1 — **a v2 deve exercitá-lo deliberadamente**, plantando dilema controverso no MOD_SINT_001 se necessário, cf. PRD Caso de Uso 3) |
| (d) | **Imutabilidade** — tentativa de reescrever qualquer arquivo da sala aborta com `StrangerRoomWriteError`; conteúdo intacto | Art. 11 / RF-SR-04 | `test_stranger_room.py` |
| (e) | **Gate de fallback ANTES da escrita** — output com `is_fallback=True` não entra na sala; ciclo pausa em `PAUSADO_LESTRADE` com marker `_runtime/fallback_{fase}.md`; `retomar_apos_fallback()` re-executa a fase (Watson volta dos checkpoints) e a sala permanece válida | a fase é re-executável porque a sala não foi contaminada | correções 2026-06-11; `test_resiliencia_agentes.py` |
| (f) | **Art. 9 — alerta crítico → Auto-Lestrade** — Watson com alertas CRITICA → `MC_alerta_critico_lestrade.md` + estado `AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO`; no autorun, `LESTRADE_PROCEED_AUTHORIZED` retoma e Sherlock inicia | notificação registrada no trace; metadados no índice | RF-OR-05, RF-MY-06, CA-FUN-06 |
| (g) | **Ciclo completo MOD_SINT_001 pontuado** — A1 ponta a ponta com a v2 integrada; pontuar contra `gabarito_mod_sint_001.md` (4 INC primárias + 2 latentes + 6 verdadeiros negativos): MET-04 ≥ 70%, MET-05 < 15%, MET-07 ≥ baseline, MET-09 = 0 ocorrências | a v2 não regrediu em relação ao v1 calibrado | protocolo da Onda 2 em `11_aceitacao_metricas.md` |
| (h) | **Regra da crítica única** — em toda avaliação `CRITICA`, exatamente um ponto questionado (o de maior impacto); crítica vaga ou múltipla é falha de integração | contrato de prompt de `avaliar_agente` respeitado fim-a-fim | RF-MY-04; contrato Mycroft |

**Metadados agregados (todas as execuções):** ao final de cada fase, o
`audit_index.csv` registra rodadas executadas, overrule, alerta crítico
(watson_integridade) e dilema encaminhado (sherlock_validacao) — RF-SR-06.

## 3. Sequência de execução da fase

1. **Merge interno na branch:** consolidar PT-MY-1..4, PT-IR-1, PT-WA-1, PT-SH-1
   em `feat/reescrita-v2`; `pytest tests/` completo verde; `ruff check` limpo.
2. **Cenários (a)–(f), (h) com mocks** (pytest-httpx + CliRunner) — rápidos e
   determinísticos.
3. **Bancada com ChatTCU:** `diogenes bench smoke` + `bench preview` de todos os
   call_types (diff byte a byte contra v1) + `bench call` pontuais.
4. **Cenário (g):** `diogenes autorun --module MOD_SINT_001 --activity 1` (sem
   `--auto-seal` na primeira execução); pontuar contra o gabarito; registrar no
   histórico do gabarito (RF-HF-05).
5. **Cenário (c) real:** se nenhuma fase exercitou 2 rodadas, plantar a
   controvérsia no MOD_SINT_001 e repetir (PRD, Caso de Uso 3: a não exercitação
   plena do protocolo descumpre o critério de sucesso).
6. **Gate G-INT:** checklist abaixo + chancela → merge de `feat/reescrita-v2` na
   `main` encerra a Reescrita Guiada v2.

## 4. Pacote de Trabalho

### Pacote de Trabalho PT-INT-1 — Integração e teste da Stranger Room
**Fatia/Fase:** Integração final | **Pré-requisitos:** G-M1..G-M4, G-IR, G-WA, G-SH | **Status:** A INICIAR

#### Objetivo
Integrar os quatro agentes v2 sob o Orquestrador e comprovar os 8 cenários da
Seção 2, encerrando a reescrita com um ciclo MOD_SINT_001 pontuado contra o
gabarito.

#### Contexto mínimo (leitura obrigatória do devsquad)
Este plano + `docs/conformidade/06_strangers_room.md` +
`docs/reescrita_v2/00_METODOLOGIA.md` (Seções 5, 6 e 8) + os 4 SDD_derivados
(Seções "Erro e resiliência").

#### Escopo — entregáveis
- Suíte de integração cobrindo os cenários (a)–(f) e (h) com mocks.
- Execução assistida dos passos 3–5 da Seção 3 (bancada + ciclo real — quem roda
  os comandos é o desenvolvedor; o devsquad prepara scripts/fixtures).
- Relatório de pontuação do cenário (g) registrado no histórico do gabarito.
- **Fora de escopo:** mudanças de comportamento nos agentes (qualquer ajuste
  volta ao Pacote do agente dono); mudanças de formato dos arquivos da sala.

#### Arquivos de referência (somente leitura)
`src/diogenes/orchestrator/{orchestrator,states,stranger_room}.py`,
`tests/integration/test_ciclo_completo.py`, `tests/unit/test_stranger_room.py`,
`tests/unit/test_resiliencia_agentes.py`,
`docs/conformidade/gabarito_mod_sint_001.md` (uso restrito — nunca expor aos agentes).

#### Arquivos a produzir (v2)
`tests/integration/test_integracao_stranger_room_v2.py` (ou extensão dos
existentes) na branch `feat/reescrita-v2`.

#### Critérios de aceite (= gate G-INT)
- [ ] Cenários (a)–(h) comprovados (a–f, h por teste; g por execução real pontuada).
- [ ] `pytest tests/` completo verde; suíte v1 inteira preservada.
- [ ] `bench preview` byte-idêntico ao v1 em todos os call_types (ou divergência registrada em "Decisões v2").
- [ ] MET-04 ≥ 70% e ≥ baseline; MET-05 < 15%; MET-09 = 0; sem regressão de MET-07.
- [ ] `audit_index.csv` com metadados agregados corretos (RF-SR-06).
- [ ] Chancela do desenvolvedor registrada abaixo → merge na `main`.

#### Prompt sugerido (colar no Copilot devsquad)
> Fase de integração da reescrita v2 do projeto Diógenes (branch
> `feat/reescrita-v2`). Os 4 agentes (Mycroft, Irene, Watson, Sherlock) já foram
> reescritos e aprovados individualmente. Sua tarefa: escrever a suíte de
> integração da Stranger Room cobrindo os cenários (a)–(f) e (h) de
> `docs/reescrita_v2/integracao/PLANO_INTEGRACAO_stranger_room.md` — aprovação
> direta; 1 rodada (golden: caso NV-GLOBAL-01 do baseline); 2 rodadas com
> martelo forçado (Art. 8 — a 3ª chamada deve ser impedida pelo Orquestrador);
> imutabilidade (`StrangerRoomWriteError`); gate de `is_fallback` ANTES da
> escrita na sala com retomada da fase; alerta crítico → Auto-Lestrade (Art. 9);
> regra da crítica única. Use pytest-httpx para mockar o LLM (padrão de
> `tests/integration/test_ciclo_completo.py`) e CliRunner para os comandos.
> Restrições: não altere o comportamento dos agentes nem o formato dos arquivos
> da sala; não toque no gabarito (`gabarito_mod_sint_001.md` é uso restrito);
> síncrono, sem threads. Entregável:
> `tests/integration/test_integracao_stranger_room_v2.py` com todos os cenários
> verdes.

#### Registro do gate G-INT

| Critério | Status | Data | Observações |
|---|---|---|---|
| Cenários (a)–(h) | ☐ | — | — |
| Suíte completa verde | ☐ | — | — |
| Prompts byte-idênticos | ☐ | — | — |
| Métricas (g) | ☐ | — | — |
| Metadados RF-SR-06 | ☐ | — | — |
| **Chancela final (fim da v2)** | ☐ | — | — |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
