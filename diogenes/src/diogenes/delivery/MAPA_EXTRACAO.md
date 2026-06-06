# Mapa de Extração — esquema (`entrega_mapa_extracao.json`)

Produzido por `Mycroft.mapear_dados_modulo` (ou autorado à mão por Lestrade) e gravado
em `workspace/cycles/{cycle_id}/output/entrega_mapa_extracao.json`. Diz ao
`ExtractorFinanceiro` **onde** estão os dados na planilha principal — nunca os valores.

```jsonc
{
  "modulo_nome": "Pessoa Física",
  "versao": "1.0 | Atividade 1",
  "planilha_principal": "AUX_MOD_10 PF - execução.xlsx",   // nome do arquivo em inputs/

  // Texto descritivo (redigido pelo agente; NÃO contém números da planilha)
  "narrativa": {
    "proposta": {"descricao": "...", "contexto_narrativo": "...", "fonte": "..."},
    "objetivo": "...",
    "objetivo_detalhado": "...",
    "arquivos": {
      "principal":  [{"nome": "...", "descricao": "...", "tamanho": "36 KB"}],
      "auxiliares": [{"nome": "...", "descricao": "...", "tamanho": "3 MB"}],
      "fontes":     [{"nome": "DIRPF", "tipo": "Declaração", "descricao": "..."}]
    },
    "notas_metodologicas": [
      {"nome": "Nota V11.docx", "data": "24/04/2026", "descricao": "...",
       "conteudo_resumo": "...", "situacao_inventario": "Presente", "observacao": "..."}
    ],
    "testes": {
      "camada_1": [{"id": "V-01", "descricao": "...", "resultado": "...", "status": "Atendido"}],
      "camada_2": [...],
      "camada_3": [...]
    }
  },

  // Camada financeira — apenas LOCALIZAÇÕES; os números são lidos por openpyxl.
  // formato ∈ {moeda, bilhoes, milhoes, inteiro, percentual, texto}
  "blocos": [
    {
      "id": "visao_geral", "titulo": "Visão Geral", "descricao": "...",
      "kpis": [
        {"rotulo": "Arrecadação própria", "aba": "Resumo", "celula": "B3",
         "formato": "bilhoes", "nota": "2024", "destaque": "green"}
      ],
      "tabelas": [
        {"titulo": "Composição", "aba": "Resumo", "intervalo": "A1:C10",
         "cabecalho_na_primeira_linha": true, "fonte": "DIRPF"}
      ],
      "graficos": [
        {"tipo": "barras", "titulo": "Débitos por ano", "aba": "Resumo",
         "intervalo_labels": "A2:A4", "intervalo_valores": "B2:B4", "nota": ""}
      ]
    }
  ],
  "valores_agregados": [
    {"descricao": "Débitos totais", "aba": "Resumo",
     "celula_2023": "B12", "celula_2024": "C12", "formato": "bilhoes"}
  ],
  "sensibilidade_redutor": {
    "aba": "Sensibilidade", "intervalo_redutores": "A2:A6", "intervalo_valores": "B2:B6"
  }
}
```

## Regras

- **Números nunca aparecem aqui.** Só nomes de aba e referências de célula/intervalo.
- Campo ausente ou célula deslocada gera *aviso* (não erro): a entrega prossegue.
- `cabecalho_na_primeira_linha` (default `true`) usa a 1ª linha do intervalo como cabeçalho.
- Se o mapa não existir, a Fase de Entrega gera os entregáveis só com a camada de
  auditoria (ocorrências do Sherlock + relatório consolidado).
