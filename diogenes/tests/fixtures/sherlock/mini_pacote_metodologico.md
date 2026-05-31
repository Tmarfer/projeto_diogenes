# Fixture: Sherlock validacao_inicial (call_type: validacao_inicial)
# Origem: ciclo MOD_010_A1_20260531T041556Z, pacote metodológico reduzido
# Uso: diogenes_call_agent_fixture(agent_id="sherlock", call_type="validacao_inicial", fixture_path=THIS)

## Contexto da Chamada

Você está verificando a aderência metodológica do módulo MOD_010 (Pessoas Físicas
— Produtor Rural PF) à metodologia homologada pelo Acórdão 2833/2025-Plenário.

## Pacote Metodológico (resumido por Mycroft)

O módulo estima a base de cálculo da CBS para produtores rurais pessoa física
usando dados de NFe (SPED) cruzados com bases cadastrais (CNAE, NCM).

Cadeia declarada:
1. Extração de NFe por UF/CNAE/NCM (base_nfe.csv)
2. Mapeamento CNAE→NCM via tabela auxiliar (de_para.csv)
3. Aplicação de matriz de incidência (matriz_incidencia.csv)
4. Resultado final consolidado (resultado_mod10.csv)

## Watson Consolidado (extrato)

```markdown
## Posição Consolidada
CONSISTENTE

## Tabela de Alertas
| Severidade | ID | Localização | Descrição |
|---|---|---|---|
| MEDIA | W010-035 | de_para.csv | Ausência de campo "responsavel_tecnico" |

## Cadeia de Produção dos Dados
NFe SPED → base_nfe.csv → de_para.csv (mapeamento) → matriz_incidencia.csv → resultado final

## Arquivos Não Analisáveis
Nenhum.
```

## Ponto de Verificação Atual

Ponto 10.4 — Resultado da Verificação de Aderência Metodológica (Camadas 1 e 2)

Verifique se a cadeia de produção declarada pela RFB é rastreável nos arquivos
fornecidos e se os critérios metodológicos do Acórdão estão atendidos.
