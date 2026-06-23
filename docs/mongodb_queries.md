# MongoDB Queries for Higher Education Disability Data (2022)

This document demonstrates comprehensive MongoDB queries on the `gold_course_indicators` collection, including find operations with filters/projections, aggregation pipelines, and analysis queries.

## Collection Structure

The `gold_course_indicators` collection contains one document per IES+Curso combination per year:

```javascript
{
  _id: "2022_1_10000",  // {year}_{ies_id}_{course_id}
  ano: 2022,
  uf: "SP",
  
  ies: {
    idIes: "1",
    nome: "Universidade de São Paulo",
    sigla: "USP",
    tipoOrganizacaoAcademica: "Universidade",
    tipoCategoriaAdministrativa: "Pública Federal",
    endereco: { ... }
  },
  
  curso: {
    idCurso: "10000",
    nome: "Engenharia Civil",
    nomeCine: "Engineering",
    tipoModalidadeEnsino: "Presencial",
    areaGeral: { id: "8", nome: "Engenharias, Arquitetura e Urbanismo" },
    // ...
  },
  
  indicadoresAluno: {
    vagas: 100,
    inscritos: 500,
    ingressantes: 80,
    matriculas: 250,
    concluintes: 60
  },
  
  indicadoresDeficiencia: {
    matriculas: 25,
    ingressantes: 8,
    concluintes: 5,
    reservaVaga: { ... }
  },
  
  sisu: {
    hasMatch: true,
    inscricoesTotal: 400,
    inscricoesPcd: 50,
    aprovadosRegular: 300,
    aprovadosPcd: 45,
    matriculadosF
inal: 250,
    matriculadosPcdFinal: 20,
    demografia: {
      porSexo: [
        { sexo: "Masculino", quantidade: 15 },
        { sexo: "Feminino", quantidade: 5 }
      ],
      porFaixaEtaria: [
        { faixaEtaria: "18-24", quantidade: 12 },
        { faixaEtaria: "25-29", quantidade: 8 }
      ],
      porMunicipio: [
        { codigoMunicipio: "3550308", nomeMunicipio: "São Paulo", quantidade: 18 }
      ]
    }
  },
  
  metricasCalculadas: {
    percentualMatriculasPcd: 10.0,
    taxaConclusaoGeral: 75.0,
    taxaConclusaoPcd: 62.5,
    taxaPerdaGeral: 25.0,
    taxaPerdaPcd: 37.5
  }
}
```

---

## 1. FIND QUERIES - Basic Filters and Projections

### 1.1 Find all courses in a specific state

```javascript
db.gold_course_indicators.find(
  { uf: "SP", ano: 2022 },
  { 
    "ies.sigla": 1, 
    "ies.nome": 1,
    "curso.nome": 1,
    "indicadoresAluno.matriculas": 1,
    "indicadoresDeficiencia.matriculas": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1
  }
)
.sort({ "metricasCalculadas.percentualMatriculasPcd": -1 })
.limit(20)
```

**Use case:** Regional overview of PcD enrollment across courses

---

### 1.2 Find all courses from a specific institution

```javascript
db.gold_course_indicators.find(
  { 
    "ies.idIes": "1",
    ano: 2022
  },
  {
    "curso.nome": 1,
    "curso.tipoModalidadeEnsino": 1,
    "curso.areaGeral": 1,
    "indicadoresAluno": 1,
    "indicadoresDeficiencia": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1
  }
)
.sort({ "curso.nome": 1 })
```

**Use case:** Institutional PcD indicators across all programs

---

### 1.3 Find courses with highest PcD enrollment

```javascript
db.gold_course_indicators.find(
  { 
    ano: 2022,
    "indicadoresDeficiencia.matriculas": { $gt: 0 }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "indicadoresDeficiencia.matriculas": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1
  }
)
.sort({ "indicadoresDeficiencia.matriculas": -1 })
.limit(50)
```

**Use case:** Identify leading courses for PcD access

---

### 1.4 Find distance education courses with PcD data

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "curso.tipoModalidadeEnsino": "Distância",
    "indicadoresAluno.matriculas": { $gt: 0 }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "indicadoresAluno.matriculas": 1,
    "indicadoresDeficiencia.matriculas": 1,
    "metricasCalculadas": 1
  }
)
```

**Use case:** Analyze PcD participation in distance education

---

### 1.5 Find courses by administrative category

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "ies.tipoCategoriaAdministrativa": "Pública Federal",
    "indicadoresDeficiencia.matriculas": { $exists: true }
  },
  {
    "ies.sigla": 1,
    "ies.tipoCategoriaAdministrativa": 1,
    "curso.nome": 1,
    "indicadoresDeficiencia.matriculas": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1
  }
)
.sort({ "indicadoresDeficiencia.matriculas": -1 })
```

