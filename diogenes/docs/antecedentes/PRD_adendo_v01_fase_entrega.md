---
documento: PRD — Adendo v0.1 — Fase de Entrega e Subcomandos Complementares
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
data: 2026-06-10
uso: Interno Restrito
referencia: PRD_Piloto_Diogenes_v01.md (documento base)
---

# **PRD — Adendo v0.1 — Fase de Entrega**

## Propósito deste adendo

O PRD v0.1 (R-13, linhas 580 e 1092) declarou a conversão dos relatórios para DOCX no
padrão Design System TCU-CBS como **pós-piloto**, delegada ao motor gerador do projeto maior.
Durante o desenvolvimento do piloto, a decisão foi tomada de **vendorizar o motor para
dentro do Diógenes** — eliminando a dependência de caminho OneDrive em runtime e permitindo
a execução completa em ambiente isolado.

Este adendo formaliza essa evolução com novos requisitos funcionais (`RF-EN-*`, `RF-AU-*`,
`RF-RP-*`, `RF-BE-*`, `RF-IR-*`) e resolve a tensão com R-13 declarando a Fase de Entrega
como **Evoluído** (intenção preservada, meio de execução incorporado ao sistema).

---

## Bloco 1 — Requisitos da Fase de Entrega (`RF-EN-*`)

**RF-EN-01.** O sistema deve expor o subcomando `diogenes deliver --cycle {id}` que,
dado um ciclo em qualquer estado pós-`confirm-manifest`, gera os artefatos institucionais
em `workspace/cycles/{id}/output/entrega/`. O parâmetro `--no-qa` pula a etapa de QA
(`avaliar_entrega`); `--no-assets` pula PDF/PNG da ficha síntese (requer Playwright).

**RF-EN-02.** O motor de entrega deve ser **determinístico**: valores numéricos entram
exclusivamente via `ExtractorFinanceiro` (openpyxl, lendo células da planilha indicadas
pelo mapa de extração). Nenhum valor numérico é transcrito pelo LLM — o agente descreve
localizações, nunca conteúdos. Violações desta regra são detectáveis por revisão do
`entrega_mapa_extracao.json` (que nunca contém dígitos em posição de valor).

**RF-EN-03.** O mapa de extração (`entrega_mapa_extracao.json`) deve ser persistido em
`output/` e auditável por Lestrade sem acesso à planilha. Contém apenas nomes de aba e
referências de célula/intervalo. Pode ser produzido pelo LLM (call_type `mapear_dados_modulo`
do Mycroft) ou autorado manualmente. Sua ausência gera aviso mas não bloqueia a entrega —
os artefatos são gerados com a camada de auditoria.

**RF-EN-04.** A Fase de Entrega deve produzir os seguintes artefatos mínimos:

| Artefato | Formato | Conteúdo |
|---|---|---|
| Dashboard | HTML (inline) | KPIs financeiros, tabela de inconsistências, estado do ciclo |
| Apêndice | DOCX (padrão TCU-CBS) | Proposta, arquivos, testes, inconsistências numeradas |
| Relatório Consolidado | DOCX | Texto do Mycroft consolidado (higienizado por RF-EN-06) |
| Relatório Narrativo | DOCX | Narrativa estruturada com blocos financeiros e ocorrências |
| Relatório Pré-Atendimento | DOCX | Batimento inconsistências × posição declarada da RFB |
| Ficha Síntese | HTML + PDF + PNG | Resumo executivo A4 bifolha (PDF/PNG requerem Playwright) |

**RF-EN-05.** Após gerar os artefatos, o sistema deve invocar Mycroft (call_type
`avaliar_entrega`) para QA de aderência. O veredito (`APROVADO` \| `REQUER_AJUSTE`)
deve ser registrado no `audit_index.csv` e no `manifesto_entrega_*.json`. `--no-qa`
pula esta etapa e registra veredito como `NAO_AVALIADO`.

**RF-EN-06.** Todo texto LLM incorporado nos artefatos externos (Relatório Narrativo,
Relatório Consolidado, Relatório Pré-Atendimento) deve passar pela função
`sanitizar_delivery_text()` (`motors/motor_saida.py`) antes de ser convertido para DOCX.
A função aplica as etapas de higienização do Motor de Saída (remoção de marcas internas,
substituições institucionais, colapso de brancos excessivos) sem requisito de workspace.

