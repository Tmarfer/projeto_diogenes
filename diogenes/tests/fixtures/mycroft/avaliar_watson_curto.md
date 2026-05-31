# Fixture: Mycroft avaliar_agente (call_type: avaliar_agente)
# Origem: ciclo MOD_010_A1_20260531T041556Z, avaliação pós-Watson
# Uso: diogenes_call_agent_fixture(agent_id="mycroft", call_type="avaliar_agente", fixture_path=THIS)

## Contexto da Chamada

Watson concluiu sua análise de integridade do módulo MOD_010. Você (Mycroft)
deve avaliar o output de Watson e decidir: APROVADO, REVISÃO ou REJEIÇÃO.

## Output de Watson (watson_consolidado.md — extrato)

```markdown
## Resumo Executivo

Análise de integridade do módulo MOD_010 concluída. 84 arquivos processados,
1 alerta de severidade MEDIA identificado.

## Tabela de Alertas

| Severidade | ID | Localização | Descrição |
|---|---|---|---|
| MEDIA | W010-035 | de_para.csv | Ausência de campo "responsavel_tecnico" |

## Cadeia de Produção dos Dados

NFe SPED → base_nfe.csv → de_para.csv → matriz_incidencia.csv → resultado final

## Posição Consolidada

CONSISTENTE

## Arquivos Não Analisáveis

Nenhum.
```

## Métricas do Ciclo Watson

- Arquivos analisados: 84/85 (1 não-analisável: CATALOGO.json)
- Alertas críticos: 0
- Alertas média: 1
- Nota metodológica com alteração: Não
- Duração: ~4h (com retries)

## Critérios de Avaliação (Mycroft)

Avalie se Watson:
1. Analisou todos os arquivos (ou justificou exclusão)
2. Registrou alertas com ID sequencial correto
3. Mapeou cadeia de produção de ponta a ponta
4. Respondeu à premissa 1 (anos-base) e premissa 3 (nota metodológica)
5. Produziu posição consolidada coerente com os alertas
