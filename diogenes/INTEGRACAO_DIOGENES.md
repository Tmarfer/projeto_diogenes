# Guia de Integração — Irene v1.3.0 → Projeto Diógenes
## DVA-CBS | TC 015.848/2025-6

> **Status de Irene:** Homologado (v1.3.0) — pronto para integração.
> **Base de referência:** SDD Diógenes Local v0.1, Bloco 15 (irene.py e estados do Orchestrator).

---

## 1. O que Irene entrega ao Diógenes

Irene é a **Etapa de Catalogação** que precede Watson. Ela transforma os arquivos
brutos entregues pela RFB (XLSXs + CSVs do motor_v2) em um catálogo semântico
estruturado que Watson usa para saber **quais abas analisar**, **qual o papel de cada
uma** e **quais merecem extrato detalhado**.

Sem Irene, Watson recebe os arquivos sem contexto estrutural e precisa inferir a
função de cada aba por conta própria — o que aumenta o consumo de tokens, o tempo
de processamento e o risco de classificação equivocada.

---

## 2. Arquivos a migrar para o repositório do Diógenes

### 2.1 — O pacote irene como dependência

**Opção A (recomendada):** instalar o pacote irene no mesmo ambiente virtual do Diógenes:

```bash
# A partir da raiz do repositório irene_standalone:
pip install -e ".[dev]"
# ou, para produção sem dev:
pip install -e .
```

**Opção B:** copiar o diretório `irene/` para dentro do repositório do Diógenes e
adicionar ao `sys.path` conforme o `irene.py` do SDD Bloco 15.

### 2.2 — Arquivos obrigatórios para o Diógenes

Copiar para o repositório do Diógenes:

```
De irene_standalone/          Para diogenes/
─────────────────────────────────────────────────────────────────
irene/                    →   (instalar como pacote, ver 2.1)
irene_manifesto_template.yaml → docs/irene/manifesto_template.yaml
```

### 2.3 — Arquivo irene.py no Diógenes

Criar `src/diogenes/irene.py` conforme especificado no SDD Diógenes Local v0.1,
Bloco 15. O arquivo já está especificado — basta implementar com a função
`executar_irene()` que chama o pipeline C1-C5 de Irene e retorna o estado
para o Orchestrator.

---

## 3. Variáveis de ambiente a adicionar ao .env do Diógenes

```dotenv
# Provider Irene (mesmo provider usado pelo Diógenes ou independente)
IRENE_PROVIDER=chattcu
IRENE_MODEL=claude-4-7-opus
IRENE_CHATTCU_BASE_URL=https://chat-tcu.apps.tcu.gov.br
# IRENE_API_KEY não necessária no modo chattcu

# Limiares (valores calibrados no MOD_010)
IRENE_LIMIAR_AMOSTRAGEM=0.95
IRENE_LIMIAR_CONFIANCA=0.65
```

---

## 4. Inputs de entrada (o que Irene recebe)

| Input | Tipo | Responsável por fornecer | Descrição |
|-------|------|--------------------------|-----------|
| `caminho_manifesto` | `str \| Path` | Mycroft (call_type: acionar_irene) | Caminho para o arquivo `manifesto_mod{id}.yaml` preenchido por Lestrade |
| `modulo` | `str` | Orchestrator | Identificador do módulo (ex: `MOD_010_Pessoa_Fisica`) |
| `descricao_modulo` | `str` | Mycroft (opcional) | Contexto adicional para C4 |
| `dir_saida` | `str \| Path` (opcional) | Orchestrator | Override do diretório de saída |

**Pré-condição:** o Motor de Curadoria (motor_v2) deve ter sido executado antes de
acionar Irene. Os XLSXs originais e o `CATALOGO.json` devem estar disponíveis nos
caminhos declarados no manifesto.

---

## 5. Outputs produzidos por Irene (o que Diógenes recebe)

### 5.1 — Retorno da função `executar_irene()`

```python
(estado: str, metricas: dict)
```

**estado** — um de:
- `"IRENE_APROVADO"` — pipeline concluído, recomendação APROVADO
- `"IRENE_ALERTA"` — pipeline concluído, recomendação ALERTA (Watson deve ponderar)
- `"IRENE_BLOQUEADO"` — pipeline concluído, recomendação BLOQUEADO (Watson recebe com flag)
- `"IRENE_ERRO_FATAL"` — falha irrecuperável em C1-C3 ou no carregamento do módulo

