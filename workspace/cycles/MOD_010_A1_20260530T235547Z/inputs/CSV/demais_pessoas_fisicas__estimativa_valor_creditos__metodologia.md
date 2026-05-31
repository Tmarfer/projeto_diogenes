# Metodologia

> Fonte: Estimativa Valor Créditos.xlsx

2) Os totais por CPF do Carnê-Leão foram comparados com os valores do Livro Caixa declarados na DIRPF, e selecionada uma amostra de cpfs com uma variação máxima de 10% entre os dois valores

3) Os lançamentos do livro caixa no Carnê-Leão foram analisados para identificar qual percentual dos valores pode ser apropriado como crédito da CBS

4) Cálculo do percentual para aplicação ao valor total do livro caixa declarado na DIRPF

5) Aplicação do percentual calculado ao valor do livro caixa declarado na DIRPF

OBS.: Sobre tabelas utilizadas

1) Tabela de Rendimentos recebidos de pessoa física: cópia de view original da base de dados da DIRPF, conforme comando de criação abaixo
create table u08105524775.gnirpf_irpf_repf stored as parquet as 
	select * from dbbr_irpf_119_11706_ada.tab_8_aa_irpfmx_rend_pf_view where an_exercicio = <ano>;

2) Tabela de Declarações de IRPF: tabela com dados originários da base de dados da DIRPF, tratados para manter apenas declarações válidas e vigentes, conforme processo utilizado para geração do estudo dos Grandes Números IRPF. SQL original abaixo
select * from dbbr_irpf_119_11706_ada.tab_7_aa_irpfmx_declaracao_view where an_exercicio = <ano> and co_situacao_decl not in (85, 80);

3) Tabela de Demonstrativos do Carnê-Leão: demonstrativo anual do contribuinte, ao qual é associado o plano de contas
dbbr_irpf_carne_leao.demonstrativos

4) Tabela de Lançamentos referentes a Pagamentos do Carnê-Leão: lançamentos individuais associados ao demonstrativo
dbbr_irpf_carne_leao.lancamentos_pagamentos