# Fixture: Watson consolidar_watson (call_type: consolidar_watson)
# Origem: ciclo MOD_010_A1_20260531T041556Z, 3 análises anteriores
# Uso: diogenes_call_agent_fixture(agent_id="watson", call_type="consolidar_watson", fixture_path=THIS)

## Contexto da Chamada

Você concluiu a análise individual de todos os arquivos do módulo MOD_010.
Agora deve produzir o watson_consolidado.md com inventário, cadeia de produção,
alertas consolidados e posição final.

## Análises Anteriores (resumo)

### Arquivo 1: base_nfe.csv
- Metadados: presentes (ano_ref, uf, cnae, ncm)
- Alertas: nenhum
- Último ID: W010-124
- Cadeia: fonte primária (dados NFe extraídos da base SPED)

### Arquivo 2: de_para.csv
- Metadados: parciais (sem data de geração)
- Alertas: W010-035 (MEDIA) — ausência de campo "responsavel_tecnico"
- Cadeia: tabela auxiliar de mapeamento CNAE→NCM

### Arquivo 3: matriz_incidencia.csv
- Metadados: presentes
- Alertas: nenhum
- Cadeia: resultado intermediário (aplica de_para sobre base_nfe)

## Inventário Final

| # | Arquivo | Tipo | Alertas |
|---|---------|------|---------|
| 1 | base_nfe.csv | tabela_dados | 0 |
| 2 | de_para.csv | tabela_mapeamento | 1 (MEDIA) |
| 3 | matriz_incidencia.csv | resultado_intermediario | 0 |

## Premissas Observadas

- Nota metodológica com alteração detectada: Não
- Anos-base efetivos: 2023/2024 (conforme premissa 1)

## Último ID de Alerta Global

W010-124
