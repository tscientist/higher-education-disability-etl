// Executar com:
// mongosh "mongodb://localhost:27017/NOME_DO_BANCO" mongodb_etl_equivalente_bigquery.js

const YEAR = 2022;

const COURSE_STAGE = "stg_censo_curso";
const IES_STAGE = "stg_censo_ies";
const SISU_STAGE = "stg_sisu_microdados";

const SILVER_SISU = "silver_sisu_aggregated_2022_mongo";
const GOLD_COURSE = "gold_course_indicators_source_2022_mongo";

print("Iniciando ETL MongoDB equivalente ao BigQuery...");

print("Removendo coleções de saída antigas...");
db[SILVER_SISU].drop();
db[GOLD_COURSE].drop();

print("Criando índices nas coleções staging...");

db[COURSE_STAGE].createIndex({ ano: 1, id_ies: 1, id_curso: 1 });
db[IES_STAGE].createIndex({ ano: 1, id_ies: 1 });
db[SISU_STAGE].createIndex({ ano: 1, id_ies: 1, id_curso: 1 });

print("Etapa 1: Criando coleção Silver SISU agregada...");

db[SISU_STAGE].aggregate(
  [
    {
      $match: {
        ano: YEAR,
      },
    },
    {
      $addFields: {
        idIesStr: { $toString: "$id_ies" },
        idCursoStr: { $toString: "$id_curso" },

        modalidadeConcorrenciaNorm: {
          $toLower: { $ifNull: ["$modalidade_concorrencia", ""] },
        },
        tipoCotaNorm: {
          $toLower: { $ifNull: ["$tipo_cota", ""] },
        },
        sexoNorm: {
          $switch: {
            branches: [
              {
                case: {
                  $in: [
                    { $toUpper: { $ifNull: ["$sexo", ""] } },
                    ["F", "FEMININO"],
                  ],
                },
                then: "Feminino",
              },
              {
                case: {
                  $in: [
                    { $toUpper: { $ifNull: ["$sexo", ""] } },
                    ["M", "MASCULINO"],
                  ],
                },
                then: "Masculino",
              },
            ],
            default: "Não informado",
          },
        },
      },
    },
    {
      $addFields: {
        isPcd: {
          $or: [
            {
              $regexMatch: {
                input: "$modalidadeConcorrenciaNorm",
                regex: /deficiencia|deficiência|pcd/,
              },
            },
            {
              $regexMatch: {
                input: "$tipoCotaNorm",
                regex: /deficiencia|deficiência|pcd/,
              },
            },
          ],
        },

        statusAprovadoBool: {
          $cond: [{ $eq: ["$status_aprovado", true] }, true, false],
        },

        possuiMatricula: {
          $cond: [
            {
              $and: [
                { $ne: ["$status_matricula", null] },
                { $ne: ["$status_matricula", ""] },
              ],
            },
            true,
            false,
          ],
        },

        idadeAproximada: {
          $cond: [
            { $ne: ["$ano_nascimento", null] },
            { $subtract: ["$ano", { $toInt: "$ano_nascimento" }] },
            null,
          ],
        },
      },
    },
    {
      $addFields: {
        faixaEtaria: {
          $switch: {
            branches: [
              {
                case: {
                  $and: [
                    { $ne: ["$idadeAproximada", null] },
                    { $lt: ["$idadeAproximada", 18] },
                  ],
                },
                then: "Menor de 18",
              },
              {
                case: {
                  $and: [
                    { $gte: ["$idadeAproximada", 18] },
                    { $lte: ["$idadeAproximada", 24] },
                  ],
                },
                then: "18-24",
              },
              {
                case: {
                  $and: [
                    { $gte: ["$idadeAproximada", 25] },
                    { $lte: ["$idadeAproximada", 34] },
                  ],
                },
                then: "25-34",
              },
              {
                case: {
                  $and: [
                    { $gte: ["$idadeAproximada", 35] },
                    { $lte: ["$idadeAproximada", 44] },
                  ],
                },
                then: "35-44",
              },
              {
                case: {
                  $and: [
                    { $gte: ["$idadeAproximada", 45] },
                    { $lte: ["$idadeAproximada", 59] },
                  ],
                },
                then: "45-59",
              },
              {
                case: {
                  $gte: ["$idadeAproximada", 60],
                },
                then: "60+",
              },
            ],
            default: "Não informado",
          },
        },
      },
    },
    {
      $group: {
        _id: {
          ano: "$ano",
          id_ies: "$idIesStr",
          id_curso: "$idCursoStr",
        },

        nome_curso: { $first: "$nome_curso" },
        sigla_ies: { $first: "$sigla_ies" },
        campus: { $first: "$campus" },
        turno: { $first: "$turno" },
        periodicidade: { $first: "$periodicidade" },

        inscricoes_total: { $sum: 1 },

        inscricoes_pcd: {
          $sum: {
            $cond: ["$isPcd", 1, 0],
          },
        },

        aprovados_regular: {
          $sum: {
            $cond: [
              {
                $and: ["$statusAprovadoBool", { $eq: ["$isPcd", false] }],
              },
              1,
              0,
            ],
          },
        },

        aprovados_pcd: {
          $sum: {
            $cond: [
              {
                $and: ["$statusAprovadoBool", "$isPcd"],
              },
              1,
              0,
            ],
          },
        },

        matriculados_final: {
          $sum: {
            $cond: [
              {
                $and: ["$possuiMatricula", { $eq: ["$isPcd", false] }],
              },
              1,
              0,
            ],
          },
        },

        matriculados_pcd_final: {
          $sum: {
            $cond: [
              {
                $and: ["$possuiMatricula", "$isPcd"],
              },
              1,
              0,
            ],
          },
        },

        nota_candidato_media_geral: {
          $avg: {
            $convert: {
              input: "$nota_candidato",
              to: "double",
              onError: null,
              onNull: null,
            },
          },
        },

        nota_candidato_media_pcd: {
          $avg: {
            $cond: [
              "$isPcd",
              {
                $convert: {
                  input: "$nota_candidato",
                  to: "double",
                  onError: null,
                  onNull: null,
                },
              },
              null,
            ],
          },
        },

        nota_corte_media_regular: {
          $avg: {
            $convert: {
              input: "$nota_corte",
              to: "double",
              onError: null,
              onNull: null,
            },
          },
        },

        nota_corte_media_pcd: {
          $avg: {
            $cond: [
              "$isPcd",
              {
                $convert: {
                  input: "$nota_corte",
                  to: "double",
                  onError: null,
                  onNull: null,
                },
              },
              null,
            ],
          },
        },

        sexo_values: {
          $push: "$sexoNorm",
        },

        faixa_etaria_values: {
          $push: "$faixaEtaria",
        },

        municipio_values: {
          $push: {
            id_municipio: {
              $toString: { $ifNull: ["$id_municipio_candidato", ""] },
            },
            municipio: {
              $ifNull: ["$municipio_candidato", "Não informado"],
            },
            uf: {
              $ifNull: ["$uf_candidato", "Não informado"],
            },
          },
        },
      },
    },
    {
      $project: {
        _id: {
          $concat: [
            { $toString: "$_id.ano" },
            "_",
            "$_id.id_ies",
            "_",
            "$_id.id_curso",
          ],
        },

        ano: "$_id.ano",
        id_ies: "$_id.id_ies",
        id_curso: "$_id.id_curso",

        nome_curso: 1,
        sigla_ies: 1,
        campus: 1,
        turno: 1,
        periodicidade: 1,

        inscricoes_total: 1,
        inscricoes_pcd: 1,
        aprovados_regular: 1,
        aprovados_pcd: 1,
        matriculados_final: 1,
        matriculados_pcd_final: 1,

        nota_candidato_media_geral: {
          $round: ["$nota_candidato_media_geral", 2],
        },
        nota_candidato_media_pcd: {
          $round: ["$nota_candidato_media_pcd", 2],
        },
        nota_corte_media_regular: {
          $round: ["$nota_corte_media_regular", 2],
        },
        nota_corte_media_pcd: {
          $round: ["$nota_corte_media_pcd", 2],
        },

        demografia: {
          sexo: "$sexo_values",
          faixa_etaria: "$faixa_etaria_values",
          municipios: "$municipio_values",
        },

        etlMetadata: {
          source: "MongoDB aggregation from stg_sisu_microdados",
          createdAt: "$$NOW",
        },
      },
    },
    {
      $merge: {
        into: SILVER_SISU,
        on: "_id",
        whenMatched: "replace",
        whenNotMatched: "insert",
      },
    },
  ],
  {
    allowDiskUse: true,
  },
);

