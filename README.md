# Higher Education Disability ETL

**Complete ETL pipeline** for analyzing the distribution of students with disabilities in Brazilian higher education, integrating Higher Education Census and SISU data from BigQuery into MongoDB.

## Quick Start

For immediate guidance, see **[QUICKSTART.md](QUICKSTART.md)** for installation, configuration, and running the pipeline.

## What's New

This implementation includes a **complete 12-phase ETL pipeline**:

### Phases Implemented 

| Phase | Name | File |
|-------|------|------|
| 1 | Extract BigQuery Staging Data | `src/etl/phase_1_extract.py` |
| 2 | Transform Censo Curso + Censo IES | `src/etl/phase_2_transform_censo.py` |
| 3 | Transform SISU Microdados | `src/etl/phase_3_transform_sisu.py` |
| 4-6 | Join, Build Final Documents & Calculate Metrics | `src/etl/phase_456_join_build_metrics.py` |
| 7 | MongoDB Load | `src/etl/phase_7_mongodb_load.py` |
| 8 | Create Indexes | `src/etl/phase_8_create_indexes.py` |
| 9 | Query Examples | `scripts/mongodb_query_examples.py` |
| 10 | Explain Plans & Performance | `scripts/mongodb_explain_plan.py` |
| 11 | Validation & Test Output | `src/etl/phase_11_validation.py` |
| 12 | Documentation | `docs/ETL_ARCHITECTURE.md` |


 🏗️ Architecture

### Data Flow

```
BigQuery (stg_censo_ies, stg_censo_curso, stg_sisu_microdados)
    ↓
Phase 1: Extract
    ↓
Phase 2: Transform Censo (normalize + join)
    ↓
Phase 3: Transform SISU (aggregate demographics)
    ↓
Phases 4-6: Join, Build, Calculate Metrics
    ↓
Phase 7: MongoDB Load (upsert)
    ↓
Phase 8: Create Indexes
    ↓
MongoDB: gold_course_indicators + sisu_aggregated
```

### MongoDB Collections

**`gold_course_indicators`** (Main analytical collection)
- One document per course per institution per year
- Document ID: `{ano}_{id_ies}_{id_curso}`
- Includes: Census indicators, SISU data (if matched), computed metrics
- 9 indexes for efficient querying

**`sisu_aggregated`** (Optional, for separate SISU analysis)
- SISU data aggregated by course/institution/year
- Demographic breakdowns (sex, age group, municipality)
- Used for $lookup joins with main collection

## 🔒 Privacy & Data Security

This implementation prioritizes academic research while protecting privacy:

### Removed (Direct Identifiers)
- CPF numbers
- Candidate names
- ENEM inscription numbers
- Registration numbers
- Any other personal identifiers

### Kept (Demographic for Analysis)
- Birth date - transformed to age + age group (18-24, 25-29, etc.)
- Sex - normalized (F/M/NAO_INFORMADO)
- Municipality - ID + name + state (aggregated analysis only)

**Rationale:** These enable important research questions about access equity without identifying individuals.

## Data Structure

### Example Gold Course Indicator Document

```javascript
{
  "_id": "2022_634_15002",
  "ano": 2022,
  "uf": "RS",
  "ies": {
    "idIes": "634",
    "nome": "UNIVERSIDADE FEDERAL DE PELOTAS",
    "sigla": "UFPEL",
    "tipoOrganizacaoAcademica": "1",
    "tipoCategoriaAdministrativa": "1"
  },
  "curso": {
    "idCurso": "15002",
    "nome": "Ciência Da Computação",
    "tipoGrauAcademico": "1",
    "tipoModalidadeEnsino": "1",
    "indicadorGratuito": true
  },
  "indicadoresAluno": {
    "vagas": 99,
    "inscritos": 1092,
    "ingressantes": 92,
    "matriculas": 377,
    "concluintes": 32
  },
  "indicadoresDeficiencia": {
    "alunos": 9,
    "ingressantes": 4,
    "matriculas": 8,
    "concluintes": 1
  },
  "metricasCalculadas": {
    "percentualMatriculasPcd": 2.12,
    "taxaConclusaoGeral": 34.78,
    "taxaConclusaoPcd": 25.0,
    "taxaPerdaGeral": 65.22,
    "taxaPerdaPcd": 75.0
  },
  "sisu": {
    "hasMatch": true,
    "inscricoesTotal": 123,
    "inscricoesPcd": 10,
    "aprovadosRegular": 20,
    "aprovadosPcdRegular": 2,
    "demografia": {
      "porSexo": [ ... ],
      "porFaixaEtaria": [ ... ],
      "porMunicipio": [ ... ]
    }
  }
}
```

