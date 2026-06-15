---
documento: SDD Derivado — Irene Adler (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - src/diogenes/irene.py + src/diogenes/irene_chattcu.py (referência v1)
  - docs/agentes/irene/{agent,soul,skills,heartbeat}.md
  - docs/auditoria_agentes/irene/contrato.md
  - INTEGRACAO_DIOGENES.md
---

# SDD Derivado — Irene Adler

> O "como" da reescrita v2 de Irene. Parte de onde o
> [PRD_derivado_irene.md](PRD_derivado_irene.md) encerra. Irene é **biblioteca
> Python** (C1–C5) — este SDD descreve o wrapper de integração e o adaptador
> LLM do C4, não um invocador de agente. Pacote de Trabalho único: PT-IR-1
> (Seção 11).

---

## 1. Relação com o SDD mestre

Irene é posterior ao SDD v0.1 (gap documental nº 1 de `12_sdd_gaps.md`). As
fontes arquiteturais são: `INTEGRACAO_DIOGENES.md` (integração do pipeline no
Orquestrador), o adendo v01 do PRD (RF-IR-*) e o Bloco 1.2 do SDD (decisões
fundadoras, que valem integralmente: síncrono, filesystem-first).

## 2. Posição na arquitetura

```
confirm-manifest
  └─► Orquestrador [VERIFICANDO_EXISTENCIA]
        ├─ verificar_catalogo_existente()  ── catálogo ≥ 1.3.0? ──► REUTILIZAR
        └─ senão [AGUARDANDO_IRENE]
             └─► executar_irene(manifesto) ── C1→C2→C3→C4→C5 ──► (estado, metricas)
                   └─► copiar_catalogo_para_ciclo() ──► [IRENE_CONCLUIDA] ──► Mycroft M1
```

- **Quem chama:** o Orquestrador (fase condicional, `DIOGENES_IRENE_HABILITADO=true`).
- **Efeito dos estados de retorno:** `IRENE_ERRO_FATAL` → `ABORTADO_FALHA_AGENTE`;
  `IRENE_BLOQUEADO` → não-fatal (Watson recebe catálogo com ressalvas; Mycroft
  inclui ressalva no `MC_tasks_watson.md`); `IRENE_ALERTA` → prossegue com flag.
- **Cooldown pós-Irene:** `DIOGENES_POST_IRENE_COOLDOWN_S` (pausa antes de
  Mycroft/Watson; ignorada em DEV_MODE) — mitiga saturação do ChatTCU.

## 3. Interface pública (contrato a preservar)

| Função (v1) | Assinatura/Comportamento |
|---|---|
| `executar_irene(...)` (`irene.py:41`) | executa C1–C5; retorna `(estado: str, metricas: dict)` |
| `verificar_catalogo_existente(...)` (`:256`) | catálogo válido se `versao_irene ≥ VERSAO_IRENE_MINIMA` (`"1.3.0"`, comparação semântica `_versao_valida:349`) |
| `_derivar_manifesto_irene(cycle_id, workspace_path)` (`:360`) | constrói `irene_manifesto.yaml`: varre `01_ENTRADA_COPIADA` + `04_TRANSFORMADO` via rglob (com `_eh_ignorado`); auto-gera `CATALOGO.json` mínimo se ausente |
| `copiar_catalogo_para_ciclo(...)` (`:450`) | copia `irene_catalog.yaml` para `cycles/{id}/` |
| `arquivar_inputs_existentes(input_dir)` (`:482`) | arquiva entradas anteriores |
| `_sample_c4_dev(perfis, amostragens)` (`:303`) | recorte de N abas — só DEV_MODE (`IRENE_C4_SAMPLE_N`) |
| `patch_c4_para_chattcu(...)` (`irene_chattcu.py:72`) | injeta cliente ChatTCU no estágio C4 do pacote `irene` (`custom_criar_cliente`, `_chamar_chattcu` com 2 tentativas) |
| `garantir_irene_no_path(package_dir)` (`irene_chattcu.py:37`) | disponibiliza o pacote `irene` no sys.path |

**Parâmetros (fonte: `.env`, não `agents_spec.yaml`):** `IRENE_PROVIDER=chattcu`,
`IRENE_MODEL=gpt-5.5-thinking`, temperatura 0.1, max_tokens 8000, timeout 180s
(`agent.md`). *Atenção ao achado F1: hoje o pacote `irene` lê config própria —
ver Decisões v2.*

## 4. Consolidação dos 4 arquivos de definição

Irene **não** segue o padrão `system = soul + skills` — os arquivos de
`docs/agentes/irene/` documentam a biblioteca; o **system_prompt do C4 vive em
`irene/semantica.py`** (pacote vendorizado). Síntese:

| Arquivo | Conteúdo essencial |
|---|---|
| `soul.md` | Identidade; 5 componentes C1–C5; os 5 artefatos; "o catálogo é contrato, não orientação" |
| `skills.md` | Capacidades técnicas por estágio; 11 papéis de aba; gate de scores; limites operacionais (verbatim no PRD_derivado §2) |
| `agent.md` | `agent_type: staff`; parâmetros do C4; estados de retorno; colunas do audit_index |
| `heartbeat.md` | Protocolo `acionar_irene` (executado **mecanicamente** pelo invocador, sem LLM) — transcrito verbatim abaixo |

### 4.1 `heartbeat.md` — transcrição verbatim

O conteúdo abaixo é a transcrição integral de `docs/agentes/irene/heartbeat.md`
(2026-06-11). Os 5 passos são o contrato do acionamento; em caso de dúvida, o
arquivo original prevalece. *Nota F2 do dossiê: os Passos referem a topologia
real (`01_ENTRADA_COPIADA`/`04_TRANSFORMADO`); qualquer resíduo de
`input/{modulo}/XLSX/` em `agent.md` é doc drift a corrigir na v2.*

<!-- INÍCIO TRANSCRIÇÃO VERBATIM heartbeat.md (Irene) -->
# Heartbeat — Irene Adler
## Agente de Catalogação Documental | DVA-CBS | Projeto Diógenes

---

*Este arquivo descreve o protocolo de acionamento de Irene. Irene não é
chamada como LLM — é acionada como biblioteca Python pelo Orquestrador.
A decisão EXECUTAR/REUTILIZAR é mecânica e executada deterministicamente
pelo invocador (`verificar_catalogo_existente()` em `irene.py`), em nome
de Mycroft, sem chamada LLM — ver nota na seção `acionar_irene` do
heartbeat de Mycroft.*

---

# Heartbeat de Mycroft — acionar_irene

## Situação desta chamada

O manifesto do ciclo foi confirmado por Lestrade. O Orquestrador chegou à
fase de catalogação. Mycroft precisa verificar se existe um catálogo válido
de uma execução anterior do Irene para este módulo, ou se é necessário
executar o pipeline completo agora.

## Protocolo de Mycroft para esta chamada

**Passo 1: Verificar existência de catálogo anterior.**
Existe `irene_catalog.yaml` na raiz do diretório do ciclo (`cycles/{cycle_id}/`) com
`versao_irene >= 1.3.1`? Se sim, o catálogo pode ser reutilizado.
Registrar: `irene_resultado: CATALOGO_REUTILIZADO`.
Se não, prosseguir para o Passo 2.

**Passo 2: Derivar o manifesto do Irene a partir do manifesto do ciclo.**
O manifesto do Diógenes contém a lista de arquivos no workspace.
Construir `irene_manifesto.yaml` com:
- `modulo`: identificador do módulo do ciclo
- `raiz_projeto`: caminho do workspace (diretório do ciclo)
- `arquivos_xlsx`: lista de todos os arquivos Excel varridos no diretório de inputs (`01_ENTRADA_COPIADA` e `04_TRANSFORMADO`)
- `catalogo_json`: `CATALOGO.json` na pasta de inputs se existir, senão o Diógenes auto-gera um `CATALOGO.json` mínimo (`{"entradas": []}`) para viabilizar a execução do Irene.

**Passo 3: Acionar Irene.**
Chamar `executar_irene(caminho_manifesto)` via `src/diogenes/irene.py`.
Registrar timestamp de início em `irene_invocada_at_utc`.

**Passo 4: Avaliar retorno.**
- `IRENE_APROVADO`: prosseguir para Watson normalmente.
- `IRENE_ALERTA`: prosseguir para Watson com flag — Watson recebe o catálogo
  com nota de alerta; Mycroft incluirá ressalva no MC_tasks_watson.md.
- `IRENE_BLOQUEADO`: pausar o ciclo. Registrar bloqueio no audit_index.
  Notificar Lestrade com o score e a justificativa do bloqueio.
- `IRENE_ERRO_FATAL`: abortar o ciclo com status `ABORTADO_FALHA_AGENTE`.
  Registrar o erro completo no audit_index.

**Passo 5: Incorporar catálogo do Irene no pacote para Watson.**
O `irene_catalog.yaml` retornado deve ser incluído como contexto inicial
no `MC_tasks_watson.md`. Watson não precisa inferir o papel de cada aba —
o Irene já classificou. Mycroft usa a classificação para priorizar as tasks:
`resultado_final` primeiro, depois `resultado_intermediario`, depois os demais.

## Campos obrigatórios na resposta de Mycroft

```yaml
resultado: EXECUTAR | REUTILIZAR
irene_resultado: IRENE_APROVADO | IRENE_ALERTA | IRENE_BLOQUEADO | IRENE_ERRO_FATAL | CATALOGO_REUTILIZADO
score_irene: 0.0000
justificativa: "[uma frase explicando a decisão]"
caminho_catalogo: "[caminho absoluto do irene_catalog.yaml]"
tasks_watson_ajustadas: true | false
```

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
<!-- FIM TRANSCRIÇÃO VERBATIM heartbeat.md (Irene) -->

---

## 5. Estruturas de dados e contrato do catálogo

Irene não usa dataclasses de `models.py` — o contrato é o **schema do
`irene_catalog.yaml`** (PRD_derivado §4) e a tupla de retorno
`(estado: str, metricas: dict)`. Campos do cabeçalho: `versao_irene`,
`score_consolidado`, `recomendacao`. Por aba: `papel`, `confianca_papel`,
`score_fidedignidade`, `requer_revisao_humana`, `tem_formulas`,
`candidata_totalizador`, `flags_atencao[]`, `colunas_detalhadas[]`.

**Regra de compatibilidade:** o schema é consumido por
`MycrooftAgent._ler_catalogo_irene/_formatar_secao_catalogo_irene` (fatia M1) e
pelo template `definir_tasks_watson` — mudanças de schema exigem versionar
`versao_irene` e atualizar `VERSAO_IRENE_MINIMA` em conjunto.

## 6. Artefatos no filesystem

| Lê | Escreve |
|---|---|
| `manifest.md` do ciclo; `cycles/{id}/inputs/` (`01_ENTRADA_COPIADA`, `04_TRANSFORMADO`); `CATALOGO.json` (ou auto-gera mínimo) | `irene_manifesto.yaml`; `IRENE_OUT/{modulo}/`: `irene_catalog.yaml`, `irene_confidence.md`, `irene_formulas.md`, `irene_extrato_*.md`, `irene_execution.log`; cópia do catálogo em `cycles/{id}/irene_catalog.yaml` |

Originais **nunca** modificados (apenas leitura).

## 7. Fluxo de execução

1. `verificar_catalogo_existente()` — reuso se `versao ≥ 1.3.0` (registro
   `CATALOGO_REUTILIZADO`); senão:
2. `_derivar_manifesto_irene()` → 3. `executar_irene()` C1→C5 (C4 com
   `patch_c4_para_chattcu`; `IRENE_C4_SAMPLE_N` só em DEV_MODE) →
4. avaliação do estado de retorno (efeitos na Seção 2) →
5. `copiar_catalogo_para_ciclo()` + registro no `audit_index.csv` + incorporação
   no pacote de Watson via Mycroft (prioridade `resultado_final` primeiro).

## 8. Erro e resiliência

- Exceção em qualquer estágio C1–C5 → `IRENE_ERRO_FATAL` → `ABORTADO_FALHA_AGENTE`.
- C3: MCP Excel forçadamente desabilitado → **fallback openpyxl** (CSV ausente
  não aborta — baseline operou com 3 CSVs ausentes).
- C4/ChatTCU: `_chamar_chattcu` com 2 tentativas por aba.
- `IRENE_BLOQUEADO` **não é fatal** — ressalva propagada a Watson.

## 9. Decisões v2

| Tema | Decisão |
|---|---|
| Interface `executar_irene() → (estado, metricas)` e estados de retorno | **Preservar** (contrato com o Orquestrador) |
| Schema do `irene_catalog.yaml` | **Preservar** — critério central do gate G-IR (valida contra a fixture de M1) |
| Gate de scores (0.95/0.65 + falha em `resultado_final`) | **Preservar** |
| F1 — fonte de verdade do modelo do C4 | **A decidir na reescrita:** unificar leitura via `config.py`/.env do Diógenes OU documentar a config própria do pacote `irene` |
| F2 — doc drift de diretórios | **Corrigir** `agent.md` para a topologia real |
| F3 — limiar de `confianca_papel` por aba (< 0.80 → revisão humana) | **Aberta** — se adotada, registrar aqui + revalidar fixture |
| F4 — `resultado_final` com confiança baixa rebaixa para ALERTA | **Aberta** — idem |
| Cobertura de `irene_chattcu.py` (0% no v1) | **Obrigatória na v2** (testes do adaptador com mock) |

## 10. Testes de referência v1

- `tests/unit/` — testes do wrapper (`verificar_catalogo_existente`,
  `_derivar_manifesto_irene`, versão semântica).
- `tests/integration/test_ciclo_completo.py` — fase Irene no E2E mockado.
- **Lacuna v1 a fechar:** `irene_chattcu.py` sem cobertura.
- Fixture golden: `irene_catalog.yaml` do baseline `MOD_010_A1_20260602T202655Z`
  (71 abas, score 0.9529, APROVADO).

---

## 11. Pacote de Trabalho

### Pacote de Trabalho PT-IR-1 — Reescrita do wrapper Irene + adaptador C4
**Fatia/Fase:** Irene (completa) | **Pré-requisitos:** G-M1 | **Status:** A INICIAR

#### Objetivo
Reescrever `src/diogenes/irene.py` e `src/diogenes/irene_chattcu.py` preservando
a interface com o Orquestrador e o schema do catálogo, e fechando a lacuna de
cobertura do adaptador ChatTCU.

#### Contexto mínimo (leitura obrigatória do devsquad)
Este derivado (Seções 2–9) + `docs/reescrita_v2/irene/PRD_derivado_irene.md`
(Seções 3–5, 8) + `INTEGRACAO_DIOGENES.md` + `docs/reescrita_v2/00_METODOLOGIA.md`
(Seções 5 e 8).

#### Escopo — entregáveis
- `executar_irene`, `verificar_catalogo_existente`, `_derivar_manifesto_irene`,
  `copiar_catalogo_para_ciclo`, `arquivar_inputs_existentes`, `_versao_valida`,
  `_sample_c4_dev`.
- `patch_c4_para_chattcu` + `garantir_irene_no_path` com testes (mock do cliente).
- **Fora de escopo:** o pacote `irene` em si (estágios C1–C5 internos — é
  dependência vendorizada, não alvo da reescrita); Orquestrador; Mycroft.

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/irene.py`, `src/diogenes/irene_chattcu.py`,
`src/diogenes/orchestrator/orchestrator.py` (fase Irene).

#### Arquivos a produzir (v2)
Na branch `feat/reescrita-v2`, mesmo path: `src/diogenes/irene.py`,
`src/diogenes/irene_chattcu.py` (+ testes em `tests/unit/`).

#### Critérios de aceite
- [ ] RF-IR-01/02/03 atestados com evidência `arquivo:linha`.
- [ ] Catálogo v2 valida contra a fixture golden do baseline (mesmo schema; gate idêntico).
- [ ] Reuso de catálogo: `versao ≥ 1.3.0` reutiliza; inferior regenera.
- [ ] `IRENE_BLOQUEADO` não-fatal; `IRENE_ERRO_FATAL` → `ABORTADO_FALHA_AGENTE` (testes).
- [ ] `irene_chattcu.py` com cobertura de testes (adeus 0%).
- [ ] `IRENE_C4_SAMPLE_N` honrado apenas em DEV_MODE.

#### Prompt sugerido (colar no Copilot devsquad)
> Você vai reescrever a camada de integração da Irene no projeto Diógenes
> (branch `feat/reescrita-v2`): `src/diogenes/irene.py` (wrapper do pipeline
> C1–C5) e `src/diogenes/irene_chattcu.py` (adaptador LLM do estágio C4). Leia
> `docs/reescrita_v2/irene/SDD_derivado_irene.md` e o PRD derivado. O código v1
> é referência canônica. Restrições inegociáveis: Irene é biblioteca síncrona
> (sem threads/asyncio); a interface `executar_irene() → (estado, metricas)` e
> os 4 estados de retorno são contrato com o Orquestrador; o schema do
> `irene_catalog.yaml` não muda (validar contra a fixture do baseline); o C4 só
> envia metadados estruturais ao LLM — nunca dados fiscais; originais do pacote
> RFB são somente leitura; `config.py` é o único leitor de configuração do
> Diógenes. Entregáveis: os dois módulos + testes unitários, incluindo cobertura
> do adaptador ChatTCU com cliente mockado (lacuna do v1). Os estágios C1–C5
> internos do pacote `irene` estão fora de escopo.

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
