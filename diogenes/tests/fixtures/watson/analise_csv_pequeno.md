# Fixture: Watson analise_inicial (call_type: analise_inicial)
# Origem: ciclo MOD_010_A1_20260531T041556Z, arquivo CSV pequeno
# Uso: diogenes_call_agent_fixture(agent_id="watson", call_type="analise_inicial", fixture_path=THIS)

## Contexto da Chamada

Você está analisando o arquivo abaixo como parte do módulo MOD_010 (Pessoas Físicas — Produtor Rural).

## Inputs Disponíveis

```
CSV/produtor_rural_pf__2023__base_debitos_2023__base_nfe.csv
```

## Catálogo Irene (extrato do arquivo)

```yaml
- nome_original: base_nfe
  csv_correspondente: produtor_rural_pf__2023__base_debitos_2023__base_nfe.csv
  linhas: 1247
  colunas: 8
  papel: tabela_dados
  confianca_papel: 0.85
  score_fidedignidade: 1.0
  tem_formulas: false
  candidata_totalizador: false
```

## Amostra do CSV (primeiras 5 linhas)

```csv
uf,cnae,ncm,valor_nfe,qtd_nfe,ano_ref,mes_ref,tipo_operacao
SP,0111301,10011000,152847.32,47,2023,1,saida
MG,0111301,10011000,89421.15,28,2023,1,saida
PR,0111302,10012000,45213.87,12,2023,1,saida
RS,0111302,10012000,67891.44,19,2023,2,saida
```

## Tasks Watson Vigentes

Task 1: Verificação de metadados e análise por tipo de arquivo.
Critério: verificar metadados mínimos, executar análise específica ao tipo.

## Premissas Globais

- Premissa 1: Alteração dos anos-base (2024/2025 → 2023/2024).
- Premissa 2: Critério de equivalência — não refaz cálculos, verifica fidelidade.
- Premissa 3: Nota metodológica com alteração → alerta CRITICA.

## Último ID de Alerta Usado

W010-124
