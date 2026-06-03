# Avaliação — Bench MOD_010 multi-tipo (gpt-5.5) + Planejamento da próxima etapa

**Run:** `workspace/_bench/pipeline_MOD_010_20260602T122851Z`
**Data:** 2026-06-02 | Modelo: `gpt-5.5-thinking` | Perfil: `stable-gpt55`
**Escopo:** 12 arquivos amostrados por tipo (csv=2, documento=2, notebook=2, planilha=2, script=2, sql=2) + metodologia (cat. C, 20k chars) + corpus jurídico curado (cat. D, 30k chars).
**Resultado:** 19/19 passos OK | 65 min | 336k tokens in + 145k out | custo_ref ≈ USD 6,5.

---

## 1. Veredito por dimensão

| Dimensão | Veredito | Evidência |
|----------|----------|-----------|
| **Ingestão multi-tipo (objetivo do teste)** | ✅ **Sucesso total** | Watson traduziu SQL (tabelas/filtros/schema/datas), leu células de notebooks, interpretou `pd_utils.py`/`rd_utils.py`, mapeou abas de XLSX e CSVs. |
| **Metodologia + corpus jurídico → Sherlock** | ✅ **Chegou e foi usado** | Sherlock citou `Metodologia_Foco_10 §§`, `RN-10.XX`, arts. 127/130/140/164/165 LC 214/2025 ao classificar cada eixo. |
| **Consolidação Watson cross-file** | ✅ **Íntegra (50 KB)** | Inventário das 12 análises, 92 alertas (16 CRÍTICA / 33 ALTA / 39 MÉDIA / 4 BAIXA), notas metodológicas com localização por linha. |
| **Curadoria Mycroft (avaliação)** | ✅ **Crítica cirúrgica** | Questionou superclassificação CRÍTICA de metadados (Watson) e a inconsistência "Bifurcação: Não" vs classificações condicionais (Sherlock) — crítica de ponto único, conforme Art. 8. |
| **Achados técnicos reais** | ✅ **Alto valor** | Filtro `>= 3.600.000` vs metodologia "superior a R$ 3,6 mi"; exclusões hardcoded de outliers/NF-e/eSocial; `CONTROLE!E7` não rastreável; arrecadação negativa sem justificativa; truncamento de artefatos centrais. |
| **Confiabilidade ChatTCU** | ⚠️ **OK com retry** | 3 erros transitórios (502/timeout) recuperados por `max_retries=2`; watson_01/02 levaram 730–830s com retry. |

---

## 2. Limitações expostas pelo teste (são do escopo do bench / do file_prep, NÃO da ingestão)

1. **Truncamento do `file_prep` degradou análises.** SQL cortado em 8.000 chars e planilhas em 15 linhas/aba → 5 dos 12 arquivos saíram "Parcial — conteúdo truncado" (SQLs, notebooks, planilha grande). Watson detectou e registrou o corte, mas analisou material incompleto.
2. **Sherlock saiu `LIMITADO` por desenho do bench, não por falta de insumo.** O perfil usa `sherlock_mode=freeform_aux_only` (validação monolítica, preliminar). O fluxo **oficial** é `mapear_pontos → verificar_ponto × N → consolidar_sherlock` (11 seções) — que o bench não executa.
3. **O bench não roda as rodadas de revisão.** Mycroft criticou (r0) Watson e Sherlock corretamente, mas o bench não aciona `resposta_r1`/`fixar_decisao`; por isso Mycroft, na consolidação, corretamente **recusou emitir** o `MC_consolidado.md` (relatório estruturado incompleto).
4. **Watson não recebeu `MC_tasks_watson.md` por arquivo** (cada análise é isolada no bench). No fluxo oficial ele recebe.

> Conclusão: o bench cumpriu seu objetivo — provar que o universo de entradas é ingerido e analisado com qualidade. Levar isso ao **fluxo oficial** é a próxima etapa.

---

## 3. Planejamento da próxima etapa (alinhado ao SDD Bloco 14 — Sprint 4 / Fase D)

