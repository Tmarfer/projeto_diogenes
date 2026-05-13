-- =============================================================================
-- script_extracao.sql — MOD_SINT_001 | DVA-CBS | TC 015.848/2025-6
-- ETL inicial: extração, filtragem por CNAE e limpeza de dados CBS/TI
-- Executor: SERPRO / COSIT | Data: 2026-02-12
-- Base: EFD-Contribuições 2025 + DCTF Web 2025 + CNPJ Cadastro
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PASSO 1: Criação da base filtrada por CNAE (serviços de TI)
-- Tabela-fonte: efd.registro_m200 (receitas apuradas por empresa/período)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_efd_ti_2025 AS
SELECT
    e.cnpj_raiz,
    e.cnpj_completo,
    e.competencia_aaaamm,
    e.cnae_principal,
    e.vl_bc_cofins          AS base_calculo_cbs,
    e.vl_cofins_apurado     AS cbs_apurado,
    e.vl_rec_brt            AS receita_bruta_total,
    e.vl_rec_devolucoes     AS devolucoes,
    e.vl_rec_descontos_inco AS descontos_incondicionais,
    c.porte_empresa,
    c.municipio_uf,
    CASE
        WHEN e.vl_bc_cofins > 0
        THEN e.vl_cofins_apurado / e.vl_bc_cofins
        ELSE NULL
    END                     AS aliquota_efetiva
FROM efd.registro_m200 e
INNER JOIN cadastro.cnpj c
    ON e.cnpj_raiz = c.cnpj_raiz
WHERE e.competencia_aaaamm BETWEEN 202501 AND 202512
  AND e.cnae_principal IN (
      '6201500', -- Desenvolvimento sob encomenda
      '6202300', -- Desenvolvimento customizável
      '6203100', -- Desenvolvimento não-customizável
      '6209100'  -- Suporte técnico e outros
  )
  AND e.ind_mov = 1          -- apenas declarações com movimento
  AND e.vl_rec_brt > 0      -- excluir declarações zeradas;


-- -----------------------------------------------------------------------------
-- PASSO 2: Consolidação anual por CNPJ raiz
-- Agrega os 12 meses de cada empresa em um único registro anual
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_consolidado_anual AS
SELECT
    cnpj_raiz,
    cnae_principal,
    porte_empresa,
    COUNT(DISTINCT competencia_aaaamm)          AS meses_declarados,
    SUM(base_calculo_cbs)                       AS bc_total_anual,
    SUM(cbs_apurado)                            AS cbs_total_anual,
    SUM(receita_bruta_total)                    AS receita_bruta_anual,
    CASE
        WHEN SUM(base_calculo_cbs) > 0
        THEN SUM(cbs_apurado) / SUM(base_calculo_cbs)
        ELSE NULL
    END                                         AS aliquota_efetiva_anual,
    MAX(municipio_uf)                           AS uf
FROM vw_efd_ti_2025
GROUP BY cnpj_raiz, cnae_principal, porte_empresa
HAVING SUM(base_calculo_cbs) > 0;


-- -----------------------------------------------------------------------------
-- PASSO 3: Identificação de outliers (critério: ±3 desvios-padrão)
-- -----------------------------------------------------------------------------
WITH stats AS (
    SELECT
        AVG(aliquota_efetiva_anual)    AS media,
        STDDEV(aliquota_efetiva_anual) AS desvio_padrao
    FROM vw_consolidado_anual
    WHERE aliquota_efetiva_anual IS NOT NULL
),
outliers AS (
    SELECT
        c.cnpj_raiz,
        c.aliquota_efetiva_anual,
        s.media,
        s.desvio_padrao,
        ABS(c.aliquota_efetiva_anual - s.media) / s.desvio_padrao AS z_score,
        CASE
            WHEN ABS(c.aliquota_efetiva_anual - s.media) / s.desvio_padrao > 3
            THEN 1
            ELSE 0
        END AS flag_outlier
    FROM vw_consolidado_anual c
    CROSS JOIN stats s
)
CREATE OR REPLACE VIEW vw_outliers AS
SELECT * FROM outliers WHERE flag_outlier = 1;


-- -----------------------------------------------------------------------------
-- PASSO 4: Cálculo da alíquota de referência por porte (excluindo outliers)
-- RESULTADO FINAL que alimenta a planilha_cbs.xlsx
-- -----------------------------------------------------------------------------
SELECT
    c.porte_empresa,
    COUNT(DISTINCT c.cnpj_raiz)                         AS qtd_empresas,
    SUM(c.bc_total_anual)                               AS bc_total_bi_reais,
    SUM(c.cbs_total_anual)                              AS cbs_total_bi_reais,
    ROUND(
        SUM(c.cbs_total_anual) / SUM(c.bc_total_anual) * 100,
        2
    )                                                   AS aliquota_referencia_pct
FROM vw_consolidado_anual c
LEFT JOIN vw_outliers o ON c.cnpj_raiz = o.cnpj_raiz
WHERE o.cnpj_raiz IS NULL   -- excluir outliers
GROUP BY c.porte_empresa
ORDER BY
    CASE c.porte_empresa
        WHEN 'ME'     THEN 1
        WHEN 'EPP'    THEN 2
        WHEN 'Outros' THEN 3
    END;


-- =============================================================================
-- RESULTADO ESPERADO (conferido com planilha_cbs.xlsx, aba "Resultado_Final"):
-- porte_empresa | qtd_empresas | aliquota_referencia_pct
-- ME            | 48.230       | 8.65
-- EPP           | 31.450       | 8.71
-- Outros        |  8.807       | 8.78
-- Total         | 88.487       | 8.77
-- =============================================================================
