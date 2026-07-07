// =============================================================================
// consultas.js — Consultas MongoDB para gold_cursos_sisu
// Executar: mongosh <connection-string> --file docs/consultas.js
// Ou cole cada bloco no MongoDB Compass / mongosh interativo.
//
// Estrutura da collection gold_cursos_sisu
// ─────────────────────────────────────────
// _id  : "{ano}_{id_ies}_{id_curso}_{id_municipio}"
//         Uma linha por campus (polo EaD pode gerar N docs para mesmo curso).
//
// sisu : bloco agregado por (ano, id_ies, id_curso) — SEM id_municipio.
//         O SISU não tem granularidade de campus; cursos EaD compartilham
//         o mesmo bloco SISU entre todos os polos (comportamento intencional,
//         espelha o join do BigQuery silver/gold SQL).
//         Campo sisu.siglaUfIes indica a UF sede da IES no SISU.
// =============================================================================

const db_name   = "higher_education";
const db        = db.getSiblingDB(db_name);
const col       = db.gold_cursos_sisu;
const col_ies   = db.ies;

// =============================================================================
// Q1 — find + projeção: cursos em SP com % matrícula PcD ≥ 5%
// Cobre: filtro simples, dot notation, projeção, sort.
// =============================================================================
print("\n=== Q1 — find + projeção ===");
col.find(
  {
    ano: 2022,
    uf:  "SP",
    "metricasCalculadas.percentualMatriculasPcd": { $gte: 5 }
  },
  {
    _id: 1,
    uf: 1,
    "curso.nome": 1,
    "ies.nome": 1,
    "indicadoresDeficiencia.matriculas": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1
  }
)
.sort({ "metricasCalculadas.percentualMatriculasPcd": -1 })
.limit(5)
.forEach(printjson);

// =============================================================================
// Q2 — dot notation + $elemMatch em array de objetos
// Cursos com ao menos 1 mulher PcD matriculada no SISU.
// Cobre: acesso a array aninhado, $elemMatch.
// =============================================================================
print("\n=== Q2 — $elemMatch em array porSexo ===");
col.find(
  {
    "sisu.hasMatch": true,
    "sisu.demografia.porSexo": {
      $elemMatch: { sexo: "F", matriculados_pcd: { $gte: 1 } }
    }
  },
  {
    _id: 1,
    uf: 1,
    "curso.nome": 1,
    "ies.sigla": 1,
    "sisu.demografia.porSexo": 1
  }
)
.limit(5)
.forEach(printjson);

// =============================================================================
// Q3 — aggregation: ranking de UF por matrículas PcD (Censo)
// Cobre: $match, $group, $addFields, $sort, $project.
// =============================================================================
print("\n=== Q3 — ranking UF por matrículas PcD ===");
col.aggregate([
  { $match: { ano: 2022 } },
  { $group: {
      _id: "$uf",
      totalMatriculasPcd: { $sum: "$indicadoresDeficiencia.matriculas" },
      totalMatriculas:    { $sum: "$indicadoresAluno.matriculas" },
      totalCursos:        { $sum: 1 }
  }},
  { $addFields: {
      percentualPcd: {
        $cond: {
          if:   { $gt: ["$totalMatriculas", 0] },
          then: { $round: [
            { $multiply: [{ $divide: ["$totalMatriculasPcd", "$totalMatriculas"] }, 100] },
            2
          ]},
          else: 0
        }
      }
  }},
  { $sort:    { totalMatriculasPcd: -1 } },
  { $project: { _id: 0, uf: "$_id", totalMatriculasPcd: 1,
                totalMatriculas: 1, percentualPcd: 1, totalCursos: 1 } }
]).forEach(printjson);

// =============================================================================
// Q4 — aggregation: distribuição modalidade × categoria administrativa
// Cobre: $group em múltiplos campos, $sort, $project.
// =============================================================================
print("\n=== Q4 — modalidade × categoria ===");
col.aggregate([
  { $match: { ano: 2022 } },
  { $group: {
      _id: {
        modalidade: "$curso.tipoModalidadeEnsino",
        categoria:  "$ies.tipoCategoriaAdministrativa"
      },
      totalCursos:        { $sum: 1 },
      totalMatriculas:    { $sum: "$indicadoresAluno.matriculas" },
      totalMatriculasPcd: { $sum: "$indicadoresDeficiencia.matriculas" }
  }},
  { $sort: { totalCursos: -1 } },
  { $project: {
      _id: 0,
      modalidade: "$_id.modalidade",
      categoria:  "$_id.categoria",
      totalCursos: 1, totalMatriculas: 1, totalMatriculasPcd: 1
  }},
  { $limit: 10 }
]).forEach(printjson);

// =============================================================================
// Q5 — $lookup: enriquecer gold com dados completos da coleção ies
// Cobre: $lookup com pipeline, $let, $expr, $arrayElemAt.
// =============================================================================
print("\n=== Q5 — $lookup coleção ies ===");
col.aggregate([
  { $match: { ano: 2022, "metricasCalculadas.percentualMatriculasPcd": { $gte: 10 } } },
  { $lookup: {
      from: "ies",
      let:  { ano_curso: "$ano", id_ies_curso: "$ies.idIes" },
      pipeline: [
        { $match: { $expr: { $and: [
            { $eq: ["$ano", "$$ano_curso"] },
            { $eq: [{ $toString: "$id_ies" }, "$$id_ies_curso"] }
        ]}}},
        { $project: {
            _id: 0,
            quantidade_docentes_exercicio: 1,
            quantidade_docentes_exercicio_doutorado: 1,
            indicador_biblioteca_internet: 1
        }}
      ],
      as: "_ies_full"
  }},
  { $addFields: { ies_extra: { $arrayElemAt: ["$_ies_full", 0] } } },
  { $unset: "_ies_full" },
  { $project: {
      _id: 1, uf: 1,
      "curso.nome": 1, "ies.nome": 1, "ies.sigla": 1,
      "metricasCalculadas.percentualMatriculasPcd": 1,
      ies_extra: 1
  }},
  { $sort: { "metricasCalculadas.percentualMatriculasPcd": -1 } },
  { $limit: 5 }
]).forEach(printjson);

