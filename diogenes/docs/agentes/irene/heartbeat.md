# Heartbeat — Irene Adler
## Agente de Catalogação Documental | DVA-CBS | Projeto Diógenes

---

*Este arquivo descreve o protocolo que Mycroft segue ao acionar Irene.
Irene não é chamada como LLM — é acionada como biblioteca Python pelo
Orquestrador, sob instrução de Mycroft via call_type `acionar_irene`.*

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
