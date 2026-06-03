# Agent — Irene Adler
## Agente de Catalogação Documental | DVA-CBS | Projeto Diógenes

---

## Identificação

```yaml
agent_id: irene
agent_role: agente_catalogacao_documental
agent_formal_name: "Irene Adler"
agent_type: staff          # não é agente LLM — é biblioteca Python
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
versao: 1.3.1
```

---

## Parâmetros de modelo (componente C4)

```yaml
provider: chattcu
model: "gpt-5.5-thinking"     # configurado no .env (IRENE_MODEL) — alinhado com o TCU em produção
temperatura: 0.1
max_tokens: 8000
timeout_segundos: 180
raciocinio: true
busca_web: false
```

---

## Posição no Departamento

```yaml
reporta_para: mycroft
acionado_por: orchestrator (sob instrução de mycroft)
precede: watson
tipo_chamada: biblioteca_python   # não via LLM — via executar_irene()
call_type_mycroft: acionar_irene
```

---

## Composição da invocação

```yaml
# Irene é invocada como função Python, não como LLM.
# O system_prompt do C4 está em irene/semantica.py.
# O heartbeat de Mycroft define o protocolo de acionamento.

invocacao:
  funcao: executar_irene(caminho_manifesto)
  modulo: src.diogenes.irene
  retorno: (estado: str, metricas: dict)

estados_retorno:
  - IRENE_APROVADO
  - IRENE_ALERTA
  - IRENE_BLOQUEADO
  - IRENE_ERRO_FATAL

artefatos_produzidos:
  - irene_catalog.yaml      # contrato com Watson
  - irene_confidence.md
  - irene_formulas.md
  - irene_extrato_*.md
  - irene_execution.log
```

---

## Registro no audit_index

```yaml
colunas_irene:
  irene_invocada_at_utc: "[timestamp ISO 8601]"
  irene_resultado: "[estado retornado]"
  irene_score: "[score_consolidado como string]"
  irene_dir_saida: "[caminho absoluto do IRENE_OUT]"
```

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
