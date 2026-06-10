# Gaps do SDD — onde o documento diverge do código

> `docs/sdd/SDD_Piloto_Diogenes_v01.md` (v0.1, 2026-05-07) vs. código em 2026-06-09
> Regra de decisão por item: **quem está certo — o SDD ou o código?**

## Diagnóstico geral

O SDD tem os **14 blocos escritos** (linhas 26-5511), mas o cabeçalho declara
"Em construção (Bloco 1 de 14)" — desatualizado e induz a erro. O documento
**antecede três evoluções estruturais** do sistema:

1. **Fase Irene** (catalogação semântica C1-C5) — zero menções no SDD.
2. **Migração OpenRouter → ChatTCU/MSAL** — 56 menções a OpenRouter; zero a ChatTCU.
3. **Fase de Entrega** (`diogenes deliver`) — zero menções.

Em todos os casos, **o código está certo** (decisões de governança e de produto
posteriores ao SDD). O SDD é declarado "fonte da verdade" pelo CLAUDE.md — esta
defasagem precisa ser fechada para que a declaração volte a ser verdadeira.

## Itens por bloco

| Bloco | Divergência | Quem está certo | Ação | Prio | Onda |
|---|---|---|---|---|---|
| Cabeçalho | "Em construção (Bloco 1 de 14)" com 14 blocos escritos | Código/realidade | Atualizar status para "Blocos 1-14 consolidados; revisão v0.2 em curso" | P2 | 3 |
| Bloco 3 (Stack) | Não lista python-docx, matplotlib, playwright, duckdb, msal, requests, pdfminer.six | Código (`pyproject.toml` justifica cada uma) | Atualizar tabela de dependências | P2 | 3 |
| Bloco 4 (Config) | Descreve `DIOGENES_ENV` + `DIOGENES_LLM_API_KEY/BASE_URL` como seleção de provider | Código (`DIOGENES_LLM_PROVIDER`; MSAL sem API key) | Reescrever seção de variáveis; documentar `DIOGENES_IRENE_*`, `DIOGENES_CORPUS_JURIDICO_DIR`, `DIOGENES_DEV_MODE`, `DIOGENES_SSL_VERIFY` | P1 | 3 |
| Bloco 6 (LLMClient) | OpenRouter como provider do piloto; sem governança | Código (`llm/base.py` guardião: ChatTCU único em produção, OpenRouter só sob pytest) | Reescrever: ChatTCU/MSAL como provider primário, governança bloqueante, duas assinaturas de `get_llm_client()` | P1 | 3 |
| Bloco 8 (Orquestrador) | Máquina de estados sem `AGUARDANDO_IRENE`/`IRENE_CONCLUIDA`/`AGUARDANDO_COMPLETUDE`/estados de entrega | Código (`states.py`) | Atualizar diagrama de estados e transições | P1 | 3 |
| Bloco 9 (Agentes) | Sem call_types condicionais (`validacao_planilha_rn*`), sem `mapear_pontos`, sem call_types de entrega; sem Irene | Código | Adicionar tabela completa de call_types por agente; **novo sub-bloco: Irene** (C1-C5, DuckDB, catálogo reutilizável ≥1.3.0, ChatTCU em C4) | P1 | 3 |
| Bloco 11 (Motor de Saída) | Decisão tripla de Lestrade | Código (auto-higienização + `seal --accept-occurrences`) — divergência deliberada já registrada | Documentar o fluxo real | P2 | 3 |
| Bloco 12 (CLI) | Sem `autorun`, `report`, `deliver`, `complete-sherlock`, grupo `bench` | Código | Atualizar tabela de subcomandos | P2 | 3 |
| Bloco 13 (Testes) | Baseline desatualizada | Código (305 testes) | Atualizar contagens e estratégia (pytest-httpx, golden tests da Onda 1) | P3 | 3 |
| Bloco 14 (Roadmap) | Fases A/B com modelos free/baratos OpenRouter | Realidade (bench GPT-5.4/5.5/Claude via ChatTCU; free abandonado) | Reescrever histórico das fases executadas | P2 | 3 |

## Blocos novos a escrever (v0.2)

| Bloco | Conteúdo | Semente | Prio | Onda |
|---|---|---|---|---|
| **Bloco 15 — Fase de Entrega** | `motor_entrega.py` (determinístico), `delivery/` (parsing, extractor openpyxl, builders, dashboard, pacote), vendor TCU (`vendor/tcu/` + política de revendorização do VENDOR.md), mapa de extração (localizações-nunca-valores), call_types LLM (`mapear_dados_modulo`, `redigir_apendice`, `avaliar_entrega`), QA, hook no autorun | `delivery/MAPA_EXTRACAO.md` + `VENDOR.md` | P1 | 3 |
| **Bloco 16 — Painel local (reports/)** | `EventLogger` → `report.html` ao vivo; `diogenes report`; equivalente LangSmith sem SaaS | `reports/cycle_report.py` | P2 | 3 |
| **Bloco 17 — Motor de Perfilamento** | Análise estatística determinística CSV/XLSX via DuckDB pré-Watson | `motors/motor_perfilamento.py` (581 linhas, 44+ testes) | P2 | 3 |

## Tensão com o PRD — conversão DOCX (R-13)

PRD linhas 84, 580 (R-13) e 1092 declaram a conversão DOCX como **pós-piloto**,
delegada ao motor do projeto maior. A realidade: o motor foi **vendorizado para
dentro** do Diógenes (decisão boa — elimina dependência de caminho OneDrive em
runtime). Resolução formal:

1. Matriz marca a Fase de Entrega como `Evoluído` em relação a R-13 (não é violação).
2. **PRD-adendo (ou PRD v02)** com novos requisitos `RF-EN-*` cobrindo a Fase de
   Entrega — proposta mínima:
   - RF-EN-01: invocação via `diogenes deliver --cycle` (e hook automático no autorun)
   - RF-EN-02: motor determinístico; valores numéricos só via extractor (nunca pelo LLM)
   - RF-EN-03: mapa de extração com localizações, persistido e auditável
   - RF-EN-04: artefatos mínimos (Dashboard, Apêndice, Consolidado, Narrativo, Pré-Atendimento, Ficha)
   - RF-EN-05: QA via `avaliar_entrega` com veredito registrado
   - RF-EN-06: texto LLM da entrega varrido pelo Motor de Saída antes de virar DOCX *(a implementar — Onda 3)*
   - RF-EN-07: relatório selado (`.md`) permanece a fonte; DOCX é derivado
3. Mesmo tratamento para `autorun`, `report`, `bench` e Irene (RFs `RF-AU/RP/BE/IR-*`).
