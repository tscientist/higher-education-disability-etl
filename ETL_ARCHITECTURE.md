# Arquitetura ETL

Pipeline para análise de estudantes com deficiência no ensino superior brasileiro.  
Integra dados do Censo da Educação Superior e do SISU via BigQuery, carregando-os no MongoDB.

Para instruções de execução, veja **[QUICKSTART.md](QUICKSTART.md)**.

---

## Fluxo de Dados

```
BigQuery (basedosdados — tabelas públicas)
    │
    ├── br_inep_censo_educacao_superior.curso   WHERE ano = 2022
    ├── br_inep_censo_educacao_superior.ies     WHERE ano = 2022
    └── br_mec_sisu.microdados                 WHERE ano = 2022
    │
    ▼
src/mongo/load_dados.py
    │
    ├── MongoDB: cursos          (~573 mil docs)
    ├── MongoDB: ies             (~2,5 mil docs)
    └── MongoDB: sisu            (~3,5 milhões docs)
    │
    ▼
src/mongo/build_gold_cursos_sisu.py
    │
    └── MongoDB: gold_cursos_sisu  (~573 mil docs)
```

---

## Scripts

| Script | O que faz |
|--------|-----------|
| `src/mongo/load_dados.py` | Lê as 3 tabelas do BigQuery e insere nas coleções brutas do MongoDB |
| `src/mongo/build_gold_cursos_sisu.py` | Constrói `gold_cursos_sisu` com join + embedding + métricas calculadas |
| `src/mongo/consultas.py` | Executa as 8 consultas analíticas no MongoDB |
| `docs/consultas.js` | As mesmas 8 consultas em sintaxe mongosh |
| `dashboard/app.py` | Dashboard Streamlit |
| `dashboard/api.py` | API REST FastAPI com endpoints para cada pergunta analítica |

---

## Coleções MongoDB

### `cursos`, `ies`, `sisu`
Coleções brutas carregadas diretamente do BigQuery. Estrutura idêntica às tabelas de origem (campos snake_case).

### `gold_cursos_sisu`
Coleção analítica principal. Um documento por curso/campus/ano.

**Chave primária:** `{ano}_{id_ies}_{id_curso}_{id_municipio}`

**Estrutura do documento:**

```json
{
  "_id": "2022_634_15002_4314902",
  "schemaVersion": 1,
  "ano": 2022,
  "uf": "RS",
  "idMunicipio": "4314902",

  "ies": {
    "idIes": "634",
    "nome": "Universidade Federal de Pelotas",
    "sigla": "UFPel",
    "tipoOrganizacaoAcademica": "Universidade",
    "tipoCategoriaAdministrativa": "Pública Federal",
    "endereco": { "logradouro": "...", "bairro": "...", "cep": "..." }
  },

  "curso": {
    "idCurso": "15002",
    "nome": "Ciência da Computação",
    "areaGeral": { "id": "06", "nome": "Computação e TIC" },
    "tipoGrauAcademico": "Bacharelado",
    "tipoModalidadeEnsino": "Presencial",
    "indicadorGratuito": true
  },

  "indicadoresAluno": {
    "vagas": 99, "inscritos": 1092,
    "ingressantes": 92, "matriculas": 377, "concluintes": 32
  },

  "indicadoresDeficiencia": {
    "alunos": 9, "ingressantes": 4,
    "matriculas": 8, "concluintes": 1,
    "reservaVaga": { "ingressantes": 3, "matriculas": 6, "concluintes": 0 }
  },

  "indicadoresPermanencia": {
    "apoioSocial": { "alunos": 40, "ingressantes": 10, "matriculas": 35, "concluintes": 7 },
    "situacao": { "trancada": 5, "desvinculada": 8, "transferida": 2, "falecidos": 0 }
  },

  "sisu": {
    "hasMatch": true,
    "siglaUfIes": "RS",
    "inscricoesTotal": 980, "inscricoesPcd": 45,
    "aprovadosRegular": 95, "aprovadosPcd": 18,
    "matriculadosFinal": 76, "matriculadosPcdFinal": 12,
    "notaCandidatoMediaGeral": 672.4, "notaCandidatoMediaPcd": 634.8,
    "notaCorteMediaGeral": 651.2, "notaCorteMediaPcd": 618.5,
    "demografia": {
      "porSexo": [
        { "sexo": "M", "inscricoes": 580, "inscricoes_pcd": 28, "aprovados_pcd": 11, "matriculados_pcd": 7 },
        { "sexo": "F", "inscricoes": 400, "inscricoes_pcd": 17, "aprovados_pcd": 7,  "matriculados_pcd": 5 }
      ],
      "porFaixaEtaria": [
        { "faixa_etaria": "18-24", "inscricoes": 740, "inscricoes_pcd": 30 }
      ],
      "porMunicipio": [
        { "id_municipio_candidato": "4314902", "uf": "RS", "inscricoes": 420, "inscricoes_pcd": 20 }
      ]
    }
  },

  "metricasCalculadas": {
    "percentualMatriculasPcd": 2.12,
    "taxaConclusaoGeral": 34.78,
    "taxaConclusaoPcd": 25.0,
    "taxaPerdaGeral": 65.22,
    "taxaPerdaPcd": 75.0
  },

  "etlMetadata": {
    "source": ["cursos", "ies", "sisu"],
    "loadedAt": "2025-07-07T12:00:00",
    "yearRange": { "start": 2022, "end": 2022 }
  }
}
```

