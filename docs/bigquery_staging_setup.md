# BigQuery Staging Setup

## Data Source

**Source:** [Base dos Dados](https://basedosdados.org/)

All data copied in this staging process originates from public and shared BigQuery datasets maintained by Base dos Dados.

### References

- **SISU (Sistema de Seleção Unificado):** https://basedosdados.org/dataset/8326e3d7-9cd2-4144-863f-c380fefef82c
- **Censo da Educação Superior:** https://basedosdados.org/dataset/a3b57cca-ff80-4bf2-8bac-c145109e06a7
- **INEP - Microdados Censo da Educação Superior:** https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior

## Overview

This project's ETL pipeline reads data from public and shared BigQuery datasets maintained by Base dos Dados. To ensure reliable and efficient operations, selected records from these source datasets were copied into staging tables within the project's own Google Cloud dataset.

These staging tables form a staging layer that decouples the ETL from direct dependencies on external public datasets. The ETL reads from these staging tables instead of querying the public source tables on each run.

The staging dataset serves as a controlled, project-owned copy of the necessary source data, enabling consistent ETL execution and reducing repeated access to shared resources.

## Destination Dataset

**Project:** `higher-education-disability`

**Dataset:** `ppgti_etl_test`

### Staging Tables Created

- `stg_sisu_microdados`
- `stg_censo_curso`
- `stg_censo_ies`
- `stg_censo_dicionario`

## Source Dataset: SISU

### Table: microdados

**Source table:**
```
basedosdados.br_mec_sisu.microdados
```

**Destination table:**
```
higher-education-disability.ppgti_etl_test.stg_sisu_microdados
```

**Data copied:** Records from 2018 to 2022

**SQL used to create/populate the staging table:**

```sql
CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl_test.stg_sisu_microdados` AS
SELECT *
FROM `basedosdados.br_mec_sisu.microdados`
WHERE ano BETWEEN 2018 AND 2022;
```

**Validation query for destination:**

```sql
SELECT COUNT(*) AS total_registros
FROM `higher-education-disability.ppgti_etl_test.stg_sisu_microdados`;
```

**Validation query for source (same filter):**

```sql
SELECT COUNT(*) AS total_registros
FROM `basedosdados.br_mec_sisu.microdados`
WHERE ano BETWEEN 2018 AND 2022;
```

The counts from both queries should match after the copy completes successfully.

## Source Dataset: Higher Education Census

Source dataset: `basedosdados.br_inep_censo_educacao_superior`

### Table: curso

**Source table:**
```
basedosdados.br_inep_censo_educacao_superior.curso
```

**Destination table:**
```
higher-education-disability.ppgti_etl_test.stg_censo_curso
```

**Data copied:** Records from 2018 to 2022

**SQL used to create/populate the staging table:**

```sql
CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl_test.stg_censo_curso` AS
SELECT *
FROM `basedosdados.br_inep_censo_educacao_superior.curso`
WHERE ano BETWEEN 2018 AND 2022;
```

**Validation query for destination:**

```sql
SELECT COUNT(*) AS total_registros
FROM `higher-education-disability.ppgti_etl_test.stg_censo_curso`;
```

**Validation query for source (same filter):**

```sql
SELECT COUNT(*) AS total_registros
FROM `basedosdados.br_inep_censo_educacao_superior.curso`
WHERE ano BETWEEN 2018 AND 2022;
```

The counts from both queries should match after the copy completes successfully.

### Table: ies

**Source table:**
```
basedosdados.br_inep_censo_educacao_superior.ies
```

**Destination table:**
```
higher-education-disability.ppgti_etl_test.stg_censo_ies
```

**Data copied:** Records from 2018 to 2022

**SQL used to create/populate the staging table:**

```sql
CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl_test.stg_censo_ies` AS
SELECT *
FROM `basedosdados.br_inep_censo_educacao_superior.ies`
WHERE ano BETWEEN 2018 AND 2022;
```

**Validation query for destination:**

```sql
SELECT COUNT(*) AS total_registros
FROM `higher-education-disability.ppgti_etl_test.stg_censo_ies`;
```

**Validation query for source (same filter):**

```sql
SELECT COUNT(*) AS total_registros
FROM `basedosdados.br_inep_censo_educacao_superior.ies`
WHERE ano BETWEEN 2018 AND 2022;
```

The counts from both queries should match after the copy completes successfully.

### Table: dicionario

**Source table:**
```
basedosdados.br_inep_censo_educacao_superior.dicionario
```

**Destination table:**
```
higher-education-disability.ppgti_etl_test.stg_censo_dicionario
```

**Data copied:** Dictionary records for tables 'curso' and 'ies'

**SQL used to create/populate the staging table:**

```sql
CREATE OR REPLACE TABLE `higher-education-disability.ppgti_etl_test.stg_censo_dicionario` AS
SELECT *
FROM `basedosdados.br_inep_censo_educacao_superior.dicionario`
WHERE id_tabela IN ('curso', 'ies');
```

**Validation query for destination:**

```sql
SELECT COUNT(*) AS total_registros
FROM `higher-education-disability.ppgti_etl_test.stg_censo_dicionario`;
```

**Validation query for source (same filter):**

```sql
SELECT COUNT(*) AS total_registros
FROM `basedosdados.br_inep_censo_educacao_superior.dicionario`
WHERE id_tabela IN ('curso', 'ies');
```

The counts from both queries should match after the copy completes successfully.

## Safety Note

The public source tables in the `basedosdados` project are **never modified** by the staging copy process.

The `CREATE OR REPLACE TABLE` command only creates or replaces the **destination table** in:

```
higher-education-disability.ppgti_etl_test
```

The source tables are only read in the `FROM` clause. No write, update, or delete operations are performed on the source tables.

## How to Confirm the Copy Worked

After running each staging copy query:

1. Execute the **destination validation query** against the staging table in `higher-education-disability.ppgti_etl_test`
2. Execute the **source validation query** (with the same filter) against the source table in `basedosdados`
3. Compare the `total_registros` counts from both queries

If the counts match, the copy was successful.

**Example comparison:**

| Query | Result |
|-------|--------|
| Destination: `stg_sisu_microdados` | 1,234,567 registros |
| Source: `br_mec_sisu.microdados` (ano 2018-2022) | 1,234,567 registros |
| Status | ✓ Match - Copy successful |
