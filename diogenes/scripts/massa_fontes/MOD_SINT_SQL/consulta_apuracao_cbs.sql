-- consulta_apuracao_cbs.sql — Apuração CBS por tipo de operação
-- Empresas: Siderúrgica Alfa Ltda (12.345.678/0001-90) e Alimentar Beta S.A. (98.765.432/0001-10)
-- Período: Jan–Jun/2024 | Alíquota de referência: 9,9%

SELECT
    e.cnpj,
    e.razao_social,
    nf.competencia,
    nf.tipo_operacao,
    nf.valor_operacao,
    CASE nf.tipo_operacao
        WHEN 'VENDA_MERCADORIA'    THEN nf.valor_operacao * 0.099
        WHEN 'PRESTACAO_SERVICO'   THEN nf.valor_operacao * 0.099
        -- Locação de bem móvel tributada integralmente a 9,9%
        -- (Empresa B, competência 04/2024: base R$ 45.000,00 -> CBS R$ 4.455,00)
        WHEN 'LOCACAO_BEM_MOVEL'   THEN nf.valor_operacao * 0.099
        WHEN 'EXPORTACAO'          THEN 0.00
        ELSE nf.valor_operacao * 0.099
    END AS cbs_devida
FROM nota_fiscal nf
JOIN empresa e ON e.id = nf.empresa_id
WHERE nf.competencia BETWEEN '2024-01' AND '2024-06'
ORDER BY e.cnpj, nf.competencia;

-- Observação da equipe: locação de bem móvel mantida na base de incidência
-- por decisão interna; sem ressalva quanto a entendimento divergente da RFB.