print("Silver SISU criada:");
print(db[SILVER_SISU].countDocuments());

print("Criando índice na Silver SISU...");
db[SILVER_SISU].createIndex({ ano: 1, id_ies: 1, id_curso: 1 });

print("Etapa 2: Criando coleção Gold Censo + IES + SISU...");

db[COURSE_STAGE].aggregate(
  [
    {
      $match: {
        ano: YEAR,
      },
    },
    {
      $addFields: {
        idIesStr: { $toString: "$id*ies" },
        idCursoStr: { $toString: "$id_curso" },
      },
    },
    {
      $lookup: {
        from: IES_STAGE,
        let: {
          anoCurso: "$ano",
          idIesCurso: "$id_ies",
        },
        pipeline: [
          {
            $match: {
              $expr: {
                $and: [
                  { $eq: ["$ano", "$$anoCurso"] },
                  { $eq: ["$id_ies", "$$idIesCurso"] },
                ],
              },
            },
          },
          {
            $limit: 1,
          },
        ],
        as: "ies_lookup",
      },
    },
    {
      $unwind: {
        path: "$ies_lookup",
        preserveNullAndEmptyArrays: true,
      },
    },
    {
      $lookup: {
        from: SILVER_SISU,
        let: {
          anoCurso: "$ano",
          idIesCurso: "$idIesStr",
          idCurso: "$idCursoStr",
        },
        pipeline: [
          {
            $match: {
              $expr: {
                $and: [
                  { $eq: ["$ano", "$$anoCurso"] },
                  { $eq: ["$id_ies", "$$idIesCurso"] },
                  { $eq: ["$id_curso", "$$idCurso"] },
                ],
              },
            },
          },
          {
            $limit: 1,
          },
        ],
        as: "sisu_lookup",
      },
    },
    {
      $unwind: {
        path: "$sisu_lookup",
        preserveNullAndEmptyArrays: true,
      },
    },
    {
      $addFields: {
        quantidade_matriculas_safe: {
          $convert: {
            input: "$quantidade_matriculas",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
        quantidade_matriculas_deficiencia_safe: {
          $convert: {
            input: "$quantidade_matriculas_deficiencia",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
        quantidade_ingressantes_safe: {
          $convert: {
            input: "$quantidade_ingressantes",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
        quantidade_ingressantes_deficiencia_safe: {
          $convert: {
            input: "$quantidade_ingressantes_deficiencia",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
        quantidade_concluintes_safe: {
          $convert: {
            input: "$quantidade_concluintes",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
        quantidade_concluintes_deficiencia_safe: {
          $convert: {
            input: "$quantidade_concluintes_deficiencia",
            to: "double",
            onError: 0,
            onNull: 0,
          },
        },
      },
    },
    {
      $project: {
        _id: {
          $concat: [
            { $toString: "$ano" },
            "*",
            "$idIesStr",
            "_",
            "$idCursoStr",
          ],
        },

        schemaVersion: { $literal: 1 },
        ano: "$ano",
        uf: "$sigla_uf",
        idMunicipio: { $toString: "$id_municipio" },

        ies: {
          idIes: "$idIesStr",
          nome: "$ies_lookup.nome",
          sigla: "$ies_lookup.sigla_ies",
          categoriaAdministrativa: "$ies_lookup.categoria_administrativa",
          organizacaoAcademica: "$ies_lookup.organizacao_academica",
          municipio: "$ies_lookup.nome_municipio",
          uf: "$ies_lookup.sigla_uf",
        },

        curso: {
          idCurso: "$idCursoStr",
          nome: "$nome_curso",
          nomeCine: "$nome_curso_cine",
          grauAcademico: "$tipo_grau_academico",
          modalidadeEnsino: "$tipo_modalidade_ensino",
          areaGeral: "$nome_area_geral",
        },

        indicadoresAluno: {
          vagas: "$quantidade_vagas",
          inscritos: "$quantidade_inscritos",
          ingressantes: "$quantidade_ingressantes_safe",
          matriculas: "$quantidade_matriculas_safe",
          concluintes: "$quantidade_concluintes_safe",
        },

        indicadoresDeficiencia: {
          alunosDeficiencia: "$quantidade_alunos_deficiencia",
          ingressantesDeficiencia: "$quantidade_ingressantes_deficiencia_safe",
          matriculasDeficiencia: "$quantidade_matriculas_deficiencia_safe",
          concluintesDeficiencia: "$quantidade_concluintes_deficiencia_safe",
        },

        sisu: {
          hasMatch: {
            $cond: [{ $ifNull: ["$sisu_lookup", false] }, true, false],
          },
          inscricoesTotal: { $ifNull: ["$sisu_lookup.inscricoes_total", 0] },
          inscricoesPcd: { $ifNull: ["$sisu_lookup.inscricoes_pcd", 0] },
          aprovadosRegular: { $ifNull: ["$sisu_lookup.aprovados_regular", 0] },
          aprovadosPcd: { $ifNull: ["$sisu_lookup.aprovados_pcd", 0] },
          matriculadosFinal: {
            $ifNull: ["$sisu_lookup.matriculados_final", 0],
          },
          matriculadosPcdFinal: {
            $ifNull: ["$sisu_lookup.matriculados_pcd_final", 0],
          },
          notaCandidatoMediaGeral: "$sisu_lookup.nota_candidato_media_geral",
          notaCandidatoMediaPcd: "$sisu_lookup.nota_candidato_media_pcd",
          notaCorteMediaRegular: "$sisu_lookup.nota_corte_media_regular",
          notaCorteMediaPcd: "$sisu_lookup.nota_corte_media_pcd",
          demografia: "$sisu_lookup.demografia",
        },

        metricasCalculadas: {
          percentualMatriculasPcd: {
            $cond: [
              { $gt: ["$quantidade_matriculas_safe", 0] },
              {
                $round: [
                  {
                    $multiply: [
                      {
                        $divide: [
                          "$quantidade_matriculas_deficiencia_safe",
                          "$quantidade_matriculas_safe",
                        ],
                      },
                      100,
                    ],
                  },
                  2,
                ],
              },
              null,
            ],
          },

          taxaConclusaoGeral: {
            $cond: [
              { $gt: ["$quantidade_ingressantes_safe", 0] },
              {
                $round: [
                  {
                    $multiply: [
                      {
                        $divide: [
                          "$quantidade_concluintes_safe",
                          "$quantidade_ingressantes_safe",
                        ],
                      },
                      100,
                    ],
                  },
                  2,
                ],
              },
              null,
            ],
          },

          taxaConclusaoPcd: {
            $cond: [
              { $gt: ["$quantidade_ingressantes_deficiencia_safe", 0] },
              {
                $round: [
                  {
                    $multiply: [
                      {
                        $divide: [
                          "$quantidade_concluintes_deficiencia_safe",
                          "$quantidade_ingressantes_deficiencia_safe",
                        ],
                      },
                      100,
                    ],
                  },
                  2,
                ],
              },
              null,
            ],
          },

          taxaPerdaGeral: {
            $cond: [
              { $gt: ["$quantidade_ingressantes_safe", 0] },
              {
                $round: [
                  {
                    $multiply: [
                      {
                        $divide: [
                          {
                            $subtract: [
                              "$quantidade_ingressantes_safe",
                              "$quantidade_concluintes_safe",
                            ],
                          },
                          "$quantidade_ingressantes_safe",
                        ],
                      },
                      100,
                    ],
                  },
                  2,
                ],
              },
              null,
            ],
          },

          taxaPerdaPcd: {
            $cond: [
              { $gt: ["$quantidade_ingressantes_deficiencia_safe", 0] },
              {
                $round: [
                  {
                    $multiply: [
                      {
                        $divide: [
                          {
                            $subtract: [
                              "$quantidade_ingressantes_deficiencia_safe",
                              "$quantidade_concluintes_deficiencia_safe",
                            ],
                          },
                          "$quantidade_ingressantes_deficiencia_safe",
                        ],
                      },
                      100,
                    ],
                  },
                  2,
                ],
              },
              null,
            ],
          },
        },

        etlMetadata: {
          source: [COURSE_STAGE, IES_STAGE, SILVER_SISU],
          createdBy: "MongoDB aggregation pipeline",
          loadedAt: "$$NOW",
        },
      },
    },
    {
      $merge: {
        into: GOLD_COURSE,
        on: "_id",
        whenMatched: "replace",
        whenNotMatched: "insert",
      },
    },
  ],
  {
    allowDiskUse: true,
  },
);

print("Gold criada:");
print(db[GOLD_COURSE].countDocuments());

print("Criando índices finais na coleção Gold...");

db[GOLD_COURSE].createIndex({ ano: 1 });
db[GOLD_COURSE].createIndex({ uf: 1 });
db[GOLD_COURSE].createIndex({ "ies.idIes": 1 });
db[GOLD_COURSE].createIndex({ "curso.idCurso": 1 });
db[GOLD_COURSE].createIndex({ "curso.nome": 1 });
db[GOLD_COURSE].createIndex({ "curso.modalidadeEnsino": 1 });
db[GOLD_COURSE].createIndex({ "ies.categoriaAdministrativa": 1 });
db[GOLD_COURSE].createIndex({
  ano: 1,
  uf: 1,
  "metricasCalculadas.percentualMatriculasPcd": -1,
});

print("ETL finalizado com sucesso.");

print("Exemplo de documento Gold:");
printjson(db[GOLD_COURSE].findOne());