**metricas** — dict com:
```python
{
    "score_consolidado": float,       # ex: 0.9737
    "recomendacao": str,              # "APROVADO" | "ALERTA" | "BLOQUEADO"
    "versao_irene": str,              # ex: "1.3.0"
    "abas_classificadas": int,        # ex: 66
    "abas_total": int,                # ex: 66
    "tokens_total": int,              # ex: 383891
    # NOTA: tokens_total inclui reasoning interno do modelo (~3.800 tok/aba
    # no Opus com raciocinio=True). O YAML útil por aba é ~80 tokens.
    # Não interpretar tokens_total como volume de texto gerado.
    "tempo_c4_segundos": float,       # ex: 667.3
    "dir_saida": str,                 # caminho absoluto do IRENE_OUT
    "artefatos": {                    # caminhos dos 5 artefatos
        "catalog": str,
        "confidence": str,
        "formulas": str,
        "extrato": str,
        "log": str,
    }
}
```

### 5.2 — Artefatos em disco (lidos diretamente por Watson)

```
{dir_saida}/
├── irene_catalog.yaml      ← PRINCIPAL: Watson lê este arquivo primeiro
├── irene_confidence.md     ← Watson usa para priorizar abas com flags
├── irene_formulas.md       ← Watson usa para verificar totalizadores
├── irene_extrato_*.md      ← Watson usa para análise semântica das abas prioritárias
└── irene_execution.log     ← Mycroft usa para registro de trace
```

**O `irene_catalog.yaml` é o contrato principal entre Irene e Watson.** Sua estrutura:

```yaml
modulo: MOD_010_Pessoa_Fisica
gerado_em: "2026-05-29T20:15:01Z"
versao_irene: "1.3.0"
score_consolidado: 0.9737
recomendacao: BLOQUEADO  # APROVADO | ALERTA | BLOQUEADO
arquivos:
  - nome_original: Base_Creditos.xlsx
    papel: resultado_final
    confianca_papel: 0.92
    score_fidedignidade: 0.98
    requer_revisao_humana: false
    flags_atencao: []
    # ...
```

---

## 6. Máquina de estados do Orchestrator (novos estados)

Conforme SDD Diógenes Local v0.1, Bloco 15, adicionar ao `CycleState`:

```python
VERIFICANDO_EXISTENCIA = "VERIFICANDO_EXISTENCIA"
AGUARDANDO_IRENE       = "AGUARDANDO_IRENE"
IRENE_CONCLUIDA        = "IRENE_CONCLUIDA"
```

**Transições:**
```
INICIANDO_CICLO → VERIFICANDO_EXISTENCIA
VERIFICANDO_EXISTENCIA → AGUARDANDO_IRENE  (se manifesto válido)
AGUARDANDO_IRENE → IRENE_CONCLUIDA         (se estado IRENE_APROVADO ou IRENE_ALERTA)
AGUARDANDO_IRENE → ERRO_FATAL              (se estado IRENE_ERRO_FATAL)
IRENE_CONCLUIDA → AGUARDANDO_WATSON        (fluxo normal)
```

---

## 7. Call_type do Mycroft: `acionar_irene`

Adicionar ao `mycroft_heartbeat.md` e `mycroft_skills.md` o call_type `acionar_irene`:

**Objetivo:** Mycroft verifica o manifesto, aciona Irene via `executar_irene()`,
avalia o estado retornado e decide se Watson deve ser acionado normalmente,
com alerta ou com bloqueio.

**MC_instrucao_irene.md** (arquivo que Mycroft produz antes de acionar Irene):
```markdown
---
call_type: acionar_irene
cycle_id: [cycle_id]
modulo: [modulo]
caminho_manifesto: [caminho absoluto]
descricao_modulo: [contexto adicional se houver]
---
[Contexto da ativação: por que Irene está sendo acionada agora]
```

---

## 8. Checklist de integração

Execute esta checklist antes de declarar a integração concluída:

- [ ] Irene instalado no ambiente virtual do Diógenes (`import irene` funciona)
- [ ] Variáveis de ambiente do Irene adicionadas ao `.env` do Diógenes
- [ ] `src/diogenes/irene.py` criado com `executar_irene()` implementado
- [ ] Três novos estados adicionados ao `CycleState`
- [ ] Transições adicionadas ao `TRANSICOES_VALIDAS` do Orchestrator
- [ ] Call_type `acionar_irene` adicionado ao `mycroft_heartbeat.md`
- [ ] Call_type `acionar_irene` adicionado ao `mycroft_skills.md`
- [ ] Teste de integração `test_irene_integration.py` criado e passando
- [ ] Execução end-to-end com MOD_SINT_001 + Irene mock validada
- [ ] Execução real com MOD_010 + Irene real validada

---

## 9. Versão do irene_catalog.yaml esperada pelo Diógenes

O Orchestrator verifica o campo `versao_irene` no catálogo antes de acionar Watson.
A versão mínima aceita é `1.3.0`. Versões anteriores devem ser rejeitadas com
mensagem clara pedindo reexecução do Irene.

```python
# Em src/diogenes/irene.py
VERSAO_IRENE_MINIMA = "1.3.0"
```

---

*Guia de Integração Irene → Diógenes | DVA-CBS | TC 015.848/2025-6*
*Tribunal de Contas da União | SecexContas*
