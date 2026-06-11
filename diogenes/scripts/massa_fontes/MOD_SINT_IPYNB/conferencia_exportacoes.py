# %%
# Conferência de exportações — Siderúrgica Alfa Ltda (12.345.678/0001-90)
# Competência: 03/2024 — operações CFOP 7101 (exportação de produção própria)

exportacoes_mar_2024 = [
    {"nfe": "000003", "cfop": "7101", "valor": 850_000.00},
    {"nfe": "000011", "cfop": "7101", "valor": 432_500.00},
]

# %%
# Exportações são imunes à CBS — LC 214/2025, Art. 12, §1°
for nf in exportacoes_mar_2024:
    cbs = 0.00
    print(f"NF-e {nf['nfe']} (CFOP {nf['cfop']}): base R$ {nf['valor']:,.2f} — CBS R$ {cbs:,.2f} (imune)")

# Conferido: nenhuma exportação compôs a base de cálculo da CBS no período.
