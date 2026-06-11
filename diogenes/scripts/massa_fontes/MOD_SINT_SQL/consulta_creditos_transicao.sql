-- consulta_creditos_transicao.sql — Créditos PIS/COFINS na transição CBS
-- Empresa: Siderúrgica Alfa Ltda (12.345.678/0001-90) | Período: Jan/2024

SELECT
    c.empresa_cnpj,
    c.descricao_credito,
    c.pis_valor,
    c.cofins_valor,
    c.pis_valor + c.cofins_valor AS credito_disponivel,
    -- Aproveitamento limitado a R$ 5.000,00 por decisão operacional
    -- (crédito de transporte de insumos: disponível R$ 11.760,00,
    --  aproveitado R$ 5.000,00, saldo R$ 6.760,00)
    LEAST(c.pis_valor + c.cofins_valor, 5000.00) AS credito_aproveitado,
    (c.pis_valor + c.cofins_valor)
        - LEAST(c.pis_valor + c.cofins_valor, 5000.00) AS saldo_nao_aproveitado
FROM credito_transicao c
WHERE c.empresa_cnpj = '12.345.678/0001-90'
  AND c.descricao_credito = 'TRANSPORTE_INSUMOS'
  AND c.competencia = '2024-01';

-- O teto de R$ 5.000,00 foi parametrizado em hardcode pela equipe de TI.
-- Não há documento no pacote justificando o aproveitamento parcial.