**Use case:** Compare PcD access across public/private sectors

---

### 1.6 Find courses in a specific area

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "curso.areaGeral.id": "8"  // Engineering
  },
  {
    "ies.sigla": 1,
    "curso.areaGeral.nome": 1,
    "curso.areaEspecifica.nome": 1,
    "indicadoresAluno.matriculas": 1,
    "indicadoresDeficiencia.matriculas": 1
  }
)
```

**Use case:** Subject-specific PcD enrollment analysis

---

### 1.7 Project only calculated metrics

```javascript
db.gold_course_indicators.find(
  { ano: 2022 },
  {
    "_id": 0,
    "ies.sigla": 1,
    "ies.nome": 1,
    "curso.nome": 1,
    "uf": 1,
    "metricasCalculadas": 1,
    "indicadoresAluno.matriculas": 1
  }
)
```

**Use case:** Export metric data for external analysis

---

## 2. FIND QUERIES - $elemMatch on SISU Demographics

### 2.1 Find courses with SISU enrollments for specific sex

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "sisu.demografia.porSexo": {
      $elemMatch: {
        sexo: "Feminino",
        quantidade: { $gt: 10 }
      }
    }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "sisu.demografia.porSexo": 1
  }
)
```

**Use case:** Identify courses with significant female PcD enrollment in SISU

---

### 2.2 Find courses with specific age group presence in SISU

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "sisu.demografia.porFaixaEtaria": {
      $elemMatch: {
        faixaEtaria: "18-24",
        quantidade: { $gte: 5 }
      }
    }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "sisu.demografia.porFaixaEtaria": 1,
    "indicadoresAluno.ingressantes": 1
  }
)
```

**Use case:** Analyze PcD students entering university at traditional ages

---

### 2.3 Find courses with SISU enrollments from specific municipality

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "sisu.demografia.porMunicipio": {
      $elemMatch: {
        codigoMunicipio: "3550308",  // São Paulo
        quantidade: { $gt: 0 }
      }
    }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "sisu.demografia.porMunicipio": 1
  }
)
```

**Use case:** Analyze geographic accessibility of SISU PcD candidates

---

### 2.4 Find courses with diverse SISU age group representation

```javascript
db.gold_course_indicators.find(
  {
    ano: 2022,
    "sisu.demografia.porFaixaEtaria": {
      $elemMatch: {
        quantidade: { $gt: 0 }
      }
    }
  },
  {
    "ies.sigla": 1,
    "curso.nome": 1,
    "sisu.demografia": 1
  }
)
.limit(100)
```

**Use case:** Courses with multi-generational PcD participation

---

## 3. AGGREGATION PIPELINES - Advanced Analysis

### 3.1 Q1: PcD enrollment evolution (by state, 2022)

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$uf",
      totalMatriculas: { $sum: "$indicadoresAluno.matriculas" },
      totalMatriculasPcd: { $sum: "$indicadoresDeficiencia.matriculas" },
      cursoCount: { $sum: 1 },
      avgPercentualPcd: { $avg: "$metricasCalculadas.percentualMatriculasPcd" }
    }
  },
  {
    $project: {
      _id: 1,
      totalMatriculas: 1,
      totalMatriculasPcd: 1,
      cursoCount: 1,
      percentualGeral: {
        $cond: [
          { $eq: ["$totalMatriculas", 0] },
          0,
          { $multiply: [{ $divide: ["$totalMatriculasPcd", "$totalMatriculas"] }, 100] }
        ]
      },
      avgPercentualPcd: { $round: ["$avgPercentualPcd", 2] }
    }
  },
  { $sort: { totalMatriculasPcd: -1 } }
])
```

**Use case:** State-level PcD enrollment overview

---

### 3.2 Q2: UFs with largest PcD enrollments

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$uf",
      totalPcD: { $sum: "$indicadoresDeficiencia.matriculas" },
      maxPcDCourse: { $max: "$indicadoresDeficiencia.matriculas" },
      avgPcDPerCourse: { $avg: "$indicadoresDeficiencia.matriculas" },
      courseCount: { $sum: 1 }
    }
  },
  {
    $project: {
      uf: "$_id",
      _id: 0,
      totalPcD: 1,
      courseCount: 1,
      maxPcDCourse: 1,
      avgPcDPerCourse: { $round: ["$avgPcDPerCourse", 2] }
    }
  },
  { $sort: { totalPcD: -1 } },
  { $limit: 10 }
])
```