##  Query Examples

### Find Courses with High PcD Enrollment

```python
db.gold_course_indicators.find({
  "metricasCalculadas.percentualMatriculasPcd": { "$gt": 10 },
  "ano": 2022
})
```

### PcD Enrollments by Region

```python
db.gold_course_indicators.aggregate([
  { "$match": { "ano": 2022 } },
  { "$group": {
      "_id": "$uf",
      "totalPcd": { "$sum": "$indicadoresDeficiencia.matriculas" },
      "totalMatriculas": { "$sum": "$indicadoresAluno.matriculas" }
  }},
  { "$sort": { "totalPcd": -1 } }
])
```

For 11+ complete query examples, see **[scripts/mongodb_query_examples.py](scripts/mongodb_query_examples.py)**

## Running the Pipeline

### Option 1: Full Pipeline (Recommended)

```bash
python main.py
```

Executes all phases (1-8) plus validation in one command.

### Option 2: Phase-Based Execution (For Testing)

```bash
# Extract only
python main.py --mode extract

# Extract through build (no MongoDB)
python main.py --mode build

# Full pipeline
python main.py --mode full
```

### Option 3: Python API

```python
from src.etl.pipeline_orchestrator import ETLPipelineOrchestrator

orchestrator = ETLPipelineOrchestrator()
result = orchestrator.run_full_pipeline()
```

## Analytical Capabilities

### Questions Answered

1. How did PcD enrollments evolve over years?
2. Which regions concentrate most PcD students?
3. Does PcD distribution differ between in-person and distance education?
4. Which administrative categories have highest PcD participation?
5. How do general vs PcD completion rates compare by region?
6. In which UFs is PcD loss rate highest?
7. What is the SISU access funnel for PcD candidates?
8. Is there correlation between SISU demand and Census enrollment?

Plus demographic breakdowns by:
- Sex
- Age group
- Candidate municipality

See **[scripts/mongodb_query_examples.py](scripts/mongodb_query_examples.py)** for complete implementations.

## Performance

### Indexes Created

9 indexes across key fields:
- Simple indexes (ano, uf, id_ies, id_curso, modality, category)
- Array indexes (SISU demographics)
- Compound index for common multi-field queries

### Query Performance

With indexes, typical queries return results in **< 100ms** even on datasets with millions of documents.

Use **[scripts/mongodb_explain_plan.py](scripts/mongodb_explain_plan.py)** to analyze query performance.

## Configuration

### Environment Variables

```env
# Google Cloud
GCP_PROJECT_ID=higher-education-disability
GCP_CREDENTIALS_PATH=credentials.json

# MongoDB  
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=higher_education

# ETL Configuration
ETL_START_YEAR=2018
ETL_END_YEAR=2022
ETL_LIMIT=1000        # Optional: limit rows for testing
```

For complete setup, see **[QUICKSTART.md](QUICKSTART.md)**

## Installation

