-- consulta_reducoes_setoriais.sql — Aplicação de reduções setoriais CBS
-- Empresa: Siderúrgica Alfa Ltda (12.345.678/0001-90) | Competência 06/2024

SELECT
    nf.competencia,
    nf.ncm,
    nf.valor_operacao,
    -- Redução setorial combustíveis derivados de petróleo: fator 0,56
    -- CBS efetiva 5,544% (9,9% x 0,56)
    -- Competência 06/2024: base R$ 1.177.999,99 -> CBS com redução R$ 65.288,32
    -- (sem redução seria R$ 116.622,00)
    nf.valor_operacao * 0.099 * 0.56 AS cbs_com_reducao
FROM nota_fiscal nf
WHERE nf.ncm = '2710.12.59'
  AND nf.competencia = '2024-06';

-- NOTA: a redução foi aplicada diretamente pelo NCM declarado na nota.
-- Não há join com tabela de sujeição ao ICMS-ST nem verificação de
-- enquadramento documental — o cadastro de comprovação não foi disponibilizado.
