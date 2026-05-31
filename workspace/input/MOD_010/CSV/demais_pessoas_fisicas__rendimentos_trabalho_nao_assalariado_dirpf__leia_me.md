# Leia-me

> Fonte: Rendimentos Trabalho Não Assalariado - DIRPF.xlsx

Rend Trab Não Assalariado

Correção Ocup Não Determinadas

Totais Rend TNA por Categoria

OBS.: Sobre tabelas utilizadas

1) Tabela de Rendimentos recebidos de pessoa física: cópia de view original da base de dados da DIRPF
create table u08105524775.gnirpf_irpf_repf stored as parquet as 
	select * from dbbr_irpf_119_11706_ada.tab_8_aa_irpfmx_rend_pf_view where an_exercicio = <ano>;

2) Tabela de Declarações de IRPF: tabela com dados originários da base de dados da DIRPF, tratados para manter apenas declarações válidas e vigentes, conforme processo utilizado para geração do estudo dos Grandes Números IRPF
select * from dbbr_irpf_119_11706_ada.tab_7_aa_irpfmx_declaracao_view where an_exercicio = <ano> and co_situacao_decl not in (85, 80);