**RF-EN-07.** O relatório `.md` chancelado pela Lestrade (`relatorio_preliminar_{id}.md`)
é e permanece a fonte primária do ciclo. A Fase de Entrega nunca o sobrescreve — lê-o
como entrada para `p.relatorio_markdown`. O DOCX consolidado é derivado desse campo.
Toda rastreabilidade retroage ao `.md` versionado no workspace.

---

## Bloco 2 — Requisitos de Execução Automatizada (`RF-AU-*`)

**RF-AU-01.** O sistema deve expor o subcomando `diogenes autorun --module {id} --activity
{n}` que executa o ciclo completo de forma autônoma: `start → confirm-manifest →
[execução dos agentes] → verify-output → deliver → seal`. O flag `--auto-seal` permite
que o ciclo seja chancelado automaticamente após verificação limpa do Motor de Saída.

**RF-AU-02.** O `autorun` deve abrir o painel HTML local (`diogenes report --format html`)
ao iniciar, permitindo acompanhamento ao vivo pela Lestrade. O painel é atualizado a cada
evento pelo `EventLogger`.

**RF-AU-03.** O `autorun` deve respeitar `DIOGENES_DEV_MODE=true`: em DEV_MODE, retries
e timeouts são curtos, `seal` automático é bloqueado, e `IRENE_C4_SAMPLE_N` é honrado.

---

## Bloco 3 — Requisitos do Painel Local (`RF-RP-*`)

**RF-RP-01.** O sistema deve expor o subcomando `diogenes report --cycle {id}` que exibe
um relatório do ciclo no terminal (Markdown) ou no browser (HTML com `--format html`).
O HTML inclui avatares dos agentes, tabela de LLM calls com latência/tokens, linha do
tempo de estados, e lista de ocorrências detectadas.

**RF-RP-02.** O `EventLogger` deve regenerar `_cycle_dir/report.html` a cada chamada de
`log()` (best-effort — falhas de I/O são silenciosas para não interromper o ciclo).
O painel deve suportar auto-refresh via `<meta http-equiv="refresh">`.

---

## Bloco 4 — Requisitos da Bancada Cirúrgica (`RF-BE-*`)

**RF-BE-01.** O sistema deve expor o grupo de subcomandos `diogenes bench` para testes
isolados de prompt/modelo/conectividade sem rodar o ciclo completo:

| Subcomando | Função |
|---|---|
| `bench smoke` | Verifica conectividade com o provider configurado |
| `bench validate-models` | Valida os modelos listados em `agents_spec.yaml` |
| `bench preview {agente} --call-type {ct}` | Monta o prompt sem chamar o LLM |
| `bench call {agente} --call-type {ct} --prompt {texto}` | Chamada LLM isolada |

**RF-BE-02.** O `bench pipeline` deve herdar `DIOGENES_CORPUS_JURIDICO_DIR` do `.env`
quando `--legal-corpus` não for fornecido.

---

## Bloco 5 — Requisitos da Fase Irene (`RF-IR-*`)

**RF-IR-01.** O sistema deve suportar a fase de catalogação semântica Irene (C1-C5),
habilitada por `DIOGENES_IRENE_HABILITADO=true`. Irene opera como biblioteca
(`executar_irene()` em `irene.py`) invocada pelo Orquestrador antes da fase Watson.

**RF-IR-02.** Irene deve reutilizar catálogo existente quando `versao_catalogo ≥
VERSAO_IRENE_MINIMA` — evitando reprocessamento. `IRENE_ERRO_FATAL` transita o
ciclo para `ABORTADO_FALHA_AGENTE`; `IRENE_BLOQUEADO` é não-fatal (Watson recebe
o catálogo com ressalvas).

**RF-IR-03.** `IRENE_C4_SAMPLE_N` limita a catalogação C4/C5 a N abas, honrado apenas
em `DEV_MODE`. Em produção, todas as abas são catalogadas.

---

## Resolução de tensões com o PRD v0.1

| Cláusula PRD | Status | Resolução |
|---|---|---|
| R-13 (linha 580): conversão DOCX pós-piloto | **Evoluído** | Motor vendorizado (delivery/vendor/tcu/) — intenção de isolamento preservada, execução incorporada |
| R-13 (linha 1092): integração ao motor externo como tarefa pós-piloto | **Evoluído** | Eliminada a dependência de caminho OneDrive; o Diógenes é auto-suficiente |
| Ausência de RF para `autorun`, `report`, `bench`, Irene | **Regularizado** | RF-AU-*, RF-RP-*, RF-BE-*, RF-IR-* neste adendo |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