**Use case:** Identify states with highest PcD access

---

### 3.3 Q3: PcD distribution - In-person vs Distance

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$curso.tipoModalidadeEnsino",
      totalMatriculas: { $sum: "$indicadoresAluno.matriculas" },
      totalPcD: { $sum: "$indicadoresDeficiencia.matriculas" },
      ingressantes: { $sum: "$indicadoresAluno.ingressantes" },
      ingressantesPcd: { $sum: "$indicadoresDeficiencia.ingressantes" },
      concluintes: { $sum: "$indicadoresAluno.concluintes" },
      concluentesPcd: { $sum: "$indicadoresDeficiencia.concluintes" }
    }
  },
  {
    $project: {
      modalidade: "$_id",
      _id: 0,
      totalMatriculas: 1,
      totalPcD: 1,
      percentualPcD: {
        $cond: [
          { $eq: ["$totalMatriculas", 0] },
          0,
          { $multiply: [{ $divide: ["$totalPcD", "$totalMatriculas"] }, 100] }
        ]
      },
      taxaConclusaoGeral: {
        $cond: [
          { $eq: ["$ingressantes", 0] },
          0,
          { $multiply: [{ $divide: ["$concluintes", "$ingressantes"] }, 100] }
        ]
      },
      taxaConclusaoPcd: {
        $cond: [
          { $eq: ["$ingressantesPcd", 0] },
          0,
          { $multiply: [{ $divide: ["$concluentesPcd", "$ingressantesPcd"] }, 100] }
        ]
      }
    }
  }
])
```

**Use case:** Compare PcD participation and outcomes by teaching modality

---

### 3.4 Q4: Administrative categories with highest PcD

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$ies.tipoCategoriaAdministrativa",
      totalPcD: { $sum: "$indicadoresDeficiencia.matriculas" },
      totalMatriculas: { $sum: "$indicadoresAluno.matriculas" },
      courseCount: { $sum: 1 },
      instituicoes: { $addToSet: "$ies.sigla" }
    }
  },
  {
    $project: {
      categoria: "$_id",
      _id: 0,
      totalPcD: 1,
      totalMatriculas: 1,
      courseCount: 1,
      instituicoes: { $size: "$instituicoes" },
      percentualPcD: {
        $cond: [
          { $eq: ["$totalMatriculas", 0] },
          0,
          { $multiply: [{ $divide: ["$totalPcD", "$totalMatriculas"] }, 100] }
        ]
      }
    }
  },
  { $sort: { totalPcD: -1 } }
])
```

**Use case:** Analyze PcD enrollment across institutional sectors

---