---

## Join SISU × Censo

O SISU não tem granularidade de campus — apenas de curso/IES. Por isso o join usa a chave `(ano, id_ies, id_curso)`, sem `id_municipio`.

Cursos EaD que aparecem em múltiplos municípios no Censo recebem o mesmo bloco SISU em todos os documentos — comportamento idêntico ao join do BigQuery.

O `id_municipio` no `_id` do documento identifica o campus no Censo, não a localização do candidato.

---

## Índices em `gold_cursos_sisu`

| Índice | Campos | Finalidade |
|--------|--------|-----------|
| `idx_ano` | `ano` | Filtros por ano |
| `idx_uf_ano` | `uf, ano` | Filtros por UF |
| `idx_ies_ano` | `ies.idIes, ano` | Lookup por IES |
| `idx_curso_ano` | `curso.idCurso, ano` | Lookup por curso |
| `idx_modalidade_ano` | `curso.tipoModalidadeEnsino, ano` | Filtro por modalidade |
| `idx_categoria_ano` | `ies.tipoCategoriaAdministrativa, ano` | Filtro por categoria |
| `idx_sisu_match` | `sisu.hasMatch` | Filtrar cursos com SISU |
| **`idx_esr_pcd_analysis`** | `ano, uf, indicadoresDeficiencia.matriculas, metricasCalculadas.percentualMatriculasPcd` | Consultas PcD (ESR composto) |

---

## Consultas Implementadas

| # | Técnica MongoDB | Pergunta |
|---|----------------|----------|
| Q1 | `find` + projeção + dot notation | Cursos em SP com % PcD ≥ 5% |
| Q2 | `$elemMatch` em array | Cursos com mulheres PcD matriculadas |
| Q3 | `aggregate` `$group` + `$sort` | Ranking de UF por matrículas PcD |
| Q4 | `aggregate` `$group` multi-campo | Modalidade × categoria administrativa |
| Q5 | `$lookup` com pipeline | Gold enriquecida com dados completos da IES |
| Q6 | `find` + sort + limit | Top-10 taxa de conclusão PcD |
| Q7 | `explain` COLLSCAN vs IXSCAN | Demonstração do índice ESR |
| Q8 | `aggregate` `$group` em campo aninhado | % PcD por área geral do conhecimento |

---

## Privacidade

Os microdados do SISU contêm dados pessoais dos candidatos. O ETL:

- **Descarta** durante a agregação: CPF, nome, número de inscrição ENEM
- **Transforma** `data_nascimento` em faixa etária agregada (`18-24`, `25-29`, etc.)
- **Mantém apenas agregados** na `gold_cursos_sisu`: contagens, médias e arrays por grupo

Nenhum dado individual identificável é armazenado na coleção analítica.
