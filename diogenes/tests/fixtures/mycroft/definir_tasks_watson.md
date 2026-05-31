# Fixture: Mycroft definir_tasks_watson (call_type: definir_tasks_watson)
# Origem: ciclo MOD_010_A1_20260531T041556Z
# Uso: diogenes_call_agent_fixture(agent_id="mycroft", call_type="definir_tasks_watson", fixture_path=THIS)

## Contexto da Chamada

Você (Mycroft) está definindo as tarefas que Watson deve executar para o módulo
MOD_010 (Pessoas Físicas — Produtor Rural PF).

## Catálogo Irene (resumo)

```yaml
modulo: MOD_010
score_consolidado: 0.974
recomendacao: APROVADO
total_abas: 66
total_xlsx: 1
```

### Papéis identificados:
- tabela_dados: 15 abas (dados NFe, bases cadastrais)
- tabela_mapeamento: 8 abas (de-para CNAE/NCM)
- resultado_intermediario: 20 abas (matrizes de incidência)
- aba_auxiliar: 18 abas (parâmetros, constantes)
- documentacao: 5 abas (leia-me, metadados)

## Inputs Disponíveis

```
CSV/
├── aux_mod_10_pf_execucao__aux_mod_10.csv
├── aux_mod_10_pf_execucao__aux_mod_10_1.csv
├── aux_mod_10_pf_execucao__aux_mod_10_2.csv
├── produtor_rural_pf__2023__base_debitos_2023__base_nfe.csv
├── produtor_rural_pf__consumo_final_contas_nacionais__de_para.csv
├── produtor_rural_pf__matriz_de_incidencia__ncm__sheet.csv
└── [... 78 outros CSVs]
XLSX/
└── AUX_MOD_10 PF - execução.xlsx (66 abas)
```

## Descrição Metodológica (extrato)

O módulo MOD_010 estima a base de cálculo da CBS para produtores rurais PF.
Metodologia: cruzamento de dados NFe (SPED) com bases cadastrais, aplicação
de matriz de incidência por CNAE/NCM, consolidação por UF.

## Instruções para Output

Produza as Tasks de Watson no formato padronizado:
- Task 1: análise por arquivo
- Task 2: rastreabilidade da cadeia
- Task 3: consolidação e posição
Inclua premissas globais e critérios de conclusão.