### 3.5 Q5: Completion rates comparison (General vs PcD)

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $project: {
      uf: 1,
      taxaConclusaoGeral: "$metricasCalculadas.taxaConclusaoGeral",
      taxaConclusaoPcd: "$metricasCalculadas.taxaConclusaoPcd",
      diferenca: {
        $subtract: [
          "$metricasCalculadas.taxaConclusaoGeral",
          "$metricasCalculadas.taxaConclusaoPcd"
        ]
      },
      ingressantes: "$indicadoresAluno.ingressantes"
    }
  },
  {
    $match: {
      ingressantes: { $gt: 0 },
      taxaConclusaoGeral: { $ne: null },
      taxaConclusaoPcd: { $ne: null }
    }
  },
  {
    $group: {
      _id: "$uf",
      cursoCount: { $sum: 1 },
      avgTaxaGeralPorUf: { $avg: "$taxaConclusaoGeral" },
      avgTaxaPcdPorUf: { $avg: "$taxaConclusaoPcd" },
      avgDiferenca: { $avg: "$diferenca" },
      maxDiferenca: { $max: "$diferenca" },
      minDiferenca: { $min: "$diferenca" }
    }
  },
  {
    $project: {
      uf: "$_id",
      _id: 0,
      cursoCount: 1,
      avgTaxaGeral: { $round: ["$avgTaxaGeralPorUf", 2] },
      avgTaxaPcd: { $round: ["$avgTaxaPcdPorUf", 2] },
      diferenca: { $round: ["$avgDiferenca", 2] },
      dispersao: {
        $round: [{ $subtract: ["$maxDiferenca", "$minDiferenca"] }, 2]
      }
    }
  },
  { $sort: { cursoCount: -1 } }
])
```

**Use case:** Identify UFs where PcD completion lags behind general population

---

### 3.6 Q6: UFs with highest PcD loss rates

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$uf",
      ingressantes: { $sum: "$indicadoresAluno.ingressantes" },
      ingressantesPcd: { $sum: "$indicadoresDeficiencia.ingressantes" },
      concluintes: { $sum: "$indicadoresAluno.concluintes" },
      concluentesPcd: { $sum: "$indicadoresDeficiencia.concluintes" }
    }
  },
  {
    $project: {
      uf: "$_id",
      _id: 0,
      taxaPerdaGeral: {
        $cond: [
          { $eq: ["$ingressantes", 0] },
          null,
          { $multiply: [
            { $divide: [
              { $subtract: ["$ingressantes", "$concluintes"] },
              "$ingressantes"
            ]},
            100
          ]}
        ]
      },
      taxaPerdaPcd: {
        $cond: [
          { $eq: ["$ingressantesPcd", 0] },
          null,
          { $multiply: [
            { $divide: [
              { $subtract: ["$ingressantesPcd", "$concluentesPcd"] },
              "$ingressantesPcd"
            ]},
            100
          ]}
        ]
      },
      diferencaPerdas: {
        $cond: [
          { $or: [
            { $eq: ["$ingressantes", 0] },
            { $eq: ["$ingressantesPcd", 0] }
          ]},
          null,
          { $subtract: [
            { $multiply: [
              { $divide: [
                { $subtract: ["$ingressantesPcd", "$concluentesPcd"] },
                "$ingressantesPcd"
              ]},
              100
            ]},
            { $multiply: [
              { $divide: [
                { $subtract: ["$ingressantes", "$concluintes"] },
                "$ingressantes"
              ]},
              100
            ]}
          ]}
        ]
      }
    }
  },
  { $match: { diferencaPerdas: { $ne: null } } },
  { $sort: { diferencaPerdas: -1 } }
])
```

**Use case:** Identify states where PcD students have higher dropout rates

---

### 3.7 Q7: SISU access funnel for PcD candidates (2022)

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022, "sisu.hasMatch": true } },
  {
    $group: {
      _id: null,
      totalInscricoesPcd: { $sum: "$sisu.inscricoesPcd" },
      totalAprovadosPcd: { $sum: "$sisu.aprovadosPcd" },
      totalMatriculadosPcd: { $sum: "$sisu.matriculadosPcdFinal" },
      cursoCount: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      etapa: "SISU 2022 - PcD Funnel",
      totalInscricoesPcd: 1,
      totalAprovadosPcd: 1,
      totalMatriculadosPcd: 1,
      cursoCount: 1,
      taxaAprovacao: {
        $cond: [
          { $eq: ["$totalInscricoesPcd", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalAprovadosPcd", "$totalInscricoesPcd"] },
              100
            ]},
            2
          ]}
        ]
      },
      taxaMatriculacao: {
        $cond: [
          { $eq: ["$totalAprovadosPcd", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalMatriculadosPcd", "$totalAprovadosPcd"] },
              100
            ]},
            2
          ]}
        ]
      },
      taxaConversao: {
        $cond: [
          { $eq: ["$totalInscricoesPcd", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalMatriculadosPcd", "$totalInscricoesPcd"] },
              100
            ]},
            2
          ]}
        ]
      }
    }
  }
])
```

**Use case:** Analyze SISU PcD candidate journey from application to enrollment

---

### 3.8 Q8: SISU PcD demand vs Censo PcD enrollments

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $project: {
      uf: 1,
      sisuDemandaPcd: "$sisu.inscricoesPcd",
      censoPcD: "$indicadoresDeficiencia.matriculas",
      razaoSisuVsCenso: {
        $cond: [
          { $eq: ["$indicadoresDeficiencia.matriculas", 0] },
          null,
          { $divide: ["$sisu.inscricoesPcd", "$indicadoresDeficiencia.matriculas"] }
        ]
      }
    }
  },
  {
    $match: { razaoSisuVsCenso: { $ne: null } }
  },
  {
    $group: {
      _id: "$uf",
      totalSisuDemandaPcd: { $sum: "$sisuDemandaPcd" },
      totalCensoPcd: { $sum: "$censoPcD" },
      avgRazao: { $avg: "$razaoSisuVsCenso" },
      maxRazao: { $max: "$razaoSisuVsCenso" },
      cursoCount: { $sum: 1 }
    }
  },
  {
    $project: {
      uf: "$_id",
      _id: 0,
      totalSisuDemandaPcd: 1,
      totalCensoPcd: 1,
      cursoCount: 1,
      demandaParaPcDEnrolled: {
        $round: [
          { $cond: [
            { $eq: ["$totalCensoPcd", 0] },
            0,
            { $divide: ["$totalSisuDemandaPcd", "$totalCensoPcd"] }
          ]},
          2
        ]
      },
      avgRazaoPorCurso: { $round: ["$avgRazao", 2] }
    }
  },
  { $sort: { totalSisuDemandaPcd: -1 } }
])
```