> **Meta do SDD (Sprint 4, marco verificável):** *"Relatório Preliminar de Análise do MOD_010 produzido, avaliação humana positiva… inconsistências encontradas, fundamentação metodológica coerente, linguagem institucional"* — critério de conclusão do piloto.

Para sair do bench validado e chegar ao Relatório Preliminar oficial:

### Etapa 1 — Motor de Start ingere a entrega real (multi-tipo, recursiva, manifesto de entrega)
- **Problema:** a entrega real é uma árvore com pasta-data (`2026_04_27/01_ENTRADA_COPIADA/...`); `motors/motor_start.py` hoje escaneia `workspace/input/{MOD}/` de forma plana.
- **Ação:** promover a lógica já validada no bench (`_load_delivery`: allowlist/denylist + varredura recursiva) para um módulo compartilhado (ex. `persistence/delivery.py`) reusado por motor_start **e** bench. Consumir o **manifesto de entrega** (`02_INSUMOS_GERADOS/protocolo_recebimento.md` + `metadados.json` + `hashes_integridade.txt`) e validar integridade contra ele (SHA-256), preservando imutabilidade (Art. 13).
- **Arquivos:** `motors/motor_start.py`, `persistence/manifest.py`, `docs/agentes/manifesto_abertura_template.md`, novo `persistence/delivery.py`.

### Etapa 2 — Revisar limites de truncamento do `file_prep`
- **Problema:** SQL@8.000 chars e XLSX@15 linhas truncaram artefatos centrais (5/12 "Parciais").
- **Ação:** parametrizar tetos por tipo em `config`/`runtime.yaml`; aumentar SQL (script completo até teto maior), ler mais linhas/abas de XLSX. Calibrar contra orçamento de tokens (planilha grande já gerou 25k tokens input).
- **Arquivos:** `agents/file_prep.py`, `runtime.yaml`.

### Etapa 3 — Wire do Apêndice/corpus jurídico no orquestrador oficial
- **Problema:** o orquestrador oficial ainda não carrega cat. C (metodologia/RN) nem cat. D (corpus jurídico); `mapear_pontos`/`verificar_ponto` por ponto não estão exercitados ponta a ponta.
- **Ação:** promover a injeção cat. C + cat. D (validada no bench) para o fluxo oficial: Mycroft `mapear_pontos` lê o Apêndice/metodologia do módulo; o invocador injeta o trecho por ponto em cada `verificar_ponto`; `consolidar_sherlock` produz as 11 seções + JSON. Define onde o corpus jurídico curado por módulo é referenciado (decisão híbrida já fixada).
- **Arquivos:** `orchestrator/orchestrator.py`, `agents/sherlock.py`, `agents/mycroft.py`.

### Etapa 4 — Executar o ciclo oficial completo (Fase D) e produzir o Relatório Preliminar
- `diogenes start --module MOD_010 --activity 1` → `confirm-manifest` → orquestrador → `relatorio_preliminar_*.md` → `verify-output` → avaliação humana.
- **Orçamento:** o run de 12 arquivos custou ~USD 6,5/65 min. O MOD_010 completo (~90+ arquivos) deve escalar para ~horas e dezenas de USD — **revisar `teto_custo_ciclo_usd`** (SDD assume 10; custo real será maior) e usar `resume`/checkpoints contra os 502/timeout do ChatTCU.

### Dependências e ordem
```
Etapa 1 ─┐
Etapa 2 ─┼──> Etapa 4 (ciclo oficial completo → Relatório Preliminar)
Etapa 3 ─┘
```
Etapas 1, 2 e 3 são independentes entre si; a 4 depende das três. Sugestão de priorização: **1 → 3 → 2 → 4** (1 e 3 destravam o fluxo; 2 é calibração).

---

## 4. Decisões a confirmar antes de implementar
- Validar a 1ª etapa com `--limit` (subconjunto) no ciclo oficial antes do run completo, para conferir tokens/tempo reais.
- Confirmar o mapeamento recorte-jurídico ↔ módulo (qual subpasta de `ARCABOCO_JURIDICO/normas_para_motor` corresponde ao MOD_010).
- Decidir se o manifesto de entrega passa a ser **obrigatório** (bloqueia o start se ausente) ou **best-effort** (só valida quando presente).

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