// =============================================================================
// Q6 — top-10 cursos com maior taxa de conclusão PcD
// Cobre: $match com múltiplas condições, $sort, $limit, $project.
// =============================================================================
print("\n=== Q6 — top-10 taxa conclusão PcD ===");
col.find(
  {
    ano: 2022,
    "sisu.hasMatch": true,
    "metricasCalculadas.taxaConclusaoPcd": { $gt: 0 },
    "indicadoresDeficiencia.ingressantes": { $gte: 5 }
  },
  {
    _id: 0, uf: 1,
    "curso.nome": 1, "ies.sigla": 1,
    "indicadoresDeficiencia.ingressantes": 1,
    "indicadoresDeficiencia.concluintes": 1,
    "metricasCalculadas.taxaConclusaoPcd": 1,
    "metricasCalculadas.taxaConclusaoGeral": 1,
    "sisu.inscricoesPcd": 1
  }
)
.sort({ "metricasCalculadas.taxaConclusaoPcd": -1 })
.limit(10)
.forEach(printjson);

// =============================================================================
// Q7 — explain: COLLSCAN → IXSCAN com índice ESR
// Cobre: explain("executionStats"), hint, índice composto ESR.
// =============================================================================
print("\n=== Q7 — explain COLLSCAN ===");
var planScan = col.find(
  {
    ano: 2022,
    uf:  "SP",
    "metricasCalculadas.percentualMatriculasPcd": { $gte: 5, $lte: 20 }
  }
)
.sort({ "indicadoresDeficiencia.matriculas": -1 })
.hint({ $natural: 1 })
.explain("executionStats");

var es = planScan.executionStats;
print("COLLSCAN — stage: "      + es.executionStages.stage);
print("  totalDocsExamined:   " + es.totalDocsExamined);
print("  nReturned:           " + es.nReturned);
print("  executionTimeMillis: " + es.executionTimeMillis + " ms");

print("\n=== Q7 — explain IXSCAN (índice ESR) ===");
var planIdx = col.find(
  {
    ano: 2022,
    uf:  "SP",
    "metricasCalculadas.percentualMatriculasPcd": { $gte: 5, $lte: 20 }
  }
)
.sort({ "indicadoresDeficiencia.matriculas": -1 })
.hint("idx_esr_pcd_analysis")
.explain("executionStats");

var es2 = planIdx.executionStats;
var inner = es2.executionStages.inputStage || es2.executionStages;
print("IXSCAN — stage: "        + inner.stage);
print("  totalKeysExamined:   " + es2.totalKeysExamined);
print("  totalDocsExamined:   " + es2.totalDocsExamined);
print("  nReturned:           " + es2.nReturned);
print("  executionTimeMillis: " + es2.executionTimeMillis + " ms");
print("  indexName:           " + (inner.indexName || "idx_esr_pcd_analysis"));

// =============================================================================
// Q8 — % PcD por área geral do conhecimento
// Cobre: $group em campo aninhado, $addFields com $divide/$multiply, $sort.
// =============================================================================
print("\n=== Q8 — % PcD por área geral ===");
col.aggregate([
  { $match: { ano: 2022 } },
  { $group: {
      _id: { areaId: "$curso.areaGeral.id", areaNome: "$curso.areaGeral.nome" },
      totalCursos:          { $sum: 1 },
      totalMatriculas:      { $sum: "$indicadoresAluno.matriculas" },
      totalMatriculasPcd:   { $sum: "$indicadoresDeficiencia.matriculas" },
      cursosComSisu:        { $sum: { $cond: ["$sisu.hasMatch", 1, 0] } },
      totalInscricoesSisu:  { $sum: { $ifNull: ["$sisu.inscricoesTotal", 0] } },
      totalPcdSisu:         { $sum: { $ifNull: ["$sisu.inscricoesPcd",   0] } }
  }},
  { $addFields: {
      percentualPcdCenso: {
        $cond: {
          if: { $gt: ["$totalMatriculas", 0] },
          then: { $round: [
            { $multiply: [{ $divide: ["$totalMatriculasPcd", "$totalMatriculas"] }, 100] }, 2
          ]},
          else: null
        }
      },
      percentualPcdSisu: {
        $cond: {
          if: { $gt: ["$totalInscricoesSisu", 0] },
          then: { $round: [
            { $multiply: [{ $divide: ["$totalPcdSisu", "$totalInscricoesSisu"] }, 100] }, 2
          ]},
          else: null
        }
      }
  }},
  { $sort: { percentualPcdCenso: -1 } },
  { $project: {
      _id: 0,
      areaGeral:           "$_id.areaNome",
      totalCursos: 1,      totalMatriculas: 1,     totalMatriculasPcd: 1,
      percentualPcdCenso: 1, cursosComSisu: 1,     percentualPcdSisu: 1
  }}
]).forEach(printjson);
