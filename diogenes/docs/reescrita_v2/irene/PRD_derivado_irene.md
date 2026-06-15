---
documento: PRD Derivado — Irene Adler (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - docs/antecedentes/PRD_adendo_v01_fase_entrega.md (RF-IR-01..03)
  - docs/auditoria_agentes/irene/{contrato,dossie}.md
  - docs/agentes/irene/{agent,soul,skills,heartbeat}.md
  - INTEGRACAO_DIOGENES.md
---

# PRD Derivado — Irene Adler

> Recorte para o escopo de Irene Adler, Agente de Catalogação Documental.
> **Atenção à natureza diferente:** Irene **não é agente LLM de ciclo** — é uma
> **biblioteca Python** (pipeline C1–C5) acionada pelo Orquestrador antes de
> Watson; só o estágio C4 chama LLM, e apenas com **metadados estruturais**.
> Este derivado usa o vocabulário "estágios C1–C5" no lugar de "call_types".
> O "como" está em [SDD_derivado_irene.md](SDD_derivado_irene.md).

---

## 1. Identidade e missão

Irene Adler cataloga, classifica e estrutura o terreno documental **antes** que
Watson analise e Sherlock valide: valida o que existe, perfila cada aba, verifica
fidedignidade CSV↔XLSX, classifica o papel funcional de cada aba e consolida o
catálogo. Sem Irene, Watson entra cego num conjunto de planilhas; com Irene,
Watson sabe onde olhar primeiro (`resultado_final` → `resultado_intermediario` →
demais). Opera em cinco etapas sequenciais (C1–C5), cada uma com artefato
rastreável — sem improviso, sem etapas puladas, sem resultado parcial: ou o ciclo
passa inteiro, ou sinaliza bloqueio com justificativa precisa (`soul.md`).

Reporta a Mycroft; é acionada pelo Orquestrador (decisão EXECUTAR/REUTILIZAR é
**mecânica, sem LLM**, executada por `verificar_catalogo_existente()` em nome de
Mycroft).

## 2. Escopo do recorte

**Entra na reescrita de Irene:**
- O wrapper `src/diogenes/irene.py` (`executar_irene`, derivação de manifesto,
  reuso de catálogo, cópia para o ciclo) e o adaptador
  `src/diogenes/irene_chattcu.py` (`patch_c4_para_chattcu`).
- O contrato do `irene_catalog.yaml` com Watson/Mycroft.

**NÃO entra (limites operacionais — verbatim do `skills.md`):**
- Irene **não** analisa a correção dos valores fiscais — isso é Watson.
- Irene **não** valida a metodologia CBS — isso é Sherlock.
- Irene **não** emite opinião sobre a qualidade do cálculo da RFB.
- Irene **não** acessa dados sigilosos via LLM — apenas metadados estruturais.
- Irene **não** modifica os arquivos originais recebidos — apenas leitura.
- Sem Stranger Room, sem ciclo de revisão, sem heartbeat por call_type.

## 3. Requisitos funcionais (transcritos do adendo v01, Bloco 5)

| RF | Texto (resumo fiel) | Status v1 | Gap conhecido |
|---|---|---|---|
| **RF-IR-01** | O sistema suporta a fase de catalogação semântica Irene (C1–C5), habilitada por `DIOGENES_IRENE_HABILITADO=true`; Irene opera como biblioteca (`executar_irene()` em `irene.py`) invocada pelo Orquestrador antes da fase Watson | Conforme | — |
| **RF-IR-02** | Irene reutiliza catálogo existente quando `versao_catalogo ≥ VERSAO_IRENE_MINIMA` (1.3.0). `IRENE_ERRO_FATAL` → ciclo `ABORTADO_FALHA_AGENTE`; `IRENE_BLOQUEADO` é **não-fatal** (Watson recebe o catálogo com ressalvas) | Conforme | — |
| **RF-IR-03** | `IRENE_C4_SAMPLE_N` limita a catalogação C4/C5 a N abas, honrado **apenas em DEV_MODE**; em produção todas as abas são catalogadas | Conforme | — |

**Pipeline e gate (contrato + skills.md):**

| Estágio | Função | Falha |
|---|---|---|
| C1 Manifesto | valida existência/integridade dos arquivos | exceção → `IRENE_ERRO_FATAL` |
| C2 Profiling | perfila cada aba (dimensões, fórmulas, vínculos, totalizadores) | idem |
| C3 Amostragem | fidedignidade CSV↔XLSX, tolerância 1e-6 | MCP Excel desabilitado → **fallback openpyxl** (não aborta) |
| C4 Semântica | classifica papel de cada aba via LLM (só metadados) | roteado por `patch_c4_para_chattcu` |
| C5 Artefatos | consolida 5 artefatos + recomendação | — |

**Gate de recomendação:** `APROVADO` score ≥ 0.95 · `ALERTA` 0.65 ≤ score < 0.95 ·
`BLOQUEADO` score < 0.65 **ou falha em aba `resultado_final`**.
**Estados de retorno:** `IRENE_APROVADO | IRENE_ALERTA | IRENE_BLOQUEADO | IRENE_ERRO_FATAL`.

**11 papéis de aba reconhecidos:** `resultado_final`, `resultado_intermediario`,
`base_bruta`, `base_classificada`, `base_tratada`, `memoria_de_calculo`,
`validacao_comparativa`, `tabela_mapeamento`, `matriz_parametrica`,
`aba_auxiliar`, `nao_classificado`.

## 4. Requisitos de interface

**Input:** manifesto do ciclo → `irene_manifesto.yaml` derivado (módulo,
raiz_projeto, `arquivos_xlsx` varridos em `01_ENTRADA_COPIADA` + `04_TRANSFORMADO`
via rglob, `catalogo_json` — auto-gerado mínimo `{"entradas": []}` se ausente).

**Outputs (5 artefatos em `IRENE_OUT/{modulo}/`):** `irene_catalog.yaml`
(**contrato com Watson** — copiado para `cycles/{id}/irene_catalog.yaml`),
`irene_confidence.md`, `irene_formulas.md`, `irene_extrato_*.md`,
`irene_execution.log`.

**Estrutura do catálogo por aba:** `papel`, `confianca_papel`,
`score_fidedignidade`, `requer_revisao_humana`, `tem_formulas`,
`candidata_totalizador`, `flags_atencao[]`, `colunas_detalhadas[]` (com
`tipo_fisico`, `tipo_semantico`, `confianca_tipo`, nulos, distintos, soma/média).
Cabeçalho: `versao_irene`, `score_consolidado`, `recomendacao`.

**Efeitos no Orquestrador:** estados `VERIFICANDO_EXISTENCIA → AGUARDANDO_IRENE →
IRENE_CONCLUIDA`; registro no `audit_index.csv` (`irene_invocada_at_utc`,
`irene_resultado`, `irene_score`, `irene_dir_saida`).

## 5. Limites constitucionais e regras hard

| Regra | Conteúdo |
|---|---|
| **Art. 4** | Não inicia sozinha; acionada pelo Orquestrador sob instrução de Mycroft |
| **Metadados-only no LLM** | C4 envia apenas metadados estruturais — nunca dados fiscais |
| **Originais intocados** | Apenas leitura dos arquivos recebidos |
| **Tudo ou nada** | Sem resultado parcial; bloqueio sempre com justificativa |
| **Catálogo é contrato** | `irene_catalog.yaml` é ponto de partida obrigatório de Watson, não orientativo |

## 6. RNFs aplicáveis (recorte)

- **RNF-RAST:** artefatos rastreáveis por estágio + `irene_execution.log`.
- **RNF-PORT-04:** config via `.env` (`IRENE_PROVIDER`, `IRENE_MODEL`,
  `IRENE_C4_SAMPLE_N`, `DIOGENES_IRENE_HABILITADO`, `DIOGENES_POST_IRENE_COOLDOWN_S`).
- **RNF-SEGU-05:** C4 via ChatTCU (provider institucional).
- **CA-OPE-10 (hotspot):** `irene_chattcu.py` com 0% de cobertura no v1 — a v2
  deve cobrir o adaptador com testes.

## 7. Critérios de aceitação e métricas (recorte)

- **Critério central da v2:** o catálogo gerado pela Irene v2 **valida contra a
  mesma fixture usada na fatia M1 de Mycroft** — preserva o contrato com
  Watson/Mycroft (mesmo schema, mesmos campos, gate idêntico).
- Baseline real de referência: ciclo `MOD_010_A1_20260602T202655Z` — 71 abas
  perfiladas (C3, 269s) e classificadas (C4, 1.998s), `score_consolidado 0.9529 →
  APROVADO`, fallback openpyxl operante com 3 CSVs ausentes.

## 8. Lições do piloto v1 (dossiê)

1. **F1 — duas fontes de verdade de modelo:** `carregar_config_irene()` lê config
   própria do pacote `irene`, não o `agents_spec.yaml`; o C4 rodou
   `gpt-5.5-thinking` com `agent.md` declarando Claude. **Decisão pendente para a
   v2:** unificar a fonte de verdade do modelo do C4 (registrar em "Decisões v2").
2. **F2 — doc drift de diretórios:** `heartbeat.md`/`agent.md` descrevem
   `input/{modulo}/XLSX/`; o real é a topologia do `--delivery`
   (`01_ENTRADA_COPIADA` + `04_TRANSFORMADO`). A v2 documenta a topologia real.
3. **F3 — confiança baixa por aba não gera flag:** abas com `confianca_papel`
   0.72–0.78 ficaram `requer_revisao_humana: false` (score consolidado mascara).
   Candidata a calibração v2: limiar por aba (ex.: < 0.80 → revisão humana).
4. **F4 — `resultado_final` fraco não rebaixa o gate:** aba `resultado_final` com
   confiança 0.72 não disparou atenção. Candidata a calibração v2: rebaixar
   recomendação para ALERTA nesse caso.
5. **F5 — controle positivo:** nenhuma violação de limite constitucional — as
   flags descrevem estrutura, nunca correção fiscal.

> F3/F4 são **mudanças de comportamento**: se adotadas na v2, registrar em
> "Decisões v2" do SDD_derivado e revalidar o critério central da Seção 7.

## 9. Registro de gate

| Gate | Critérios (Metodologia §5) | Data | Chancela | Observações |
|---|---|---|---|---|
| G-IR | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6 | — | — | Critério 2 (prompt) aplica-se só ao C4 |

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
