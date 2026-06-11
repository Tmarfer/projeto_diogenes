# %%
# Créditos PIS/COFINS na transição — Siderúrgica Alfa Ltda (12.345.678/0001-90)
# Competência: Jan/2024

creditos = [
    {"descricao": "TRANSPORTE_INSUMOS", "pis": 2_100.00, "cofins": 9_660.00},
    {"descricao": "ENERGIA_ELETRICA",   "pis": 1_350.00, "cofins": 6_210.00},
]

# %%
# Teto operacional de aproveitamento definido pela equipe (R$ 5.000,00)
TETO_APROVEITAMENTO = 5_000.00

for c in creditos:
    disponivel = c["pis"] + c["cofins"]
    aproveitado = min(disponivel, TETO_APROVEITAMENTO) if c["descricao"] == "TRANSPORTE_INSUMOS" else disponivel
    saldo = disponivel - aproveitado
    print(f"{c['descricao']}: disponível R$ {disponivel:,.2f} | "
          f"aproveitado R$ {aproveitado:,.2f} | saldo R$ {saldo:,.2f}")
# TRANSPORTE_INSUMOS: disponível R$ 11.760,00 | aproveitado R$ 5.000,00 | saldo R$ 6.760,00
# O teto de R$ 5.000,00 não tem documento de justificativa no pacote.
