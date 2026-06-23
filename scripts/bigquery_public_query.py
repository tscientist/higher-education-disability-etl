from google.cloud import bigquery

client = bigquery.Client(project="higher-education-disability")

query = """
SELECT
  dados.ano,
  dados.sigla_uf,
  dados.id_municipio,
  dados.id_ies,
  dados.nome_curso,
  dados.id_curso,
  dados.nome_curso_cine,
  dados.tipo_grau_academico,
  dados.tipo_modalidade_ensino,
  dados.quantidade_vagas,
  dados.quantidade_inscritos,
  dados.quantidade_ingressantes,
  dados.quantidade_matriculas,
  dados.quantidade_concluintes,
  dados.quantidade_alunos_deficiencia,
  dados.quantidade_ingressantes_deficiencia,
  dados.quantidade_matriculas_deficiencia,
  dados.quantidade_concluintes_deficiencia
FROM `basedosdados.br_inep_censo_educacao_superior.curso` AS dados
WHERE dados.ano = 2022
LIMIT 10
"""

df = client.query(query).to_dataframe()

print(df)
print(f"Total rows returned: {len(df)}")