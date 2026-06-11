# %%
# Memória de cálculo CBS — Alimentar Beta S.A. (98.765.432/0001-10)
# Período: Jan–Jun/2024 | Alíquota de referência: 9,9%
ALIQUOTA_CBS = 0.099

# %%
# Competência 04/2024 — receitas da Empresa B
receitas_abr_2024 = {
    "venda_alimentos_basicos": 120_000.00,   # NCM 1006.30.21 — alíquota zero
    "locacao_bem_movel": 45_000.00,          # empilhadeira locada a terceiro
    "prestacao_servico_admin": 30_000.00,
}

# %%
# CBS sobre locação de bem móvel: tributada integralmente a 9,9%
# (decisão interna da contabilidade — sem ressalva de entendimento divergente)
cbs_locacao = receitas_abr_2024["locacao_bem_movel"] * ALIQUOTA_CBS
print(f"CBS locação 04/2024: R$ {cbs_locacao:,.2f}")  # R$ 4.455,00

# %%
# Competência 03/2024 — serviços de saúde com alíquota reduzida 50%
# Aplicado fator 0,5 diretamente sobre toda a receita de serviços do CNAE
# de saúde, sem segregar serviços administrativos hospitalares.
receita_servicos_saude_mar = 190_000.00
cbs_saude = receita_servicos_saude_mar * ALIQUOTA_CBS * 0.5
print(f"CBS saúde 03/2024: R$ {cbs_saude:,.2f}")  # R$ 9.405,00 (sem redução: R$ 18.810,00)

# %%
# Alimentos básicos (Anexo I): alíquota zero aplicada — NCMs verificados
cbs_alimentos = receitas_abr_2024["venda_alimentos_basicos"] * 0.0
print(f"CBS alimentos 04/2024: R$ {cbs_alimentos:,.2f}")