```bash
# Clone repository
git clone <repo-url>
cd brazil-higher-education-disability-etl

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Verification

Verify installation and check which collections exist:

```bash
python scripts/verify_mongodb.py
```

## Data Preparation Overview

Before running the ETL pipeline, the raw Higher Education Census microdata files must be prepared and loaded into BigQuery.

The current data preparation flow is:

```text
INEP CSV files → Parquet files → Google Cloud Storage → BigQuery → MongoDB
```

The conversion from CSV to Parquet is performed by a local Python script. The upload to Google Cloud Storage is currently a manual step performed through the Google Cloud CLI.

## Preparing INEP Microdata

The Higher Education Census microdata files are originally provided by INEP in CSV format. Before loading them into BigQuery, the files must be converted to Parquet.

Place the original INEP CSV files inside:

```bash
data/raw/
```

Expected files:

```bash
data/raw/microdados_ed_sup_ies_2024.csv
data/raw/microdados_cadastro_cursos_2024.csv
```

Run the conversion script:

```bash
python scripts/convert_to_parquet.py
```

The generated Parquet files will be saved in:

```bash
data/parquet/
```

Expected output:

```bash
data/parquet/microdados_ed_sup_ies_2024.parquet
data/parquet/microdados_cadastro_cursos_2024.parquet
```

## Project Structure

```
src/
  etl/              # All pipeline phases
  clients/          # BigQuery and MongoDB clients
  config/           # Configuration management
  utils/            # Logging and utilities
  
scripts/
  mongodb_query_examples.py    # 11+ query examples
  mongodb_explain_plan.py      # Performance analysis
  verify_mongodb.py            # Connection check
  convert_to_parquet.py        # Data preparation
  
docs/
  ETL_ARCHITECTURE.md          # Detailed architecture
  
QUICKSTART.md                  # Quick start guide
IMPLEMENTATION_SUMMARY.md      # Implementation details
```

## 🤝 Contributing

This is an academic research project. Contributions welcome for:
- New analytical queries
- Performance optimizations
- Documentation improvements
- Bug fixes

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check **[QUICKSTART.md](QUICKSTART.md)** for common issues
3. Run **[scripts/verify_implementation.py](scripts/verify_implementation.py)** to verify installation
4. Check logs in `logs/etl_*.log` for detailed error messages

---

The conversion script requires:

```bash
pandas
pyarrow
```

If needed, install them with:

```bash
python -m pip install pandas pyarrow
```

## Uploading Parquet Files to Google Cloud Storage

After generating the Parquet files, they must be uploaded to Google Cloud Storage.

At this stage of the project, the upload process is manual and performed through the Google Cloud CLI.

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
```

### 2. Select the GCP project

```bash
gcloud config set project YOUR_GCP_PROJECT_ID
```

Confirm the active configuration:

```bash
gcloud config list
```

### 3. Define the bucket and destination path

Replace the bucket name with the bucket used by the project:

```bash
export BUCKET_NAME="your-bucket-name"
export GCS_PATH="microdados/educacao_superior/2024/parquet"
```

The final destination will be:

```bash
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/
```

### 4. Upload the generated Parquet files

```bash
gcloud storage cp data/parquet/*.parquet gs://$BUCKET_NAME/$GCS_PATH/
```

### 5. Validate the uploaded files

```bash
gcloud storage ls gs://$BUCKET_NAME/$GCS_PATH/
```

Expected result:

```bash
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_ed_sup_ies_2024.parquet
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_cadastro_cursos_2024.parquet
```

### Notes

* The Cloud Storage bucket location must be compatible with the BigQuery dataset location.
* The upload step is currently manual and must be executed after generating the Parquet files.
* Future versions of this project may automate the upload process directly from the ETL pipeline.

## Loading Parquet Files into BigQuery

After the files are uploaded to Cloud Storage, they can be loaded into BigQuery as raw tables.

Suggested raw tables:

```text
raw_ies_2024
raw_cursos_2024
```

Suggested source files:

```text
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_ed_sup_ies_2024.parquet
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_cadastro_cursos_2024.parquet
```

These raw BigQuery tables will later be used by the ETL pipeline to transform and load the data into MongoDB.

## Loading Parquet Files from Cloud Storage into BigQuery

After uploading the generated Parquet files to Google Cloud Storage, the files must be loaded into BigQuery as raw tables.

This step is currently performed manually through the Google Cloud CLI.

The flow is:

```text
Local Parquet files → Google Cloud Storage → BigQuery raw tables → MongoDB