**Use case:** Compare SISU demand for PcD positions vs actual Censo enrollments

---

### 3.9 Q9: Courses with highest PcD concentration

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $project: {
      _id: 1,
      ies: 1,
      curso: 1,
      uf: 1,
      percentualPcd: "$metricasCalculadas.percentualMatriculasPcd",
      matriculas: "$indicadoresAluno.matriculas",
      matriculasPcd: "$indicadoresDeficiencia.matriculas"
    }
  },
  {
    $match: {
      percentualPcd: { $gt: 0 },
      matriculas: { $gt: 30 }  // Filter out very small courses
    }
  },
  { $sort: { percentualPcd: -1 } },
  { $limit: 30 },
  {
    $project: {
      sigla: "$ies.sigla",
      nomeCurso: "$curso.nome",
      uf: 1,
      percentualPcd: { $round: ["$percentualPcd", 2] },
      matriculas: 1,
      matriculasPcd: 1
    }
  }
])
```

**Use case:** Identify courses with highest PcD inclusive participation

---

### 3.10 Q10: Area-based PcD analysis

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022 } },
  {
    $group: {
      _id: "$curso.areaGeral.nome",
      totalMatriculas: { $sum: "$indicadoresAluno.matriculas" },
      totalPcD: { $sum: "$indicadoresDeficiencia.matriculas" },
      totalConcluintes: { $sum: "$indicadoresAluno.concluintes" },
      totalConcluintesPcd: { $sum: "$indicadoresDeficiencia.concluintes" },
      cursoCount: { $sum: 1 }
    }
  },
  {
    $project: {
      area: "$_id",
      _id: 0,
      totalMatriculas: 1,
      totalPcD: 1,
      cursoCount: 1,
      percentualPcd: {
        $cond: [
          { $eq: ["$totalMatriculas", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalPcD", "$totalMatriculas"] },
              100
            ]},
            2
          ]}
        ]
      },
      taxaConclusaoGeral: {
        $cond: [
          { $eq: ["$totalMatriculas", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalConcluintes", "$totalMatriculas"] },
              100
            ]},
            2
          ]}
        ]
      },
      taxaConclusaoPcd: {
        $cond: [
          { $eq: ["$totalPcD", 0] },
          0,
          { $round: [
            { $multiply: [
              { $divide: ["$totalConcluintesPcd", "$totalPcD"] },
              100
            ]},
            2
          ]}
        ]
      }
    }
  },
  { $sort: { totalPcD: -1 } }
])
```

**Use case:** Identify which study areas have strongest PcD programs

---

## 4. USING INDEXES FOR PERFORMANCE

### 4.1 Query using ESR index for PcD analysis

The ESR (Equality, Sort, Range) index supports this query efficiently:

```javascript
// Index: { ano: 1, uf: 1, "indicadoresDeficiencia.matriculas": -1, "metricasCalculadas.percentualMatriculasPcd": 1 }

db.gold_course_indicators
  .find({
    ano: 2022,                                      // Equality
    uf: "SP",                                        // Equality
    "metricasCalculadas.percentualMatriculasPcd": { // Range
      $gte: 5,
      $lte: 20
    }
  })
  .sort({ "indicadoresDeficiencia.matriculas": -1 }) // Sort
  .explain("executionStats")
```

**Index Path:**
1. Use index to filter `ano = 2022`
2. Further filter `uf = "SP"`
3. Use index for sorting by PcD matriculas (descending)
4. Finally filter by percentage range

Expected: `IXSCAN` stage (index scan), not `COLLSCAN` (collection scan)

---

### 4.2 Query using compound index for regional analysis

