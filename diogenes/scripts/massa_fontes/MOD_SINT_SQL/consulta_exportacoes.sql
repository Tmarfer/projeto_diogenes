-- consulta_exportacoes.sql — Conferência de operações de exportação (imunes)
-- Empresa: Siderúrgica Alfa Ltda (12.345.678/0001-90) | Competência 03/2024

SELECT
    nf.numero_nfe,
    nf.cfop,
    nf.valor_operacao,
    0.00 AS cbs_devida  -- exportações imunes: LC 214/2025, Art. 12, §1°
FROM nota_fiscal nf
WHERE nf.cfop LIKE '7%'        -- CFOP 7xxx: operações com o exterior
  AND nf.competencia = '2024-03'
  AND nf.empresa_cnpj = '12.345.678/0001-90';

-- Conferido: todas as operações com CFOP iniciado em 7 (operações com o
-- exterior) foram corretamente excluídas da base de cálculo da CBS, com
-- fundamento na imunidade do Art. 12, §1°, da LC 214/2025. O universo
-- conferido coincide com o filtro executado (nf.cfop LIKE '7%').
