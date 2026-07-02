-- Phase 3: Create gold_course_indicators_source_2022 table
-- Final analytical table joining Censo + IES + SISU aggregated
-- One row per course per institution per year (2022)
--
-- This is the final source table that Python ETL will read in pages

CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl.gold_course_indicators_source_2022` AS

WITH

-- stg_censo_ies pode ter múltiplas linhas por (ano, id_ies) — deduplica
censo_ies_dedup AS (
  SELECT *
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY ano, id_ies ORDER BY id_ies) AS rn
    FROM `higher-education-disability.ppgti_etl.stg_censo_ies`
    WHERE ano = 2022
  )
  WHERE rn = 1
)

SELECT
  -- Keys: inclui id_municipio para suportar IES EaD com múltiplos polos
  c.ano,
  c.id_ies,
  c.id_curso,
  c.sigla_uf,
  c.id_municipio as id_municipio_curso,
  
  -- IES data
  i.nome as ies_nome,
  i.sigla as ies_sigla,
  i.tipo_organizacao_academica as ies_tipo_organizacao_academica,
  i.tipo_categoria_administrativa as ies_tipo_categoria_administrativa,
  i.endereco as ies_endereco,
  i.numero as ies_numero,
  i.complemento as ies_complemento,
  i.bairro as ies_bairro,
  i.cep as ies_cep,
  i.id_municipio as id_municipio_ies,
  
  -- Course identification
  c.nome_curso,
  c.nome_curso_cine,
  c.id_curso_cine,
  c.id_area_geral,
  c.nome_area_geral,
  c.id_area_especifica,
  c.nome_area_especifica,
  c.id_area_detalhada,
  c.nome_area_detalhada,
  
  -- Course classification
  c.tipo_dimensao,
  c.tipo_organizacao_academica as curso_tipo_organizacao_academica,
  c.tipo_organizacao_administrativa as curso_tipo_organizacao_administrativa,
  c.rede,
  c.tipo_grau_academico,
  c.indicador_gratuito,
  c.tipo_modalidade_ensino,
  c.tipo_nivel_academico,
  
  -- General indicators
  c.quantidade_vagas,
  c.quantidade_inscritos,
  c.quantidade_ingressantes,
  c.quantidade_matriculas,
  c.quantidade_concluintes,
  
  -- PcD indicators
  c.quantidade_alunos_deficiencia,
  c.quantidade_ingressantes_deficiencia,
  c.quantidade_matriculas_deficiencia,
  c.quantidade_concluintes_deficiencia,
  
  -- Reserve vacancy indicators
  c.quantidade_ingressantes_reserva_vaga,
  c.quantidade_ingressantes_reserva_vaga_rede_publica,
  c.quantidade_ingressantes_reserva_vaga_etnico,
  c.quantidade_ingressantes_reserva_vaga_deficiencia,
  c.quantidade_ingressantes_reserva_vaga_social_renda_familiar,
  c.quantidade_ingressantes_reserva_vaga_outros,
  c.quantidade_matriculas_reserva_vaga,
  c.quantidade_matriculas_reserva_vaga_rede_publica,
  c.quantidade_matriculas_reserva_vaga_etnico,
  c.quantidade_matriculas_reserva_vaga_deficiencia,
  c.quantidade_matriculas_reserva_vaga_social_renda_familiar,
  c.quantidade_matriculas_reserva_vaga_outros,
  c.quantidade_concluintes_reserva_vaga,
  c.quantidade_concluintes_reserva_vaga_rede_publica,
  c.quantidade_concluintes_reserva_vaga_etnico,
  c.quantidade_concluintes_reserva_vaga_deficiencia,
  c.quantidade_concluintes_reserva_vaga_social_renda_familiar,
  c.quantidade_concluintes_reserva_vaga_outros,
  
  -- Permanence/status indicators
  c.quantidade_alunos_situacao_trancada,
  c.quantidade_alunos_situacao_desvinculada,
  c.quantidade_alunos_situacao_transferida,
  c.quantidade_alunos_situacao_falecidos,
  c.quantidade_alunos_parfor,
  c.quantidade_ingressantes_parfor,
  c.quantidade_matriculas_parfor,
  c.quantidade_concluintes_parfor,
  c.quantidade_alunos_apoio_social,
  c.quantidade_ingressantes_apoio_social,
  c.quantidade_matriculas_apoio_social,
  c.quantidade_concluintes_apoio_social,
  c.quantidade_alunos_atividade_extracurricular,
  c.quantidade_ingressantes_atividade_extracurricular,
  c.quantidade_matriculas_atividade_extracurricular,
  c.quantidade_concluintes_atividade_extracurricular,
  c.quantidade_alunos_mobilidade_academica,
  c.quantidade_ingressantes_mobilidade_academica,
  c.quantidade_matriculas_mobilidade_academica,
  c.quantidade_concluintes_mobilidade_academica,
  
  -- SISU aggregated (if available)
  s.inscricoes_total as sisu_inscricoes_total,
  s.inscricoes_pcd as sisu_inscricoes_pcd,
  s.aprovados_regular as sisu_aprovados_regular,
  s.aprovados_pcd as sisu_aprovados_pcd,
  s.matriculados_final as sisu_matriculados_final,
  s.matriculados_pcd_final as sisu_matriculados_pcd_final,
  s.nota_candidato_media_geral as sisu_nota_candidato_media_geral,
  s.nota_candidato_media_pcd as sisu_nota_candidato_media_pcd,
  s.nota_corte_media_geral as sisu_nota_corte_media_geral,
  s.nota_corte_media_pcd as sisu_nota_corte_media_pcd,
  s.demografia_por_sexo as sisu_demografia_por_sexo,
  s.demografia_por_faixa_etaria as sisu_demografia_por_faixa_etaria,
  s.demografia_por_municipio_candidato as sisu_demografia_por_municipio_candidato,
  
  -- SISU match flag
  (s._id IS NOT NULL) as sisu_has_match
  
FROM `higher-education-disability.ppgti_etl.stg_censo_curso` c
LEFT JOIN censo_ies_dedup i
  ON c.ano = i.ano
  AND c.id_ies = i.id_ies
LEFT JOIN `higher-education-disability.ppgti_etl.silver_sisu_aggregated_2022` s
  ON c.ano = s.ano
  AND c.id_ies = s.id_ies
  AND c.id_curso = s.id_curso
WHERE c.ano = 2022
ORDER BY c.id_ies, c.id_curso;