```javascript
// Index: { uf: 1, ano: 1 }

db.gold_course_indicators.aggregate([
  { $match: { uf: "SP", ano: 2022 } },  // Uses index
  { $group: { _id: "$ies.tipoCategoriaAdministrativa", count: { $sum: 1 } } }
])
.explain("executionStats")
```

---

## 5. DOT NOTATION EXAMPLES

### 5.1 Accessing nested fields in find queries

```javascript
// Access institution fields
db.gold_course_indicators.find(
  { "ies.tipoCategoriaAdministrativa": "Pública Federal" },
  { "ies.nome": 1, "ies.sigla": 1 }
)

// Access course area hierarchy
db.gold_course_indicators.find(
  { "curso.areaGeral.id": "8" },  // Filter by area
  { 
    "curso.areaGeral.nome": 1,
    "curso.areaEspecifica.nome": 1,
    "curso.areaDetalhada.nome": 1
  }
)

// Access calculated metrics
db.gold_course_indicators.find(
  { "metricasCalculadas.percentualMatriculasPcd": { $gt: 15 } },
  { 
    "curso.nome": 1,
    "metricasCalculadas.percentualMatriculasPcd": 1,
    "metricasCalculadas.taxaConclusaoPcd": 1
  }
)

// Access nested SISU data
db.gold_course_indicators.find(
  { "sisu.hasMatch": true },
  { 
    "sisu.inscricoesTotal": 1,
    "sisu.inscricoesPcd": 1,
    "sisu.notaCandidatoMediaPcd": 1
  }
)
```

---

## 6. $LOOKUP EXAMPLE - Joining with sisu_aggregated

The `sisu_aggregated` collection mirrors SISU data by (ano, id_ies, id_curso). You can use `$lookup` to join:

```javascript
db.gold_course_indicators.aggregate([
  { $match: { ano: 2022, uf: "SP" } },
  {
    $lookup: {
      from: "sisu_aggregated",
      let: { 
        ano: "$ano",
        id_ies: "$ies.idIes",
        id_curso: "$curso.idCurso"
      },
      pipeline: [
        {
          $match: {
            $expr: {
              $and: [
                { $eq: ["$ano", "$$ano"] },
                { $eq: ["$id_ies", "$$id_ies"] },
                { $eq: ["$id_curso", "$$id_curso"] }
              ]
            }
          }
        },
        {
          $project: {
            _id: 0,
            sisuDemografia: "$demografia",
            sisuAproveitos: "$aproveitamento"
          }
        }
      ],
      as: "sisuDetail"
    }
  },
  {
    $unwind: {
      path: "$sisuDetail",
      preserveNullAndEmptyArrays: true
    }
  },
  {
    $project: {
      ies: "$ies.sigla",
      curso: "$curso.nome",
      censoPcd: "$indicadoresDeficiencia.matriculas",
      sisuDemografia: "$sisuDetail.sisuDemografia"
    }
  }
])
```

---

## 7. PERFORMANCE TIPS

1. **Use indexes for large datasets**: Always filter by indexed fields first
2. **Project only needed fields**: Reduce document size in transmission
3. **Push $match early in pipeline**: Apply filters before $group/$lookup
4. **Use $explain()**: Check if queries use index scans vs collection scans
5. **Batch operations**: Use bulk_write for multiple inserts/updates
6. **Monitor slow queries**: Check MongoDB logs for queries >100ms

---

## 8. RUNNING THESE QUERIES

### From MongoDB Shell

```bash
mongo mongodb://localhost:27017/higher_education
use higher_education

// Paste any query from above
db.gold_course_indicators.find(...).explain("executionStats")
```

### From Python

```python
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['higher_education']
collection = db['gold_course_indicators']

# Find query
results = collection.find({"uf": "SP", "ano": 2022}, {"ies.nome": 1})
for doc in results:
    print(doc)

# Aggregation pipeline
pipeline = [
    { "$match": { "ano": 2022 } },
    { "$group": { "_id": "$uf", "total": { "$sum": "$indicadoresDeficiencia.matriculas" } } }
]
results = collection.aggregate(pipeline)
for doc in results:
    print(doc)
```

---

## Document Version History

- **v1.0** (2024): Initial query documentation for 2022 dataset
- **Collections**: gold_course_indicators, sisu_aggregated
- **Indexes**: 10 on gold_course_indicators, 3 on sisu_aggregated
- **Year Coverage**: 2022 (single year, multi-year support for future versions)
