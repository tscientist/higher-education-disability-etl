-- Phase 2: Create silver_sisu_aggregated_2022 table
-- Aggregates SISU microdados by (ano, id_ies, id_curso, sigla_uf_ies)
-- For year 2022 only
--
-- Pattern: pre-aggregate each demographic dimension in its own CTE,
-- then ARRAY_AGG the already-aggregated rows (no nested aggregation).

CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl.silver_sisu_aggregated_2022` AS

WITH

-- Step 1: normalize raw columns
base AS (
  SELECT
    ano,
    id_ies,
    id_curso,
    sigla_uf_ies,

    -- PcD flag on STRING columns
    (
      LOWER(modalidade_concorrencia) LIKE '%defici%'
      OR LOWER(tipo_cota)             LIKE '%defici%'
      OR LOWER(modalidade_concorrencia) LIKE '%pcd%'
      OR LOWER(tipo_cota)             LIKE '%pcd%'
    ) AS is_pcd,

    -- status_aprovado is BOOLEAN
    status_aprovado AS is_approved,

    -- status_matricula is STRING
    (status_matricula IS NOT NULL AND TRIM(status_matricula) != '') AS is_enrolled,

    -- nota columns are FLOAT
    nota_candidato,
    nota_corte,

    CASE
      WHEN LOWER(TRIM(sexo)) IN ('f', 'feminino')  THEN 'F'
      WHEN LOWER(TRIM(sexo)) IN ('m', 'masculino') THEN 'M'
      ELSE 'NAO_INFORMADO'
    END AS sexo_normalized,

    EXTRACT(YEAR FROM CURRENT_DATE())
      - EXTRACT(YEAR FROM SAFE.PARSE_DATE('%Y-%m-%d', data_nascimento))
      AS idade_approx,

    id_municipio_candidato,
    sigla_uf_candidato

  FROM `higher-education-disability.ppgti_etl.stg_sisu_microdados`
  WHERE ano = 2022
),

-- Step 2: derive age group
enriched AS (
  SELECT
    *,
    CASE
      WHEN idade_approx IS NULL OR idade_approx < 0 THEN 'nao_informado'
      WHEN idade_approx < 18 THEN '0-17'
      WHEN idade_approx < 25 THEN '18-24'
      WHEN idade_approx < 30 THEN '25-29'
      WHEN idade_approx < 35 THEN '30-34'
      WHEN idade_approx < 40 THEN '35-39'
      WHEN idade_approx < 50 THEN '40-49'
      WHEN idade_approx < 60 THEN '50-59'
      ELSE '60+'
    END AS faixa_etaria
  FROM base
),

-- Step 3: top-level totals per course
totals AS (
  SELECT
    ano, id_ies, id_curso, sigla_uf_ies,
    COUNT(*)                                                        AS inscricoes_total,
    COUNTIF(is_pcd)                                                 AS inscricoes_pcd,
    COUNTIF(is_approved AND NOT is_pcd)                             AS aprovados_regular,
    COUNTIF(is_approved AND is_pcd)                                 AS aprovados_pcd,
    COUNTIF(is_enrolled AND NOT is_pcd)                             AS matriculados_final,
    COUNTIF(is_enrolled AND is_pcd)                                 AS matriculados_pcd_final,
    ROUND(AVG(CASE WHEN NOT is_pcd THEN nota_candidato END), 2)     AS nota_candidato_media_geral,
    ROUND(AVG(CASE WHEN is_pcd     THEN nota_candidato END), 2)     AS nota_candidato_media_pcd,
    ROUND(AVG(CASE WHEN NOT is_pcd THEN nota_corte     END), 2)     AS nota_corte_media_geral,
    ROUND(AVG(CASE WHEN is_pcd     THEN nota_corte     END), 2)     AS nota_corte_media_pcd
  FROM enriched
  GROUP BY ano, id_ies, id_curso, sigla_uf_ies
),

-- Step 4a: aggregate by sex first, then ARRAY_AGG rows
demo_sexo_agg AS (
  SELECT
    ano, id_ies, id_curso,
    sexo_normalized                    AS sexo,
    COUNT(*)                           AS inscricoes,
    COUNTIF(is_pcd)                    AS inscricoes_pcd,
    COUNTIF(is_approved AND is_pcd)    AS aprovados_pcd,
    COUNTIF(is_enrolled AND is_pcd)    AS matriculados_pcd
  FROM enriched
  WHERE sexo_normalized IS NOT NULL
  GROUP BY ano, id_ies, id_curso, sexo_normalized
),
demo_sexo AS (
  SELECT ano, id_ies, id_curso,
    ARRAY_AGG(STRUCT(sexo, inscricoes, inscricoes_pcd, aprovados_pcd, matriculados_pcd))
      AS demografia_por_sexo
  FROM demo_sexo_agg
  GROUP BY ano, id_ies, id_curso
),

-- Step 4b: aggregate by age group first, then ARRAY_AGG rows
demo_faixa_agg AS (
  SELECT
    ano, id_ies, id_curso,
    faixa_etaria,
    COUNT(*)                           AS inscricoes,
    COUNTIF(is_pcd)                    AS inscricoes_pcd,
    COUNTIF(is_approved AND is_pcd)    AS aprovados_pcd,
    COUNTIF(is_enrolled AND is_pcd)    AS matriculados_pcd
  FROM enriched
  WHERE faixa_etaria IS NOT NULL
  GROUP BY ano, id_ies, id_curso, faixa_etaria
),
demo_faixa AS (
  SELECT ano, id_ies, id_curso,
    ARRAY_AGG(STRUCT(faixa_etaria, inscricoes, inscricoes_pcd, aprovados_pcd, matriculados_pcd))
      AS demografia_por_faixa_etaria
  FROM demo_faixa_agg
  GROUP BY ano, id_ies, id_curso
),

-- Step 4c: aggregate by municipality first, then ARRAY_AGG rows
demo_municipio_agg AS (
  SELECT
    ano, id_ies, id_curso,
    id_municipio_candidato,
    sigla_uf_candidato                 AS uf,
    COUNT(*)                           AS inscricoes,
    COUNTIF(is_pcd)                    AS inscricoes_pcd,
    COUNTIF(is_approved AND is_pcd)    AS aprovados_pcd,
    COUNTIF(is_enrolled AND is_pcd)    AS matriculados_pcd
  FROM enriched
  WHERE id_municipio_candidato IS NOT NULL
  GROUP BY ano, id_ies, id_curso, id_municipio_candidato, sigla_uf_candidato
),
demo_municipio AS (
  SELECT ano, id_ies, id_curso,
    ARRAY_AGG(STRUCT(id_municipio_candidato, uf, inscricoes, inscricoes_pcd, aprovados_pcd, matriculados_pcd))
      AS demografia_por_municipio_candidato
  FROM demo_municipio_agg
  GROUP BY ano, id_ies, id_curso
)

-- Step 5: join everything
SELECT
  t.ano,
  t.id_ies,
  t.id_curso,
  t.sigla_uf_ies,
  CONCAT(CAST(t.ano AS STRING), '_', t.id_ies, '_', t.id_curso) AS _id,
  t.inscricoes_total,
  t.inscricoes_pcd,
  t.aprovados_regular,
  t.aprovados_pcd,
  t.matriculados_final,
  t.matriculados_pcd_final,
  t.nota_candidato_media_geral,
  t.nota_candidato_media_pcd,
  t.nota_corte_media_geral,
  t.nota_corte_media_pcd,
  ds.demografia_por_sexo,
  df.demografia_por_faixa_etaria,
  dm.demografia_por_municipio_candidato

FROM totals t
LEFT JOIN demo_sexo      ds ON t.ano = ds.ano AND t.id_ies = ds.id_ies AND t.id_curso = ds.id_curso
LEFT JOIN demo_faixa     df ON t.ano = df.ano AND t.id_ies = df.id_ies AND t.id_curso = df.id_curso
LEFT JOIN demo_municipio dm ON t.ano = dm.ano AND t.id_ies = dm.id_ies AND t.id_curso = dm.id_curso

ORDER BY t.ano DESC, t.id_ies, t.id_curso;
